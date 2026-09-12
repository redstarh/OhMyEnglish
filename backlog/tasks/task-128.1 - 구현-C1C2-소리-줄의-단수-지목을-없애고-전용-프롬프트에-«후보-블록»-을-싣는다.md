---
id: TASK-128.1
title: '구현 C1+C2: 소리 줄의 단수 지목을 없애고 전용 프롬프트에 «후보 블록» 을 싣는다'
status: To Do
assignee: []
created_date: '2026-09-12 03:54'
updated_date: '2026-09-12 03:56'
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-12 KST 계획 정정 — ⛔ TASK-128.2 와 «한 단위로» 실행해야 함. 쪼갠 것이 내 판단이었고 코드를 읽어 보니 성립하지 않음.
기전: C2 가 build_pronunciation_prompt 의 시그니처를 sound: str → known_sounds: Sequence[str] 로 바꿈. 그런데 factory.create_voice_adapter 는 모드를 «pronunciation_sound is not None» 으로 판정하므로, 시그니처가 바뀌면 그 판정도 «같은 커밋에서» 바뀌어야 함(그것이 C3 임). ⇒ .1 만 커밋하면 조립이 깨진 상태가 남음.
⚠️ 범위 실측: pronunciation_sound·build_pronunciation_prompt·_pronunciation_sound_or_none 참조가 «8파일 39곳» 임(app 4 · tests 4). 직접 셌음:
  app/audio_gateway/factory.py · nova.py · session.py · api/ws.py
  tests/unit/test_ws_mode.py · test_nova.py · tests/integration/test_gateway.py · test_ws.py
⇒ 착수하는 세션은 .1+.2 를 한 묶음으로 잡고 .3(회차)까지 «같은 세션에서» 끝내는 것을 권고함 — 그 사이 바이트 게이트가 빨간 상태이므로 중간 커밋을 남기지 않는 편이 낫음.

구체적 변경 자리(직접 읽어 확인했음):
1. nova.py:483-492 의 후보 블록을 «작은 헬퍼로 추출» 함 — 전용 프롬프트와 일반 프롬프트가 같은 문면을 쓰게. ⛔ 두 곳에 쓰면 한쪽이 낡음.
2. nova._SOUND_INSTRUCTION 에서 {sound} 를 없앰. {grammar_first} 칸은 그대로(결정 71).
3. nova.build_pronunciation_prompt(known_sounds) — 고정부 + 후보 블록 + 소리 줄.
4. factory.py:44 pronunciation_sound: str | None → pronunciation_mode: bool. 그 위 주석의 「소리 키가 오면 그 모드다」 계약 서술도 함께 고침.
5. ws.py:366 폴백 제거 — 소리를 못 골라도 mode=pronunciation 이면 전용 모드로 감(결정 72 가 그 뜻을 바꿨음).
6. ws.py:380 set_session_mode 조건을 «pronunciation_sound is not None» → «pronunciation_requested» 로. ⚠️ TASK-112(결정 67)의 「소리가 정해진 뒤에 적는다」 근거가 폴백의 존재에 기대고 있었으므로 그 주석도 함께 고쳐야 함.
7. ws.py:158 _pronunciation_sound_or_none → 「후보 목록에 계획의 초점을 앞에 더한다」로 역할 변경(삭제하지 않음).
<!-- SECTION:NOTES:END -->
