#!/bin/bash
# TASK-106 팔 A4(nolist) — 「놓친 소리 목록」에서 an_as_a 를 뺀 팔 6회 + 대조군 1회.
# ⛔ 상한은 회차 기록 §5 가 소유한다: A5 6 · B 1 · 합 7 세션.
set -uo pipefail
cd /Users/redstar/MyProject/OhMyEnglish/app/backend || exit 1
PY=.venv/bin/python
SP=../../tests/harness/spike_nova_protocol.py
EV=../../.harness/evidence
RD=../../tests/harness/runs/2026-09-11-task106-matched-sound
PF=$RD/prompt_noq.txt
N=${1:-6}
for i in $(seq 1 "$N"); do
  TS=$(date -u +%Y%m%dT%H%M%SZ)
  echo "########## 팔 A5(noq · 질문 목록 제거) $i/$N — $TS"
  $PY "$SP" --wav p2m.wav,p2a.wav --tools --prompt-file "$PF" \
    --out "$EV/D106-noq-p2m+p2a-$TS.json" 2>&1 | tail -6
  sleep 3
done
TS=$(date -u +%Y%m%dT%H%M%SZ)
echo "########## 팔 B(base · 대조군) — $TS"
$PY "$SP" --wav p2m.wav,p2a.wav --tools --out "$EV/D106-base-p2m+p2a-$TS.json" 2>&1 | tail -6
echo "########## 끝"
