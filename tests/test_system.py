"""
Comprehensive Capstone Verification and Quality Assurance Test Suite.
Directly implements Section 8 (Verification Summary) and Section 4 (Constraints Evaluation):
  1. Role-Based Access Control & Field-Level Encryption (ISO/IEC 27001)
  2. Database Integrity & ISO 8601 Date Compliance
  3. Financial Margin Accuracy (Gross Margin = Revenue - COGS)
  4. Computer Vision OCR Expiration Extraction & System Error Rate (< 5% per ISO 25010)
  5. Stock Depletion Velocity & RMSE Calculation (Section 4.1)
  6. Peak Load Checkout Stress Test
"""
import sys
import os
import unittest
import json
from datetime import datetime

# Add root folder to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app
from database.db import query_db, execute_db
from database.seed_data import seed_database
from modules.ocr_scanner import scanner
from modules.predictive_engine import calculate_rmse, run_model_rmse_evaluation

class TestSulitStoreSystem(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Configure test client and seed database
        app.config["TESTING"] = True
        cls.client = app.test_client()
        seed_database()

    # -------------------------------------------------------------------------
    # Test 1: ISO 8601 Date Standardization Compliance
    # -------------------------------------------------------------------------
    def test_iso_8601_date_compliance(self):
        """Verify that all recorded product expiration dates follow YYYY-MM-DD format."""
        products = query_db("SELECT sku, expiration_date FROM tbl_product_master WHERE expiration_date IS NOT NULL")
        self.assertGreater(len(products), 0, "Product master should contain records with expiration dates")
        
        for p in products:
            date_str = p["expiration_date"]
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                self.assertIsNotNone(dt)
            except ValueError:
                self.fail(f"Product {p['sku']} has non-ISO-8601 expiration date: {date_str}")

    # -------------------------------------------------------------------------
    # Test 2: Role-Based Access Control (RBAC) & Confidentiality (ISO/IEC 27001)
    # -------------------------------------------------------------------------
    def test_rbac_cashier_confidentiality(self):
        """Cashiers must NEVER receive confidential cost_price (COGS) or profit metrics."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 2
            sess["role"] = "cashier"
            sess["username"] = "cashier1"

        # 1. Product listing should have cost_price stripped
        res = self.client.get("/api/products")
        data = res.get_json()
        self.assertTrue(data["success"])
        for prod in data["products"]:
            self.assertNotIn("cost_price", prod, "Cashier should not see cost_price")
            self.assertNotIn("gross_margin", prod, "Cashier should not see gross_margin")

        # 2. Financial analytics summary should be denied (HTTP 403)
        analytics_res = self.client.get("/api/analytics/summary")
        self.assertEqual(analytics_res.status_code, 403, "Cashier must be denied access to financial analytics")

    def test_rbac_admin_full_access(self):
        """Admins must have full access to financial metrics and COGS."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["role"] = "admin"
            sess["username"] = "admin"

        res = self.client.get("/api/analytics/summary")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("gross_revenue", data["kpis"])
        self.assertIn("total_cogs", data["kpis"])
        self.assertIn("gross_margin", data["kpis"])

    # -------------------------------------------------------------------------
    # Test 3: Financial Integrity (Gross Margin = Sales Revenue - Total COGS)
    # -------------------------------------------------------------------------
    def test_financial_margin_formula(self):
        """Verify that gross profit margin strictly equals Revenue minus COGS."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["role"] = "admin"
            sess["username"] = "admin"

        res = self.client.get("/api/analytics/summary")
        kpis = res.get_json()["kpis"]
        
        revenue = kpis["gross_revenue"]
        cogs = kpis["total_cogs"]
        margin = kpis["gross_margin"]

        calculated_margin = round(revenue - cogs, 2)
        self.assertAlmostEqual(margin, calculated_margin, places=2,
                               msg="Gross Margin must strictly equal Revenue - COGS")

    # -------------------------------------------------------------------------
    # Test 4: Computer Vision OCR Expiration Extraction & System Error Rate
    # -------------------------------------------------------------------------
    def test_ocr_date_parsing_and_error_rate(self):
        """Verify multi-format date extraction and verify System Error Rate < 0.05."""
        evaluation = scanner.evaluate_system_error_rate()
        
        self.assertGreaterEqual(evaluation["accuracy_percentage"], 95.0,
                                "OCR extraction accuracy must be at least 95%")
        self.assertLessEqual(evaluation["system_error_rate"], 0.05,
                             "System Error Rate must be < 5% per Section 4.2 / ISO 25010")
        self.assertTrue(evaluation["benchmark_passed"])

    # -------------------------------------------------------------------------
    # Test 5: Predictive Analytics Stock Depletion & RMSE Computation
    # -------------------------------------------------------------------------
    def test_predictive_rmse_computation(self):
        """Verify RMSE formula execution and demand velocity calculation."""
        actual = [10, 12, 14, 11, 13]
        predicted = [11, 11, 13, 12, 12]
        rmse = calculate_rmse(actual, predicted)
        
        # sqrt(mean([(-1)^2, (1)^2, (1)^2, (-1)^2, (1)^2])) = sqrt(5/5) = 1.0
        self.assertEqual(rmse, 1.0)

        # Full catalog evaluation test
        eval_result = run_model_rmse_evaluation()
        self.assertIn("overall_rmse", eval_result)
        self.assertGreater(eval_result["total_data_points"], 0)
        self.assertGreater(len(eval_result["product_evaluations"]), 0)

    # -------------------------------------------------------------------------
    # Test 6: Point-of-Sale Atomic Checkout & Receipt Generation
    # -------------------------------------------------------------------------
    def test_pos_atomic_checkout(self):
        """Verify checkout decrements stock, records transaction, and returns receipt."""
        prod = query_db("SELECT sku, current_stock_qty, retail_price FROM tbl_product_master WHERE current_stock_qty >= 5 LIMIT 1", one=True)
        initial_stock = prod["current_stock_qty"]
        
        payload = {
            "items": [{"sku": prod["sku"], "quantity": 2}],
            "payment_method": "Cash",
            "amount_tendered": prod["retail_price"] * 2 + 50.0,
            "customer_name": "Test QA Buyer",
            "terminal_id": "TEST-TERM"
        }

        res = self.client.post("/api/pos/checkout", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("receipt_number", data)
        self.assertEqual(data["change_given"], 50.0)

        # Verify stock decremented
        updated_prod = query_db("SELECT current_stock_qty FROM tbl_product_master WHERE sku = ?", (prod["sku"],), one=True)
        self.assertEqual(updated_prod["current_stock_qty"], initial_stock - 2)

    # -------------------------------------------------------------------------
    # Test 7: Peak Transaction Load Stress Test (Section 4.2)
    # -------------------------------------------------------------------------
    def test_peak_hour_stress_test(self):
        """Simulate peak hour transaction stress test and verify 0% failure."""
        res = self.client.post("/api/system/stress_test")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["successful_checkouts"], 100)
        self.assertLess(data["system_error_rate"], 0.05)


if __name__ == "__main__":
    unittest.main()
