"""Silver layer: clean and conform customers.

Reads customers from Bronze and normalizes the customer attributes.

Customer-country conflicts and null CustomerIDs are intentionally kept
in Silver and handled later as data quality concerns.
"""

from pyspark.sql import functions as F

from src.common.spark_session import get_spark


BRONZE_TABLE = "local.bronze.customers"
SILVER_TABLE = "local.silver.customers"
PARTITION_COLUMN = "ingestion_date"


def clean_customers(spark=None):
    spark = spark or get_spark("silver_clean_customers")

    bronze = spark.table(BRONZE_TABLE)
    bronze_count = bronze.count()

    print(f"Read {bronze_count:,} rows from {BRONZE_TABLE}")

    # Normalize customer attributes while preserving the source records.
    customers = bronze.select(
        F.trim("CustomerID").alias("CustomerID"),
        F.trim("Country").alias("Country"),
        "ingestion_date",
    )

    spark.sql("CREATE NAMESPACE IF NOT EXISTS local.silver")

    # Replace only the ingestion partition processed by this run.
    if spark.catalog.tableExists(SILVER_TABLE):
        customers.writeTo(SILVER_TABLE).overwritePartitions()
    else:
        (
            customers.writeTo(SILVER_TABLE)
            .using("iceberg")
            .partitionedBy(F.col(PARTITION_COLUMN))
            .create()
        )

    print(f"Wrote {SILVER_TABLE}")

    return customers


if __name__ == "__main__":
    clean_customers()