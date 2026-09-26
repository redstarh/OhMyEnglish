---
id: TASK-267
title: 백엔드가 스텁 어댑터로 떠서 학습이 즉시 끝나고 가짜 오류가 쌓이는 결함을 고친다
status: In Progress
assignee: []
created_date: '2026-09-26 01:30'
updated_date: '2026-09-26 01:35'
labels: []
dependencies: []
ordinal: 331000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-26 10:16 기동한 :8002 가 VOICE_ADAPTER 없이 떠 기본값 stub 으로 동작함. 학습 시작 즉시 FIXTURE_TURNS 세 턴이 재생되고 세션이 닫혀 결과 화면(오늘 학습을 마쳤어요)으로 넘어감. dev DB 에 가짜 세션·오류가 누적됨.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 원인을 실행 중 프로세스와 DB 행으로 확인함
- [x] #2 기본 설정으로 띄워도 픽스처 발화가 dev DB 에 기록되지 않음을 테스트로 고정함
- [x] #3 백엔드를 nova 로 재기동하고 학습 시작이 실제 세션으로 열림을 확인함
- [ ] #4 오염된 dev DB 행의 처리를 사용자 결정에 따라 마침
<!-- AC:END -->
