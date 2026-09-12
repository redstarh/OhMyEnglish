---
id: TASK-128.3
title: '검증 회차: 결정 72 판을 회귀·판별 두 팔로 재고 바이트 게이트를 갱신한다'
status: To Do
assignee: []
created_date: '2026-09-12 03:54'
labels: []
dependencies:
  - TASK-128.2
parent_task_id: TASK-128
ordinal: 136000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
설계 정본: docs/design/2026-09-12-decision72-sound-as-candidate.md §4. ⛔ 상한과 해석 규칙은 그 회차 기록 §0 이 소유하고 설계서가 정하지 않는다.
⛔ 판별 팔의 성공 조건이 «이전과 반대» 다 — 지금까지는 「계획 키가 실린다」가 결함이었고 이제는 「계획 키가 실리지 않는다」가 성공이다.
⚠️ 후보 목록에 f_as_p 를 그대로 둔다 — 후보 기제가 「없는 소리를 발명하지 않는다」를 지키는지 함께 재기 때문이다. 빼면 그 판별력이 사라진다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 회귀 팔(pq06→pq12 · 후보 th_as_s)에서 코칭이 유지되는지 본다 — 기준선 ARM-A 4/4
- [ ] #2 판별 팔(pq13→pq13a · 후보 f_as_p · 오디오에 없음)에서 기록된 target_sound 가 f_as_p 가 «아닌» 것이 되는지 본다 — 기준선은 f_as_p 3/3 x2회차
- [ ] #3 상한과 해석 규칙을 돌리기 «전에» 회차 기록에 적는다
- [ ] #4 결과로 TASK-116 을 닫거나 남긴다 — 닫으면 그 확정 근거를 그 태스크에 적는다
<!-- AC:END -->
