#!/bin/bash
# TASK-86 결정 57 — 팔 A7(soundq · 새 규칙이 만든 질문) 8회 + 대조군 B 2회.
# ⛔ 상한은 회차 기록 §0 의 2단계 표가 소유한다: A7 8 · B 2 · 합 10 세션. 중간에 늘리지 않는다.
set -uo pipefail
cd /Users/redstar/MyProject/OhMyEnglish/app/backend || exit 1
PY=.venv/bin/python
SP=../../tests/harness/spike_nova_protocol.py
EV=../../.harness/evidence
RD=../../tests/harness/runs/2026-09-11-task86-sound-shaped-questions
PF=$RD/prompt_soundq.txt
N=${1:-8}
for i in $(seq 1 "$N"); do
  TS=$(date -u +%Y%m%dT%H%M%SZ)
  echo "########## 팔 A7(soundq) $i/$N — $TS"
  $PY "$SP" --wav p2m.wav,p2a.wav --tools --prompt-file "$PF" \
    --out "$EV/D86soundq-p2m+p2a-$TS.json" 2>&1 | tail -6
  sleep 3
  if [ $((i % 4)) -eq 0 ]; then
    TS=$(date -u +%Y%m%dT%H%M%SZ)
    echo "########## 팔 B(base · 대조군) — $TS"
    $PY "$SP" --wav p2m.wav,p2a.wav --tools \
      --out "$EV/D86soundq-base-p2m+p2a-$TS.json" 2>&1 | tail -6
    sleep 3
  fi
done
echo "########## 끝"
