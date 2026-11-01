---
id: TASK-306
title: 사용자 시나리오 화면 보드 — 실제 앱 화면으로 홈·모든 메뉴 흐름 표시
status: Done
assignee: []
created_date: '2026-11-01 04:13'
updated_date: '2026-11-01 04:57'
labels: []
dependencies: []
ordinal: 371000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 지시 2026-11-01: 홈 및 모든 메뉴 흐름에서 버튼을 누르고 진행하는 과정을 사용자 사용 시나리오에 맞춰 보여 줌. 도구는 draw.io 가 아니라 「실제 나의 화면으로 시나리오가 표시되는 것」. ⇒ 앱을 실제로 조작해 단계마다 실제 화면을 찍고, 시나리오별로 화살표로 이은 흐름 보드 HTML 을 docs/ux/ 에 두고 사용자 Chrome 에서 엶. 시험용 스택(stub · 격리 DB)에서 찍음.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 시나리오 목록(홈·문장 연습·코치 세션·문법 코스·영상·이력·주간·결과)이 정해지고 단계마다 실제 화면이 있음
- [x] #2 흐름 보드 HTML 이 docs/ux/ 에 있고 사용자 Chrome 에서 열림
- [x] #3 dev DB 쓰기가 없음
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
보드: docs/ux/2026-11-01-user-scenarios/index.html — 시나리오 10 · 14줄 · 70단계, 실제 앱 화면 + 누른 요소 빨간 테두리 · testid. TASK-307 뒤 다시 찍음. 사용자 Chrome 에서 열었음. dev DB 기준선 그대로.
<!-- SECTION:NOTES:END -->
