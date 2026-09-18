---
id: TASK-186
title: '구현: 낭독 회차를 서버가 세어 이벤트에 실는다'
status: Done
assignee: []
created_date: '2026-09-18 02:28'
updated_date: '2026-09-18 02:33'
labels: []
dependencies:
  - TASK-185
ordinal: 247000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
shadowing_recording 이벤트에 회차를 더한다. 정본이 DB 의 발화 수이므로 새로 고침·재접속에도 복원된다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 이벤트가 회차를 싣는다
- [x] #2 발화 수에서 계산하므로 재접속에도 값이 유지된다
- [x] #3 말하기 세션에는 영향이 없다
<!-- AC:END -->
