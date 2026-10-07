"""Analytics: top 3 products with the largest unit price drop last month."""

from pyspark.sql import functions as F
from pyspark.sql.window import Window

from src.common.spark_session import get_spark

DIM_PRODUCT_TABLE = "local.gold.dim_product"


def top_product_price_drops(spark=None):
    spark = spark or get_spark("top_product_price_drops")

    dim_product = spark.table(DIM_PRODUCT_TABLE)

    by_stock_code = Window.partitionBy("stock_code").orderBy("valid_from")
    previous_unit_price = F.lag("unit_price").over(by_stock_code)
    previous_valid_from = F.lag("valid_from").over(by_stock_code)

    changes = (
        dim_product.select(
            "stock_code", "description", "unit_price", "valid_from",
            previous_unit_price.alias("previous_unit_price"),
            previous_valid_from.alias("previous_valid_from"),
        )
        .filter(
            # A real version change must come from a different snapshot
            # date -- two SCD2 rows sharing the same valid_from are
            # conflicting records from one source snapshot, not a genuine
            # price history step, and must not be read as a price drop.
            F.col("previous_valid_from").isNotNull()
            & (F.col("previous_valid_from") != F.col("valid_from"))
        )
        .withColumn("price_drop", F.col("previous_unit_price") - F.col("unit_price"))
        .filter(F.col("price_drop") > 0)
    )

    # "Last month" relative to whenever this runs, not a hardcoded date.
    month_start = F.trunc(F.current_date(), "MM")
    previous_month_start = F.add_months(month_start, -1)
    last_month_changes = changes.filter(
        (F.col("valid_from") >= previous_month_start) & (F.col("valid_from") < month_start)
    )

    result = (
        last_month_changes.select(
            "stock_code", "description", "previous_unit_price", "unit_price", "price_drop", "valid_from"
        )
        .orderBy(F.desc("price_drop"))
        .limit(3)
    )

    if result.isEmpty():
        print("No valid SCD2 price drops found for last month -- insufficient product price history in this dataset.")
    else:
        result.show(truncate=False)

    return result


if __name__ == "__main__":
    top_product_price_drops()
