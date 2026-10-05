"""
Seed data generator for Sulit Store POS & Inventory Management System.
Generates realistic retail inventory, users, and historical transactions
to immediately demonstrate predictive analytics, RMSE, and profit intelligence.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import hashlib
from datetime import datetime, timedelta
import random
from database.db import get_db_connection, init_db, query_db, execute_db

def hash_password(password: str) -> str:
    """Generate SHA-256 hash for secure user credentials."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def seed_database():
    """Populate database with default users, products, and historical sales."""
    init_db()
    
    # Check if users already exist
    existing_users = query_db("SELECT COUNT(*) as count FROM tbl_users")
    if existing_users and existing_users[0]['count'] > 0:
        return {"status": "already_seeded", "message": "Database already contains seed data."}

    # 1. Seed Users (RBAC)
    users = [
        ("admin", hash_password("admin123"), "Store Manager", "admin"),
        ("cashier1", hash_password("cashier123"), "Maria Santos (Cashier)", "cashier"),
        ("customer1", hash_password("cust123"), "Juan Dela Cruz (Customer)", "customer")
    ]
    for username, p_hash, full_name, role in users:
        execute_db(
            "INSERT INTO tbl_users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
            (username, p_hash, full_name, role)
        )
    
    # 2. Seed Products (Retail Inventory for Sulit Store)
    # Expiration dates relative to current date for realistic testing:
    today = datetime.now().date()
    
    products = [
        # (sku, barcode, name, category, cost_price, retail_price, stock, reorder, days_to_expire, srp, unit)
        ("SKU-CAN-001", "4800016644021", "Argentina Corned Beef 175g", "Canned Goods", 32.50, 42.00, 48, 15, 240, 41.50, "can"),
        ("SKU-CAN-002", "4800016644038", "Century Tuna Flakes in Oil 155g", "Canned Goods", 34.00, 45.00, 32, 12, 180, 44.50, "can"),
        ("SKU-CAN-003", "4800016644045", "555 Sardines in Tomato Sauce 155g", "Canned Goods", 19.50, 26.00, 60, 20, 300, 25.00, "can"),
        ("SKU-NOO-001", "4800016111011", "Lucky Me! Pancit Canton Original 80g", "Instant Noodles", 11.20, 16.00, 150, 30, 90, 15.50, "pouch"),
        ("SKU-NOO-002", "4800016111028", "Lucky Me! Pancit Canton Chilimansi 80g", "Instant Noodles", 11.20, 16.00, 120, 30, 75, 15.50, "pouch"),
        ("SKU-NOO-003", "4800016111035", "Nissin Cup Noodles Seafood 40g", "Instant Noodles", 24.50, 32.00, 18, 15, 45, 31.00, "cup"),
        ("SKU-COF-001", "4800016222019", "Kopiko Blanca 3-in-1 Coffee 30g", "Beverages", 8.80, 14.00, 85, 25, 120, 13.50, "sachet"),
        ("SKU-COF-002", "4800016222026", "Nescafe Classic Stick 2g", "Beverages", 3.20, 6.00, 200, 40, 365, 5.50, "sachet"),
        ("SKU-COF-003", "4800016222033", "Great Taste White Twin Pack 50g", "Beverages", 14.50, 22.00, 70, 20, 110, 21.00, "twin-pack"),
        ("SKU-DRY-001", "4800016333017", "Bear Brand Fortified Powdered Milk 33g", "Dairy", 10.50, 17.00, 95, 25, 150, 16.50, "sachet"),
        ("SKU-DRY-002", "4800016333024", "Alaska Evaporated Milk 370ml", "Dairy", 28.00, 38.00, 25, 10, 85, 37.00, "can"),
        ("SKU-SNK-001", "4800016444015", "SkyFlakes Crackers 25g (Pack of 10)", "Snacks", 55.00, 75.00, 40, 15, 60, 73.00, "pack"),
        ("SKU-SNK-002", "4800016444022", "Piattos Cheese Flavored Potato Chips 85g", "Snacks", 28.50, 38.00, 35, 12, 50, 37.50, "bag"),
        ("SKU-SNK-003", "4800016444039", "Oishi Prawn Crackers 60g", "Snacks", 17.00, 24.00, 28, 10, 40, 23.50, "bag"),
        ("SKU-CND-001", "4800016555013", "Datu Puti Vinegar 350ml", "Condiments", 15.00, 22.00, 42, 10, 365, 21.00, "bottle"),
        ("SKU-CND-002", "4800016555020", "Datu Puti Soy Sauce 350ml", "Condiments", 16.50, 24.00, 38, 10, 365, 23.00, "bottle"),
        ("SKU-BEV-001", "4800016777011", "San Miguel Pale Pilsen 330ml Can", "Liquor & Beer", 42.00, 58.00, 48, 15, 180, 56.00, "can"),
        ("SKU-BEV-002", "4800016777028", "Red Horse Extra Strong Beer 500ml", "Liquor & Beer", 52.00, 72.00, 36, 12, 180, 70.00, "bottle"),
        # Near-expiry items for testing warning badges & computer vision OCR
        ("SKU-DRY-EXP", "4800016999019", "Magnolia Fresh Milk 1L", "Dairy", 85.00, 115.00, 8, 10, 12, 112.00, "carton"), # Expiring in 12 days!
        ("SKU-BKR-EXP", "4800016999026", "Gardenia Classic White Bread 600g", "Bakery", 62.00, 82.00, 6, 8, 4, 80.00, "loaf"), # Expiring in 4 days!
        ("SKU-PAS-EXP", "4800016999033", "Chiz Boy Spread 220g", "Dairy", 42.00, 60.00, 5, 6, -3, 58.00, "jar") # Expired 3 days ago!
    ]
    
    for sku, barcode, name, category, cost, retail, stock, reorder, days_exp, srp, unit in products:
        exp_date = (today + timedelta(days=days_exp)).isoformat()
        execute_db(
            """INSERT INTO tbl_product_master 
               (sku, barcode, product_name, category, cost_price, retail_price, 
                current_stock_qty, reorder_threshold, expiration_date, srp_market_price, unit_measure)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (sku, barcode, name, category, cost, retail, stock, reorder, exp_date, srp, unit)
        )
    
    # 3. Seed Realistic Historical Transactions for Past 14 Days
    # This guarantees the predictive stock forecasting engine and Chart.js have rich data
    random.seed(2412038) # Seeded for reproducibility!
    
    fast_skus = ["SKU-NOO-001", "SKU-NOO-002", "SKU-COF-001", "SKU-COF-003", "SKU-CAN-001", "SKU-CAN-002", "SKU-SNK-001"]
    all_products = query_db("SELECT sku, cost_price, retail_price FROM tbl_product_master WHERE current_stock_qty > 0")
    prod_lookup = {p['sku']: p for p in all_products}
    
    receipt_idx = 1000
    for day_offset in range(14, 0, -1):
        trans_date = datetime.now() - timedelta(days=day_offset)
        # 6 to 12 transactions per day
        num_transactions = random.randint(7, 12)
        daily_revenue = 0.0
        daily_cogs = 0.0
        
        for _ in range(num_transactions):
            receipt_idx += 1
            receipt_no = f"RCP-{trans_date.strftime('%Y%m%d')}-{receipt_idx:04d}"
            payment_method = random.choice(["Cash", "GCash", "Cash", "GCash", "Debit"])
            gcash_ref = f"GC-{random.randint(10000000, 99999999)}" if payment_method == "GCash" else None
            
            # Select 1 to 4 items in this cart
            num_items = random.randint(1, 4)
            chosen_skus = random.sample(list(prod_lookup.keys()), num_items)
            
            total_amt = 0.0
            total_cost = 0.0
            cart_items = []
            
            for sku in chosen_skus:
                prod = prod_lookup[sku]
                # Fast moving items sell more
                qty = random.randint(2, 6) if sku in fast_skus else random.randint(1, 3)
                line_total = prod['retail_price'] * qty
                line_cost = prod['cost_price'] * qty
                total_amt += line_total
                total_cost += line_cost
                cart_items.append((sku, qty, prod['cost_price'], prod['retail_price'], line_total))
            
            tendered = total_amt if payment_method != "Cash" else float(int(total_amt / 50 + 1) * 50)
            change = tendered - total_amt if payment_method == "Cash" else 0.0
            
            t_hour = random.randint(8, 20)
            t_min = random.randint(0, 59)
            t_time = trans_date.replace(hour=t_hour, minute=t_min).strftime("%Y-%m-%d %H:%M:%S")
            
            trans_id = execute_db(
                """INSERT INTO tbl_pos_transaction_log
                   (receipt_number, terminal_id, cashier_user_id, total_amount, total_cost_price,
                    payment_method, amount_tendered, change_given, gcash_ref_number,
                    order_type, order_status, transaction_timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'InStore', 'Completed', ?)""",
                (receipt_no, "TERM-01", 2, round(total_amt, 2), round(total_cost, 2),
                 payment_method, round(tendered, 2), round(change, 2), gcash_ref, t_time)
            )
            
            for sku, qty, c_price, r_price, l_total in cart_items:
                execute_db(
                    """INSERT INTO tbl_pos_transaction_items
                       (transaction_id, sku, quantity_sold, unit_cost_price, unit_retail_price, line_total)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (trans_id, sku, qty, c_price, r_price, round(l_total, 2))
                )
            
            daily_revenue += total_amt
            daily_cogs += total_cost
        
        # Archive daily profitability (ISO 8601)
        gross_margin = daily_revenue - daily_cogs
        margin_pct = (gross_margin / daily_revenue * 100) if daily_revenue > 0 else 0.0
        rec_date = trans_date.strftime("%Y-%m-%d")
        execute_db(
            """INSERT INTO tbl_profitability_archive
               (reporting_period, gross_revenue, total_cogs, gross_margin, margin_percentage, total_transactions, recorded_date)
               VALUES ('Daily', ?, ?, ?, ?, ?, ?)""",
            (round(daily_revenue, 2), round(daily_cogs, 2), round(gross_margin, 2), round(margin_pct, 2), num_transactions, rec_date)
        )
    
    # 4. Seed Audit Log Event
    execute_db(
        """INSERT INTO tbl_security_audit_log
           (user_id, username, action, resource, status, ip_address, details)
           VALUES (1, 'admin', 'SYSTEM_INITIALIZATION', 'tbl_product_master', 'SUCCESS', '127.0.0.1', 'Sulit Store database initialized with seed catalog and historical transactions')"""
    )
    
    return {"status": "success", "message": "Sulit Store database successfully initialized and seeded."}

if __name__ == "__main__":
    result = seed_database()
    print("Seed Result:", result)
