# Lakehouse Pipeline

Data pipeline exercise implementing a Bronze / Silver / Gold architecture with
dimensional modeling on Spark.

## Overview

<!-- TODO: one or two sentences on what this project does and the data it processes -->

## Project structure

```
lakehouse-pipeline/
├── ANALYSIS.md              # data exploration journal: findings, issues, assumptions
├── docs/
│   ├── data_model.md        # dimensional model documentation + diagram
│   └── data_quality_rules.md
├── notebooks/                # ad-hoc exploration scripts/notebooks
├── src/
│   ├── common/                # shared utilities (Spark session, data quality helpers)
│   ├── bronze/                # raw ingestion
│   ├── silver/                # cleansing, conforming
│   ├── gold/                  # dimensional model build
│   └── analytics/             # analytic queries
├── tests/
│   └── fixtures/              # small sample data used in unit tests
└── data/
    ├── bronze/
    ├── silver/
    └── gold/
```

## Requirements

<!-- TODO: confirm exact versions once set up -->
- Python 3.x
- PySpark
- pytest

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## How to run

<!-- TODO: document the actual commands once the pipeline is implemented -->

### Run the full pipeline

```bash
# TODO
```

### Run tests

```bash
pytest tests/
```

## Data sources

| Name | Ingestion frequency | Format |
|---|---|---|
| products | Daily | csv |
| customers | Daily | csv |
| orders | Hourly | csv |

## Design notes

See [docs/data_model.md](docs/data_model.md) for the dimensional model and
[docs/data_quality_rules.md](docs/data_quality_rules.md) for the proposed data
quality rules. See [ANALYSIS.md](ANALYSIS.md) for the data exploration journal.

## Assumptions

<!-- TODO: list key assumptions made during the exercise -->

## AI usage disclosure

<!-- Per the exercise instructions: note here if/where AI tools were used -->
