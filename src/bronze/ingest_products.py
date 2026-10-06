"""Bronze layer: ingest raw products as-is into the bronze zone.

Reads data/raw/products.csv (header, all columns as strings -- no casting,
no renaming of the source columns) and writes it, partitioned by
`ingestion_date`, to an Iceberg table at local.bronze.products.
"""

from pyspark.sql import functions as F

from src.common.spark_session import get_spark

RAW_PATH = "data/raw/products.csv"
ICEBERG_TABLE = "local.bronze.products"
PARTITION_COLUMN = "ingestion_date"


def ingest_products(spark=None):
    spark = spark or get_spark("bronze_ingest_products")

    products = (
        spark.read.option("header", True).csv(RAW_PATH)
        .withColumn(PARTITION_COLUMN, F.current_date())
    )

    row_count = products.count()
    print(f"ingest_products: read {row_count:,} rows from {RAW_PATH}")

    spark.sql("CREATE NAMESPACE IF NOT EXISTS local.bronze")
    if spark.catalog.tableExists(ICEBERG_TABLE):
        products.writeTo(ICEBERG_TABLE).overwritePartitions()
    else:
        products.writeTo(ICEBERG_TABLE).using("iceberg").partitionedBy(F.col(PARTITION_COLUMN)).create()
    print(f"ingest_products: wrote iceberg table {ICEBERG_TABLE} (partitioned by {PARTITION_COLUMN})")

    return products


if __name__ == "__main__":
    ingest_products()
