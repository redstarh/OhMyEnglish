#!/bin/bash
# TASK-90 단계 B — pq 케이스를 한 번씩 순차로 돌린다. 케이스마다 로그를 따로 남긴다.
set -u
cd /Users/redstar/MyProject/OhMyEnglish/app/backend || exit 1
mkdir -p /tmp/pq_logs
for c in pq01 pq02 pq03 pq04 pq05 pq07 pq08 pq09 pq10 pq11 pq12; do
  TS=$(date -u '+%Y%m%dT%H%M%SZ')
  echo "=== $c @ $TS ==="
  .venv/bin/python ../../tests/harness/spike_nova_protocol.py \
    --wav ${c}.wav --tools --app-prompt \
    --out ../../.harness/evidence/PQ-${c}-${TS}.json \
    > /tmp/pq_logs/${c}-${TS}.log 2>&1
  echo "exit=$? log=/tmp/pq_logs/${c}-${TS}.log"
  grep -E '^전사문/텍스트|^raw ->|^\[tool use 판정\]' /tmp/pq_logs/${c}-${TS}.log
  sleep 3
done
echo "=== ALL DONE ==="
