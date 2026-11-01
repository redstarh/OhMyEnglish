---
id: TASK-304
title: 홈 Start speaking = 문법 코스 문장 연습(영상 없이)을 오늘의 연습 카드 자리에서 · 홈에서 추천 코치 대화 제거
status: In Progress
assignee: []
created_date: '2026-11-01 02:52'
updated_date: '2026-11-01 03:11'
labels: []
dependencies: []
ordinal: 369000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 지시 2026-11-01: 「home에서 start speaking 을 누르면 practice 의 아래 하단 영역이 start speaking 이 위치한 그 자리에 표시되도록 해 · youtube 화면이 따로 표시되지 않아도 돼 · youtube 에서 참조할 내용은 학습하는 문장의 패턴만 필요해」 + 결정 「코치 대화 빼기」(홈에서 추천 코치 대화 제거, More practice 의 다른 학습은 유지). 문법 코스 Day 화면의 문장 연습 영역을 영상과 분리한 공용 컴포넌트로 빼고 홈 카드와 코스 화면이 함께 씀. 영상 없이 저장해도 영상 위치를 덮지 않음. 하네스의 코치 세션 시작 경로를 practice-free_talk 로 바꿈. 결과 화면 partial_failure 총평 대기(codex 리뷰)도 포함.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 홈 Start speaking 이 현재 Day 의 문장 연습을 카드 자리에서 영상 없이 열고 Auto/Manual·Listen/Slow·Back/Start/Next·Finish Day 가 동작함
- [ ] #2 홈에서 영상 위치 저장이 0 으로 덮이지 않고 코스 화면과 진도가 이어짐
- [ ] #3 코스 Day 화면은 그대로 동작함(회차)
- [ ] #4 하네스가 free_talk 로 코치 세션을 시작하고 통과함 · 결과 화면이 partial_failure 에서도 총평을 기다림
- [ ] #5 설계서에 결정과 근거를 기록함
<!-- AC:END -->
