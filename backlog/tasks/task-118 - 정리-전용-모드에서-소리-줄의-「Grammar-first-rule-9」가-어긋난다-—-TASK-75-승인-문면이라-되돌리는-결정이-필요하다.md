---
id: TASK-118
title: '정리: 전용 모드에서 소리 줄의 「Grammar first rule 9」가 어긋난다 — TASK-75 승인 문면이라 되돌리는 결정이 필요하다'
status: Done
assignee: []
created_date: '2026-09-11 23:49'
updated_date: '2026-09-12 03:36'
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
- [x] #1 전용 모드에서만 이 구절이 어긋나는지 확인한다 — 일반 세션에서는 규칙 9 문면이 Grammar first 라 맞는다
- [x] #2 고치는 안 둘을 적는다 — 소리 줄을 모드별로 가르는 안과 문구를 내용으로 바꾸는 안. 각각이 「한 곳에서만 정한다」 규약(nova.py build_pronunciation_prompt docstring)에 무엇을 치르는지 함께 적는다
- [x] #3 사용자 결정을 받는다 — TASK-75 승인 문면을 바꾸는 것이므로 팀리드가 정하지 않는다
- [x] #4 고치면 회차를 다시 돌려 바이트 게이트를 갱신한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-12 — 사용자 결정 71(AskUserQuestion · 세션 ohmyenglish-f4 가 받음): 「전용 모드에서만 구절을 버린다」. 정본은 docs/ops/captain-instruction-register.md 「결정 71」임. ⇒ 일반 세션 문면은 그대로 두므로 TASK-75 의 승인은 그것이 참인 모드에서 그대로 살고 자기모순만 사라짐. ⚠️ test_nova.py 가 그 문자열을 고정하므로 모드별로 가른 단정이 필요함. 구현은 nova.py 를 소유한 갈래(세션 ohmyenglish-19)에 전달했음.

2026-09-12 KST — 사용자 결정 71 로 닫았음. 회차 정본: tests/harness/runs/2026-09-12-task123-118-subtract-key-forcing.md (TASK-123 과 한 묶음 — 같은 문면이고 바이트 게이트가 어느 쪽이든 재측정을 강제함).

AC#1 — 전용 모드에서만 어긋난다는 것을 확인했음. 전용 프롬프트의 규칙 9 에는 Grammar first 절이 없고(유보를 걷은 판) 일반 세션에는 실재함. ⇒ 같은 구절이 한 모드에서만 자기모순임.
AC#2 — 안 둘을 적었고 사용자가 «모드별로 가름» 을 골랐음(결정 71). 치른 대가: build_pronunciation_prompt docstring 의 「소리 줄을 한 곳에 둔다」 규약에 칸 하나(_GRAMMAR_FIRST_CLAUSE)를 열었음. ⛔ 주석에 「칸을 더 열지 마라」를 못박았음 — 칸마다 그 규약이 약해짐.
AC#3 — 사용자 결정을 받았음(결정 71 · 대장 docs/ops/captain-instruction-register.md:221 · AskUserQuestion 으로 직접 물었고 물은 주체는 세션 ohmyenglish-f4). ⛔ 나는 그 전달을 그대로 받지 않고 «대장에서 직접 읽어» 확인했음.
AC#4 — 회차를 다시 돌려 바이트 게이트를 갱신했음. 전용 프롬프트 1,927자 → 1,660자 · rule 번호 참조 [] · Grammar first 없음. ARM-A 코칭 4/4 로 기준선과 같아 회귀 없음.

단정을 «반대 방향으로 둘» 뒀음 — test_the_sound_line_replaces_grammar_first_and_spends_the_one_correction 이 일반 세션에서 그 구절을 요구하고, 신설한 test_the_dedicated_prompt_never_names_the_grammar_first_rule 이 전용 모드에서 그것이 없어야 함을 요구함. 후자에 음성 대조 둘을 붙였음(줄을 통째로 지운 것이 조용히 통과하지 않게).
<!-- SECTION:NOTES:END -->
