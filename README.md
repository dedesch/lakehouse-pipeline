# Lakehouse Pipeline

## 1. Overview

A Bronze / Silver / Gold data pipeline built with PySpark, ingesting
customers, products and orders and modelling them into a dimensional star
schema. Tables are stored as [Apache Iceberg](https://iceberg.apache.org/)
tables (local `hadoop` catalog) rather than plain files, so each layer gets
schema, snapshots and atomic writes.

## 2. Architecture

- **Bronze** (`src/bronze`) -- raw ingestion, as-is from `data/raw/*.csv`.
  Each row is tagged with ingestion metadata (`ingestion_date`, and
  `ingestion_hour` for orders, which is ingested hourly; customers and
  products are ingested daily) used as the partition key.
- **Silver** (`src/silver`) -- cleaning, normalization and technical data
  quality handling: type casting, business-key normalization, exact-duplicate
  removal, and date parsing. No business-level data quality decisions are
  made here (see [Key implementation decisions](#5-key-implementation-decisions)).
- **Gold** (`src/gold`) -- star schema:
  - `fact_orders`
  - `dim_customer`
  - `dim_product`
  - `dim_date`

  `dim_customer` and `dim_product` are Slowly Changing Dimensions (Type 2):
  changes to a customer's country or a product's description/price across
  different ingestion snapshots are tracked as separate, time-bounded
  versions (`valid_from` / `valid_to` / `is_current`).

## 3. Project structure

- `src/bronze` -- raw ingestion scripts (one per source).
- `src/silver` -- cleansing/conforming scripts.
- `src/gold` -- dimension and fact table builds.
- `src/analytics` -- the four requested analytic queries.
- `tests` -- pytest suite covering the most important transformation rules.
- `docs` -- dimensional model and data quality documentation.
- `notebooks` -- exploratory data analysis notebook behind `ANALYSIS.md`.

## 4. How to run

Requires Python 3.14 and a JDK compatible with Spark 4.1 (e.g. Temurin 21).
`.env/bin/activate` pins `JAVA_HOME` to a working JDK for this project --
without it, Spark/Iceberg fail to start a session. The Iceberg runtime JAR
is resolved automatically at startup (`spark.jars.packages`); no manual JAR
download is needed.

```bash
python3.14 -m venv .env
source .env/bin/activate
pip install -r requirements.txt
```

**Full pipeline** (Bronze -> Silver -> Gold -> tests, in one go):

```bash
./scripts/build.sh
```

**Individual stages:**

```bash
# Bronze
python -m src.bronze.ingest_customers
python -m src.bronze.ingest_products
python -m src.bronze.ingest_orders

# Silver
python -m src.silver.clean_customers
python -m src.silver.clean_products
python -m src.silver.clean_orders

# Gold
python -m src.gold.build_dim_customer
python -m src.gold.build_dim_product
python -m src.gold.build_dim_date
python -m src.gold.build_fact_orders

# Analytics
python -m src.analytics.top_countries_by_customers
python -m src.analytics.revenue_by_country
python -m src.analytics.price_vs_sales_volume
python -m src.analytics.top_product_price_drops
```

**Tests:**

```bash
pytest
```

## 5. Key implementation decisions

- Exact duplicate order lines are removed in Silver.
- `StockCode` is normalized (`upper(trim(...))`) in both orders and products.
- Cancellations (`InvoiceNo` starting with `C`) and negative quantities are
  preserved, not removed.
- Conflicting customer or product states within the same ingestion snapshot
  are treated as a data quality issue and excluded from Gold.
- Genuine changes across different snapshots are tracked as SCD2 history.
- Orders with a missing or unmatched `CustomerID` resolve to the Unknown
  Customer dimension member (`customer_key = -1`).

## 6. Known limitation

`ingestion_date` is a technical processing date (when a Bronze snapshot was
taken), not the historical period the provided orders actually cover --
`InvoiceDate` predates every `ingestion_date` in this dataset. Because of
this, `fact_orders` cannot be temporally joined against SCD2 validity
windows and instead uses each dimension's current/reference record for
every order line. Accurate historical pricing/attribution would require
source data with effective-dated history aligned to the order period.

## 7. Analytics

See `src/analytics`:

- `top_countries_by_customers.py` -- top 10 countries by number of customers.
- `revenue_by_country.py` -- revenue distribution by country.
- `price_vs_sales_volume.py` -- average unit price vs. sales volume, per product.
- `top_product_price_drops.py` -- top 3 products by unit price drop last month.

The price-drop analysis depends on having multiple historical SCD2 product
snapshots; with only the provided snapshot(s), it may correctly return an
empty result rather than a fabricated one.

## 8. Documentation

- [docs/data_model.md](docs/data_model.md) -- dimensional model and ER diagram.
- [ANALYSIS.md](ANALYSIS.md) -- data exploration journal (findings, issues, assumptions).
- [notebooks/data_analysis.ipynb](notebooks/data_analysis.ipynb) -- the exploration notebook behind it.

## AI usage disclosure

AI tools were used selectively during this exercise as a development assistant, mainly for:

- generating and refining unit tests;
- rephrasing and improving documentation;
- accelerating some of the more complex exploratory data analysis;
- assisting with parts of the Gold-layer implementation and analytics.

AI-generated suggestions were reviewed and adapted before being included. Data quality decisions, modelling choices, assumptions, and the final implementation were validated against the provided dataset.