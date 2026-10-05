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
    
    # Database Configuration:
    # DB_ENGINE can be 'sqlite' (default local zero-setup) or 'postgresql' (cloud-hosted)
    DATABASE_URL = os.environ.get("DATABASE_URL")
    DB_ENGINE = "postgresql" if DATABASE_URL else os.environ.get("DB_ENGINE", "sqlite").lower()
    
    # SQLite local file path
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLITE_PATH = os.path.join(BASE_DIR, "database", "sulit_store.db")
    
    # PostgreSQL Cloud connection parameters (using standard placeholders)
    PG_HOST = os.environ.get("PG_HOST", "localhost")
    PG_PORT = int(os.environ.get("PG_PORT", 5432))
    PG_DATABASE = os.environ.get("PG_DATABASE", "sulit_store_db")
    PG_USER = os.environ.get("PG_USER", "postgres")
    PG_PASSWORD = os.environ.get("PG_PASSWORD", "YOUR_POSTGRES_PASSWORD")
    
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
