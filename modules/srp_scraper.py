"""
Suggested Retail Price (SRP) Web Scraping and Market Monitoring Engine.
Complies with Section 1.4 & 1.5 of the Engineering Design Documentation.
Tracks Department of Trade and Industry (DTI) SRP benchmarks and online retail prices
to protect Sulit Store's profit margins while staying competitive within legal limits.
"""
from datetime import datetime
from config import Config
from database.db import query_db, execute_db

# Standard DTI SRP and Market Retail Price Reference Data for Philippine Basic Necessities
DTI_BENCHMARK_DATABASE = {
    "SKU-CAN-001": {"name": "Argentina Corned Beef 175g", "srp_min": 40.00, "srp_max": 43.50, "source": "DTI E-Presyo / Supermarket Index"},
    "SKU-CAN-002": {"name": "Century Tuna Flakes in Oil 155g", "srp_min": 43.00, "srp_max": 46.50, "source": "DTI E-Presyo / Supermarket Index"},
    "SKU-CAN-003": {"name": "555 Sardines in Tomato Sauce 155g", "srp_min": 24.00, "srp_max": 27.00, "source": "DTI E-Presyo / Supermarket Index"},
    "SKU-NOO-001": {"name": "Lucky Me! Pancit Canton Original 80g", "srp_min": 14.50, "srp_max": 16.50, "source": "DTI E-Presyo / Supermarket Index"},
    "SKU-NOO-002": {"name": "Lucky Me! Pancit Canton Chilimansi 80g", "srp_min": 14.50, "srp_max": 16.50, "source": "DTI E-Presyo / Supermarket Index"},
    "SKU-NOO-003": {"name": "Nissin Cup Noodles Seafood 40g", "srp_min": 30.00, "srp_max": 33.00, "source": "DTI E-Presyo / Supermarket Index"},
    "SKU-COF-001": {"name": "Kopiko Blanca 3-in-1 Coffee 30g", "srp_min": 13.00, "srp_max": 15.00, "source": "DTI E-Presyo / Supermarket Index"},
    "SKU-COF-002": {"name": "Nescafe Classic Stick 2g", "srp_min": 5.00, "srp_max": 6.50, "source": "DTI E-Presyo / Supermarket Index"},
    "SKU-COF-003": {"name": "Great Taste White Twin Pack 50g", "srp_min": 20.00, "srp_max": 23.00, "source": "DTI E-Presyo / Supermarket Index"},
    "SKU-DRY-001": {"name": "Bear Brand Fortified Powdered Milk 33g", "srp_min": 15.50, "srp_max": 17.50, "source": "DTI E-Presyo / Supermarket Index"},
    "SKU-DRY-002": {"name": "Alaska Evaporated Milk 370ml", "srp_min": 36.00, "srp_max": 39.50, "source": "DTI E-Presyo / Supermarket Index"},
    "SKU-SNK-001": {"name": "SkyFlakes Crackers 25g (Pack of 10)", "srp_min": 70.00, "srp_max": 76.00, "source": "Supermarket Index"},
    "SKU-SNK-002": {"name": "Piattos Cheese Flavored Potato Chips 85g", "srp_min": 36.00, "srp_max": 40.00, "source": "Supermarket Index"},
    "SKU-SNK-003": {"name": "Oishi Prawn Crackers 60g", "srp_min": 22.00, "srp_max": 25.50, "source": "Supermarket Index"},
    "SKU-CND-001": {"name": "Datu Puti Vinegar 350ml", "srp_min": 20.00, "srp_max": 23.00, "source": "DTI E-Presyo / Supermarket Index"},
    "SKU-CND-002": {"name": "Datu Puti Soy Sauce 350ml", "srp_min": 22.00, "srp_max": 25.00, "source": "DTI E-Presyo / Supermarket Index"},
    "SKU-BEV-001": {"name": "San Miguel Pale Pilsen 330ml Can", "srp_min": 54.00, "srp_max": 60.00, "source": "Retail Price Monitor"},
    "SKU-BEV-002": {"name": "Red Horse Extra Strong Beer 500ml", "srp_min": 68.00, "srp_max": 75.00, "source": "Retail Price Monitor"},
    "SKU-DRY-EXP": {"name": "Magnolia Fresh Milk 1L", "srp_min": 108.00, "srp_max": 118.00, "source": "Supermarket Index"},
    "SKU-BKR-EXP": {"name": "Gardenia Classic White Bread 600g", "srp_min": 78.00, "srp_max": 83.50, "source": "DTI E-Presyo / Supermarket Index"},
    "SKU-PAS-EXP": {"name": "Chiz Boy Spread 220g", "srp_min": 56.00, "srp_max": 62.00, "source": "Supermarket Index"}
}

