#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${MNEMOSYNE_R8_BASE_URL:-http://127.0.0.1:8088}"

echo "== health =="
curl -fsS "$BASE_URL/health"
echo

echo "== submit valid proposal =="
curl -fsS -X POST "$BASE_URL/proposals" \
  -H 'Content-Type: application/json' \
  -d '{
    "tenant": "demo",
    "workflow": "r8",
    "entity": "job-1",
    "operation": "valid_transition",
    "payload": {"valid_under_c": true, "value": 1}
  }'
echo

echo "== submit bypass attempt =="
curl -fsS -X POST "$BASE_URL/proposals" \
  -H 'Content-Type: application/json' \
  -d '{
    "tenant": "demo",
    "workflow": "r8",
    "entity": "job-1",
    "operation": "raw_append",
    "payload": {"direct_commit": true}
  }'
echo

echo "== state =="
curl -fsS "$BASE_URL/state/demo/job-1"
echo

echo "== metrics =="
curl -fsS "$BASE_URL/metrics"
