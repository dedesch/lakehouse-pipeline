# Data Analysis Journal

Running log of data exploration: findings, issues, doubts, assumptions, and
ad-hoc queries. 


## 3. Generic profiling

### products
```text
root
 |-- StockCode: string (nullable = true)
 |-- Description: string (nullable = true)
 |-- UnitPrice: string (nullable = true)
```
- **5,635 rows**, **3 columns**, no exact duplicate rows
- `StockCode`: 0 nulls · `Description`: 960 nulls · `UnitPrice`: 0 nulls (inferred as `string`)

### customers
```text
root
 |-- CustomerID: string (nullable = true)
 |-- Country: string (nullable = true)
```
- **4,389 rows**, **2 columns**, no exact duplicate rows
- `CustomerID`: 9 nulls · `Country`: 0 nulls

### orders
```text
root
 |-- InvoiceNo: string (nullable = true)
 |-- StockCode: string (nullable = true)
 |-- Quantity: string (nullable = true)
 |-- InvoiceDate: string (nullable = true)
 |-- CustomerID: string (nullable = true)
```
- **541,909 rows**, **5 columns**, **5,429 exact duplicate rows**
- `InvoiceNo`: 0 nulls · `StockCode`: 0 nulls · `Quantity`: 0 nulls (inferred as `string`) ·
  `InvoiceDate`: 0 nulls (inferred as `string`) · `CustomerID`: **135,080 nulls**

## 4. Products analysis

### 4.1 Volume and key uniqueness
- **3,965 distinct `StockCode` values** out of 5,635 rows — `StockCode` is **not unique**

### 4.2 Price quality
- Price range: **0.0–5.0**
- **10 non-positive prices**

### 4.3 Repeated StockCode investigation
- Repeated `StockCode` values can have different descriptions and prices.
- Manual inspection shows a mix of actual product records and operational/correction
  records (e.g. `wrongly coded`, `temp adjustment`).
- Duplicate `StockCode` records therefore cannot be assumed to represent price history.
- Further analysis is required before defining cleansing rules or selecting a canonical
  product record.
- 577 product records have descriptions that are not fully uppercase.
- 417 StockCodes have both uppercase and non-uppercase descriptions.
- 54 StockCodes have no fully uppercase description.
- Manual inspection confirms that valid product descriptions may contain lowercase
  characters (e.g. dimensions, units, brand/product names).
- Therefore, description casing cannot be used reliably to distinguish product
  records from operational/correction records.

## 5. Customers analysis

### 5.1 Volume and key uniqueness
- **4,373 distinct `CustomerID` values** out of 4,389 rows — `CustomerID` is **not unique**
- **9 records have a null `CustomerID`** and therefore cannot be reliably linked to orders
- Customer distribution is highly concentrated in the **United Kingdom** (3,951 records)

### 5.2 Conflicting customer-country mappings
- **8 `CustomerID`s are associated with two different countries**
- The source provides no timestamp or additional attribute to determine which country is correct
- Requires an explicit cleansing/modelling assumption

## 6. Orders analysis

### 6.1 Volume and cardinality
- **25,900 distinct invoices**
- **4,070 distinct `StockCode` values**
- **4,372 distinct `CustomerID` values**
- (5,429 exact duplicate rows — see §3)

### 6.2 Quantity analysis
- Quantity ranges from **-80,995 to 80,995**
- **10,624 rows** have non-positive quantities

### 6.3 Cancellation / negative quantity investigation
- **9,288 rows** belong to cancellation invoices (`InvoiceNo` starting with `C`)
- The remaining **1,336** negative-quantity rows are not cancellation invoices, and
  **all of them have a null `CustomerID`**
- This pattern suggests these 1,336 records may represent inventory or operational
  adjustments rather than customer transactions, though this cannot be confirmed from
  the available data
- **Decision needed**: negative quantities should not be removed without an explicit
  business/cleansing assumption (see §8)

### 6.4 Candidate grain investigation
- `(InvoiceNo, StockCode)` is **not unique**; some combinations occur multiple times,
  even after removing exact duplicate rows
- The same product can legitimately occur multiple times within an invoice with
  different quantities
- `(InvoiceNo, StockCode)` therefore cannot be used as a unique business key

## 7. Cross-source integrity

### 7.1 Customer integrity
- All non-null `CustomerID` values in `orders` have a matching record in `customers`

### 7.2 Product integrity
- **2,041 order lines** initially referenced `StockCode` values not matching `products`
- Investigation showed casing inconsistencies (e.g. `85132b` vs `85132B`)

### 7.3 StockCode normalization
- After normalizing `StockCode` with `trim` and `upper`, **all order StockCodes match
  the products dataset**
- **Decision**: `StockCode` should be normalized using `upper(trim(StockCode))` in the
  Silver layer before joins and referential integrity checks

## 8. Conclusions / modelling inputs

### Established
- **Fact table grain**: one row per individual order line from the source dataset,
  after removal of exact duplicates. The source provides no order-line identifier, so
  individual source rows are preserved rather than aggregated.
  `(InvoiceNo, StockCode)` is **not** a valid natural/business key (§6.4).
- **StockCode normalization**: `upper(trim(StockCode))` must be applied in the Silver
  layer before any join or referential integrity check (§7.3). Once applied, there are
  no orphan `StockCode`s between `orders` and `products`.
- **Customer referential integrity**: no cleansing action needed — every non-null
  `CustomerID` in `orders` already matches `customers` (§7.1).

### Open decisions — need an explicit assumption before modelling
- [ ] **Negative quantities / cancellations**: keep, flag, or exclude the 1,336
      non-cancellation negative-quantity rows (all with null `CustomerID`)? (§6.3)
- [ ] **Conflicting customer-country mappings**: which country to keep for the 8
      affected `CustomerID`s, given no disambiguating attribute exists? (§5.2)
- [ ] **Price snapshot semantics**: `products` is ingested as daily snapshots with
      potentially differing prices per `StockCode`, but `orders` carries no price
      column at all — which price should be attached to an order line? **Not yet
      investigated.**
- [ ] **`InvoiceDate` format, timezone, and overall date range**: not yet investigated
      — only a raw sample of the column has been looked at so far.



### Product price cleansing decision

The product dataset contains multiple records for the same `StockCode`, often with different descriptions and prices. Manual inspection showed that product master data is mixed with operational records such as `check`, `damaged`, `found`, `adjustment`, `amazon`, and `dotcom`, as well as records with missing descriptions.

After removing records with null descriptions and records whose descriptions exactly match identified operational terms, **3,412 out of 3,849 products (88.7%) have a single unambiguous price**, compared with 2,651 out of 3,965 (66.9%) in the raw dataset.

The remaining **437 products (11.3%) still have multiple prices** and cannot be reliably resolved because the source provides no effective date or other attribute indicating which price should be selected. These products affect approximately **16.4% of the order lines**.

The cleansing strategy therefore removes only clearly identifiable operational records and avoids more aggressive heuristics that could incorrectly remove valid products. Products for which the price remains ambiguous are treated as a known data quality issue and are not assigned an arbitrary price. The appropriate business rule should be validated with the relevant business and source-system owners before these records are used for authoritative price or revenue analytics.

**AI usage:** AI assistance was used during this analysis to accelerate exploratory queries and help challenge data-cleansing hypotheses. The resulting assumptions and cleansing decisions were validated against the dataset before being adopted.