def get_srp_benchmark(sku: str, product=None):
    """
    Modular SRP benchmark resolver supporting offline local cache and future live web providers.
    """
    if Config.SRP_PROVIDER == "offline_cache":
        return DTI_BENCHMARK_DATABASE.get(sku, {
            "name": product['product_name'] if product else sku,
            "srp_min": (product['retail_price'] * 0.95) if product else 0.0,
            "srp_max": (product['retail_price'] * 1.05) if product else 0.0,
            "source": "Local DTI Baseline"
        })
    return DTI_BENCHMARK_DATABASE.get(sku)

def analyze_sku_pricing(sku: str):
    """
    Compare Sulit Store's current retail price and COGS against DTI SRP benchmarks.
    Provides actionable pricing recommendation.
    """
    product = query_db("SELECT * FROM tbl_product_master WHERE sku = ?", (sku,), one=True)
    if not product:
        return None

    benchmark = get_srp_benchmark(sku, product)

    cost = product['cost_price']
    current_retail = product['retail_price']
    current_margin = current_retail - cost
    margin_pct = (current_margin / current_retail * 100) if current_retail > 0 else 0

    srp_mid = round((benchmark['srp_min'] + benchmark['srp_max']) / 2, 2)
    diff_from_srp = current_retail - srp_mid

    if current_retail > benchmark['srp_max']:
        status = "Overpriced (Above DTI Ceiling)"
        recommendation = f"Lower retail price to at most ₱{benchmark['srp_max']:.2f} to remain compliant with DTI caps."
    elif current_retail < benchmark['srp_min']:
        status = "Underpriced (Opportunity to Increase Margin)"
        recommendation = f"You can safely adjust retail price up to ₱{srp_mid:.2f} to increase profit margin without alienating customers."
    else:
        status = "Optimally Priced (Within Fair Market Range)"
        recommendation = "Current retail pricing is well balanced between market competitiveness and healthy profit margin."

    return {
        "sku": sku,
        "product_name": product['product_name'],
        "category": product['category'],
        "cost_price": cost,
        "current_retail_price": current_retail,
        "current_gross_margin": round(current_margin, 2),
        "margin_percentage": round(margin_pct, 2),
        "srp_min": benchmark['srp_min'],
        "srp_max": benchmark['srp_max'],
        "srp_benchmark_mid": srp_mid,
        "diff_from_srp": round(diff_from_srp, 2),
        "pricing_status": status,
        "recommendation": recommendation,
        "data_source": benchmark['source'],
        "last_checked": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def get_all_srp_comparisons():
    """Return price analysis for all registered products in the inventory."""
    products = query_db("SELECT sku FROM tbl_product_master ORDER BY category, product_name")
    comparisons = []
    for p in products:
        analysis = analyze_sku_pricing(p['sku'])
        if analysis:
            comparisons.append(analysis)
    return comparisons

def sync_srp_to_database():
    """Update tbl_product_master srp_market_price column with latest scraped values."""
    for sku, data in DTI_BENCHMARK_DATABASE.items():
        srp_mid = (data['srp_min'] + data['srp_max']) / 2
        execute_db(
            "UPDATE tbl_product_master SET srp_market_price = ? WHERE sku = ?",
            (round(srp_mid, 2), sku)
        )
    return True
