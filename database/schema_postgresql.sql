-- =============================================================================
-- Sulit Store Profit-Intelligent Inventory Management & POS System
-- PostgreSQL Normalized Database Schema
-- Standards: ISO/IEC 27001 (Security & RBAC), ISO 8601 (Date-Time Standards)
-- Capstone: Major Design Project - Team 8 (CPE 025A / CPEQC 029_030)
-- Team: Team 8
-- =============================================================================

-- Drop tables if needed for clean setup (re-runnable script)
DROP TABLE IF EXISTS tbl_security_audit_log CASCADE;
DROP TABLE IF EXISTS tbl_profitability_archive CASCADE;
DROP TABLE IF EXISTS tbl_pos_transaction_items CASCADE;
DROP TABLE IF EXISTS tbl_pos_transaction_log CASCADE;
DROP TABLE IF EXISTS tbl_product_master CASCADE;
DROP TABLE IF EXISTS tbl_users CASCADE;

-- 1. User & Role Management Table (RBAC: ISO/IEC 27001)
CREATE TABLE tbl_users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'cashier', 'customer')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Product Master Table
CREATE TABLE tbl_product_master (
    sku VARCHAR(20) PRIMARY KEY,
    barcode VARCHAR(50) UNIQUE,
    product_name VARCHAR(120) NOT NULL,
    category VARCHAR(50) NOT NULL,
    cost_price NUMERIC(10,2) NOT NULL,      -- Confidential COGS (Admin only)
    retail_price NUMERIC(10,2) NOT NULL,    -- Selling Price
    current_stock_qty INT NOT NULL DEFAULT 0 CHECK (current_stock_qty >= 0),
    reorder_threshold INT NOT NULL DEFAULT 10,
    expiration_date DATE,                   -- ISO 8601 format (YYYY-MM-DD)
    srp_market_price NUMERIC(10,2),         -- Online DTI/Market SRP benchmark
    unit_measure VARCHAR(20) DEFAULT 'piece',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. POS Transaction Log Table (Headers)
CREATE TABLE tbl_pos_transaction_log (
    transaction_id SERIAL PRIMARY KEY,
    receipt_number VARCHAR(30) UNIQUE NOT NULL,
    terminal_id VARCHAR(20) NOT NULL DEFAULT 'TERM-01',
    cashier_user_id INT REFERENCES tbl_users(user_id),
    total_amount NUMERIC(10,2) NOT NULL,
    total_cost_price NUMERIC(10,2) NOT NULL,  -- Computed COGS for the sale
    payment_method VARCHAR(20) NOT NULL CHECK (payment_method IN ('Cash', 'GCash', 'Debit')),
    amount_tendered NUMERIC(10,2),
    change_given NUMERIC(10,2) DEFAULT 0.00,
    gcash_ref_number VARCHAR(50),
    order_type VARCHAR(20) NOT NULL DEFAULT 'InStore' CHECK (order_type IN ('InStore', 'OnlinePickup')),
    order_status VARCHAR(20) NOT NULL DEFAULT 'Completed' CHECK (order_status IN ('PendingPickup', 'ReadyForPickup', 'Completed', 'Cancelled')),
    customer_name VARCHAR(100) DEFAULT 'Walk-in Customer',
    customer_phone VARCHAR(20),
    transaction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. POS Transaction Line Items Table
CREATE TABLE tbl_pos_transaction_items (
    item_id SERIAL PRIMARY KEY,
    transaction_id INT NOT NULL REFERENCES tbl_pos_transaction_log(transaction_id) ON DELETE CASCADE,
    sku VARCHAR(20) NOT NULL REFERENCES tbl_product_master(sku),
    quantity_sold INT NOT NULL CHECK (quantity_sold > 0),
    unit_cost_price NUMERIC(10,2) NOT NULL,
    unit_retail_price NUMERIC(10,2) NOT NULL,
    line_total NUMERIC(10,2) NOT NULL
);

-- 5. Profitability Archive Table
CREATE TABLE tbl_profitability_archive (
    archive_id SERIAL PRIMARY KEY,
    reporting_period VARCHAR(20) NOT NULL CHECK (reporting_period IN ('Daily', 'Weekly', 'Monthly')),
    gross_revenue NUMERIC(12,2) NOT NULL,
    total_cogs NUMERIC(12,2) NOT NULL,
    gross_margin NUMERIC(12,2) NOT NULL,
    margin_percentage NUMERIC(6,2) NOT NULL,
    total_transactions INT NOT NULL DEFAULT 0,
    recorded_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Security Audit Log Table (ISO/IEC 27001 Compliance)
CREATE TABLE tbl_security_audit_log (
    audit_id SERIAL PRIMARY KEY,
    user_id INT REFERENCES tbl_users(user_id),
    username VARCHAR(50),
    action VARCHAR(100) NOT NULL,
    resource VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'SUCCESS',
    ip_address VARCHAR(45),
    details TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create Indexes for High Performance Queries
CREATE INDEX idx_product_category ON tbl_product_master(category);
CREATE INDEX idx_product_expiry ON tbl_product_master(expiration_date);
CREATE INDEX idx_trans_timestamp ON tbl_pos_transaction_log(transaction_timestamp);
CREATE INDEX idx_trans_order_status ON tbl_pos_transaction_log(order_status);
CREATE INDEX idx_profit_recorded_date ON tbl_profitability_archive(recorded_date);
