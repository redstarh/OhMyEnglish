#!/bin/bash
# TASK-86 결정 63 — 팔 S3(−rule4 · S1 에서 규칙 4 만 뺌) 4회 + 대조군 1회.
# ⛔ 상한은 회차 기록 §3 이 소유한다: S3 4 · B 1 · 합 5 세션. 중간에 늘리지 않는다.
set -uo pipefail
cd /Users/redstar/MyProject/OhMyEnglish/app/backend || exit 1
PY=.venv/bin/python
SP=../../tests/harness/spike_nova_protocol.py
EV=../../.harness/evidence
RD=../../tests/harness/runs/2026-09-11-task86-length-boundary
for i in 1 2 3 4; do
  TS=$(date -u +%Y%m%dT%H%M%SZ)
  echo "########## 팔 S3(-rule4) $i/4 — $TS"
  $PY "$SP" --wav p2m.wav,p2a.wav --tools --prompt-file "$RD/prompt_bound_norule4.txt" \
    --out "$EV/D86nr4-p2m+p2a-$TS.json" 2>&1 | tail -6
  sleep 3
done
TS=$(date -u +%Y%m%dT%H%M%SZ)
echo "########## 팔 B(base · 대조군) — $TS"
$PY "$SP" --wav p2m.wav,p2a.wav --tools --out "$EV/D86nr4-base-p2m+p2a-$TS.json" 2>&1 | tail -6
echo "########## 끝"
