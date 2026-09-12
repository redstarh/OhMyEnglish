---
id: TASK-128.1
title: '구현 C1+C2: 소리 줄의 단수 지목을 없애고 전용 프롬프트에 «후보 블록» 을 싣는다'
status: To Do
assignee: []
created_date: '2026-09-12 03:54'
labels: []
dependencies: []
parent_task_id: TASK-128
ordinal: 134000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
설계 정본: docs/design/2026-09-12-decision72-sound-as-candidate.md §2. 결정 72 이행의 첫 단계이고 nova.py 만 만진다.
C1 — _SOUND_INSTRUCTION 에서 «- Sound to coach today: {sound}» 단수 지목을 없앤다. ⛔ 줄 자체는 남긴다 — 결정 56(질문 목록보다 앞)과 결정 75(규칙 9·4 대체)가 그 줄에 살아 있고 지우면 둘이 함께 죽는다. {grammar_first} 칸은 그대로(결정 71).
C2 — build_pronunciation_prompt 의 인자를 sound: str → known_sounds: Sequence[str] 로 바꾸고 전용 프롬프트에도 후보 블록을 싣는다. 전용 모드에는 지금 후보가 하나도 없다(팩토리가 놓친 소리 목록을 뺀다).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 TDD — 전용 프롬프트에 단수 지목이 «없다» 와 후보 블록이 «있다» 를 반대 방향 단정 둘로 먼저 쓴다
- [ ] #2 결정 56·75·71 의 단정 셋이 그대로 통과하는 것을 확인한다 — 줄을 지운 것이 조용히 통과하지 않게 음성 대조를 붙인다
- [ ] #3 바이트 게이트가 깨지는 것을 확인하고 «회차 전에 갱신하지 않는다» (순서: 문면 → 회차 → 판정 → 게이트)
<!-- AC:END -->
