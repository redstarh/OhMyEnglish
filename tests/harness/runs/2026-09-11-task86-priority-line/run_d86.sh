#!/bin/bash
# TASK-106 — 하네스 팔 A6(prio · 보강된 소리 줄) 8회 + 대조군 B 2회.
# ⛔ 상한은 회차 기록 §0 이 소유한다: A2 8 · B 2 · 합 10 세션.
set -uo pipefail
cd /Users/redstar/MyProject/OhMyEnglish/app/backend || exit 1
PY=.venv/bin/python
SP=../../tests/harness/spike_nova_protocol.py
EV=../../.harness/evidence
RD=../../tests/harness/runs/2026-09-11-task86-priority-line
PF=$RD/prompt_prio.txt
N=${1:-8}
for i in $(seq 1 "$N"); do
  TS=$(date -u +%Y%m%dT%H%M%SZ)
  echo "########## 팔 A6(prio · 보강된 소리 줄) $i/$N — $TS"
  $PY "$SP" --wav p2m.wav,p2a.wav --tools --prompt-file "$PF" \
    --out "$EV/D86-prio-p2m+p2a-$TS.json" 2>&1 | tail -6
  sleep 3
  if [ $((i % 4)) -eq 0 ]; then
    TS=$(date -u +%Y%m%dT%H%M%SZ)
    echo "########## 팔 B(base · 대조군) — $TS"
    $PY "$SP" --wav p2m.wav,p2a.wav --tools \
      --out "$EV/D86-base-p2m+p2a-$TS.json" 2>&1 | tail -6
    sleep 3
  fi
done
echo "########## 끝"
