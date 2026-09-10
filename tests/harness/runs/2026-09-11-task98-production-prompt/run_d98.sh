#!/bin/bash
# TASK-98 — 제품 프롬프트(계획 실림) 팔 A' 와 기반 프롬프트 대조군 팔 B 를 교대로 돌린다.
# ⛔ --prompt-file 과 --app-prompt 를 함께 주지 않는다(스크립트가 거부한다).
set -uo pipefail
cd /Users/redstar/MyProject/OhMyEnglish/app/backend || exit 1
PY=.venv/bin/python
SP=../../tests/harness/spike_nova_protocol.py
EV=../../.harness/evidence
PF=../../tests/harness/runs/2026-09-11-task98-production-prompt/prompt_production.txt
N=${1:-4}
for i in $(seq 1 "$N"); do
  TS=$(date -u +%Y%m%dT%H%M%SZ)
  echo "########## 팔 A' (제품 프롬프트 · 계획 실림) $i/$N — $TS"
  $PY "$SP" --wav p2m.wav,p2a.wav --tools --prompt-file "$PF" \
    --out "$EV/D98-prod-p2m+p2a-$TS.json" 2>&1 | tail -6
  sleep 3
  TS=$(date -u +%Y%m%dT%H%M%SZ)
  echo "########## 팔 B (기반 프롬프트 · 대조군) $i/$N — $TS"
  $PY "$SP" --wav p2m.wav,p2a.wav --tools \
    --out "$EV/D98-base-p2m+p2a-$TS.json" 2>&1 | tail -6
  sleep 3
done
echo "########## 끝"; ls -1t "$EV"/D98-*.json | head -20
