# 🛒 Sulit Store Profit-Intelligent POS & Inventory Management System

**Academic Project:** Major Design Project (CPE 025A / CPEQC 029_030)  
**Institution:** Technological Institute of the Philippines (T.I.P.) Quezon City  
**Author:** Ivan Rex B. Tamondong (ID: 2412038) – Team 8  
**Client:** Sulit Store  
**Standards:** ISO/IEC 25010 (Software Quality), ISO/IEC 27001 (Data Security), ISO 8601 (Date Standards)

---

## 🚀 Quick Start: How to Run on Localhost (Offline Mode)

The application is configured to run **100% offline on Localhost** with zero lag using an optimized local SQLite engine.

### Prerequisites
- Python 3.10+ (tested with Python 3.14)
- Web browser (Chrome, Edge, Firefox)

### Step 1: Open PowerShell and navigate to the project directory
```powershell
cd "D:\Downloads\Team 8\ProfitIntelligent"
```

### Step 2: Start the application server
```powershell
python app.py
```

You will see the startup banner:
```text
======================================================================
Sulit Store Profit-Intelligent POS & Inventory System
Developer: Team 8 (ID: 2412038)
Mode: LOCALHOST | DB: SQLITE | SRP: OFFLINE_CACHE
Course: CPE 025A / CPEQC 029_030 | Server running on http://0.0.0.0:5000
======================================================================
```

### Step 3: Open the Web Application
Open your browser and navigate to:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 🔑 Pre-Seeded Demo Accounts (RBAC)

The system automatically initializes and seeds local test accounts:

| Role | Username | Password | Permissions & Views |
| :--- | :--- | :--- | :--- |
| **Store Manager (Admin)** | `admin` | `admin123` | Full access: COGS, profit analytics, inventory restock, DTI SRP, audit logs |
| **Cashier** | `cashier1` | `cashier123` | POS checkout, barcode scan. *COGS & gross margins are masked (ISO 27001)* |
| **Customer** | `customer1` | `cust123` | Public online ordering catalog, retail price view, cart checkout |

---

## ⚙️ Modular Architecture: The 1-Line Switch

All environment, database, and algorithm settings are isolated in [`config.py`](config.py).

### How It Works Now (Localhost Mode)
In [`config.py`](config.py):
```python
DEPLOYMENT_MODE = "localhost"
```
- **Database:** Connects to local `database/sulit_store.db` with Write-Ahead Logging (`WAL` mode) for microsecond query speeds.
- **DTI SRP Monitor:** Uses the built-in local cache (0ms network latency).
- **OCR Engine:** Uses local OpenCV preprocessing and regular expression date parsing (100% offline).
- **Cookies:** Plain HTTP compatible for localhost development.

### How to Switch to Online Cloud Deployment in the Future
When you are ready to deploy online (e.g. Render, Neon PostgreSQL, or VPS), **make this one change**:

1. In [`config.py`](config.py#L24), change:
   ```python
   DEPLOYMENT_MODE = "cloud"
   ```
   *(Or keep the file as-is and set the environment variable `DEPLOYMENT_MODE=cloud` on your host).*
2. Provide your cloud database connection string in your environment:
   ```bash
   DATABASE_URL="postgresql://user:password@ep-host.region.neon.tech/sulit_store_db?sslmode=require"
   ```
3. The application will automatically:
   - Route all queries to PostgreSQL.
   - Enforce HTTPS Secure Cookie flags (`SESSION_COOKIE_SECURE = True`).
   - Listen dynamically on the host's assigned `$PORT`.

---

## 🎛️ Configurable Business Parameters

You can customize inventory policies in [`config.py`](config.py) without touching any algorithm formulas:

```python
# Supplier delivery window (days)
DEFAULT_LEAD_TIME_DAYS = 3

# Safety buffer stock (days)
DEFAULT_SAFETY_STOCK_DAYS = 2

# Number of days of historical sales analyzed for velocity
SALES_HISTORY_WINDOW_DAYS = 14

# Expiry date warning threshold (days before expiration)
EXPIRY_ALERT_WARNING_DAYS = 30

# Critical expiration threshold for clearance discounts
EXPIRY_ALERT_CRITICAL_DAYS = 7
```

---

## 🧪 Running Automated Tests

To verify system integrity, RBAC masking, date compliance, and predictive calculation accuracy:

```powershell
python -m unittest tests/test_system.py
```

Expected output:
```text
Ran 8 tests in ~2.8s
OK
```

---

## 🛠️ Troubleshooting

### Error: `Address already in use` or Port 5000 is Busy
If port 5000 is held by an earlier background Python process:
```powershell
Stop-Process -Name python -Force
python app.py
```

### Error: `jinja2.exceptions.TemplateNotFound: index.html`
Ensure your terminal is located directly inside the `ProfitIntelligent` folder before starting:
```powershell
cd "D:\Downloads\Team 8\ProfitIntelligent"
python app.py
```

---

## 📁 Repository Structure
```text
ProfitIntelligent/
├── app.py                  # Main Flask application and RESTful API endpoints
├── config.py               # Central modular configuration (Local vs Cloud switch)
├── server.py               # WSGI entrypoint adapter for Gunicorn / Cloud hosts
├── README.md               # User guide and instructions for running the system
├── requirements.txt        # Python package dependencies
├── Procfile                # Cloud process file for Render / Heroku
├── database/
│   ├── db.py               # Unified DB abstraction layer (SQLite WAL + PostgreSQL)
│   ├── sulit_store.db      # High-performance local SQLite database
│   ├── seed_data.py        # Default users, products, and retail sales records
│   ├── schema_sqlite.sql   # SQLite schema definition
│   └── schema_postgresql.sql # PostgreSQL schema definition
├── modules/
│   ├── predictive_engine.py # Sales velocity, depletion forecast, RMSE
│   ├── ocr_scanner.py      # OpenCV image processing & ISO 8601 date parsing
│   ├── srp_scraper.py      # DTI SRP price benchmarks & margin protection
│   └── audit_logger.py     # ISO 27001 security event logging
├── static/
│   ├── css/                # Custom UI styling, POS themes, and charts
│   └── js/                 # Modular frontend controllers (pos.js, ocr.js, etc.)
├── templates/
│   └── index.html          # Single-page interface (POS, Inventory, Analytics)
├── tests/
│   └── test_system.py      # Automated system test suite (8 test cases)
└── uploads/                # Directory for temporary OCR image uploads
```
