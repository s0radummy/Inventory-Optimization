-- ============================================================================
-- SQLite-runnable equivalents of the KPI queries in SQL-scripts.pdf.
-- These run against db/inventory.db (built by db/build_database.py) via the
-- retail_data view, proving the normalized schema supports the same
-- analytics as the original flat-table script.
--
-- Differences from the MySQL originals:
--   - Date is already stored as ISO 'YYYY-MM-DD' text, so STR_TO_DATE is
--     unnecessary, DATE(Date) is used instead.
--   - YEARWEEK(..., 1) is replaced with STRFTIME('%Y-%W', Date), SQLite's
--     ISO-week equivalent.
-- ============================================================================

-- Total Inventory per Store
SELECT
    Store_ID,
    ROUND(SUM(Inventory_Level), 2) AS Total_Inventory
FROM retail_data
GROUP BY Store_ID
ORDER BY Total_Inventory DESC;

-- Total Inventory per Product
SELECT
    Product_ID,
    ROUND(SUM(Inventory_Level), 2) AS Total_Inventory
FROM retail_data
GROUP BY Product_ID
ORDER BY Total_Inventory DESC;

-- Inventory per Category and Region
SELECT
    Region,
    Category,
    ROUND(SUM(Inventory_Level), 2) AS Total_Inventory
FROM retail_data
GROUP BY Region, Category
ORDER BY Region, Total_Inventory DESC;

-- Reorder Point Estimation Using Moving Average and Category-based Lead Time
WITH demand_window AS (
    SELECT
        DATE(Date) AS date_converted,
        Store_ID,
        Product_ID,
        Category,
        Inventory_Level,
        Units_Sold,
        ROUND(
            AVG(Units_Sold) OVER (
                PARTITION BY Store_ID, Product_ID
                ORDER BY DATE(Date)
                ROWS BETWEEN 5 PRECEDING AND 1 PRECEDING
            ), 2
        ) AS avg_daily_demand
    FROM retail_data
),
add_lead_time AS (
    SELECT *,
        CASE
            WHEN Category IN ('Toys', 'Clothing', 'Groceries') THEN 3
            WHEN Category IN ('Furniture', 'Electronics') THEN 5
            ELSE 4
        END AS lead_time
    FROM demand_window
),
reorder_calc AS (
    SELECT
        date_converted AS Date,
        Store_ID,
        Product_ID,
        Category,
        Inventory_Level,
        avg_daily_demand,
        lead_time,
        ROUND(avg_daily_demand * lead_time, 2) AS reorder_point
    FROM add_lead_time
    WHERE avg_daily_demand IS NOT NULL
)
SELECT
    Date,
    Store_ID,
    Product_ID,
    Category,
    Inventory_Level,
    avg_daily_demand,
    lead_time,
    reorder_point,
    CASE
        WHEN Inventory_Level < reorder_point THEN 'Yes'
        ELSE 'No'
    END AS Low_Inventory_Risk
FROM reorder_calc
ORDER BY Date
LIMIT 1000;

-- Weekly Inventory Turnover for Each Product per Store
SELECT
    STRFTIME('%Y-%W', Date) AS Week,
    Product_ID,
    Store_ID,
    ROUND(SUM(Units_Sold) * 1.0 / NULLIF(AVG(Inventory_Level), 0), 2) AS weekly_turnover
FROM retail_data
GROUP BY Week, Product_ID, Store_ID
ORDER BY weekly_turnover DESC;

-- Quartile Classification of Weekly Inventory Turnover
-- (SQLite has no NTILE prior to 3.25; recent SQLite ships it, used here.)
WITH weekly_turnover_data AS (
    SELECT
        STRFTIME('%Y-%W', Date) AS Week,
        Product_ID,
        Store_ID,
        ROUND(SUM(Units_Sold) * 1.0 / NULLIF(AVG(Inventory_Level), 0), 2) AS turnover
    FROM retail_data
    GROUP BY Week, Product_ID, Store_ID
),
ranked_turnover AS (
    SELECT *, NTILE(4) OVER (ORDER BY turnover) AS quartile
    FROM weekly_turnover_data
)
SELECT
    quartile,
    ROUND(AVG(turnover), 2) AS avg_turnover,
    MIN(turnover) AS min_turnover,
    MAX(turnover) AS max_turnover
FROM ranked_turnover
GROUP BY quartile
ORDER BY quartile;

-- Overall Stockout Rate
SELECT
    ROUND(100.0 * SUM(CASE WHEN Units_Sold > Inventory_Level THEN 1 ELSE 0 END)
    / COUNT(*), 2) AS stockout_rate_percent
FROM retail_data;

-- Stockout Rate by Store
SELECT
    Store_ID,
    ROUND(
        100.0 * SUM(CASE WHEN Units_Sold > Inventory_Level THEN 1 ELSE 0 END) / COUNT(*),
        2
    ) AS stockout_rate_percent
FROM retail_data
GROUP BY Store_ID
ORDER BY stockout_rate_percent DESC;

-- Stockout Rate by Category
SELECT
    Category,
    ROUND(
        100.0 * SUM(CASE WHEN Units_Sold > Inventory_Level THEN 1 ELSE 0 END) / COUNT(*),
        2
    ) AS stockout_rate_percent
FROM retail_data
GROUP BY Category
ORDER BY stockout_rate_percent DESC;

-- Stockout Rate by Region
SELECT
    Region,
    ROUND(
        100.0 * SUM(CASE WHEN Units_Sold > Inventory_Level THEN 1 ELSE 0 END) / COUNT(*),
        2
    ) AS stockout_rate_percent
FROM retail_data
GROUP BY Region
ORDER BY stockout_rate_percent DESC;

-- Average Inventory Level by Product
SELECT
    Product_ID,
    ROUND(AVG(Inventory_Level), 2) AS avg_inventory_level
FROM retail_data
GROUP BY Product_ID
ORDER BY avg_inventory_level DESC
LIMIT 20;
