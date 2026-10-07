"""Gold layer: build the order fact table.

Enriches Silver order lines with the reference customer, product and date
dimensions. Current SCD2 records are used because the available ingestion
dates do not represent the historical effective dates of the source orders.
"""

from pyspark.sql import functions as F

from src.common.spark_session import get_spark


SILVER_TABLE = "local.silver.orders"
DIM_CUSTOMER_TABLE = "local.gold.dim_customer"
DIM_PRODUCT_TABLE = "local.gold.dim_product"
DIM_DATE_TABLE = "local.gold.dim_date"
GOLD_TABLE = "local.gold.fact_orders"


def build_fact_orders(spark=None):
    spark = spark or get_spark("gold_build_fact_orders")

    orders = (
        spark.table(SILVER_TABLE)
        .withColumn("order_date", F.to_date("InvoiceDate"))
    )

    dim_date = spark.table(DIM_DATE_TABLE).select("date", "date_key")

    # Use the current dimension records as reference values for this dataset.
    products = (
        spark.table(DIM_PRODUCT_TABLE)
        .filter(F.col("is_current"))
        .select("stock_code", "product_key", "unit_price")
    )

    customers = (
        spark.table(DIM_CUSTOMER_TABLE)
        .filter(F.col("is_current"))
        .select("customer_id", "customer_key")
    )

    joined = (
        orders
        .join(dim_date, orders["order_date"] == dim_date["date"], "left")
        .join(products, orders["StockCode"] == products["stock_code"], "inner")
        .join(customers, orders["CustomerID"] == customers["customer_id"], "left")
    )

    # Build one fact row per Silver order line.
    fact_orders = joined.select(
        F.xxhash64(
            "InvoiceNo",
            "StockCode",
            "Quantity",
            "InvoiceDate",
            "CustomerID",
        ).alias("order_key"),
        F.col("InvoiceNo").alias("invoice_no"),
        F.coalesce("customer_key", F.lit(-1).cast("long")).alias("customer_key"),
        "product_key",
        "date_key",
        F.col("Quantity").alias("quantity"),
        "unit_price",
        (F.col("Quantity") * F.col("unit_price")).alias("revenue"),
        "is_cancellation",
    )

    print(f"Writing {fact_orders.count():,} order lines")

    spark.sql("CREATE NAMESPACE IF NOT EXISTS local.gold")
    fact_orders.writeTo(GOLD_TABLE).using("iceberg").createOrReplace()

    print(f"Wrote {GOLD_TABLE}")

    return fact_orders


if __name__ == "__main__":
    build_fact_orders()