---
id: TASK-66.2
title: '구현 2: 설정 키 shadowing_clip_audio_root'
status: Done
assignee: []
created_date: '2026-09-13 22:11'
updated_date: '2026-09-13 22:27'
labels: []
dependencies: []
parent_task_id: TASK-66
ordinal: 150000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
계획서 Task 2. 학습자 녹음 뿌리를 재사용하지 않는다 — 스윕이 그 뿌리를 순회하며 걷으므로 제품 자산이 지워질 수 있고, 그 뿌리는 .gitignore 에 걸려 배포되지 않는다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 선언 기본값 tripwire 와 두 뿌리가 다르다는 단정이 통과한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
완료 2026-09-14 (세션 ohmyenglish-f4).

red 를 먼저 봤음 — 선언 기본값 tripwire 가 KeyError, 새 단정이 AttributeError 로 2 failed.

설정을 더한 뒤 test_config.py 32 passed. 게이트: ruff check 0 · ruff format 정합(E501 하나를 주석 두 줄로 갈라 고쳤음) · ty 0.

단정이 재는 것 셋: 선언 기본값이 ../../assets/clips 인가 · 학습자 녹음 뿌리와 다른가 · 그 뿌리의 «아래»가 아닌가(스윕 순회 범위 밖이라는 뜻).
<!-- SECTION:NOTES:END -->
