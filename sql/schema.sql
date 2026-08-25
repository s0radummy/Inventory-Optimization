-- ============================================================================
-- Normalized relational schema for the Inventory KPI Dashboard project.
-- MySQL-flavored DDL (matches the project's original deployment target).
--
-- Design notes (derived from profiling inventory_forecasting.csv):
--   - Grain of the source data is one row per (Date, Store_ID, Product_ID):
--     150 Store x Product pairs x 730 days = 109,500 rows, no duplicates.
--   - Product -> Category is a true 1:1 mapping (30 distinct pairs for
--     30 products), so Category normalizes cleanly onto `products`.
--   - Store -> Region is NOT fixed: every Store_ID appears with all 4
--     regions, and even individual (Store, Product) pairs span multiple
--     regions across dates. Region must stay on the fact table.
--
-- A `retail_data` view reconstructs the original flat shape so every query
-- in SQL-scripts.pdf still runs unmodified against this schema.
-- A SQLite-compatible equivalent is loaded by db/build_database.py and
-- queried by sql/kpi_queries_sqlite.sql.
-- ============================================================================

CREATE DATABASE IF NOT EXISTS retail_db;
USE retail_db;

DROP VIEW IF EXISTS retail_data;
DROP TABLE IF EXISTS inventory_facts;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS stores;

CREATE TABLE stores (
    Store_ID VARCHAR(10) PRIMARY KEY
);

CREATE TABLE products (
    Product_ID VARCHAR(10) PRIMARY KEY,
    Category   VARCHAR(50) NOT NULL
);

CREATE TABLE inventory_facts (
    Date               VARCHAR(10)    NOT NULL,   -- ISO 8601 'YYYY-MM-DD'
    Store_ID           VARCHAR(10)    NOT NULL,
    Product_ID         VARCHAR(10)    NOT NULL,
    Region             VARCHAR(20)    NOT NULL,   -- per-row attribute, see notes above
    Inventory_Level    INT            NOT NULL,
    Units_Sold         INT            NOT NULL,
    Units_Ordered      INT            NOT NULL,
    Demand_Forecast    DECIMAL(10, 2) NOT NULL,
    Price              DECIMAL(10, 2) NOT NULL,
    Discount           DECIMAL(5, 2)  NOT NULL,
    Weather_Condition  VARCHAR(20)    NOT NULL,
    Holiday_Promotion  TINYINT(1)     NOT NULL,
    Competitor_Pricing DECIMAL(10, 2) NOT NULL,
    Seasonality        VARCHAR(20)    NOT NULL,
    PRIMARY KEY (Date, Store_ID, Product_ID),
    FOREIGN KEY (Store_ID) REFERENCES stores(Store_ID),
    FOREIGN KEY (Product_ID) REFERENCES products(Product_ID)
);

CREATE INDEX idx_facts_store   ON inventory_facts (Store_ID);
CREATE INDEX idx_facts_product ON inventory_facts (Product_ID);
CREATE INDEX idx_facts_date    ON inventory_facts (Date);

-- Backward-compatible flat view: every query written against the original
-- single-table `retail_data` (see SQL-scripts.pdf) still works unchanged.
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
