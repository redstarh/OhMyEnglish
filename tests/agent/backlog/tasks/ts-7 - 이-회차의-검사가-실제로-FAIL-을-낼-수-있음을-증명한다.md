---
id: TS-7
title: 이 회차의 검사가 실제로 FAIL 을 낼 수 있음을 증명한다
status: Done
assignee: []
created_date: '2026-09-09 08:23'
updated_date: '2026-09-09 08:23'
labels: []
dependencies: []
ordinal: 7000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
6/6 PASS 는 무력한 드라이버로도 나올 수 있다. 앱을 바꾸지 않고 기준값만 어긋나게 해 검사가 어긋남을 잡는지 본다. 회차 에이전트가 5/5 어긋남을 관측했고 메인이 경계 2건을 직접 재현했다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 기준값을 어긋나게 바꾸면 5건 중 5건이 어긋남으로 잡힌다
- [x] #2 0건과 키 부재가 서로 구분된다 — b2f0d169 와 76d9ef31 로 확인한다
- [x] #3 여섯 건의 200 이 고정 응답이 아님을 404·422 로 확인한다
<!-- AC:END -->
