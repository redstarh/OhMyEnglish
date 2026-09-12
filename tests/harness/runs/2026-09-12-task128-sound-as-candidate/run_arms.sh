#!/bin/bash
# TASK-128.3 — ARM-A 4회(pq06→pq12 · 후보 th_as_s · :8012) + ARM-B 3회(pq13→pq13a · 후보 f_as_p · :8013).
# ⛔ 상한은 회차 기록 §0 이 소유한다: 합 7 세션. 중간에 늘리지 않는다.
# ⚠️ 오디오 프레임 줄을 걸러 낸다 — 원본을 메인 컨텍스트에 올리지 않는다(프레임 167개 중 대부분).
#    원본은 `.harness/evidence/<시나리오>-frames.json` 에 그대로 남는다.
set -uo pipefail
cd /Users/redstar/MyProject/OhMyEnglish/app/backend || exit 1
PY=.venv/bin/python
WS=../../tests/harness/ws_session.py
ARM=${1:-both}

run_one() {  # $1=시나리오 $2=wav들 $3=포트
  $PY "$WS" --scenario "$1" --mode pronunciation --wav "$2" \
    --url "ws://localhost:$3/ws/session" --no-register --timeout 120 2>&1 |
    grep -vE "^  audio|^  partial"
}

if [ "$ARM" = "A" ] || [ "$ARM" = "both" ]; then
  for i in 1 2 3 4; do
    echo "########## ARM-A $i/4 — $(date -u +%Y%m%dT%H%M%SZ)"
    run_one "T128A$i" pq06.wav,pq12.wav 8012
    sleep 3
  done
fi
if [ "$ARM" = "B" ] || [ "$ARM" = "both" ]; then
  for i in 1 2 3; do
    echo "########## ARM-B $i/3 — $(date -u +%Y%m%dT%H%M%SZ)"
    run_one "T128B$i" pq13.wav,pq13a.wav 8013
    sleep 3
  done
fi
echo "########## 끝"
