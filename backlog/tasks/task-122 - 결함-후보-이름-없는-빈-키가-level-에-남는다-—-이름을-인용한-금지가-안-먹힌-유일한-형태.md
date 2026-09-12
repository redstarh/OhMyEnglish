---
id: TASK-122
title: '결함 후보: 이름 없는 빈 키가 level 에 남는다 — 이름을 인용한 금지가 안 먹힌 유일한 형태'
status: To Do
assignee: []
created_date: '2026-09-12 00:16'
labels: []
dependencies: []
ordinal: 127000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-12 KST. 정본은 runs/2026-09-12-task121-level-bullet.md §2 임. TASK-121 이 - level: 불릿에 국소 금지 문장을 넣어 이름 있는 형태(reason_en · reason_note)를 0/8 로 만들었으나 빈 이름 키 "": "" 는 1/8 로 남았음. ⚠️ 그 문장에 'no blank key' 가 «이미 있음» — 즉 이름을 인용한 금지가 이름 없는 것에는 먹히지 않았음. ⛔ 전역 문장 강화로 되돌아가지 않음(TASK-119 §3 의 기각을 이 회차가 뒤집지 않았음). ⚠️ 대가는 재시도 1회이고 생산 경로가 attempts=2 로 흡수한 선례가 있음 — 「계획이 늦게 생김」이고 「안 생김」이 아님. 단 attempts 상한을 넘기면 달라지고 그 한도는 아직 재지 않았음. 누적 관측: 4회 팔에서 1건 · 8회 팔에서 1건.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 attempts 상한과 재시도 경로를 코드로 확인한다 — 이 부류가 계획을 아예 못 만드는 경우가 있는지 먼저 가른다. ⛔ 없으면 우선순위를 낮추고 문면을 더 건드리지 않는다
- [ ] #2 고칠 후보 둘을 저울질하고 근거를 적는다 — ① 규격 문면을 「모든 키 이름이 셋 중 하나여야 한다」로 바꿈 ② parse_plan 이 빈 이름 키만 무시함. ⛔ extra=forbid 를 통째로 풀지 않는다
- [ ] #3 고치면 8회 이상으로 재고 상한·해석 규칙을 돌리기 전에 적는다. ⛔ 0건을 「해결됨」으로 단정하지 않는다
<!-- AC:END -->
