"""Silver layer: clean and conform products.

Reads products from Bronze, normalizes product identifiers and descriptions,
casts prices to the expected type, and removes records identified during
profiling as operational rather than actual product records.

Products with multiple remaining prices are intentionally kept in Silver.
"""

from pyspark.sql import functions as F

from src.common.spark_session import get_spark


BRONZE_TABLE = "local.bronze.products"
SILVER_TABLE = "local.silver.products"
PARTITION_COLUMN = "ingestion_date"

# Conservative list of operational descriptions identified during profiling.
OPERATIONAL_DESCRIPTIONS = [
    "check",
    "damaged",
    "found",
    "adjustment",
    "amazon",
    "dotcom",
    "wet damaged",
    "wet/rusty",
    "stock check",
]


def clean_products(spark=None):
    spark = spark or get_spark("silver_clean_products")

    bronze = spark.table(BRONZE_TABLE)
    bronze_count = bronze.count()

    print(f"Read {bronze_count:,} rows from {BRONZE_TABLE}")

    # Clean product attributes and apply the expected data types.
    products = bronze.select(
        F.upper(F.trim("StockCode")).alias("StockCode"),
        F.trim("Description").alias("Description"),
        F.col("UnitPrice").cast("double").alias("UnitPrice"),
        "ingestion_date",
    )

    # Remove records that cannot be considered reliable product descriptions.
    products = products.filter(
        F.col("Description").isNotNull()
        & (F.col("Description") != "")
        & ~F.lower(F.col("Description")).isin(OPERATIONAL_DESCRIPTIONS)
    )

    silver_count = products.count()

    print(
        f"Removed {bronze_count - silver_count:,} blank/operational records; "
        f"{silver_count:,} rows remain"
    )

    spark.sql("CREATE NAMESPACE IF NOT EXISTS local.silver")

    # Replace only the ingestion partition processed by this run.
    if spark.catalog.tableExists(SILVER_TABLE):
        products.writeTo(SILVER_TABLE).overwritePartitions()
    else:
        (
            products.writeTo(SILVER_TABLE)
            .using("iceberg")
            .partitionedBy(F.col(PARTITION_COLUMN))
            .create()
        )

    print(f"Wrote {SILVER_TABLE}")

    return products


if __name__ == "__main__":
    clean_products()