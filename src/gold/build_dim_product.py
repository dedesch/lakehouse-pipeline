"""Gold layer: build the product dimension as SCD Type 2.

Tracks product description and price changes over time using the Silver
ingestion date as the effective date of each snapshot.
"""

from pyspark.sql import functions as F
from pyspark.sql.window import Window

from src.common.spark_session import get_spark


SILVER_TABLE = "local.silver.products"
GOLD_TABLE = "local.gold.dim_product"


def build_dim_product(spark=None):
    spark = spark or get_spark("gold_build_dim_product")

    products = spark.table(SILVER_TABLE)

    # Exclude product snapshots with conflicting states before building SCD2 history.
    ambiguous_products = (
        products
        .groupBy("StockCode", "ingestion_date")
        .agg(
            F.countDistinct(
                F.struct("Description", "UnitPrice")
            ).alias("state_count")
        )
        .filter(F.col("state_count") > 1)
        .select("StockCode", "ingestion_date")
    )

    products = products.join(
        ambiguous_products,
        ["StockCode", "ingestion_date"],
        "left_anti",
    )

    product_window = Window.partitionBy("StockCode").orderBy("ingestion_date")

    # Detect changes to the tracked product attributes.
    products = (
        products
        .withColumn(
            "previous_description",
            F.lag("Description").over(product_window),
        )
        .withColumn(
            "previous_unit_price",
            F.lag("UnitPrice").over(product_window),
        )
        .withColumn(
            "is_new_version",
            F.col("previous_description").isNull()
            | (F.col("Description") != F.col("previous_description"))
            | (F.col("UnitPrice") != F.col("previous_unit_price")),
        )
    )

    # Group consecutive snapshots belonging to the same product version.
    products = products.withColumn(
        "version",
        F.sum(F.col("is_new_version").cast("int")).over(
            product_window.rowsBetween(
                Window.unboundedPreceding,
                Window.currentRow,
            )
        ),
    )

    versions = (
        products
        .groupBy("StockCode", "version")
        .agg(
            F.first("Description").alias("description"),
            F.first("UnitPrice").alias("unit_price"),
            F.min("ingestion_date").alias("valid_from"),
        )
    )

    version_window = Window.partitionBy("StockCode").orderBy("valid_from")

    versions = versions.withColumn(
        "next_valid_from",
        F.lead("valid_from").over(version_window),
    )

    dim_product = versions.select(
        F.xxhash64("StockCode", "valid_from").alias("product_key"),
        F.col("StockCode").alias("stock_code"),
        "description",
        "unit_price",
        "valid_from",
        F.date_sub("next_valid_from", 1).alias("valid_to"),
        F.col("next_valid_from").isNull().alias("is_current"),
    )

    print(f"Writing {dim_product.count():,} product versions")

    spark.sql("CREATE NAMESPACE IF NOT EXISTS local.gold")
    dim_product.writeTo(GOLD_TABLE).using("iceberg").createOrReplace()

    print(f"Wrote {GOLD_TABLE}")

    return dim_product


if __name__ == "__main__":
    build_dim_product()