"""Unit tests for the silver layer cleansing logic."""

import datetime

from src.silver import clean_orders as clean_orders_module
from tests.helpers import write_test_table

BRONZE_ORDERS_SCHEMA = (
    "InvoiceNo string, StockCode string, Quantity string, InvoiceDate string, "
    "CustomerID string, ingestion_date date, ingestion_hour int"
)


def _run_clean_orders(spark, monkeypatch, rows, bronze_name, silver_name):
    monkeypatch.setattr(clean_orders_module, "BRONZE_TABLE", bronze_name)
    monkeypatch.setattr(clean_orders_module, "SILVER_TABLE", silver_name)
    write_test_table(spark, bronze_name, rows, BRONZE_ORDERS_SCHEMA)
    return clean_orders_module.clean_orders(spark)


def test_clean_orders_normalizes_stock_code(spark, monkeypatch):
    rows = [("536370", " abc123 ", "1", "12/1/2010 8:45", "12345", datetime.date(2026, 1, 1), 10)]
    result = _run_clean_orders(
        spark, monkeypatch, rows,
        "local.pytest.normalize_bronze", "local.pytest.normalize_silver",
    )
    assert result.collect()[0]["StockCode"] == "ABC123"


def test_clean_orders_removes_exact_duplicate_order_lines(spark, monkeypatch):
    row = ("536370", "ABC123", "1", "12/1/2010 8:45", "12345", datetime.date(2026, 1, 1), 10)
    result = _run_clean_orders(
        spark, monkeypatch, [row, row],
        "local.pytest.dedup_bronze", "local.pytest.dedup_silver",
    )
    assert result.count() == 1


def test_clean_orders_preserves_negative_quantity_and_cancellation(spark, monkeypatch):
    # "C"-prefixed InvoiceNo (cancellation) with a negative quantity: neither
    # should be dropped or altered by cleansing.
    rows = [("C536370", "ABC123", "-5", "12/1/2010 8:45", "12345", datetime.date(2026, 1, 1), 10)]
    result = _run_clean_orders(
        spark, monkeypatch, rows,
        "local.pytest.negative_bronze", "local.pytest.negative_silver",
    )
    row = result.collect()[0]
    assert row["Quantity"] == -5
    assert row["is_cancellation"] is True
