"""
Predictive Analytics & Inventory Depletion Forecasting Engine.
Complies with Section 4.1 & Section 7 Step 3 of the Engineering Design Documentation.
Calculates:
  1. Average Daily Sales Velocity (V)
  2. Projected Days Until Stockout (D)
  3. Reorder Point (ROP) = (V * Lead Time) + Safety Stock
  4. Root Mean Squared Error (RMSE) against historical sales
  5. Fast-Moving vs Slow-Moving inventory classification
"""
import numpy as np
from datetime import datetime, timedelta
from database.db import query_db

def calculate_rmse(actual_sales, forecasted_sales):
    """
    Calculate Root-Mean-Squared Error (RMSE).
    Formula: sqrt(mean((actual - forecast)^2))
    """
    actual = np.array(actual_sales, dtype=float)
    forecast = np.array(forecasted_sales, dtype=float)
    if len(actual) == 0 or len(forecast) == 0:
        return 0.0
    rmse = np.sqrt(np.mean((actual - forecast) ** 2))
    return round(float(rmse), 4)


def get_sku_daily_sales(sku: str, days: int = 14):
    """
    Fetch daily sales quantity for a specific SKU over past N days.
    Returns list of daily sold quantities indexed from oldest to newest.
    """
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    rows = query_db(
        """SELECT date(l.transaction_timestamp) as sales_date, SUM(i.quantity_sold) as daily_qty
           FROM tbl_pos_transaction_items i
           JOIN tbl_pos_transaction_log l ON i.transaction_id = l.transaction_id
           WHERE i.sku = ? AND date(l.transaction_timestamp) >= ? AND l.order_status = 'Completed'
           GROUP BY date(l.transaction_timestamp)
           ORDER BY sales_date ASC""",
        (sku, cutoff_date)
    )
    
    # Map to continuous daily array
    sales_map = {r['sales_date']: r['daily_qty'] for r in rows} if rows else {}
    daily_quantities = []
    
    for i in range(days, 0, -1):
        day_str = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        daily_quantities.append(sales_map.get(day_str, 0))
        
    return daily_quantities


def forecast_sku_depletion(sku: str, lead_time_days: int = 3, safety_stock_days: int = 2):
    """
    Compute depletion forecast, velocity, days remaining, and recommended reorder point.
    """
    product = query_db("SELECT * FROM tbl_product_master WHERE sku = ?", (sku,), one=True)
    if not product:
        return None
        
    current_stock = product['current_stock_qty']
    daily_sales = get_sku_daily_sales(sku, days=14)
    
    if not daily_sales or sum(daily_sales) == 0:
        return {
            "sku": sku,
            "product_name": product['product_name'],
            "category": product['category'],
            "current_stock": current_stock,
            "daily_velocity": 0.0,
            "days_remaining": 999.0,
            "stockout_date": "N/A (No sales history)",
            "reorder_threshold": product['reorder_threshold'],
            "recommended_reorder_point": product['reorder_threshold'],
            "is_low_stock": current_stock <= product['reorder_threshold'],
            "velocity_tier": "Slow-Moving",
            "historical_daily_sales": daily_sales,
            "historical_moving_avg": [0.0] * len(daily_sales)
        }
        
    # Simple 3-day / 7-day moving averages
    daily_sales_arr = np.array(daily_sales, dtype=float)
    avg_velocity = float(np.mean(daily_sales_arr))
    
    # Generate moving averages for evaluation
    window = 3
    moving_avg = []
    for i in range(len(daily_sales_arr)):
        if i == 0:
            moving_avg.append(daily_sales_arr[0])
        else:
            start_idx = max(0, i - window + 1)
            moving_avg.append(round(float(np.mean(daily_sales_arr[start_idx:i+1])), 2))
            
    # Days remaining before stockout
    if avg_velocity > 0:
        days_remaining = round(current_stock / avg_velocity, 1)
        stockout_dt = datetime.now() + timedelta(days=days_remaining)
        stockout_date = stockout_dt.strftime("%Y-%m-%d")
    else:
        days_remaining = 999.0
        stockout_date = "N/A"
        
    # Reorder Point (ROP) = (Velocity * Lead Time) + (Velocity * Safety Stock Days)
    safety_stock = avg_velocity * safety_stock_days
    recommended_rop = int(np.ceil((avg_velocity * lead_time_days) + safety_stock))
    
    # Fast-moving vs Moderate vs Slow
    if avg_velocity >= 4.0:
        tier = "Fast-Moving"
    elif avg_velocity >= 1.5:
        tier = "Moderate"
    else:
        tier = "Slow-Moving"
        
    return {
        "sku": sku,
        "product_name": product['product_name'],
        "category": product['category'],
        "current_stock": current_stock,
        "daily_velocity": round(avg_velocity, 2),
        "days_remaining": days_remaining,
        "stockout_date": stockout_date,
        "reorder_threshold": product['reorder_threshold'],
        "recommended_reorder_point": max(recommended_rop, product['reorder_threshold']),
        "is_low_stock": current_stock <= product['reorder_threshold'],
        "velocity_tier": tier,
        "historical_daily_sales": [int(x) for x in daily_sales],
        "historical_moving_avg": moving_avg
    }


def generate_depletion_overview():
    """Generate predictive depletion analysis for all products."""
    products = query_db("SELECT sku FROM tbl_product_master ORDER BY category, product_name")
    results = []
    
    for p in products:
        forecast = forecast_sku_depletion(p['sku'])
        if forecast:
            results.append(forecast)
            
    # Sort by urgency: fewest days remaining first
    results.sort(key=lambda x: x['days_remaining'])
    return results


def run_model_rmse_evaluation():
    """
    Capstone Evaluation Test: Computes RMSE between actual daily sales
    and moving average predicted demand across all products over the past 14 days.
    """
    products = query_db("SELECT sku, product_name FROM tbl_product_master")
    all_actual = []
    all_forecast = []
    product_evaluations = []
    
    for p in products:
        actual = get_sku_daily_sales(p['sku'], days=14)
        if len(actual) < 3:
            continue
            
        # Predict using prior 3-day moving average
        predicted = []
        for i in range(len(actual)):
            if i == 0:
                predicted.append(actual[0])
            else:
                # Prediction for day i based on average of past days up to i-1
                history_slice = actual[max(0, i-3):i]
                predicted.append(float(np.mean(history_slice)))
                
        p_rmse = calculate_rmse(actual, predicted)
        product_evaluations.append({
            "sku": p['sku'],
            "product_name": p['product_name'],
            "rmse": p_rmse,
            "mean_sales": round(float(np.mean(actual)), 2)
        })
        all_actual.extend(actual)
        all_forecast.extend(predicted)
        
    overall_rmse = calculate_rmse(all_actual, all_forecast)
    return {
        "overall_rmse": overall_rmse,
        "total_data_points": len(all_actual),
        "product_evaluations": sorted(product_evaluations, key=lambda x: x['rmse'])
    }
