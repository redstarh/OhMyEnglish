---
id: TASK-30
title: 판별력 관측 — 재설계한 단정 7건의 대조가 실제로 FAIL을 내는지 회차에서 확인
status: To Do
assignee: []
created_date: '2026-09-06 02:43'
updated_date: '2026-09-07 22:27'
labels:
  - caps-req
dependencies:
  - TASK-19
  - TASK-21
  - TASK-22
  - TASK-37
priority: high
ordinal: 30000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-29 가 7건을 재설계했으나 판별력을 '설계'했을 뿐 '관측'하지 않았다. 대조가 무력화에서 실제로 FAIL 을 내는지는 브라우저 회차에서만 관측된다 — TASK-29 안에서는 순환한다(회차가 재설계를 전제한다). 정본은 tests/harness/browser_leg.md 의 재설계 상자와 §5 표이고, 리뷰 근거는 docs/design/2026-09-06-review-outcomes.md §4 가 소유한다. 관측 전에는 이 7건을 PASS 로 보고하지 않는다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A1-4 의 when 인자 대조가 실제로 판별력을 갖는지 확인 — 세 값이 전부 같으면 FAIL 이 나는가
- [ ] #2 A1-5 의 sentinel 변형 대조가 FAIL 을 내는지 확인
- [ ] #3 A1-7 의 무음 스트림 대조가 audio 계수 0 을 내는지 확인 — 못 내면 판별력 미확인으로 기록한다
- [ ] #4 A3-1 의 상태별 세션 재방문에서 같은 요소의 문구가 바뀌는지 확인
- [ ] #5 A4-1 의 primary 세션이 corrections 를 비우지 않음을 확인하고 빈 세션 대조가 0 개를 내는지 확인
- [ ] #6 A4-2 의 기대값 교차 대조가 FAIL 을 내는지 확인 — 교정 2건 이상 세션이 필요하다. 1건뿐이면 판별력 미확인으로 기록한다
- [ ] #7 A5-1 의 순차 주입에서 같은 요소의 문구가 매번 바뀌는지 확인
- [ ] #8 관측 결과를 회차 기록에 남기고 미확인으로 남은 건을 browser_leg.md 상자에 정확한 개수로 갱신한다
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-09-07 22:27
---
연관 감사(2026-09-08 팀리드): 선행에 TASK-37 을 더했다(기존 TASK-19·21·22 는 보존). 이 태스크 설명이 「대조가 실제로 FAIL 을 내는지는 브라우저 회차에서만 관측된다」고 적는데 그 회차를 소유한 태스크가 TASK-37 이다(AC#2 가 B1~B4 재확인과 라이트·다크 5상태를 담는다). 회차를 따로 도는 대신 5차수 안에서 관측한다.
---
<!-- COMMENTS:END -->
