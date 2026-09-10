#!/bin/bash
# TASK-93 — 결정 50 의 ② 측정. 다중 턴(p2m→p2a) · 문턱을 넘는 픽스처.
#
# ⛔ 두 팔을 «교대로» 돌린다 — 한 팔을 몰아 돌리면 시간에 따른 변화가 팔 차이로 보인다.
#    TASK-90 이 경계 해석에서 정확히 그 함정에 걸렸다(§12.1).
# ⛔ --tool-choice 를 주지 않는다. 워커를 켜지 않는다. DB 를 건드리지 않는다(스파이크는
#    learning_sessions 를 만들지 않는다).
set -uo pipefail

cd /Users/redstar/MyProject/OhMyEnglish/app/backend || exit 1
PY=.venv/bin/python
SP=../../tests/harness/spike_nova_protocol.py
EV=../../.harness/evidence
N=${1:-4}

for i in $(seq 1 "$N"); do
  TS=$(date -u +%Y%m%dT%H%M%SZ)
  echo "########## 팔 A (앱 프롬프트) 회차 $i / $N — $TS"
  $PY "$SP" --wav p2m.wav,p2a.wav --tools --app-prompt \
    --out "$EV/D50-app-p2m+p2a-$TS.json" 2>&1 | tail -8
  sleep 3

  TS=$(date -u +%Y%m%dT%H%M%SZ)
  echo "########## 팔 B (기반 프롬프트 · 대조군) 회차 $i / $N — $TS"
  $PY "$SP" --wav p2m.wav,p2a.wav --tools \
    --out "$EV/D50-base-p2m+p2a-$TS.json" 2>&1 | tail -8
  sleep 3
done

echo "########## 끝 — 원자료"
ls -1t "$EV"/D50-*.json | head -20
