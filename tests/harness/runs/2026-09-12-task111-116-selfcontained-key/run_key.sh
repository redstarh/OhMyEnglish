#!/bin/bash
# TASK-116 — KEY 팔 3회 (pq05→pq05a · 심은 소리 z_as_j).
# ⛔ 상한은 회차 기록 §0 이 소유한다: 합 7 세션(REG 4 + KEY 3). 중간에 늘리지 않는다.
# 재는 것: «발화로 코칭한 소리»와 «tool 에 실린 target_sound» 가 맞는가.
set -uo pipefail
cd /Users/redstar/MyProject/OhMyEnglish/app/backend || exit 1
PY=.venv/bin/python
WS=../../tests/harness/ws_session.py
URL=ws://localhost:8013/ws/session
for i in 1 2 3; do
  echo "########## KEY $i/3 — $(date -u +%Y%m%dT%H%M%SZ)"
  $PY "$WS" --scenario "T111KEY$i" --mode pronunciation --wav pq05.wav,pq05a.wav \
    --url "$URL" --no-register --timeout 120 2>&1 | tail -12
  sleep 3
done
echo "########## KEY 끝"
