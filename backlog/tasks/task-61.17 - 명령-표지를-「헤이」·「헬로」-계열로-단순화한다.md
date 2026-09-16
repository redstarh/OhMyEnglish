---
id: TASK-61.17
title: 명령 표지를 「헤이」·「헬로」 계열로 단순화한다
status: In Progress
assignee: []
created_date: '2026-09-16 00:56'
updated_date: '2026-09-16 01:00'
labels: []
dependencies: []
parent_task_id: TASK-61
ordinal: 192000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
결정 114 가 정본이다. 표지 ASR 이 영어에서 2회 중 1회 실패하고 그 실패가 TASK-61.15 결함의 트리거다. _WAKE_FORMS 의 «형태»만 바꾸고 「표지를 앱이 판정한다」(결정 102 ① · 104 D5)는 유지한다. ⚠️ 대가를 알고 받는다 — Hello·Hey 는 학습자가 가장 자주 말하는 첫마디라 학습 발화가 표지를 얻어 voice_command 로 저장되고 분석에서 빠질 수 있다. 그 크기를 실물 회차로 잰다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 새 표지 값역을 정하고 단정으로 지킨다 — 맨 앞 검사와 공백·문장부호 무시는 유지한다
- [x] #2 기존 표지(앱 이름)를 받는 팔을 깨지 않는 것을 단정으로 지킨다
- [x] #3 게이트 여섯이 초록인 것을 직접 돌려 확인한다
- [ ] #4 실물 회차로 두 언어를 관측하고 오탐(학습 발화가 표지를 얻는 것)의 크기를 함께 센다
<!-- AC:END -->
