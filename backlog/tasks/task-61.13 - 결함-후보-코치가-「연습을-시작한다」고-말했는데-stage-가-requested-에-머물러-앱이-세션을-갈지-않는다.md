---
id: TASK-61.13
title: '결함 후보: 코치가 「연습을 시작한다」고 말했는데 stage 가 requested 에 머물러 앱이 세션을 갈지 않는다'
status: To Do
assignee: []
created_date: '2026-09-15 18:46'
labels: []
dependencies: []
parent_task_id: TASK-61
ordinal: 188000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
회차 `runs/2026-09-16-task61-12-unspecified-mode` §3 이 1회 관측했다(`answer-ko` 팔). 코치가 「Okay, we will do pronunciation practice. … Repeat after me」라 말하고 발음 연습을 그 자리에서 시작했는데 제어 이벤트의 stage 가 `requested` 에 머물러 앱은 세션을 갈지 않았다. ⇒ 학습자에게는 「바뀐 것처럼」 들리고 기록은 `speaking` 세션에 남는다. ⚠️ 안전 쪽으로 틀린 것이다(엉뚱한 세션이 열리지는 않는다) — 그래서 결함 «후보» 다. ⛔ 규칙 13 은 확인이 필요한 명령에 두 번 부르기를 요구하므로 문면 미준수이지만, 표본 1건이라 크기를 모른다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 그 모양의 크기를 실물 회차로 센다 — 종류를 답한 뒤 confirmed 까지 가는 비율
- [ ] #2 고치는 자리를 정한다: 문면을 더 세게 할지, 앱이 requested 를 받은 상태를 화면에 드러낼지
- [ ] #3 고치면 실물 회차로 관측한다
<!-- AC:END -->
