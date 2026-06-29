#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${MNEMOSYNE_R8_BASE_URL:-http://127.0.0.1:8088}"

python benchmarks/realm/r8_deployment_load.py \
  --base-url "$BASE_URL" \
  --total "${MNEMOSYNE_R8_LOAD_TOTAL:-200}" \
  --workers "${MNEMOSYNE_R8_LOAD_WORKERS:-1,4,8,16}" \
  --outdir "benchmarks/realm/reports/r8_deployment"
