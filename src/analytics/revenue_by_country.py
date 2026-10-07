"""Analytics: revenue distribution by country."""

from pyspark.sql import functions as F

from src.common.spark_session import get_spark

FACT_ORDERS_TABLE = "local.gold.fact_orders"
DIM_CUSTOMER_TABLE = "local.gold.dim_customer"


def revenue_by_country(spark=None):
    spark = spark or get_spark("revenue_by_country")

    fact_orders = spark.table(FACT_ORDERS_TABLE)

    # Current versions only: fact_orders.customer_key always references a
    # current dim_customer row (see build_fact_orders.py), but joining
    # against every SCD2 version would double-count customers whose
    # historical and current version happen to share a customer_key.
    dim_customer = spark.table(DIM_CUSTOMER_TABLE).filter(F.col("is_current"))

    # Unknown Customer (customer_key = -1) is kept, not filtered out, so
    # orders without a resolvable customer still show up under "Unknown".
    result = (
        fact_orders.join(dim_customer, "customer_key")
        .groupBy("country")
        .agg(F.sum("revenue").alias("total_revenue"))
        .orderBy(F.desc("total_revenue"))
    )

    result.show(truncate=False)
    return result


if __name__ == "__main__":
    revenue_by_country()
