---
id: TASK-61.12
title: '결함 후보: 종류를 말하지 않은 모드 변경 요청에 코치가 되묻지 않고 target 을 스스로 고른다'
status: To Do
assignee: []
created_date: '2026-09-15 18:27'
labels: []
dependencies: []
parent_task_id: TASK-61
ordinal: 187000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
회차 `runs/2026-09-16-task61-10-mode-change` §3 미충족 ② 에서 1회 관측했다. 학습자가 「Oh My English, change the practice mode.」 처럼 종류를 말하지 않았을 때 코치는 어느 연습인지 되묻지 않고 「오늘 세션을 끝내고 새 연습 세션을 시작할까요?」로 예·아니오 확인만 물었다. 백엔드 warning 이 0건이므로 페이로드는 버려지지 않았고 모델이 값역 안의 target 을 스스로 골랐다는 뜻이다. ⇒ 학습자가 「예」라고만 답하면 자기가 고르지 않은 모드로 세션이 열릴 수 있다. ⛔ 결정 111 을 뒤집지 않는다 — 종류를 «말한» 경로는 두 언어에서 2/2 로 성립했다. 구멍은 말하지 않은 경로 하나다. ⚠️ 표본 1건이므로 기전으로 단정하지 않는다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 되묻지 않는 거동의 크기를 실물 회차로 센다 — 같은 픽스처를 반복해 되묻는 비율을 얻는다
- [ ] #2 고치는 자리를 정한다: 지시문 문면인가 앱인가 — 앱이 막는 안은 「target 을 못 들은 requested 를 버리지 않고 학습자에게 되묻는 경로」이고 지금 리포에 그 경로가 없다
- [ ] #3 고치면 실물 회차로 관측한다
<!-- AC:END -->
