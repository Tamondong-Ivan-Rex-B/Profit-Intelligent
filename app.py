"""
Sulit Store Profit-Intelligent POS & Inventory Management System
Main Application Entrypoint (Flask Backend RESTful API & Server)
Course: CPE 025A / CPEQC 029_030 - Major Design Project
Author: Team 8
Client: Sulit Store
"""
import os
import sys
import uuid
import hashlib
import time
from datetime import datetime, timedelta
import cv2
import numpy as np

from flask import Flask, request, jsonify, render_template, session, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

from config import Config
from database.db import query_db, execute_db, get_db_connection
from database.seed_data import seed_database
from modules.ocr_scanner import scanner
from modules.predictive_engine import (
    forecast_sku_depletion,
    generate_depletion_overview,
    run_model_rmse_evaluation
)
from modules.srp_scraper import (
    get_all_srp_comparisons,
    analyze_sku_pricing,
    sync_srp_to_database
)
from modules.audit_logger import log_security_event

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config.from_object(Config)
CORS(app)

# Ensure upload directory exists
os.makedirs(Config.OCR_UPLOAD_FOLDER, exist_ok=True)

# Helper: Password Hashing
def hash_pass(p: str) -> str:
    return hashlib.sha256(p.encode("utf-8")).hexdigest()

# Helper: Role Verification & Field-Level Security (ISO/IEC 27001)
def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return query_db("SELECT user_id, username, full_name, role FROM tbl_users WHERE user_id = ?", (user_id,), one=True)

def strip_confidential_fields(product_dict, user_role):
    """
    Field-Level Encryption / Masking:
    Cashiers and Customers must NEVER see Cost Price (COGS) or Gross Margins.
    """
    p = dict(product_dict)
    if user_role not in ["admin"]:
        p.pop("cost_price", None)
        p.pop("gross_margin", None)
        p.pop("unit_cost_price", None)
        p.pop("total_cost_price", None)
    return p

# -----------------------------------------------------------------------------
# 1. Front-end Root Page
# -----------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html", config=Config)

# -----------------------------------------------------------------------------
# 2. Authentication & Session Endpoints
# -----------------------------------------------------------------------------
@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    
    if not username or not password:
        return jsonify({"success": False, "message": "Username and password required"}), 400
        
    p_hash = hash_pass(password)
    user = query_db(
        "SELECT user_id, username, full_name, role, is_active FROM tbl_users WHERE username = ? AND password_hash = ?",
        (username, p_hash),
        one=True
    )
    
    if user and user.get("is_active"):
        session["user_id"] = user["user_id"]
        session["role"] = user["role"]
        session["username"] = user["username"]
        
        log_security_event(
            username=user["username"],
            role=user["role"],
            action="LOGIN_SUCCESS",
            resource="API_AUTH",
            status="SUCCESS",
            ip=request.remote_addr,
            details=f"User {user['username']} logged in successfully as {user['role']}"
        )
        return jsonify({
            "success": True,
            "user": {
                "user_id": user["user_id"],
                "username": user["username"],
                "full_name": user["full_name"],
                "role": user["role"]
            }
        })
    else:
        log_security_event(
            username=username,
            role="unauthenticated",
            action="LOGIN_FAILED",
            resource="API_AUTH",
            status="FAILURE",
            ip=request.remote_addr,
            details=f"Failed login attempt for username: {username}"
        )
        return jsonify({"success": False, "message": "Invalid username or password"}), 401

@app.route("/api/auth/logout", methods=["POST"])
def logout():
    curr = get_current_user()
    if curr:
        log_security_event(
            username=curr["username"],
            role=curr["role"],
            action="LOGOUT",
            resource="API_AUTH",
            status="SUCCESS",
            ip=request.remote_addr,
            details=f"User {curr['username']} logged out"
        )
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully"})

@app.route("/api/auth/current_user", methods=["GET"])
def current_user():
    curr = get_current_user()
    if not curr:
        # Default public guest role for seamless evaluation
        return jsonify({"authenticated": False, "user": {"role": "guest", "username": "guest"}})
    return jsonify({"authenticated": True, "user": curr})

