---
id: TASK-118
title: '정리: 전용 모드에서 소리 줄의 「Grammar first rule 9」가 어긋난다 — TASK-75 승인 문면이라 되돌리는 결정이 필요하다'
status: To Do
assignee: []
created_date: '2026-09-11 23:49'
labels: []
dependencies:
  - TASK-111
ordinal: 123000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-12 KST 관측(TASK-111 회차 설계 중). 전용 프롬프트에서 규칙 9 는 «존재하지만 문면이 다르다» — 유보를 걷은 판이라 Grammar first 절이 없다. 그런데 _SOUND_INSTRUCTION 이 「take it up on that turn instead of the Grammar first rule 9」로 그 이름을 부른다. ⇒ 전용 모드에서 이 구절은 「이미 그렇게 하라고 적힌 규칙 대신 그렇게 하라」는 자기모순이다. ⛔ 그런데 그 문구는 TASK-75(사용자 승인 2026-09-10)가 정한 «대체 선언» 이고 test_nova.py::test_the_sound_line_replaces_grammar_first_and_spends_the_one_correction 이 문자열로 고정한다. 즉 고치는 것은 승인된 결정을 되돌리는 일이라 TASK-111 의 범위 밖으로 뺐다. 정본: runs/2026-09-12-task111-116-selfcontained-key.md §0 「건드리지 않는 것 하나」.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 전용 모드에서만 이 구절이 어긋나는지 확인한다 — 일반 세션에서는 규칙 9 문면이 Grammar first 라 맞는다
- [ ] #2 고치는 안 둘을 적는다 — 소리 줄을 모드별로 가르는 안과 문구를 내용으로 바꾸는 안. 각각이 「한 곳에서만 정한다」 규약(nova.py build_pronunciation_prompt docstring)에 무엇을 치르는지 함께 적는다
- [ ] #3 사용자 결정을 받는다 — TASK-75 승인 문면을 바꾸는 것이므로 팀리드가 정하지 않는다
- [ ] #4 고치면 회차를 다시 돌려 바이트 게이트를 갱신한다
<!-- AC:END -->
