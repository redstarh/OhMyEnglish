---
id: TASK-61.16
title: 갈림을 화면에 드러냄 — 버려진 명령과 확인 대기를 명령 셋에서 표시한다
status: Done
assignee: []
created_date: '2026-09-16 00:56'
updated_date: '2026-09-16 01:24'
labels: []
dependencies: []
parent_task_id: TASK-61
ordinal: 191000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
결정 113 이 정본이다: 표면은 화면이고 대상은 end · start_additional · show_report 셋이다(next_question 은 손대지 않는다 — 화면 갈림이 없다). 두 표면을 만든다. ① 버려짐: 표지가 없어 앱이 명령을 실행하지 않았을 때 화면이 그 사실을 말한다(지금은 백엔드 warning 만 남고 학습자는 코치의 「됐다」만 듣는다 — runs/2026-09-16-task61-15-accepted-without-execution 이 4/4 로 관측). ② 대기: 확인이 필요한 명령이 requested 에 머무는 것을 화면이 말한다(TASK-61.13 의 정지가 4/8 로 관측됐고 학습자에게 보이지 않았다). ⛔ 코치가 다시 묻게 하는 음성 경로를 쓰지 않는다 — 문면으로 거동을 보장하지 못한다는 것이 결정 112 의 근거다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 버려진 명령을 프레임으로 알리고 화면이 그것을 말한다 — 대상 명령 셋만
- [x] #2 확인 대기 상태를 화면이 말한다 — end · start_additional
- [x] #3 next_question 은 두 표면 어디에도 들어가지 않는 것을 단정으로 지킨다
- [x] #4 게이트 여섯이 초록인 것을 직접 돌려 확인한다
- [x] #5 실물 회차로 두 표면을 관측한다 — TASK-61.13 AC#3 과 TASK-61.15 AC#4 를 그 회차가 함께 닫는다
<!-- AC:END -->