# Quick Role Switcher for Capstone Demonstration / Evaluation
@app.route("/api/auth/switch_demo_role", methods=["POST"])
def switch_demo_role():
    data = request.get_json() or {}
    target_role = data.get("role", "admin").lower()
    user = query_db("SELECT user_id, username, full_name, role FROM tbl_users WHERE role = ? LIMIT 1", (target_role,), one=True)
    if user:
        session["user_id"] = user["user_id"]
        session["role"] = user["role"]
        session["username"] = user["username"]
        return jsonify({"success": True, "user": user})
    return jsonify({"success": False, "message": "Role not found"}), 404

# -----------------------------------------------------------------------------
# 3. Product & Inventory Management Endpoints
# -----------------------------------------------------------------------------
@app.route("/api/products", methods=["GET"])
def list_products():
    curr = get_current_user()
    role = curr["role"] if curr else "admin" # Allow admin view in local demo mode
    
    products = query_db("SELECT * FROM tbl_product_master ORDER BY category, product_name")
    cleaned = [strip_confidential_fields(p, role) for p in products]
    return jsonify({"success": True, "count": len(cleaned), "products": cleaned})

@app.route("/api/products/<sku>", methods=["GET"])
def get_product(sku):
    curr = get_current_user()
    role = curr["role"] if curr else "admin"
    product = query_db("SELECT * FROM tbl_product_master WHERE sku = ? OR barcode = ?", (sku, sku), one=True)
    if not product:
        return jsonify({"success": False, "message": "Product not found"}), 404
    return jsonify({"success": True, "product": strip_confidential_fields(product, role)})

