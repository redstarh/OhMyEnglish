---
id: TASK-166
title: '구현 ⑤: 쉐도잉 배선 — 사용자가 문장을 지정해 연습하는 경로를 연다'
status: In Progress
assignee: []
created_date: '2026-09-17 17:16'
updated_date: '2026-09-17 17:40'
labels: []
dependencies:
  - TASK-162
ordinal: 227000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
설계서 §6 을 이행한다. 지금 클립 선택은 자동이고 사용자가 고를 경로가 없다. coalesce 맨 앞 항을 더해 지정 클립을 받는다. 없는 id 는 조용히 자동 선택으로 떨어진다(기존 관례).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 _ATTACH_SHADOWING_CLIP_SQL 의 coalesce 맨 앞에 지정 id 항을 더했다
- [ ] #2 start_shadowing_session 에 item_id 인자를 더했다
- [ ] #3 api/ws.py 가 query_params 의 item 을 UUID 로 파싱하고 실패하면 None 으로 둔다 (오류로 만들지 않는다)
- [ ] #4 lib/config.ts 의 SessionEntry 에 itemId 를 더하고 sessionSocketUrl 이 item 질의로 싣는다
- [ ] #5 tests/integration/test_ws.py 에 두 경우를 더했다 — 지정 id 로 열면 그 문장이 붙고, 없는 id 면 자동 선택으로 떨어진다
<!-- AC:END -->
