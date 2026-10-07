"""Gold layer: build the customer dimension as SCD Type 2.

Tracks customer country changes over time using the Silver ingestion date
as the effective date of each snapshot.
"""

from pyspark.sql import functions as F
from pyspark.sql.window import Window

from src.common.spark_session import get_spark


SILVER_TABLE = "local.silver.customers"
GOLD_TABLE = "local.gold.dim_customer"


def build_dim_customer(spark=None):
    spark = spark or get_spark("gold_build_dim_customer")

    # Null customer IDs are represented by the Unknown Customer.
    customers = (
        spark.table(SILVER_TABLE)
        .filter(F.col("CustomerID").isNotNull())
    )

    customer_window = Window.partitionBy("CustomerID").orderBy("ingestion_date")

    # Detect when a customer's country changes.
    customers = customers.withColumn(
        "previous_country",
        F.lag("Country").over(customer_window)
    ).withColumn(
        "is_new_version",
        F.col("previous_country").isNull()
        | (F.col("Country") != F.col("previous_country"))
    )

    # Group consecutive snapshots belonging to the same customer version.
    customers = customers.withColumn(
        "version",
        F.sum(F.col("is_new_version").cast("int")).over(
            customer_window.rowsBetween(
                Window.unboundedPreceding,
                Window.currentRow
            )
        )
    )

    versions = (
        customers
        .groupBy("CustomerID", "version")
        .agg(
            F.first("Country").alias("country"),
            F.min("ingestion_date").alias("valid_from"),
        )
    )

    version_window = Window.partitionBy("CustomerID").orderBy("valid_from")

    versions = versions.withColumn(
        "next_valid_from",
        F.lead("valid_from").over(version_window)
    )

    dim_customer = (
        versions
        .select(
            F.xxhash64("CustomerID", "valid_from").alias("customer_key"),
            F.col("CustomerID").alias("customer_id"),
            "country",
            "valid_from",
            F.date_sub("next_valid_from", 1).alias("valid_to"),
            F.col("next_valid_from").isNull().alias("is_current"),
        )
    )

    # Keep orders without a CustomerID through a standard Unknown member.
    unknown_customer = spark.range(1).select(
        F.lit(-1).cast("long").alias("customer_key"),
        F.lit(None).cast("string").alias("customer_id"),
        F.lit("Unknown").alias("country"),
        F.lit(None).cast("date").alias("valid_from"),
        F.lit(None).cast("date").alias("valid_to"),
        F.lit(True).alias("is_current"),
    )

    result = dim_customer.unionByName(unknown_customer)

    print(f"Writing {result.count():,} customer versions")

    spark.sql("CREATE NAMESPACE IF NOT EXISTS local.gold")
    result.writeTo(GOLD_TABLE).using("iceberg").createOrReplace()

    print(f"Wrote {GOLD_TABLE}")

    return result


if __name__ == "__main__":
    build_dim_customer()