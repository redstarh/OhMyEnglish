#!/bin/bash
# TASK-86 결정 61 — 전용 세션 프로토타입. P1(제품 문면 그대로) 4회 · P2(규칙 9 유보 걷음) 4회 · 대조군 1회.
# ⛔ 상한은 회차 기록 §0 이 소유한다: 합 9 세션. 중간에 늘리지 않는다.
set -uo pipefail
cd /Users/redstar/MyProject/OhMyEnglish/app/backend || exit 1
PY=.venv/bin/python
SP=../../tests/harness/spike_nova_protocol.py
EV=../../.harness/evidence
RD=../../tests/harness/runs/2026-09-11-task86-dedicated-session
for arm in P1:prompt_dedicated.txt P2:prompt_dedicated_cut.txt; do
  NAME=${arm%%:*}; FILE=${arm##*:}
  for i in 1 2 3 4; do
    TS=$(date -u +%Y%m%dT%H%M%SZ)
    echo "########## 팔 $NAME(dedicated) $i/4 — $TS"
    $PY "$SP" --wav p2m.wav,p2a.wav --tools --prompt-file "$RD/$FILE" \
      --out "$EV/D86ded$NAME-p2m+p2a-$TS.json" 2>&1 | tail -6
    sleep 3
  done
done
TS=$(date -u +%Y%m%dT%H%M%SZ)
echo "########## 팔 B(base · 대조군) — $TS"
$PY "$SP" --wav p2m.wav,p2a.wav --tools --out "$EV/D86ded-base-p2m+p2a-$TS.json" 2>&1 | tail -6
echo "########## 끝"
