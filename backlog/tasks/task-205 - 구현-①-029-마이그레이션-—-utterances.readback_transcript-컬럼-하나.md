---
id: TASK-205
title: '구현 ①: 029 마이그레이션 — utterances.readback_transcript 컬럼 하나'
status: To Do
assignee: []
created_date: '2026-09-18 05:54'
labels: []
dependencies: []
ordinal: 266000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
결정 131 · 설계서 §4. 낭독 전사문을 담을 자리. ⛔ 값역 CHECK 를 DROP → ADD 하지 않는 덧붙이는 형태다 — 새 job 종류도 새 표도 만들지 않는다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 029 가 utterances 에 readback_transcript text 컬럼 하나만 더한다
- [ ] #2 기존 CHECK 를 건드리지 않는 것을 마이그레이션 본문으로 확인한다
- [ ] #3 dev DB 적용 전 pg_dump -n ohmyenglish 로 백업한다
<!-- AC:END -->
