---
id: TASK-56
title: '결함(MEDIUM): 영구 오류(4xx)에서 결과 화면이 2초마다 무한 재시도한다'
status: To Do
assignee: []
created_date: '2026-09-09 08:33'
labels: []
dependencies: []
ordinal: 59000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-09 사용자 여정 회차(TS-3)에서 관측. app/frontend/app/results/[sessionId]/page.tsx:15-20 의 TERMINAL_STATUSES 는 종료 상태 4종(final·partial_failure·connection_failed·no_utterances)만 담고, catch 분기(:117-118)가 모든 예외에 2초 재시도를 건다. 그 자리 주석은 네트워크 오류는 terminal 이 아니다 를 전제하지만 404·422 는 네트워크 오류가 아니다. 그래서 없는 세션을 연 화면이 끝없이 폴링한다. 메인이 그 줄을 직접 열어 확인했다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 4xx 응답을 terminal 로 분류해 폴링을 멈춘다
- [ ] #2 주석이 전제한 네트워크 오류와 응답이 4xx 인 경우를 코드에서 갈라 쓴다
- [ ] #3 고친 뒤 없는 uuid 화면에서 요청이 반복되지 않는 것을 직접 확인한다
<!-- AC:END -->
