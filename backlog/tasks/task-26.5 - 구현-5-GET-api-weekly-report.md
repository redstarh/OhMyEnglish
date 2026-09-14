---
id: TASK-26.5
title: '구현 5: GET /api/weekly-report'
status: Done
assignee: []
created_date: '2026-09-13 23:36'
updated_date: '2026-09-14 00:07'
labels: []
dependencies:
  - TASK-26.4
parent_task_id: TASK-26
ordinal: 164000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
계획서 Task 5. daily.py 에 붙인다 — 그 라우터의 prefix 가 이미 /api 이고 성격이 같다. 행이 없으면 404 가 아니라 200 에 analyzed=false 다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 단정 셋이 통과한다 — 200 의 필드 · 없을 때 빈 모양 · ⛔ jsonb 가 dict 로 나가는지(asyncpg 가 문자열로 준다)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
완료 2026-09-14 (세션 ohmyenglish-f4).

red 를 먼저 봤음 — 라우트 부재로 404, 그리고 고정 사용자 행이 없어 ForeignKeyViolationError. 뒤쪽은 test_daily_summary_api.py 의 픽스처 방식(고정 사용자를 스스로 심고 지움)을 그대로 가져와 고쳤음.

단정 넷이 통과함(계획의 셋을 넘었음): 200 의 필드와 ⛔ jsonb 가 dict 로 나가는가 · 행이 없으면 404 가 아니라 200 에 analyzed=false · ⛔ 주가 여럿이면 «가장 최근»이 이김 · 행이 있어도 computed_at 이 null 이면 analyzed=false. 셋째를 더한 이유: 없으면 「아무 한 행」을 주는 구현이 통과해 화면이 몇 주 전 것을 최신처럼 보임.

판정을 라우터에 두지 않았음 — 「최근이 어느 주인가」와 jsonb 변환은 services 가 갖고, daily.py 머리말의 규약(라우터에 날짜 계산을 두지 않는다)을 지켰음.

판별력: jsonb 변환을 없애 TypeError red 를 보고 되돌려 4 passed 를 다시 읽었음.

⚠️ ty 가 dict 좁히기를 잡아 cast 로 고쳤음 — jsonb 는 배열·스칼라도 담을 수 있고 화면의 계약은 객체이므로 그 자리를 빈 dict 로 접는 것을 주석에 적었음.

게이트: pytest 1181 passed · ruff 0 · format 222 files · ty 0 · tsc exit 0.
<!-- SECTION:NOTES:END -->
