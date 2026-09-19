---
id: TASK-253
title: '종료처리: 출처를 잃은 문장은 처리하지 않음 (사용자 결정)'
status: Done
assignee: []
created_date: '2026-09-19 14:22'
updated_date: '2026-09-19 14:22'
labels: []
dependencies: []
ordinal: 317000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 결정(2026-09-19): 처리하지 말고 종료처리함. 통합테스트 배치 B2 가 관측한 대가 — 출처를 잃은 문장을 앱 경로로 지울 수단이 없음(DELETE 엔드포인트 둘이 모두 video_id 를 요구하고 그 문장만 보여 주는 화면도 없음). 그래서 그 회차가 AC 측정 중 만든 문장 408d6cc5-da54-4f82-b3a7-69b32404ecd4 1건이 DB 에 남아 있음. ⛔ 결함이 아니라 설계서가 명시로 유보한 자리의 알려진 잔여임 — 뒤에서 쫓지 말 것. 반영: docs/design/2026-09-18-video-learning-design.md §10 항목 4 에 결정과 남은 행 id 를 적었음.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 그 유보를 닫는 결정이 설계서에 적혔음
- [x] #2 남은 행 1건이 결함으로 쫓기지 않도록 그 id 와 근거가 함께 적혔음
<!-- AC:END -->
