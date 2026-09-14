#!/bin/bash
# TASK-129 — 판별 팔 3회(pq13→pq13a · 계획이 고른 키 f_as_p · 일반 세션 · :8023).
# ⛔ 상한은 회차 기록 §0 이 소유한다: Nova 4 세션(판별 3 + 예비 1). 예비 1 은 B1 의 죽은 회차에 썼다.
# ⛔ `--mode` 를 주지 않는다 — 그것이 이 회차와 TASK-128 을 가르는 유일한 조건이다.
# ⚠️ `--timeout 120` 은 TASK-128 의 러너와 같은 값이다. 기본 30 은 코칭 왕복을 담지 못한다(B1 실측).
# ⚠️ 오디오·partial 줄을 걸러 낸다 — 원본은 `.harness/evidence/<시나리오>-frames.json` 에 남는다.
set -uo pipefail
cd /Users/redstar/MyProject/OhMyEnglish/app/backend || exit 1
PY=.venv/bin/python
WS=../../tests/harness/ws_session.py
export DATABASE_URL=postgresql://ohmy:ohmy@localhost:5432/ohmyenglish_t129

for i in 2 3 4; do
  echo "########## T129-B$i — $(date -u +%Y%m%dT%H%M%SZ)"
  $PY "$WS" --scenario "T129-B$i" --wav pq13.wav,pq13a.wav \
    --url "ws://localhost:8023/ws/session" --no-register --timeout 120 2>&1 |
    grep -vE "^  audio|^  partial"
  sleep 3
done
echo "########## 끝"
