"""Unit tests for the gold layer dimensional model build."""

import datetime

from src.gold import build_dim_customer as build_dim_customer_module
from src.gold import build_dim_product as build_dim_product_module
from src.gold import build_fact_orders as build_fact_orders_module
from tests.helpers import write_test_table

DATE = datetime.date(2026, 1, 1)

SILVER_CUSTOMERS_SCHEMA = "CustomerID string, Country string, ingestion_date date"
SILVER_PRODUCTS_SCHEMA = "StockCode string, Description string, UnitPrice double, ingestion_date date"
SILVER_ORDERS_SCHEMA = (
    "InvoiceNo string, StockCode string, Quantity int, InvoiceDate timestamp, "
    "CustomerID string, ingestion_date date, ingestion_hour int, is_cancellation boolean"
)
DIM_CUSTOMER_MIN_SCHEMA = "customer_key long, customer_id string, is_current boolean"
DIM_PRODUCT_MIN_SCHEMA = "product_key long, stock_code string, unit_price double, is_current boolean"
DIM_DATE_MIN_SCHEMA = "date date, date_key int"


def test_dim_customer_excludes_same_snapshot_country_conflict(spark, monkeypatch):
    # C1 has two conflicting countries in the same (CustomerID, ingestion_date)
    # snapshot; C2 is a clean control row that should still come through.
    rows = [
        ("C1", "France", DATE),
        ("C1", "Germany", DATE),
        ("C2", "Spain", DATE),
    ]
    monkeypatch.setattr(build_dim_customer_module, "SILVER_TABLE", "local.pytest.dimcust_silver")
    monkeypatch.setattr(build_dim_customer_module, "GOLD_TABLE", "local.pytest.dimcust_gold")
    write_test_table(spark, "local.pytest.dimcust_silver", rows, SILVER_CUSTOMERS_SCHEMA)

    result = build_dim_customer_module.build_dim_customer(spark)

    customer_ids = {r["customer_id"] for r in result.collect()}
    assert "C1" not in customer_ids
    assert "C2" in customer_ids


def test_dim_product_excludes_same_snapshot_conflicting_state(spark, monkeypatch):
    # P1 has two conflicting prices in the same (StockCode, ingestion_date)
    # snapshot; P2 is a clean control row that should still come through.
    rows = [
        ("P1", "Widget", 1.0, DATE),
        ("P1", "Widget", 2.0, DATE),
        ("P2", "Gadget", 5.0, DATE),
    ]
    monkeypatch.setattr(build_dim_product_module, "SILVER_TABLE", "local.pytest.dimprod_silver")
    monkeypatch.setattr(build_dim_product_module, "GOLD_TABLE", "local.pytest.dimprod_gold")
    write_test_table(spark, "local.pytest.dimprod_silver", rows, SILVER_PRODUCTS_SCHEMA)

    result = build_dim_product_module.build_dim_product(spark)

    stock_codes = {r["stock_code"] for r in result.collect()}
    assert "P1" not in stock_codes
    assert "P2" in stock_codes


def _run_build_fact_orders(spark, monkeypatch, orders_rows, customer_rows, product_rows, date_rows, suffix):
    names = {
        "SILVER_TABLE": f"local.pytest.fact_{suffix}_orders",
        "DIM_CUSTOMER_TABLE": f"local.pytest.fact_{suffix}_dim_customer",
        "DIM_PRODUCT_TABLE": f"local.pytest.fact_{suffix}_dim_product",
        "DIM_DATE_TABLE": f"local.pytest.fact_{suffix}_dim_date",
        "GOLD_TABLE": f"local.pytest.fact_{suffix}_gold",
    }
    for attr, name in names.items():
        monkeypatch.setattr(build_fact_orders_module, attr, name)

    write_test_table(spark, names["SILVER_TABLE"], orders_rows, SILVER_ORDERS_SCHEMA)
    write_test_table(spark, names["DIM_CUSTOMER_TABLE"], customer_rows, DIM_CUSTOMER_MIN_SCHEMA)
    write_test_table(spark, names["DIM_PRODUCT_TABLE"], product_rows, DIM_PRODUCT_MIN_SCHEMA)
    write_test_table(spark, names["DIM_DATE_TABLE"], date_rows, DIM_DATE_MIN_SCHEMA)

    return build_fact_orders_module.build_fact_orders(spark)


def test_fact_orders_maps_unmatched_customer_to_unknown(spark, monkeypatch):
    # One null CustomerID, one CustomerID that doesn't exist in dim_customer;
    # both must resolve to the Unknown Customer key, not be dropped.
    orders_rows = [
        ("1001", "P1", 2, datetime.datetime(2026, 1, 1, 10, 0), None, DATE, 10, False),
        ("1002", "P1", 1, datetime.datetime(2026, 1, 1, 10, 0), "NOT_IN_DIM", DATE, 10, False),
    ]
    customer_rows = [(999, "SOMEONE_ELSE", True)]
    product_rows = [(111, "P1", 2.5, True)]
    date_rows = [(DATE, 20260101)]

    result = _run_build_fact_orders(
        spark, monkeypatch, orders_rows, customer_rows, product_rows, date_rows, "unknown"
    )

    assert [r["customer_key"] for r in result.collect()] == [-1, -1]


def test_fact_orders_calculates_revenue(spark, monkeypatch):
    orders_rows = [
        ("2001", "P1", 3, datetime.datetime(2026, 1, 1, 10, 0), "CUST1", DATE, 10, False),
    ]
    customer_rows = [(1, "CUST1", True)]
    product_rows = [(111, "P1", 4.5, True)]
    date_rows = [(DATE, 20260101)]

    result = _run_build_fact_orders(
        spark, monkeypatch, orders_rows, customer_rows, product_rows, date_rows, "revenue"
    )

    row = result.collect()[0]
    assert row["revenue"] == 13.5