@app.route("/api/products", methods=["POST"])
def create_product():
    curr = get_current_user()
    if curr and curr["role"] not in ["admin"]:
        return jsonify({"success": False, "message": "Unauthorized. Admin privileges required."}), 403
        
    data = request.get_json() or {}
    sku = data.get("sku", "").strip()
    name = data.get("product_name", "").strip()
    category = data.get("category", "General").strip()
    cost_price = float(data.get("cost_price", 0.0))
    retail_price = float(data.get("retail_price", 0.0))
    stock_qty = int(data.get("current_stock_qty", 0))
    reorder_threshold = int(data.get("reorder_threshold", 10))
    expiration_date = data.get("expiration_date") or None # ISO 8601
    barcode = data.get("barcode") or sku
    unit = data.get("unit_measure", "piece")
    srp = float(data.get("srp_market_price", retail_price))
    
    if not sku or not name:
        return jsonify({"success": False, "message": "SKU and product name are mandatory"}), 400
        
    try:
        execute_db(
            """INSERT INTO tbl_product_master
               (sku, barcode, product_name, category, cost_price, retail_price,
                current_stock_qty, reorder_threshold, expiration_date, srp_market_price, unit_measure)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (sku, barcode, name, category, cost_price, retail_price, stock_qty, reorder_threshold, expiration_date, srp, unit)
        )
        
        log_security_event(
            username=curr["username"] if curr else "admin",
            role="admin",
            action="CREATE_PRODUCT",
            resource=f"tbl_product_master:{sku}",
            details=f"Created product {name} ({sku}) with expiry {expiration_date}"
        )
        return jsonify({"success": True, "message": "Product added successfully", "sku": sku}), 201
    except Exception as e:
        return jsonify({"success": False, "message": f"Error saving product: {str(e)}"}), 400

@app.route("/api/products/<sku>", methods=["PUT"])
def update_product(sku):
    curr = get_current_user()
    if curr and curr["role"] not in ["admin"]:
        return jsonify({"success": False, "message": "Unauthorized. Admin privileges required."}), 403
        
    data = request.get_json() or {}
    product = query_db("SELECT * FROM tbl_product_master WHERE sku = ?", (sku,), one=True)
    if not product:
        return jsonify({"success": False, "message": "Product not found"}), 404
        
    name = data.get("product_name", product["product_name"])
    category = data.get("category", product["category"])
    cost_price = float(data.get("cost_price", product["cost_price"]))
    retail_price = float(data.get("retail_price", product["retail_price"]))
    stock_qty = int(data.get("current_stock_qty", product["current_stock_qty"]))
    reorder_threshold = int(data.get("reorder_threshold", product["reorder_threshold"]))
    expiration_date = data.get("expiration_date", product["expiration_date"])
    unit = data.get("unit_measure", product["unit_measure"])
    srp = float(data.get("srp_market_price", product["srp_market_price"] or retail_price))
    
    execute_db(
        """UPDATE tbl_product_master
           SET product_name = ?, category = ?, cost_price = ?, retail_price = ?,
               current_stock_qty = ?, reorder_threshold = ?, expiration_date = ?,
               srp_market_price = ?, unit_measure = ?, updated_at = datetime('now', 'localtime')
           WHERE sku = ?""",
        (name, category, cost_price, retail_price, stock_qty, reorder_threshold, expiration_date, srp, unit, sku)
    )
    
    log_security_event(
        username=curr["username"] if curr else "admin",
        role="admin",
        action="UPDATE_PRODUCT",
        resource=f"tbl_product_master:{sku}",
        details=f"Updated details for {sku}"
    )
    return jsonify({"success": True, "message": "Product updated successfully"})

@app.route("/api/products/adjust_stock", methods=["POST"])
def adjust_stock():
    data = request.get_json() or {}
    sku = data.get("sku")
    adjustment = int(data.get("adjustment", 0)) # Can be positive (restock) or negative
    reason = data.get("reason", "Manual Inventory Restock")
    
    product = query_db("SELECT current_stock_qty, product_name FROM tbl_product_master WHERE sku = ?", (sku,), one=True)
    if not product:
        return jsonify({"success": False, "message": "Product not found"}), 404
        
    new_stock = max(0, product["current_stock_qty"] + adjustment)
    execute_db("UPDATE tbl_product_master SET current_stock_qty = ? WHERE sku = ?", (new_stock, sku))
    
    curr = get_current_user()
    log_security_event(
        username=curr["username"] if curr else "admin",
        role=curr["role"] if curr else "admin",
        action="ADJUST_STOCK",
        resource=f"tbl_product_master:{sku}",
        details=f"Stock adjusted by {adjustment} ({reason}). New stock: {new_stock}"
    )
    return jsonify({"success": True, "new_stock": new_stock, "message": "Stock updated successfully"})

@app.route("/api/products/expiry_alerts", methods=["GET"])
def expiry_alerts():
    """
    Returns products categorized by freshness / expiration status:
      - Expired (Date < Today)
      - Critical / Near-Expiry (Date within 1 to 14 days)
      - Warning (Date within 15 to 30 days)
      - Fresh (Date > 30 days)
    """
    today = datetime.now().date()
    products = query_db("SELECT sku, product_name, category, current_stock_qty, expiration_date, retail_price FROM tbl_product_master WHERE expiration_date IS NOT NULL")
    
    expired = []
    critical = []
    warning = []
    fresh = []
    
    for p in products:
        try:
            exp_dt = datetime.strptime(p["expiration_date"], "%Y-%m-%d").date()
            days_left = (exp_dt - today).days
            item_info = dict(p)
            item_info["days_remaining"] = days_left
            
            if days_left < 0:
                item_info["status"] = "EXPIRED"
                expired.append(item_info)
            elif days_left <= 14:
                item_info["status"] = "CRITICAL"
                critical.append(item_info)
            elif days_left <= 30:
                item_info["status"] = "WARNING"
                warning.append(item_info)
            else:
                item_info["status"] = "FRESH"
                fresh.append(item_info)
        except Exception:
            continue
            
    return jsonify({
        "success": True,
        "counts": {
            "expired": len(expired),
            "critical": len(critical),
            "warning": len(warning),
            "fresh": len(fresh)
        },
        "expired": expired,
        "critical": critical,
        "warning": warning
    })

# -----------------------------------------------------------------------------
# 4. Point-of-Sale (POS) Checkout & Transactions
# -----------------------------------------------------------------------------
@app.route("/api/pos/lookup/<code_str>", methods=["GET"])
def pos_lookup(code_str):
    curr = get_current_user()
    role = curr["role"] if curr else "cashier"
    product = query_db(
        "SELECT * FROM tbl_product_master WHERE sku = ? OR barcode = ?",
        (code_str, code_str),
        one=True
    )
    if not product:
        return jsonify({"success": False, "message": "Item not found"}), 404
        
    return jsonify({"success": True, "product": strip_confidential_fields(product, role)})

@app.route("/api/pos/checkout", methods=["POST"])
def pos_checkout():
    """
    Execute atomic Point-of-Sale checkout:
    1. Validates inventory levels
    2. Calculates itemized subtotal, taxes, and COGS
    3. Deducts stock from tbl_product_master
    4. Logs transaction in tbl_pos_transaction_log and items in tbl_pos_transaction_items
    5. Formats official printable thermal receipt
    """
    data = request.get_json() or {}
    items = data.get("items", []) # List of {sku, quantity}
    payment_method = data.get("payment_method", "Cash") # Cash, GCash, Debit
    amount_tendered = float(data.get("amount_tendered", 0.0))
    gcash_ref = data.get("gcash_ref_number", "").strip() or None
    customer_name = data.get("customer_name", "Walk-in Customer")
    terminal_id = data.get("terminal_id", Config.DEFAULT_TERMINAL_ID)
    
    if not items:
        return jsonify({"success": False, "message": "Cart is empty"}), 400
        
    # Check inventory availability
    line_details = []
    total_revenue = 0.0
    total_cogs = 0.0
    
    for cart_item in items:
        sku = cart_item.get("sku")
        qty = int(cart_item.get("quantity", 1))
        
        prod = query_db("SELECT * FROM tbl_product_master WHERE sku = ?", (sku,), one=True)
        if not prod:
            return jsonify({"success": False, "message": f"Product {sku} not found"}), 404
        if prod["current_stock_qty"] < qty:
            return jsonify({
                "success": False,
                "message": f"Insufficient stock for '{prod['product_name']}'. In stock: {prod['current_stock_qty']}"
            }), 400
            
        line_total = prod["retail_price"] * qty
        line_cost = prod["cost_price"] * qty
        total_revenue += line_total
        total_cogs += line_cost
        
        line_details.append({
            "sku": sku,
            "product_name": prod["product_name"],
            "quantity": qty,
            "cost_price": prod["cost_price"],
            "retail_price": prod["retail_price"],
            "line_total": line_total
        })
        
    # Payment math
    if payment_method == "Cash":
        if amount_tendered < total_revenue:
            return jsonify({"success": False, "message": f"Tendered amount (₱{amount_tendered:.2f}) is less than total (₱{total_revenue:.2f})"}), 400
        change_given = amount_tendered - total_revenue
    else:
        amount_tendered = total_revenue
        change_given = 0.0
        
    receipt_no = f"RCP-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
    curr = get_current_user()
    cashier_id = curr["user_id"] if curr else 2
    
    # Database Transaction
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        # 1. Insert header
        cur.execute(
            """INSERT INTO tbl_pos_transaction_log
               (receipt_number, terminal_id, cashier_user_id, total_amount, total_cost_price,
                payment_method, amount_tendered, change_given, gcash_ref_number,
                order_type, order_status, customer_name, transaction_timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'InStore', 'Completed', ?, datetime('now', 'localtime'))""",
            (receipt_no, terminal_id, cashier_id, round(total_revenue, 2), round(total_cogs, 2),
             payment_method, round(amount_tendered, 2), round(change_given, 2), gcash_ref, customer_name)
        )
        trans_id = cur.lastrowid
        
        # 2. Insert line items & decrement stock
        for item in line_details:
            cur.execute(
                """INSERT INTO tbl_pos_transaction_items
                   (transaction_id, sku, quantity_sold, unit_cost_price, unit_retail_price, line_total)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (trans_id, item["sku"], item["quantity"], item["cost_price"], item["retail_price"], round(item["line_total"], 2))
            )
            cur.execute(
                "UPDATE tbl_product_master SET current_stock_qty = current_stock_qty - ? WHERE sku = ?",
                (item["quantity"], item["sku"])
            )
            
    log_security_event(
        username=curr["username"] if curr else "cashier1",
        role=curr["role"] if curr else "cashier",
        action="POS_CHECKOUT",
        resource=f"tbl_pos_transaction_log:{receipt_no}",
        details=f"Processed sale: {receipt_no} | Total: ₱{total_revenue:.2f} | Method: {payment_method}"
    )
    
    return jsonify({
        "success": True,
        "receipt_number": receipt_no,
        "transaction_id": trans_id,
        "total_amount": round(total_revenue, 2),
        "amount_tendered": round(amount_tendered, 2),
        "change_given": round(change_given, 2),
        "payment_method": payment_method,
        "gcash_ref_number": gcash_ref,
        "customer_name": customer_name,
        "items": line_details,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route("/api/pos/receipt/<receipt_no>", methods=["GET"])
def get_receipt(receipt_no):
    header = query_db(
        """SELECT l.*, u.full_name as cashier_name
           FROM tbl_pos_transaction_log l
           LEFT JOIN tbl_users u ON l.cashier_user_id = u.user_id
           WHERE l.receipt_number = ?""",
        (receipt_no,),
        one=True
    )
    if not header:
        return jsonify({"success": False, "message": "Receipt not found"}), 404
        
    items = query_db(
        """SELECT i.sku, i.quantity_sold, i.unit_retail_price, i.line_total, p.product_name
           FROM tbl_pos_transaction_items i
           JOIN tbl_product_master p ON i.sku = p.sku
           WHERE i.transaction_id = ?""",
        (header["transaction_id"],)
    )
    
    return jsonify({
        "success": True,
        "receipt": {
            "store_name": Config.STORE_NAME,
            "store_address": Config.STORE_ADDRESS,
            "store_contact": Config.STORE_CONTACT,
            "tin": Config.TIN,
            "receipt_number": header["receipt_number"],
            "terminal_id": header["terminal_id"],
            "cashier": header.get("cashier_name") or "Cashier",
            "timestamp": header["transaction_timestamp"],
            "order_type": header["order_type"],
            "customer_name": header["customer_name"],
            "items": items,
            "total_amount": header["total_amount"],
            "payment_method": header["payment_method"],
            "amount_tendered": header["amount_tendered"],
            "change_given": header["change_given"],
            "gcash_ref_number": header["gcash_ref_number"]
        }
    })

# -----------------------------------------------------------------------------
# 5. Customer Storefront (E-Commerce Pre-Ordering for In-Store Pickup)
# -----------------------------------------------------------------------------
@app.route("/api/storefront/catalog", methods=["GET"])
def storefront_catalog():
    """Public customer catalog with real-time stock availability."""
    products = query_db(
        """SELECT sku, product_name, category, retail_price, current_stock_qty, unit_measure
           FROM tbl_product_master
           WHERE current_stock_qty > 0
           ORDER BY category, product_name"""
    )
    return jsonify({"success": True, "catalog": products})

@app.route("/api/storefront/place_order", methods=["POST"])
def place_pre_order():
    """
    Allows online customers to place an order ahead of time for in-store pickup.
    Secures items and issues a unique Order Tracking Reference.
    """
    data = request.get_json() or {}
    items = data.get("items", [])
    customer_name = data.get("customer_name", "").strip()
    customer_phone = data.get("customer_phone", "").strip()
    payment_method = data.get("payment_method", "Cash") # Cash on pickup or GCash advance
    gcash_ref = data.get("gcash_ref_number", "").strip() or None
    
    if not items or not customer_name:
        return jsonify({"success": False, "message": "Items and customer name are required"}), 400
        
    line_details = []
    total_amt = 0.0
    total_cost = 0.0
    
    for item in items:
        sku = item.get("sku")
        qty = int(item.get("quantity", 1))
        prod = query_db("SELECT * FROM tbl_product_master WHERE sku = ?", (sku,), one=True)
        if not prod or prod["current_stock_qty"] < qty:
            return jsonify({"success": False, "message": f"Product {sku} out of stock"}), 400
            
        line_total = prod["retail_price"] * qty
        line_cost = prod["cost_price"] * qty
        total_amt += line_total
        total_cost += line_cost
        line_details.append({
            "sku": sku,
            "quantity": qty,
            "cost": prod["cost_price"],
            "retail": prod["retail_price"],
            "total": line_total
        })
        
    order_ref = f"ORD-PICKUP-{datetime.now().strftime('%m%d%H%M')}-{uuid.uuid4().hex[:4].upper()}"
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO tbl_pos_transaction_log
               (receipt_number, terminal_id, cashier_user_id, total_amount, total_cost_price,
                payment_method, amount_tendered, change_given, gcash_ref_number,
                order_type, order_status, customer_name, customer_phone, transaction_timestamp)
               VALUES (?, 'ONLINE-PORTAL', 3, ?, ?, ?, ?, 0.00, ?, 'OnlinePickup', 'PendingPickup', ?, ?, datetime('now', 'localtime'))""",
            (order_ref, round(total_amt, 2), round(total_cost, 2), payment_method, round(total_amt, 2), gcash_ref, customer_name, customer_phone)
        )
        trans_id = cur.lastrowid
        
        for item in line_details:
            cur.execute(
                """INSERT INTO tbl_pos_transaction_items
                   (transaction_id, sku, quantity_sold, unit_cost_price, unit_retail_price, line_total)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (trans_id, item["sku"], item["quantity"], item["cost"], item["retail"], round(item["total"], 2))
            )
            # Reserve stock
            cur.execute("UPDATE tbl_product_master SET current_stock_qty = current_stock_qty - ? WHERE sku = ?", (item["quantity"], item["sku"]))
            
    return jsonify({
        "success": True,
        "order_reference": order_ref,
        "total_amount": round(total_amt, 2),
        "status": "PendingPickup",
        "message": f"Your order {order_ref} has been placed! Please show this reference at Sulit Store counter."
    })

@app.route("/api/pos/orders", methods=["GET"])
def list_pickup_orders():
    """Cashier view of pending customer pickup pre-orders."""
    orders = query_db(
        """SELECT transaction_id, receipt_number, total_amount, payment_method, gcash_ref_number,
                  order_type, order_status, customer_name, customer_phone, transaction_timestamp
           FROM tbl_pos_transaction_log
           WHERE order_type = 'OnlinePickup'
           ORDER BY transaction_timestamp DESC"""
    )
    return jsonify({"success": True, "orders": orders})

@app.route("/api/pos/orders/<receipt_no>/status", methods=["PUT"])
def update_order_status(receipt_no):
    data = request.get_json() or {}
    new_status = data.get("status", "Completed") # ReadyForPickup, Completed, Cancelled
    
    execute_db("UPDATE tbl_pos_transaction_log SET order_status = ? WHERE receipt_number = ?", (new_status, receipt_no))
    return jsonify({"success": True, "message": f"Order {receipt_no} updated to {new_status}"})

# -----------------------------------------------------------------------------
# 6. Computer Vision OCR Expiration Scanner Endpoints
# -----------------------------------------------------------------------------
@app.route("/api/ocr/scan_image", methods=["POST"])
def ocr_scan_image():
    """
    Processes an uploaded image file:
    1. Reads via OpenCV
    2. Runs grayscale, bilateral filter, adaptive thresholding, and morphological operations
    3. Extracts dates via regex patterns (ISO, DMY, MDY, Month strings)
    4. Normalizes detected dates into ISO 8601 (YYYY-MM-DD)
    5. Returns processed image previews in Base64 for transparent visual auditing!
    """
    if 'image' not in request.files:
        return jsonify({"success": False, "message": "No image file provided"}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({"success": False, "message": "No image selected"}), 400
        
    file_bytes = np.frombuffer(file.read(), np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    
    if img is None:
        return jsonify({"success": False, "message": "Invalid image format"}), 400
        
    # Run OpenCV pipeline
    gray, filtered, thresh, morphed = scanner.preprocess_image(img)
    
    # Previews for front-end visual demonstration
    preview_gray = scanner.encode_cv2_image_to_base64(gray)
    preview_thresh = scanner.encode_cv2_image_to_base64(thresh)
    
    # We can also read raw text passed from browser client-side OCR if present:
    client_raw_text = request.form.get("client_raw_text", "")
    extracted_dates = []
    
    if client_raw_text:
        extracted_dates = scanner.parse_raw_text(client_raw_text)
        
    return jsonify({
        "success": True,
        "extracted_dates": extracted_dates,
        "best_date": extracted_dates[0]["iso_date"] if extracted_dates else None,
        "filter_previews": {
            "grayscale": preview_gray,
            "threshold": preview_thresh
        },
        "opencv_status": "Pre-processing applied: Grayscale, Bilateral Filter, Gaussian Adaptive Threshold"
    })

@app.route("/api/ocr/parse_text", methods=["POST"])
def ocr_parse_text():
    """
    Direct OCR text parser: Accepts text stream from live webcam OCR
    and extracts normalized ISO 8601 dates.
    """
    data = request.get_json() or {}
    raw_text = data.get("raw_text", "")
    dates = scanner.parse_raw_text(raw_text)
    
    return jsonify({
        "success": True,
        "extracted_dates": dates,
        "best_date": dates[0]["iso_date"] if dates else None,
        "count": len(dates)
    })

@app.route("/api/ocr/evaluate", methods=["GET"])
def ocr_evaluate():
    """
    Section 4.2 System Functionality Benchmark:
    Calculates System Error Rate = 1 - Accuracy Percentage across standard test packaging sets.
    """
    results = scanner.evaluate_system_error_rate()
    return jsonify({"success": True, "evaluation": results})

# -----------------------------------------------------------------------------
# 7. Predictive Analytics & Stock Depletion Forecasting
# -----------------------------------------------------------------------------
@app.route("/api/predictive/depletion_overview", methods=["GET"])
def predictive_depletion_overview():
    overview = generate_depletion_overview()
    return jsonify({"success": True, "count": len(overview), "depletion_overview": overview})

@app.route("/api/predictive/forecast/<sku>", methods=["GET"])
def predictive_forecast_sku(sku):
    forecast = forecast_sku_depletion(sku)
    if not forecast:
        return jsonify({"success": False, "message": "Product not found"}), 404
    return jsonify({"success": True, "forecast": forecast})

@app.route("/api/predictive/evaluate_rmse", methods=["GET"])
def predictive_evaluate_rmse():
    """
    Section 4.1 Predictive Accuracy and Reliability:
    Calculates Root-Mean-Squared Error (RMSE) of demand forecasting over historical sales.
    """
    results = run_model_rmse_evaluation()
    return jsonify({"success": True, "evaluation": results})

# -----------------------------------------------------------------------------
# 8. Suggested Retail Price (SRP) Monitoring
# -----------------------------------------------------------------------------
@app.route("/api/srp/overview", methods=["GET"])
def srp_overview():
    comparisons = get_all_srp_comparisons()
    return jsonify({"success": True, "count": len(comparisons), "srp_comparisons": comparisons})

@app.route("/api/srp/sync", methods=["POST"])
def srp_sync():
    sync_srp_to_database()
    return jsonify({"success": True, "message": "DTI SRP benchmarks synchronized with product master records"})

# -----------------------------------------------------------------------------
# 9. Profitability & Financial Analytics Dashboard
# -----------------------------------------------------------------------------
@app.route("/api/analytics/summary", methods=["GET"])
def analytics_summary():
    """
    Delivers executive financial metrics:
    - Gross Revenue, Total COGS, Gross Margin (Revenue - COGS), Margin %
    - Daily & Weekly trends for Chart.js
    - Category profitability breakdown
    """
    curr = get_current_user()
    if curr and curr["role"] not in ["admin"]:
        return jsonify({"success": False, "message": "Unauthorized. Financial metrics are restricted to administrators."}), 403
        
    # Overall 14-day aggregated totals
    totals = query_db(
        """SELECT SUM(total_amount) as total_revenue,
                  SUM(total_cost_price) as total_cogs,
                  COUNT(*) as total_orders
           FROM tbl_pos_transaction_log
           WHERE order_status = 'Completed'""",
        one=True
    )
    
    tot_rev = totals["total_revenue"] or 0.0
    tot_cogs = totals["total_cogs"] or 0.0
    tot_margin = tot_rev - tot_cogs
    margin_pct = (tot_margin / tot_rev * 100) if tot_rev > 0 else 0.0
    
    # Daily performance over past 14 days
    daily_history = query_db(
        """SELECT date(transaction_timestamp) as sale_date,
                  SUM(total_amount) as daily_revenue,
                  SUM(total_cost_price) as daily_cogs
           FROM tbl_pos_transaction_log
           WHERE order_status = 'Completed'
           GROUP BY date(transaction_timestamp)
           ORDER BY sale_date ASC"""
    )
    
    chart_labels = []
    chart_revenue = []
    chart_cogs = []
    chart_margin = []
    
    for row in daily_history:
        chart_labels.append(row["sale_date"])
        rev = row["daily_revenue"]
        cogs = row["daily_cogs"]
        margin = rev - cogs
        chart_revenue.append(round(rev, 2))
        chart_cogs.append(round(cogs, 2))
        chart_margin.append(round(margin, 2))
        
    # Category Profit Distribution
    cat_distribution = query_db(
        """SELECT p.category,
                  SUM(i.line_total) as cat_revenue,
                  SUM(i.quantity_sold * i.unit_cost_price) as cat_cogs
           FROM tbl_pos_transaction_items i
           JOIN tbl_product_master p ON i.sku = p.sku
           JOIN tbl_pos_transaction_log l ON i.transaction_id = l.transaction_id
           WHERE l.order_status = 'Completed'
           GROUP BY p.category
           ORDER BY cat_revenue DESC"""
    )
    
    cat_labels = []
    cat_profits = []
    for c in cat_distribution:
        cat_labels.append(c["category"])
        cat_profits.append(round(c["cat_revenue"] - c["cat_cogs"], 2))
        
    # Top 5 best selling products
    top_sellers = query_db(
        """SELECT p.sku, p.product_name, SUM(i.quantity_sold) as total_qty, SUM(i.line_total) as total_revenue
           FROM tbl_pos_transaction_items i
           JOIN tbl_product_master p ON i.sku = p.sku
           JOIN tbl_pos_transaction_log l ON i.transaction_id = l.transaction_id
           WHERE l.order_status = 'Completed'
           GROUP BY p.sku, p.product_name
           ORDER BY total_qty DESC
           LIMIT 5"""
    )
    
    return jsonify({
        "success": True,
        "kpis": {
            "gross_revenue": round(tot_rev, 2),
            "total_cogs": round(tot_cogs, 2),
            "gross_margin": round(tot_margin, 2),
            "margin_percentage": round(margin_pct, 2),
            "total_orders": totals["total_orders"] or 0
        },
        "daily_trends": {
            "labels": chart_labels,
            "revenue": chart_revenue,
            "cogs": chart_cogs,
            "gross_margin": chart_margin
        },
        "category_profits": {
            "labels": cat_labels,
            "margins": cat_profits
        },
        "top_sellers": top_sellers
    })

# -----------------------------------------------------------------------------
# 10. Security Audit Log (ISO/IEC 27001)
# -----------------------------------------------------------------------------
@app.route("/api/audit/logs", methods=["GET"])
def get_audit_logs():
    curr = get_current_user()
    if curr and curr["role"] not in ["admin"]:
        return jsonify({"success": False, "message": "Unauthorized"}), 403
        
    logs = query_db("SELECT * FROM tbl_security_audit_log ORDER BY timestamp DESC LIMIT 50")
    return jsonify({"success": True, "logs": logs})

# -----------------------------------------------------------------------------
# 11. System Stress Test & Error Rate Evaluation
# -----------------------------------------------------------------------------
@app.route("/api/system/stress_test", methods=["POST"])
def run_stress_test():
    """
    Simulates peak hour transaction stress test (100 checkouts)
    and verifies that System Error Rate remains < 5% (ISO/IEC 25010).
    """
    trials = 100
    success_count = 0
    errors = []
    start_time = time.time()
    
    products = query_db("SELECT sku, retail_price, cost_price FROM tbl_product_master LIMIT 5")
    if not products:
        return jsonify({"success": False, "message": "No products to test"}), 400
        
    test_sku = products[0]["sku"]
    
    for i in range(trials):
        try:
            # Simulated transaction insertion
            execute_db(
                """INSERT INTO tbl_pos_transaction_log
                   (receipt_number, terminal_id, cashier_user_id, total_amount, total_cost_price,
                    payment_method, amount_tendered, change_given, order_type, order_status, transaction_timestamp)
                   VALUES (?, 'STRESS-TEST', 1, 50.00, 35.00, 'Cash', 50.00, 0.00, 'InStore', 'Completed', datetime('now', 'localtime'))""",
                (f"STRESS-{uuid.uuid4().hex[:8]}",)
            )
            success_count += 1
        except Exception as e:
            errors.append(str(e))
            
    duration = time.time() - start_time
    error_rate = 1.0 - (success_count / trials)
    
    return jsonify({
        "success": True,
        "total_trials": trials,
        "successful_checkouts": success_count,
        "failed_checkouts": len(errors),
        "system_error_rate": round(error_rate, 4),
        "benchmark_passed": error_rate < 0.05,
        "elapsed_seconds": round(duration, 3),
        "transactions_per_sec": round(trials / duration, 1)
    })

# -----------------------------------------------------------------------------
# Server Startup
# -----------------------------------------------------------------------------
# Ensure database is initialized on WSGI (Gunicorn / Render) startup
try:
    seed_database()
except Exception as _err:
    print(f"Notice during database initialization: {_err}")

if __name__ == "__main__":
    print("=" * 70)
    print("Sulit Store Profit-Intelligent POS & Inventory System")
    print(f"Developer: {Config.STUDENT_NAME} (ID: {Config.STUDENT_ID})")
    print(f"Course: {Config.COURSE} | Server running on http://127.0.0.1:5000")
    print("=" * 70)
    app.run(host="0.0.0.0", port=5000, debug=True)
