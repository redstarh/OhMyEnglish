---
id: TASK-222
title: '정리 회차: 백엔드 앱 소스 전체 (codebase-cleanup)'
status: In Progress
assignee: []
created_date: '2026-09-19 00:18'
updated_date: '2026-09-19 00:18'
labels: []
dependencies: []
ordinal: 283000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 결정 2026-09-19 — 범위는 app/backend/app 전체(63파일 15,629줄). 프런트는 테스트 러너가 0건이라 회귀 게이트가 없어 제외했고, 러너 도입은 별 작업으로 둔다. 기준선(이 턴 실측): HEAD 07e81ef · 수집 1400 · 통과 1400(skip 0 이라 두 수가 같음) · ruff exit 0 · ruff format 305 files · ty exit 0 · tsc 0 · eslint 0 · next build 0. 규칙군 전수: 0건 다섯(C4 LOG PIE TID RSE) · PERF 1 RET 1 FURB 2 ISC 2 SIM 3 ARG 4 · ANN 10 RUF 18 PL 23 TRY 59 EM 59. ARG 넷은 포트 구현의 미사용 인자이고 ISC 둘은 의도한 줄바꿈 f-string 이라 둘 다 켜지 않는다. noqa 표식은 BLE001 한 건뿐이고 살아 있다(직전 회차 TASK-144.1 이 그 축을 이미 수확함). ⛔ 문면 정본 검사가 SYSTEM_PROMPT 부분 문자열 12건 포함으로 많다 — 그 문면을 건드리면 FAIL 하고, 그때 검사를 고치지 않고 내 변경을 고친다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 리뷰 여섯 갈래를 읽기 전용으로 돌려 지적을 수집하고 신뢰도로 통합한다
- [ ] #2 동작변경=예 인 지적은 갈라내 별 태스크로 등록한다
- [ ] #3 적용 뒤 수집 개수가 1400 이상이고 게이트 여덟이 통과한다
- [ ] #4 위반 0건 규칙군을 켜서 안전망을 늘린다
<!-- AC:END -->
