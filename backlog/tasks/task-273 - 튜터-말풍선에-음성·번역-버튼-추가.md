---
id: TASK-273
title: 튜터 말풍선에 음성·번역 버튼 추가
status: Done
assignee: []
created_date: '2026-09-26 04:24'
updated_date: '2026-09-26 04:28'
labels: []
dependencies: []
ordinal: 337000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 요청 2026-09-26. 버튼만 먼저 두고 백엔드가 생기기 전까지는 비활성으로 준비 중임을 알림. 연결은 TASK-274·TASK-275 가 함
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 튜터 말풍선 아래에 음성·번역 버튼이 보임
- [x] #2 하네스 줄 계약(p textContent)이 유지됨
- [x] #3 프런트 게이트 통과·화면 직접 확인
- [x] #4 커밋함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
튜터 확정 줄 아래에 [음성]·[번역] 알약 버튼(비활성 · title 준비 중이에요). <p> 밖에 둬서 줄 textContent 계약 유지 — HTML 파서로 5/5 확인. 게이트: tsc 0 · eslint 0 errors(API_BASE 경고는 기존). 라이트 화면 캡처로 직접 확인. 연결은 TASK-274(음성)·TASK-275(번역).

리뷰(sonnet) CRITICAL·HIGH 0 · LOW 2(비활성 사유가 title 뿐 · 아바타 위 정렬) — 캡처로 정렬 확인, 사유 문제는 연결 태스크가 버튼을 활성화하며 사라져 미반영.
<!-- SECTION:NOTES:END -->
