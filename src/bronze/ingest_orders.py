"""Bronze layer: ingest raw orders as-is into the bronze zone.

Reads data/raw/orders.csv (header, all columns as strings -- no casting,
no renaming of the source columns) and writes it, partitioned by
`ingestion_date` and `ingestion_hour`, to an Iceberg table at
local.bronze.orders.
"""

from pyspark.sql import functions as F

from src.common.spark_session import get_spark

RAW_PATH = "data/raw/orders.csv"
ICEBERG_TABLE = "local.bronze.orders"
PARTITION_COLUMNS = ["ingestion_date", "ingestion_hour"]


def ingest_orders(spark=None):
    spark = spark or get_spark("bronze_ingest_orders")

    orders = (
        spark.read.option("header", True).csv(RAW_PATH)
        .withColumn("ingestion_date", F.current_date())
        .withColumn("ingestion_hour", F.hour(F.current_timestamp()))
    )

    row_count = orders.count()
    print(f"ingest_orders: read {row_count:,} rows from {RAW_PATH}")

    spark.sql("CREATE NAMESPACE IF NOT EXISTS local.bronze")
    if spark.catalog.tableExists(ICEBERG_TABLE):
        orders.writeTo(ICEBERG_TABLE).overwritePartitions()
    else:
        orders.writeTo(ICEBERG_TABLE).using("iceberg").partitionedBy(
            F.col(PARTITION_COLUMNS[0]), *[F.col(c) for c in PARTITION_COLUMNS[1:]]
        ).create()
    print(f"ingest_orders: wrote iceberg table {ICEBERG_TABLE} (partitioned by {', '.join(PARTITION_COLUMNS)})")

    return orders


if __name__ == "__main__":
    ingest_orders()
