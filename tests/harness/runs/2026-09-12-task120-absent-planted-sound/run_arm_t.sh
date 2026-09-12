#!/bin/bash
# TASK-120 ARM-T — 지금 커밋된 «조건부» 문면(f84b55c) 3회.
# 오디오 pq13→pq13a(/r/→/l/) · 심은 소리 f_as_p(그 문장에 /f/ 가 없음).
# ⛔ 상한은 회차 기록 §0 이 소유한다: 최대 5세션(T 3 + C 2). 중간에 늘리지 않는다.
set -uo pipefail
cd /Users/redstar/MyProject/OhMyEnglish/app/backend || exit 1
PY=.venv/bin/python
WS=../../tests/harness/ws_session.py
URL=ws://localhost:8012/ws/session
for i in 1 2 3; do
  echo "########## ARM-T $i/3 — $(date -u +%Y%m%dT%H%M%SZ)"
  $PY "$WS" --scenario "T120T$i" --mode pronunciation --wav pq13.wav,pq13a.wav \
    --url "$URL" --no-register --timeout 120 2>&1 | tail -8
  sleep 3
done
echo "########## ARM-T 끝"
