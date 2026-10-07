"""Analytics: top 10 countries by number of customers."""

from pyspark.sql import functions as F

from src.common.spark_session import get_spark

DIM_CUSTOMER_TABLE = "local.gold.dim_customer"


def top_countries_by_customers(spark=None):
    spark = spark or get_spark("top_countries_by_customers")

    # Current customer versions only, excluding the Unknown Customer sentinel.
    customers = spark.table(DIM_CUSTOMER_TABLE).filter(
        F.col("is_current") & (F.col("customer_key") != -1)
    )

    result = (
        customers.groupBy("country")
        .agg(F.countDistinct("customer_id").alias("customer_count"))
        .orderBy(F.desc("customer_count"))
        .limit(10)
    )

    result.show(truncate=False)
    return result


if __name__ == "__main__":
    top_countries_by_customers()
