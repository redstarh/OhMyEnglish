---
id: TS-5
title: 결과 조회의 오류 경로 경계가 사용자에게 구분돼 나온다
status: Done
assignee: []
created_date: '2026-09-09 08:23'
updated_date: '2026-09-09 08:23'
labels: []
dependencies: []
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
없는 세션과 형식이 틀린 값이 서로 다른 상태로 응답되는지 본다. 메인이 직접 curl 로 재현했다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 존재하지 않는 uuid 는 HTTP 404 다
- [x] #2 uuid 형식이 아닌 값은 HTTP 422 다
<!-- AC:END -->
