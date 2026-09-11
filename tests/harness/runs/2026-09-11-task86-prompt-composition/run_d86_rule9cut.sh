#!/bin/bash
# TASK-86 결정 60 — 팔 A8(rule9cut · 규칙 9·11 문면을 걷음) 6회 + 대조군 B 1회.
# ⛔ 상한은 회차 기록 §0 이 소유한다: A8 6 · B 1 · 합 7 세션. 중간에 늘리지 않는다.
set -uo pipefail
cd /Users/redstar/MyProject/OhMyEnglish/app/backend || exit 1
PY=.venv/bin/python
SP=../../tests/harness/spike_nova_protocol.py
EV=../../.harness/evidence
RD=../../tests/harness/runs/2026-09-11-task86-prompt-composition
PF=$RD/prompt_rule9cut.txt
N=${1:-6}
for i in $(seq 1 "$N"); do
  TS=$(date -u +%Y%m%dT%H%M%SZ)
  echo "########## 팔 A8(rule9cut) $i/$N — $TS"
  $PY "$SP" --wav p2m.wav,p2a.wav --tools --prompt-file "$PF" \
    --out "$EV/D86cut-p2m+p2a-$TS.json" 2>&1 | tail -6
  sleep 3
done
TS=$(date -u +%Y%m%dT%H%M%SZ)
echo "########## 팔 B(base · 대조군) — $TS"
$PY "$SP" --wav p2m.wav,p2a.wav --tools --out "$EV/D86cut-base-p2m+p2a-$TS.json" 2>&1 | tail -6
echo "########## 끝"
