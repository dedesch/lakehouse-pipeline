#!/usr/bin/env bash
# Local build/test script: run the implemented part of the pipeline, then
# the test suite. Fails fast and loud on the first error (set -e), so a
# non-zero exit code means something is actually broken.
#
# Usage: ./scripts/build.sh

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ ! -f .env/bin/activate ]; then
  echo "error: .env virtualenv not found. Run the Setup steps in README.md first." >&2
  exit 1
fi

# shellcheck disable=SC1091
source .env/bin/activate

echo "==> Bronze: ingest customers"
python -m src.bronze.ingest_customers

echo "==> Bronze: ingest products"
python -m src.bronze.ingest_products

echo "==> Bronze: ingest orders"
python -m src.bronze.ingest_orders

echo "==> Silver: clean customers"
python -m src.silver.clean_customers

echo "==> Silver: clean products"
python -m src.silver.clean_products

echo "==> Silver: clean orders"
python -m src.silver.clean_orders

# TODO: add the gold layer scripts here once implemented.

echo "==> Tests"
set +e
pytest -q
pytest_status=$?
set -e
# pytest exits 5 for "no tests collected", which is the current, expected
# state of tests/ (still stubs) -- not a build failure. Any other non-zero
# exit (actual failures, errors, usage problems) still fails the build.
if [ "$pytest_status" -ne 0 ] && [ "$pytest_status" -ne 5 ]; then
  exit "$pytest_status"
fi

echo "==> Build OK"
