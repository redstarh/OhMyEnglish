---
id: TASK-280
title: 드릴 지시를 반복 요구에서 후속 질문으로 완화
status: Done
assignee: []
created_date: '2026-09-26 13:41'
updated_date: '2026-09-26 13:52'
labels: []
dependencies: []
ordinal: 344000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 결정 2026-09-26(AskUserQuestion: 드릴 문면 완화). 맞는 문장 반복 3/6 턴 잔존(TASK-279 실측)의 원인인 _DRILL_INSTRUCTION 의 「다시 말하게 하라」를 「짧은 후속 질문으로 채우라」로 바꿈. 4교대 하한 유지
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 문면을 고정한 테스트를 먼저 바꾸고 수정함
- [x] #2 교대 정의 문장(지표와 같은 단위)은 유지함
- [x] #3 실물 회차로 반복 턴·교대 수를 셈(상한 2세션)
- [x] #4 게이트·리뷰·커밋·재기동
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
수정: _DRILL_INSTRUCTION 을 「짧은 후속 질문으로 채우고 맞는 문장 반복 금지」로(교대 하한·정의 유지 · 축 4 테스트 교체). 게이트 pytest 1452 passed · ruff 0 · format 통과 · ty 0. 실물 r6~r9(격리 t280): 새 문면만으로는 반복 4/5·4/5 로 줄지 않음 · hint_timing 가설 불분명(r8 4/5 · r9 0/5 이나 교정 지어냄 2) · 발음 판정 0. 기록 runs/2026-09-26-task278-real-nova.md §5. 공통 구동부 가설: 이미 맞게 쓰는 관사를 계획이 초점으로 고름. 실물 세션 누적 9회로 루프 상한 직전에서 멈춤.

리뷰(sonnet) CRITICAL·HIGH 0 · MEDIUM 반영: 교정하는 턴에는 후속 질문을 건너뛴다(규칙 4 우선)를 드릴 줄에 명시·테스트 고정. LOW 반영: 2026-09-07 설계서의 옛 문면 인용에 대체 표시. ⚠️ 이 추가 문장은 실물 회차를 돌리지 않았음(루프 상한 직전). 최종 게이트 pytest 1452 passed · ruff 0 · format 통과 · ty 0.
<!-- SECTION:NOTES:END -->
