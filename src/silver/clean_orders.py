"""Silver layer: clean and conform orders.

Reads orders from Bronze, normalizes business keys, applies the expected
data types, removes exact duplicates and adds a cancellation flag.

Negative quantities and orders without a CustomerID are intentionally
kept. Their treatment depends on business rules and is handled later.
"""

from pyspark.sql import functions as F

from src.common.spark_session import get_spark


BRONZE_TABLE = "local.bronze.orders"
SILVER_TABLE = "local.silver.orders"
PARTITION_COLUMNS = ["ingestion_date", "ingestion_hour"]

INVOICE_DATE_FORMAT = "M/d/yyyy H:mm"


def clean_orders(spark=None):
    spark = spark or get_spark("silver_clean_orders")

    bronze = spark.table(BRONZE_TABLE)
    bronze_count = bronze.count()

    print(f"Read {bronze_count:,} rows from {BRONZE_TABLE}")

    # Clean the source values and apply the expected data types.
    orders = bronze.select(
        F.trim("InvoiceNo").alias("InvoiceNo"),
        F.upper(F.trim("StockCode")).alias("StockCode"),
        F.col("Quantity").cast("int").alias("Quantity"),
        F.try_to_timestamp(
            F.col("InvoiceDate"),
            F.lit(INVOICE_DATE_FORMAT)
        ).alias("InvoiceDate"),
        F.trim("CustomerID").alias("CustomerID"),
        "ingestion_date",
        "ingestion_hour",
    )

    # Remove exact order-line duplicates only. The same product may
    # legitimately appear several times within the same invoice.
    orders = orders.dropDuplicates(
        ["InvoiceNo", "StockCode", "Quantity", "InvoiceDate", "CustomerID"]
    )

    # Cancellations are identified by the source InvoiceNo convention.
    # They are flagged rather than removed.
    orders = orders.withColumn(
        "is_cancellation",
        F.col("InvoiceNo").startswith("C")
    )

    silver_count = orders.count()

    print(
        f"Removed {bronze_count - silver_count:,} exact duplicates; "
        f"{silver_count:,} rows remain"
    )

    spark.sql("CREATE NAMESPACE IF NOT EXISTS local.silver")

    # Replace only the ingestion partitions processed by this run.
    if spark.catalog.tableExists(SILVER_TABLE):
        orders.writeTo(SILVER_TABLE).overwritePartitions()
    else:
        (
            orders.writeTo(SILVER_TABLE)
            .using("iceberg")
            .partitionedBy(
                F.col("ingestion_date"),
                F.col("ingestion_hour")
            )
            .create()
        )

    print(f"Wrote {SILVER_TABLE}")

    return orders


if __name__ == "__main__":
    clean_orders()