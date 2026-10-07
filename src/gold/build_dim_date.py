"""Gold layer: build the date dimension.

Creates one row per distinct calendar date found in Silver orders.
"""

from pyspark.sql import functions as F

from src.common.spark_session import get_spark

SILVER_TABLE = "local.silver.orders"
GOLD_TABLE = "local.gold.dim_date"


def build_dim_date(spark=None):
    spark = spark or get_spark("gold_build_dim_date")

    silver = spark.table(SILVER_TABLE)

    # InvoiceDate is already a parsed timestamp in Silver; rows where it
    # could not be parsed (see src/silver/clean_orders.py) are null and are
    # dropped here -- there is no date to build a dimension row from.
    dates = (
        silver.select(F.to_date(F.col("InvoiceDate")).alias("date"))
        .filter(F.col("date").isNotNull())
        .distinct()
    )

    dim_date = dates.select(
        # Integer surrogate key in yyyyMMdd form, e.g. 2010-12-01 -> 20101201.
        F.date_format(F.col("date"), "yyyyMMdd").cast("int").alias("date_key"),
        F.col("date"),
        F.dayofmonth(F.col("date")).alias("day"),
        F.month(F.col("date")).alias("month"),
        F.date_format(F.col("date"), "MMMM").alias("month_name"),
        F.quarter(F.col("date")).alias("quarter"),
        F.year(F.col("date")).alias("year"),
        F.date_format(F.col("date"), "EEEE").alias("day_of_week"),
    )

    row_count = dim_date.count()
    print(f"build_dim_date: writing {row_count:,} distinct dates")

    spark.sql("CREATE NAMESPACE IF NOT EXISTS local.gold")
    dim_date.writeTo(GOLD_TABLE).using("iceberg").createOrReplace()
    print(f"build_dim_date: wrote iceberg table {GOLD_TABLE}")

    return dim_date


if __name__ == "__main__":
    build_dim_date()
