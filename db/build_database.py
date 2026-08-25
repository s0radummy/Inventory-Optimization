"""
Builds a local SQLite database from inventory_forecasting.csv using the
normalized schema described in sql/schema.sql and sql/erd.md.

Run from the project root:
    py db/build_database.py

Produces db/inventory.db with three tables (stores, products,
inventory_facts) and a retail_data view that reconstructs the original
flat CSV shape, so every query in sql/kpi_queries_sqlite.sql (and the
original SQL-scripts.pdf, once translated) runs against it unchanged.
"""

import sqlite3
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "inventory_forecasting.csv"
DB_PATH = Path(__file__).resolve().parent / "inventory.db"

SCHEMA_SQLITE = """
DROP VIEW IF EXISTS retail_data;
DROP TABLE IF EXISTS inventory_facts;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS stores;

CREATE TABLE stores (
    Store_ID TEXT PRIMARY KEY
);

CREATE TABLE products (
    Product_ID TEXT PRIMARY KEY,
    Category   TEXT NOT NULL
);

CREATE TABLE inventory_facts (
    Date               TEXT    NOT NULL,
    Store_ID           TEXT    NOT NULL,
    Product_ID         TEXT    NOT NULL,
    Region             TEXT    NOT NULL,
    Inventory_Level    INTEGER NOT NULL,
    Units_Sold         INTEGER NOT NULL,
    Units_Ordered      INTEGER NOT NULL,
    Demand_Forecast    REAL    NOT NULL,
    Price              REAL    NOT NULL,
    Discount           REAL    NOT NULL,
    Weather_Condition  TEXT    NOT NULL,
    Holiday_Promotion  INTEGER NOT NULL,
    Competitor_Pricing  REAL    NOT NULL,
    Seasonality        TEXT    NOT NULL,
    PRIMARY KEY (Date, Store_ID, Product_ID),
    FOREIGN KEY (Store_ID) REFERENCES stores(Store_ID),
    FOREIGN KEY (Product_ID) REFERENCES products(Product_ID)
);

CREATE INDEX idx_facts_store   ON inventory_facts (Store_ID);
CREATE INDEX idx_facts_product ON inventory_facts (Product_ID);
CREATE INDEX idx_facts_date    ON inventory_facts (Date);

CREATE VIEW retail_data AS
SELECT
    f.Date,
    f.Store_ID,
    f.Product_ID,
    p.Category,
    f.Region,
    f.Inventory_Level,
    f.Units_Sold,
    f.Units_Ordered,
    f.Demand_Forecast,
    f.Price,
    f.Discount,
    f.Weather_Condition,
    f.Holiday_Promotion,
    f.Competitor_Pricing,
    f.Seasonality
FROM inventory_facts f
JOIN products p ON p.Product_ID = f.Product_ID
JOIN stores  s ON s.Store_ID  = f.Store_ID;
"""


def main() -> None:
    df = pd.read_csv(CSV_PATH)
    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")

    stores = df[["Store ID"]].drop_duplicates().rename(columns={"Store ID": "Store_ID"})
    products = (
        df[["Product ID", "Category"]]
        .drop_duplicates()
        .rename(columns={"Product ID": "Product_ID", "Category": "Category"})
    )

    facts = df.rename(
        columns={
            "Store ID": "Store_ID",
            "Product ID": "Product_ID",
            "Inventory Level": "Inventory_Level",
            "Units Sold": "Units_Sold",
            "Units Ordered": "Units_Ordered",
            "Demand Forecast": "Demand_Forecast",
            "Weather Condition": "Weather_Condition",
            "Holiday/Promotion": "Holiday_Promotion",
            "Competitor Pricing": "Competitor_Pricing",
        }
    )[
        [
            "Date",
            "Store_ID",
            "Product_ID",
            "Region",
            "Inventory_Level",
            "Units_Sold",
            "Units_Ordered",
            "Demand_Forecast",
            "Price",
            "Discount",
            "Weather_Condition",
            "Holiday_Promotion",
            "Competitor_Pricing",
            "Seasonality",
        ]
    ]

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA_SQLITE)
        stores.to_sql("stores", conn, if_exists="append", index=False)
        products.to_sql("products", conn, if_exists="append", index=False)
        facts.to_sql("inventory_facts", conn, if_exists="append", index=False)
        conn.commit()

        counts = conn.execute(
            "SELECT (SELECT COUNT(*) FROM stores), "
            "(SELECT COUNT(*) FROM products), "
            "(SELECT COUNT(*) FROM inventory_facts), "
            "(SELECT COUNT(*) FROM retail_data)"
        ).fetchone()
    finally:
        conn.close()

    print(f"Built {DB_PATH}")
    print(f"  stores:           {counts[0]}")
    print(f"  products:         {counts[1]}")
    print(f"  inventory_facts:  {counts[2]}")
    print(f"  retail_data view: {counts[3]} rows")


if __name__ == "__main__":
    main()
