---
id: TASK-151
title: '정리: tests 트리의 누적 줄 길이 위반 17건 — 내 회차 밖에서 들어온 드리프트'
status: To Do
assignee: []
created_date: '2026-09-16 22:45'
labels: []
dependencies: []
ordinal: 212000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-17 정리 회차에서 발견. tests 트리의 lint 기준선은 H-L 이 「0」으로 적어 뒀는데(2026-09-09 TASK-37 이 정리) 지금 E501 이 17건이다. 파일별: test_pronunciation_sound_check.py 6 · test_nova.py 6 · test_gateway.py 4 · test_pipeline.py 1. 전부 한국어 주석·docstring 이고 다른 세션들이 그 뒤에 넣은 것이다(내가 오늘 넣은 8건은 이 회차에서 고쳤다). ⛔ 남의 세션 문장을 임의로 줄이지 않고 별 태스크로 둔다 — 문면을 고치는 것이므로 그 문장을 쓴 갈래가 하는 것이 맞다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 17건을 줄 나눔으로 고치고 tests 트리 기준선을 0 으로 되돌린다
- [ ] #2 H-L 항목의 「기준선 0」 서술이 다시 참이 되게 한다
<!-- AC:END -->
