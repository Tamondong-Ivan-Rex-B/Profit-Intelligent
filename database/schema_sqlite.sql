-- =============================================================================
-- Sulit Store Profit-Intelligent Inventory Management & POS System
-- SQLite Local Development & Evaluation Schema
-- Compatible with PostgreSQL design and ISO 8601 Date format
-- =============================================================================

CREATE TABLE IF NOT EXISTS tbl_users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'cashier', 'customer')),
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS tbl_product_master (
    sku TEXT PRIMARY KEY,
    barcode TEXT UNIQUE,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    cost_price REAL NOT NULL,      -- Confidential COGS
    retail_price REAL NOT NULL,    -- Selling Price
    current_stock_qty INTEGER NOT NULL DEFAULT 0,
    reorder_threshold INTEGER NOT NULL DEFAULT 10,
    expiration_date TEXT,          -- ISO 8601: YYYY-MM-DD
    srp_market_price REAL,         -- Online benchmark
    unit_measure TEXT DEFAULT 'piece',
    created_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS tbl_pos_transaction_log (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_number TEXT UNIQUE NOT NULL,
    terminal_id TEXT NOT NULL DEFAULT 'TERM-01',
    cashier_user_id INTEGER REFERENCES tbl_users(user_id),
    total_amount REAL NOT NULL,
    total_cost_price REAL NOT NULL,
    payment_method TEXT NOT NULL CHECK (payment_method IN ('Cash', 'GCash', 'Debit')),
    amount_tendered REAL,
    change_given REAL DEFAULT 0.00,
    gcash_ref_number TEXT,
    order_type TEXT NOT NULL DEFAULT 'InStore' CHECK (order_type IN ('InStore', 'OnlinePickup')),
    order_status TEXT NOT NULL DEFAULT 'Completed' CHECK (order_status IN ('PendingPickup', 'ReadyForPickup', 'Completed', 'Cancelled')),
    customer_name TEXT DEFAULT 'Walk-in Customer',
    customer_phone TEXT,
    transaction_timestamp TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS tbl_pos_transaction_items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER NOT NULL REFERENCES tbl_pos_transaction_log(transaction_id) ON DELETE CASCADE,
    sku TEXT NOT NULL REFERENCES tbl_product_master(sku),
    quantity_sold INTEGER NOT NULL CHECK (quantity_sold > 0),
    unit_cost_price REAL NOT NULL,
    unit_retail_price REAL NOT NULL,
    line_total REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS tbl_profitability_archive (
    archive_id INTEGER PRIMARY KEY AUTOINCREMENT,
    reporting_period TEXT NOT NULL CHECK (reporting_period IN ('Daily', 'Weekly', 'Monthly')),
    gross_revenue REAL NOT NULL,
    total_cogs REAL NOT NULL,
    gross_margin REAL NOT NULL,
    margin_percentage REAL NOT NULL,
    total_transactions INTEGER NOT NULL DEFAULT 0,
    recorded_date TEXT DEFAULT (date('now', 'localtime')),
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS tbl_security_audit_log (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES tbl_users(user_id),
    username TEXT,
    action TEXT NOT NULL,
    resource TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'SUCCESS',
    ip_address TEXT,
    details TEXT,
    timestamp TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_product_category ON tbl_product_master(category);
CREATE INDEX IF NOT EXISTS idx_product_expiry ON tbl_product_master(expiration_date);
CREATE INDEX IF NOT EXISTS idx_trans_timestamp ON tbl_pos_transaction_log(transaction_timestamp);
CREATE INDEX IF NOT EXISTS idx_trans_order_status ON tbl_pos_transaction_log(order_status);
CREATE INDEX IF NOT EXISTS idx_profit_recorded_date ON tbl_profitability_archive(recorded_date);
