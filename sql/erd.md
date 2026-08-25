# Entity-Relationship Diagram

Normalized schema for `retail_db` (see [schema.sql](schema.sql) for the DDL, and [build_database.py](../db/build_database.py) for the runnable SQLite build).

```mermaid
erDiagram
    STORES ||--o{ INVENTORY_FACTS : "stocks"
    PRODUCTS ||--o{ INVENTORY_FACTS : "is stocked as"

    STORES {
        varchar Store_ID PK
    }

    PRODUCTS {
        varchar Product_ID PK
        varchar Category
    }

    INVENTORY_FACTS {
        varchar Date PK
        varchar Store_ID PK,FK
        varchar Product_ID PK,FK
        varchar Region
        int Inventory_Level
        int Units_Sold
        int Units_Ordered
        decimal Demand_Forecast
        decimal Price
        decimal Discount
        varchar Weather_Condition
        tinyint Holiday_Promotion
        decimal Competitor_Pricing
        varchar Seasonality
    }
```

## Why Region isn't its own dimension

Profiling `inventory_forecasting.csv` showed every `Store_ID` paired with all 4 regions, and all 150 `(Store_ID, Product_ID)` pairs span multiple regions across dates. Region is not a fixed attribute of a store or a product in this dataset — it has to live on the fact row. `Category`, by contrast, is a true 1:1 attribute of `Product_ID` (30 distinct pairs for 30 products), so it normalizes onto `products`.

A `retail_data` view joins the three tables back into the original flat shape, so every query written against the single flat table (see [SQL-scripts.pdf](../SQL-scripts.pdf)) still runs unmodified.
