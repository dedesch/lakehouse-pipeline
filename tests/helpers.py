"""Shared test helpers.

Tests monkeypatch each pipeline module's table-name constants to point at
small tables in a dedicated local.pytest namespace, then call the real
production function -- so the actual transformation logic is exercised,
without touching the real Bronze/Silver/Gold tables.
"""

TEST_NAMESPACE = "local.pytest"


def write_test_table(spark, name, rows, schema):
    spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {TEST_NAMESPACE}")
    spark.createDataFrame(rows, schema).writeTo(name).using("iceberg").createOrReplace()
