#!/bin/bash
# TASK-123+TASK-118 — ARM-A 4회(pq06→pq12 · th_as_s · :8012) + ARM-B 3회(pq13→pq13a · f_as_p · :8013).
# ⛔ 상한은 회차 기록 §0 이 소유한다: 합 7 세션. 중간에 늘리지 않는다.
set -uo pipefail
cd /Users/redstar/MyProject/OhMyEnglish/app/backend || exit 1
PY=.venv/bin/python
WS=../../tests/harness/ws_session.py
for i in 1 2 3 4; do
  echo "########## ARM-A $i/4 — $(date -u +%Y%m%dT%H%M%SZ)"
  $PY "$WS" --scenario "T123A$i" --mode pronunciation --wav pq06.wav,pq12.wav \
    --url ws://localhost:8012/ws/session --no-register --timeout 120 2>&1 | tail -4
  sleep 3
done
for i in 1 2 3; do
  echo "########## ARM-B $i/3 — $(date -u +%Y%m%dT%H%M%SZ)"
  $PY "$WS" --scenario "T123B$i" --mode pronunciation --wav pq13.wav,pq13a.wav \
    --url ws://localhost:8013/ws/session --no-register --timeout 120 2>&1 | tail -4
  sleep 3
done
echo "########## 끝"
