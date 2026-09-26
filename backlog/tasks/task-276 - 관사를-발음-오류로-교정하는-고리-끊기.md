---
id: TASK-276
title: 관사를 발음 오류로 교정하는 고리 끊기
status: Done
assignee: []
created_date: '2026-09-26 09:23'
updated_date: '2026-09-26 09:26'
labels: []
dependencies: []
ordinal: 340000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-271 범위 밖 관측: 세션 93fb0361 에서 코치가 관사 a 를 발음 tool(an_as_a)로 3회 교정했고 판정은 전부 correct. an_as_a 가 놓친 소리 후보로 내려가 관사 문장마다 발음 교정을 부름(빈도 3 · 복습 예정)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 일반 세션 규칙 9 가 관사를 발음 보고에서 제외함
- [x] #2 발음 전용 모드 문면·공유 후보 블록은 바뀌지 않음
- [x] #3 게이트 통과
- [x] #4 리뷰 반영 후 커밋·백엔드 재기동
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
수정: SYSTEM_PROMPT 규칙 9 끝에 관사 제외 문장(전용 모드 문면·_known_sounds_block 불변 — 테스트가 전용 모드 부재를 단정). 게이트 pytest 1451 passed · ruff 0 · format 통과 · ty 0. 미확인: 실물 Nova 가 이 문장을 따르는지는 다음 실사용 대화에서 확인. 남은 선택: dev DB 의 pronunciation_an_as_a(빈도 3 · 복습 예정) 기록은 학습 이력이라 지우지 않았음.

리뷰(opus) CRITICAL·HIGH 0. MEDIUM 1 반영: 문장을 「a·an·the 를 고르거나 빼먹는 것은 문법」으로 좁혀 the 의 /ð/→/d/ 같은 진짜 소리 오류는 막지 않게 함. LOW 반영: 테스트가 두 절을 모두 고정 · 넓은 문장 부재 단정. MEDIUM 2 미반영(보고): 발음 초점 세션의 _SOUND_INSTRUCTION 'instead of the Grammar first rule 9' 가 이 문장까지 무를 수 있고, 계획이 pronunciation_an_as_a 를 초점으로 고르면 고리가 되살아남 — 근본은 잘못 분류된 키 자체(데이터 층). 최종 게이트 pytest 1451 passed · ruff 0 · format 통과 · ty 0.
<!-- SECTION:NOTES:END -->
