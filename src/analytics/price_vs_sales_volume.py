"""Analytics: relationship between average unit price and sales volume."""

from pyspark.sql import functions as F

from src.common.spark_session import get_spark

FACT_ORDERS_TABLE = "local.gold.fact_orders"


def price_vs_sales_volume(spark=None):
    spark = spark or get_spark("price_vs_sales_volume")

    # sum(quantity) keeps negative values (returns/cancellations) as-is --
    # not filtered or clamped -- so sales_volume reflects net quantity.
    result = (
        spark.table(FACT_ORDERS_TABLE)
        .groupBy("product_key")
        .agg(
            F.avg("unit_price").alias("avg_unit_price"),
            F.sum("quantity").alias("sales_volume"),
        )
    )

    result.show(truncate=False)
    return result


if __name__ == "__main__":
    price_vs_sales_volume()
