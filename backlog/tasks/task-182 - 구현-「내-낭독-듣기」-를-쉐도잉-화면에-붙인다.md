---
id: TASK-182
title: '구현: 「내 낭독 듣기」 를 쉐도잉 화면에 붙인다'
status: Done
assignee: []
created_date: '2026-09-18 01:40'
updated_date: '2026-09-18 01:52'
labels: []
dependencies:
  - TASK-180
  - TASK-181
ordinal: 243000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
녹음이 저장되어도 학습자가 다시 들을 수 없어 학습 루프가 닫히지 않는다. 클립 재생과 같은 new Audio() 경로를 쓰고 VoiceIo 는 건드리지 않는다 — 코치 음성 큐에 넣으면 발화와 섞이고 barge-in 이 낭독을 끊는다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 녹음이 저장된 뒤에만 버튼이 보인다
- [x] #2 녹음 중에는 버튼이 잠긴다
- [x] #3 화면을 벗어나면 재생이 멈춘다
- [x] #4 비교·점수·파형 UI 를 만들지 않는다
<!-- AC:END -->
