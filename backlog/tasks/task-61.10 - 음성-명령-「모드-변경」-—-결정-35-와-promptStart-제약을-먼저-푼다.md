---
id: TASK-61.10
title: 음성 명령 「모드 변경」 — 결정 35 와 promptStart 제약을 먼저 푼다
status: To Do
assignee: []
created_date: '2026-09-15 16:17'
labels: []
dependencies: []
parent_task_id: TASK-61
ordinal: 185000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
PRD §Voice Control 의 남은 명령 셋 가운데 하나다.

⛔ 지금 열 자리가 아닌 이유 둘: ① 「모드를 러너가 다시 판정하지 않는다」가 규약이다(결정 35 · audio_gateway/session.py 의 _shadowing·_pronunciation_sound 주석 둘이 같은 근거를 적어 둔다) ② Nova 지시문은 promptStart 에 한 번만 실려 세션 중 교체가 성립하지 않는다. ⇒ 세션 중 모드 변경은 사실상 「세션을 닫고 새로 여는 것」이고 그것은 TASK-61.8 의 「추가 학습」이 이미 한다.

⚠️ 그래서 이 태스크의 첫 물음은 「모드 변경이 추가 학습과 다른 기능인가」다. 다르지 않다면 PRD 목록에서 이 항목이 추가 학습으로 흡수되는지 사용자 판단을 받는다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 모드 변경이 「추가 학습」과 다른 기능인지 사용자 판단을 받는다
- [ ] #2 다르다면 결정 35 와 promptStart 제약을 어떻게 푸는지 정한다
- [ ] #3 명령을 만들면 실물 회차로 관측한다
<!-- AC:END -->
