---
id: TASK-110
title: '하네스: 슬라이스 2 산출물을 보는 스모크 단정 4건을 더한다 (계획서 Task 12 Step 3)'
status: To Do
assignee: []
created_date: '2026-09-11 13:24'
labels: []
dependencies: []
ordinal: 113000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-48(계획서 Task 12)을 닫을 때 소유자가 없는 것으로 확인된 항목이다. 계획서 docs/design/2026-09-04-learning-coach-slice2-plan.md 「Task 12: 문서를 정본과 맞춘다」 Step 3 이 정본이고, TASK-48 의 AC 셋(AS11 신설 · AC11-5 미충족 명시 · 정정 항목 대조)에는 이 넷이 들어 있지 않았다. 그래서 TASK-48 을 닫으면 원장에서 사라진다 — 그것을 막기 위해 신설했다. ⚠️ 하네스는 게이트 밖 자산이다(함정 H-AA — 스모크가 이틀간 죽어 있었던 전례가 있다). 손대기 전에 git log -1 -- tests/harness/ 와 최근 앱 변경 날짜를 대조한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 세션 종료 후 계획 job 이 걸리는 것을 스모크가 단정한다
- [ ] #2 session_plans 행 1건이 생기는 것을 단정한다
- [ ] #3 learner_notes 행 1건이 생기는 것을 단정한다
- [ ] #4 다음 세션 시작 시 스텁 지시문에 Today's plan: 이 있는 것을 단정한다
- [ ] #5 손대기 전에 하네스가 살아 있는지 확인한 결과를 회차 기록이나 태스크 노트에 적는다 — 죽은 스모크에 단정을 더하면 통과가 무의미하다
<!-- AC:END -->
