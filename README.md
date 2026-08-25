# Inventory KPI Dashboard
## Project Overview
This project analyzes inventory performance for a retail dataset with **109,500 daily records** covering 5 stores, 30 products, 5 categories, and 4 regions (Jan 2022 to Dec 2023). It tracks inventory efficiency, flags stockout risk, estimates reorder points, and forecasts demand, using SQL analytics, a trained forecasting model, and an interactive dashboard.
---
## Key Features
- **SQL-driven KPI Calculation**
  - Stockout rate by store, product, category, and region. Overall rate is **5.06%**, with Groceries and store S004 the worst offenders, and holiday/promo days pushing stockout risk from 4.93% up to 5.84%.
  - Average inventory level, weekly inventory turnover (slow/medium/fast-moving classification), and reorder-point estimation from moving-average demand times category lead time.
  - Original MySQL queries are in [`SQL-scripts.pdf`](SQL-scripts.pdf). The same analytics adapted for the normalized SQLite database below are in [`sql/kpi_queries_sqlite.sql`](sql/kpi_queries_sqlite.sql).
- **Relational Schema (ERD Design)**
  - Normalized `stores` / `products` / `inventory_facts` tables plus a `retail_data` view for backward compatibility. See [`sql/schema.sql`](sql/schema.sql) and the diagram in [`sql/erd.md`](sql/erd.md).
  - [`db/build_database.py`](db/build_database.py) loads the CSV into a real, queryable SQLite database (`db/inventory.db`).
- **Demand Forecasting**
  - [`model/train_forecast.py`](model/train_forecast.py) trains a RandomForest regressor on 7-day rolling sales/inventory history, price, discount, competitor pricing, weather, seasonality, and holiday flag, using only information that would legitimately be known ahead of time.
  - On a time-based holdout (train through Sep 2023, test on Q4 2023), the trained model scores **39.8% MAPE** against the dataset's own pre-existing `Demand Forecast` column at **15.9% MAPE** on the same rows.
  - That gap makes sense once you look closer: `Demand Forecast` correlates at **r ≈ 0.93** with actual `Units Sold`, so it looks like it was generated as the real sales number plus noise, not an independent forecast. The features a model can honestly use (price, discount, competitor pricing) correlate at **r < 0.01** with demand in this synthetic dataset, which limits how close a fair model can get. Re-run the script if you want updated numbers.
- **Data Visualization with Streamlit + Plotly**
  - Interactive charts and tables for exploring inventory trends
  - Filters by product, store, and category
  - Forecast section showing actual vs. baseline vs. model prediction per store/product, MAPE comparison, and feature importances
---
## Tech Stack
- **Python** for data processing, modeling, and the dashboard
- **Pandas** for data wrangling
- **scikit-learn** for the demand forecasting model
- **SQL / SQLite** for the normalized schema and KPI generation
- **Streamlit** for the dashboard UI
- **Plotly** for interactive visualizations
---
## Setup

```bash
pip install -r requirements.txt

# 1. Build the normalized SQLite database from the CSV
python db/build_database.py

# 2. Train the forecasting model (writes model/forecast_predictions.csv, used by the dashboard)
python model/train_forecast.py

# 3. Run the dashboard
streamlit run dashboard.py
```
---
