"""
Configuration module for Sulit Store POS & Inventory Management System.
Complies with ISO/IEC 27001 (Security) and user constraints (obvious placeholders).
"""
import os

class Config:
    # Application Metadata (Major Design Project - Team 8)
    APP_NAME = "Sulit Store Profit-Intelligent POS & Inventory System"
    STUDENT_NAME = "Team 8"
    STUDENT_ID = "2412038"
    COURSE = "CPE 025A / CPEQC 029_030"
    VERSION = "2.0.0"
    
    # Secret Key for Sessions / JWT
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "sulit-store-development-secret-key-2412038")
    
    # =========================================================================
    # SINGLE-SWITCH DEPLOYMENT CONFIGURATION:
    # Set to 'localhost' for fast, zero-lag local SQLite (default).
    # Set to 'cloud' for online deployment (e.g. Render / Neon PostgreSQL).
    # To switch from localhost to cloud in the future, change this ONE variable:
    # =========================================================================
    DEPLOYMENT_MODE = os.environ.get("DEPLOYMENT_MODE", "localhost").lower()
    
    # SQLite local file path (Primary for Localhost zero-lag operations)
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLITE_PATH = os.path.join(BASE_DIR, "database", "sulit_store.db")
    
    # Database Engine Selection:
    # When DEPLOYMENT_MODE == 'localhost', strictly use SQLite (ignores remote network calls)
    if DEPLOYMENT_MODE == "cloud" and os.environ.get("DATABASE_URL"):
        DB_ENGINE = "postgresql"
        DATABASE_URL = os.environ.get("DATABASE_URL")
    else:
        DB_ENGINE = "sqlite"
        DATABASE_URL = None
    
    # Cloud PostgreSQL parameters (used only when DEPLOYMENT_MODE == 'cloud')
    PG_HOST = os.environ.get("PG_HOST", "localhost")
    PG_PORT = int(os.environ.get("PG_PORT", 5432))
    PG_DATABASE = os.environ.get("PG_DATABASE", "sulit_store_db")
    PG_USER = os.environ.get("PG_USER", "postgres")
    PG_PASSWORD = os.environ.get("PG_PASSWORD", "YOUR_POSTGRES_PASSWORD")
    
    # =========================================================================
    # NETWORKING & SERVER SETTINGS
    # =========================================================================
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", 5000))
    DEBUG = os.environ.get("FLASK_DEBUG", "True" if DEPLOYMENT_MODE == "localhost" else "False").lower() == "true"
    SESSION_COOKIE_SECURE = (DEPLOYMENT_MODE == "cloud")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # =========================================================================
    # PREDICTIVE ANALYTICS & INVENTORY POLICY
    # =========================================================================
    DEFAULT_LEAD_TIME_DAYS = int(os.environ.get("DEFAULT_LEAD_TIME_DAYS", 3))
    DEFAULT_SAFETY_STOCK_DAYS = int(os.environ.get("DEFAULT_SAFETY_STOCK_DAYS", 2))
    SALES_HISTORY_WINDOW_DAYS = int(os.environ.get("SALES_HISTORY_WINDOW_DAYS", 14))
    EXPIRY_ALERT_WARNING_DAYS = int(os.environ.get("EXPIRY_ALERT_WARNING_DAYS", 30))
    EXPIRY_ALERT_CRITICAL_DAYS = int(os.environ.get("EXPIRY_ALERT_CRITICAL_DAYS", 7))

    # =========================================================================
    # MODULAR SUB-ENGINES (100% Offline-Capable Localhost by Default)
    # =========================================================================
    # OCR Engine: 'opencv_regex' (Zero-setup local OpenCV) or 'tesseract' / 'cloud'
    OCR_BACKEND = os.environ.get("OCR_BACKEND", "opencv_regex")
    
    # SRP Price Monitor: 'offline_cache' (Local DTI baseline) or 'live_web'
    SRP_PROVIDER = os.environ.get("SRP_PROVIDER", "offline_cache")
    
    # POS Payment Gateways
    ENABLED_PAYMENT_METHODS = ["Cash", "GCash"]

    # Computer Vision OCR Configurations
    OCR_UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "bmp"}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max image upload
    
    # Store Operational Parameters
    CURRENCY_SYMBOL = "₱"
    DEFAULT_TERMINAL_ID = "TERM-01"
    STORE_NAME = "Sulit Store"
    STORE_ADDRESS = "938 Aurora Blvd, Cubao, Quezon City"
    STORE_CONTACT = "+63 917 123 4567"
    TIN = "123-456-789-000"
    GCASH_MERCHANT_NAME = "SULIT STORE OFFICIAL"
    GCASH_MOBILE_NUMBER = "0917-123-4567"
