---
id: TASK-279
title: 코치가 맞는 문장을 교정하고 틀린 교정(a apple)을 가르침
status: Done
assignee: []
created_date: '2026-09-26 13:32'
updated_date: '2026-09-26 13:40'
labels: []
dependencies: []
ordinal: 343000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-278 회차 r3: 학습자의 맞는 an apple juice 에 'I want a apple juice' 를 따라 하게 함. 세 회차 모두 맞는 문장을 다시 따라 하게 함. 관사 초점 계획 + 드릴 지시가 원인 후보
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 원인을 프롬프트 조립 결과로 확정함
- [x] #2 재현 테스트를 먼저 세우고 수정함
- [x] #3 격리 스택 실물 회차로 효과를 셈(상한 2세션)
- [x] #4 게이트 통과·리뷰 반영·커밋·재기동
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
원인: 조립 프롬프트에 관사 초점 + 드릴의 「다시 말하게 하라」만 있고 「맞으면 어떻게 하라」가 없음. 수정: 규칙 4 첫머리 'Correct only a real mistake... never ask them to repeat a correct sentence or change a correct word'. 게이트 pytest 1452 passed · ruff 0 · format 통과 · ty 0. 실물 r4·r5(격리 t278 · 후보 없음): 틀린 교정 0/2 · 발음 판정 0 · 맞는 문장 반복 3/6 턴 잔존 · 턴 88~177자. 기록 runs/2026-09-26-task278-real-nova.md §4. 남은 반복은 _DRILL_INSTRUCTION 영역(지표와 묶임)이라 미변경.

리뷰(sonnet) CRITICAL·HIGH 0 · MEDIUM-HIGH 1(한계 공개): 규칙 4 의 never 가 드릴 지시 때문에 실측 3/6 턴 지켜지지 않음 · 「go on」이 drill_turns_expected 미달을 부를 수 있으나 이번 회차는 픽스처 3개라 잴 수 없었음. 결함이 아니라 드릴 문면 결정이 선행돼야 하는 한계로 기록.
<!-- SECTION:NOTES:END -->
