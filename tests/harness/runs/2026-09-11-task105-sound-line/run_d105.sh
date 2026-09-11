#!/bin/bash
# TASK-105 — 소리 줄이 실린 제품 프롬프트 팔 A(sound) 21회 + 대조군 팔 B(base) 5회.
#
# ⛔ 상한은 회차 기록 §0 이 소유한다: A 21 · B 5 · 합 26 세션. 이 스크립트가 그 수를 강제한다.
# ⛔ --prompt-file 과 --app-prompt 를 함께 주지 않는다(스파이크가 거부한다).
# 대조군은 4회마다 1회 끼운다 — 판별력 확인용이고 1:1 로 두면 비용이 두 배다(§0).
set -uo pipefail
cd /Users/redstar/MyProject/OhMyEnglish/app/backend || exit 1
PY=.venv/bin/python
SP=../../tests/harness/spike_nova_protocol.py
EV=../../.harness/evidence
RD=../../tests/harness/runs/2026-09-11-task105-sound-line
PF=$RD/prompt_sound.txt
A_ROUNDS=${1:-21}
for i in $(seq 1 "$A_ROUNDS"); do
  TS=$(date -u +%Y%m%dT%H%M%SZ)
  echo "########## 팔 A(sound · 제품 프롬프트 + 소리 줄) $i/$A_ROUNDS — $TS"
  $PY "$SP" --wav p2m.wav,p2a.wav --tools --prompt-file "$PF" \
    --out "$EV/D105-sound-p2m+p2a-$TS.json" 2>&1 | tail -6
  sleep 3
  if [ $((i % 4)) -eq 0 ]; then
    TS=$(date -u +%Y%m%dT%H%M%SZ)
    echo "########## 팔 B(base · 대조군) — $TS"
    $PY "$SP" --wav p2m.wav,p2a.wav --tools \
      --out "$EV/D105-base-p2m+p2a-$TS.json" 2>&1 | tail -6
    sleep 3
  fi
done
# 21회면 4의 배수가 5번(4·8·12·16·20) 나오므로 대조군은 5회다 — §0 의 상한과 같다.
echo "########## 끝"
ls -1t "$EV"/D105-*.json | head -30
