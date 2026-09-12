#!/bin/bash
# TASK-111+TASK-116 — REG 팔 4회 (pq06→pq12 · 심은 소리 th_as_s).
# ⛔ 상한은 회차 기록 §0 이 소유한다: 합 7 세션(REG 4 + KEY 3). 중간에 늘리지 않는다.
set -uo pipefail
cd /Users/redstar/MyProject/OhMyEnglish/app/backend || exit 1
PY=.venv/bin/python
WS=../../tests/harness/ws_session.py
URL=ws://localhost:8012/ws/session
for i in 1 2 3 4; do
  echo "########## REG $i/4 — $(date -u +%Y%m%dT%H%M%SZ)"
  $PY "$WS" --scenario "T111REG$i" --mode pronunciation --wav pq06.wav,pq12.wav \
    --url "$URL" --no-register --timeout 120 2>&1 | tail -40
  sleep 3
done
echo "########## REG 끝"
