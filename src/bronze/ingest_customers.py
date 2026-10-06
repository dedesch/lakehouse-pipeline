"""Bronze layer: ingest raw customers as-is into the bronze zone.

Reads data/raw/customers.csv (header, all columns as strings -- no casting,
no renaming of the source columns) and writes it, partitioned by
`ingestion_date`, to an Iceberg table at local.bronze.customers.
"""

from pyspark.sql import functions as F

from src.common.spark_session import get_spark

RAW_PATH = "data/raw/customers.csv"
ICEBERG_TABLE = "local.bronze.customers"
PARTITION_COLUMN = "ingestion_date"


def ingest_customers(spark=None):
    spark = spark or get_spark("bronze_ingest_customers")

    customers = (
        spark.read.option("header", True).csv(RAW_PATH)
        .withColumn(PARTITION_COLUMN, F.current_date())
    )

    row_count = customers.count()
    print(f"ingest_customers: read {row_count:,} rows from {RAW_PATH}")

    spark.sql("CREATE NAMESPACE IF NOT EXISTS local.bronze")
    if spark.catalog.tableExists(ICEBERG_TABLE):
        customers.writeTo(ICEBERG_TABLE).overwritePartitions()
    else:
        customers.writeTo(ICEBERG_TABLE).using("iceberg").partitionedBy(F.col(PARTITION_COLUMN)).create()
    print(f"ingest_customers: wrote iceberg table {ICEBERG_TABLE} (partitioned by {PARTITION_COLUMN})")

    return customers


if __name__ == "__main__":
    ingest_customers()
