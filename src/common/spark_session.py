"""Shared SparkSession factory.

Builds a SparkSession configured with the Iceberg Spark extension and a
single local (filesystem-backed, "hadoop" type) Iceberg catalog named
`local`, reused across bronze/silver/gold scripts. Tables are addressed as
`local.<layer>.<table>`, e.g. `local.bronze.customers`; they are physically
stored under WAREHOUSE_PATH.
"""

from pyspark.sql import SparkSession

ICEBERG_PACKAGE = "org.apache.iceberg:iceberg-spark-runtime-4.1_2.13:1.11.0"

ICEBERG_CATALOG = "local"
WAREHOUSE_PATH = "data/warehouse"


def get_spark(app_name: str) -> SparkSession:
    builder = (
        SparkSession.builder.appName(app_name)
        .master("local[*]")
        .config("spark.jars.packages", ICEBERG_PACKAGE)
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        .config(f"spark.sql.catalog.{ICEBERG_CATALOG}", "org.apache.iceberg.spark.SparkCatalog")
        .config(f"spark.sql.catalog.{ICEBERG_CATALOG}.type", "hadoop")
        .config(f"spark.sql.catalog.{ICEBERG_CATALOG}.warehouse", WAREHOUSE_PATH)
        .config("spark.sql.codegen.wholeStage", "false")
        .config("spark.sql.codegen.factoryMode", "NO_CODEGEN")
    )
    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    return spark
