---
id: TASK-92
title: 코치가 되불러 주는 교정 문장이 잘못 발음된 낱말을 그대로 담음 (pile ← file)
status: To Do
assignee: []
created_date: '2026-09-10 14:20'
labels: []
dependencies: []
ordinal: 95000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
재현: 1) cd app/backend 2) .venv/bin/python ../../tests/harness/spike_nova_protocol.py --wav pq08.wav --tools --app-prompt 3) ASSISTANT textOutput 을 읽음.

기대: 발음 오류를 교정하지 않기로 했다면(규칙 9 게이트) 교정 문장에도 그 낱말이 들어가지 않아야 함. 들어간다면 목표 낱말(file)로 들어가야 함.

실제: 시제·주어만 고치고 잘못 발음된 낱말을 정답 문장으로 되불러 줌 — 'Did you mean to say "I finished the first version of the pile"?' / 'Let'"'"'s try this sentence together. Say: "I finished the first version of the pile."' 학습자 관점에서는 앱이 틀린 발음을 승인한 것임.

증거: tests/harness/runs/2026-09-10-task90-pq-phoneme/PQ-pq08-20260910T140652Z.json · 회차 기록 §7-4 (tests/harness/runs/2026-09-10-task90-pq-phoneme.md)

HEAD: 36c3162 (앱 프롬프트 nova.py 는 adf462c 상태 · 회차 중 미변경)
시나리오: PQ 계층 pq08 (tests/harness/scenarios-PQ-qwen-phoneme.md §4.2) · 상위 회차 TASK-90

제안: 규칙 9·11 이 「코칭하지 않기로 한 턴」의 교정 문장 처리를 정하지 않음. 문법 교정 문장을 되불러 줄 때 발음 오류 낱말을 목표 낱말로 두라는 절을 검토함. ⛔ 이 회차는 원인을 특정하지 않았고 표본 1건임.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 pq08 을 같은 봉투로 다시 돌렸을 때 교정 문장에 pile 이 들어가지 않는다
<!-- AC:END -->
