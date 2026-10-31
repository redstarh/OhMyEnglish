---
id: TASK-297
title: '리디자인 T5: 모든 화면 영어 문구와 시험용 data-testid'
status: Done
assignee: []
created_date: '2026-10-31 19:05'
updated_date: '2026-10-31 19:27'
labels: []
dependencies:
  - TASK-295
ordinal: 362000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
설계: docs/design/2026-11-01-v0-home-redesign-design.md §4·§6. 문구는 단문·일상 어휘(h-doc).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 프런트 소스의 화면 문자열에 한국어가 없음(주석·데이터 키·§6 미결 제외)
- [x] #2 새 data-testid 가 있고 기존 문법 코스 testid 13개와 data 속성이 그대로임
- [x] #3 tsc · eslint 통과
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
내가 재확인: 주석 밖 한국어 9건 = 음성 명령 문구 8(영어 명령 미검증이라 설계 §6-6 대로 남김) + 한글 판별 정규식 1. course testid +10 · 기존 testid·data 속성 유지(에이전트 계수). 하네스가 읽는 문구 변경 목록은 에이전트 보고 → T6 에서 반영.
<!-- SECTION:NOTES:END -->
