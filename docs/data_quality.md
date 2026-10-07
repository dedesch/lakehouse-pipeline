# Data Quality Rules

The following data quality rules are based on issues identified during data exploration and on the current Bronze/Silver/Gold implementation.

The pipeline distinguishes between:

- **Technical invalidity** — values that cannot be used as their intended type.
- **Source data ambiguity** — conflicting information for the same entity within the same snapshot.
- **Valid business events** — unusual but legitimate values, such as cancellations or negative quantities.

## Orders

| Layer | Rule | Expected behaviour | Action |
|---|---|---|---|
| Bronze/Silver | `InvoiceNo` must not be null or blank | Every order line identifies an invoice | Proposed — currently normalized but not explicitly validated |
| Bronze/Silver | `StockCode` must not be null or blank | Every order line identifies a product | Proposed — currently normalized but not explicitly validated |
| Silver | `Quantity` must be parseable as an integer | Invalid quantities should be identified | Partially implemented — cast to `int`; invalid values become `null`. Explicit validation/quarantine is proposed |
| Silver | `InvoiceDate` must be parseable as a timestamp | Invalid dates should be identified | Partially implemented — parsed with `try_to_timestamp`; invalid values become `null` |
| Silver | Exact duplicate order lines should be removed | One row per genuine source order line | Implemented with `dropDuplicates` |
| Silver | `StockCode` should be normalized with `upper(trim(...))` | Consistent product key across sources | Implemented |
| Silver/Gold | Negative quantities and cancellation invoices are valid business events | They must not be automatically rejected | Implemented — retained and cancellations are flagged |
| Gold | Null or unmatched `CustomerID` is allowed | Order remains available for analysis | Implemented — mapped to Unknown Customer (`customer_key = -1`) |

## Customers

| Layer | Rule | Expected behaviour | Action |
|---|---|---|---|
| Gold | A `CustomerID` should have only one `Country` within the same daily snapshot | No ambiguous customer state enters Gold | Implemented |
| Gold | Multiple countries for the same customer within one snapshot are a data quality conflict | Conflicting customer snapshot is excluded rather than guessed | Implemented using a `left_anti` join |
| Gold | A country change across different daily snapshots is valid | A new SCD2 version is created | Implemented through SCD2 logic; not observable with the provided single-day snapshot |

## Products

| Layer | Rule | Expected behaviour | Action |
|---|---|---|---|
| Bronze/Silver | `StockCode` must not be null or blank | Every product row identifies a product | Proposed — currently normalized but not explicitly validated |
| Silver | `UnitPrice` must be numeric | Invalid prices should be identified | Partially implemented — cast to `double`; invalid values become `null`. Explicit validation/quarantine is proposed |
| Silver | Product description must be usable | Null, blank and identified operational descriptions should not enter the cleaned product dataset | Implemented |
| Gold | A `StockCode` should have only one coherent `(Description, UnitPrice)` state within the same daily snapshot | No ambiguous product state enters Gold | Implemented |
| Gold | Multiple product states within one snapshot are a data quality conflict | Conflicting product snapshot is excluded rather than an arbitrary value being selected | Implemented using a `left_anti` join |
| Gold | Description or price changes across different daily snapshots are valid | A new SCD2 version is created | Implemented through SCD2 logic; not observable with the provided single-day snapshot |

## Referential Integrity

| Layer | Rule | Expected behaviour | Action |
|---|---|---|---|
| Gold | Every order used for revenue analytics should resolve to a valid product | Every fact row has a valid product | Implemented through the inner join with `dim_product` |
| Gold | Orders without a valid product mapping should not enter `fact_orders` | Revenue is never calculated using a guessed price | Implemented |
| Gold | Missing or unmatched customers should not cause an order to be dropped | Order maps to Unknown Customer | Implemented with `customer_key = -1` |

## Gold Model

| Layer | Rule | Expected behaviour | Action |
|---|---|---|---|
| Gold | `fact_orders.product_key` must not be null | Every fact row references a product | Implemented implicitly through the product inner join |
| Gold | `fact_orders.customer_key` must not be null | Every fact row references a customer or Unknown Customer | Implemented through `coalesce(customer_key, -1)` |
| Gold | `revenue` must equal `quantity * unit_price` | Revenue remains derivable from its inputs | Implemented and covered by unit tests |
| Gold | Exactly one SCD2 record per business key should have `is_current = true` | One current customer/product version | Implemented by SCD2 construction; proposed as an additional automated DQ assertion |
| Gold | SCD2 validity ranges for the same business key must not overlap | Consistent historical timeline | Implemented by SCD2 construction; proposed as an additional automated DQ assertion |

## Notes

Data quality rules intentionally avoid introducing unsupported business assumptions.

In particular, negative quantities and cancellation invoices are preserved because they represent source business events rather than technical errors.

Similarly, conflicting customer or product states within the **same snapshot** are treated as data quality issues, while changes observed across **different snapshots** are treated as legitimate history and handled through SCD Type 2 dimensions.