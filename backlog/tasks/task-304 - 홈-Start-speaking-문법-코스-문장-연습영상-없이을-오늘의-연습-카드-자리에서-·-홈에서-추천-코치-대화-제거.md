---
id: TASK-304
title: 홈 Start speaking = 문법 코스 문장 연습(영상 없이)을 오늘의 연습 카드 자리에서 · 홈에서 추천 코치 대화 제거
status: Done
assignee: []
created_date: '2026-11-01 02:52'
updated_date: '2026-11-01 03:45'
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
- [x] #1 홈 Start speaking 이 현재 Day 의 문장 연습을 카드 자리에서 영상 없이 열고 Auto/Manual·Listen/Slow·Back/Start/Next·Finish Day 가 동작함
- [x] #2 홈에서 영상 위치 저장이 0 으로 덮이지 않고 코스 화면과 진도가 이어짐
- [x] #3 코스 Day 화면은 그대로 동작함(회차)
- [x] #4 하네스가 free_talk 로 코치 세션을 시작하고 통과함 · 결과 화면이 partial_failure 에서도 총평을 기다림
- [x] #5 설계서에 결정과 근거를 기록함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-11-01
- 회차 b12(tests/agent/runs/2026-11-01-b12): 카드 안 문장 연습 · 영상 위치 보존(2/2) · 코스 Day 화면 회귀 · Free talk 카드 안 세션 통과. 결함 D1(Finish Day 뒤 카드 낡음) · D2(390 폭 카드 5px 줄어듦).
- codex 리뷰: HIGH 2(연습 닫기와 세션 마이크 획득이 겹침 · 닫기 직후 다시 열면 진도 역행) · MEDIUM 1(Day 완료 뒤 낡은 카드) → 모두 수용, bf6b938 에서 고침. 회차 b12r 4/4 통과(마이크 순서 · 50ms 경쟁 · 저장 지연 변형 포함).
- codex 2차 MEDIUM(멈춘 저장이 조회를 영원히 막음) → settleSaves 에 3초 상한 · 상한을 넘긴 저장은 목록에서 뺌. 회차 b12r3·r4: 영원히 막히지 않음 확인 · 붙잡지 않으면 즉시(21~46ms).
- 판단(고리 끊기): 저장이 계속 멈춘 동안에는 닫고 열 때마다 약 3초 대기가 남음(r4 세 번째 열기 3040ms). 네트워크가 멈춘 경우라 조회 자체도 정상일 수 없어 더 고치지 않음 — 단정은 「영원히 막히지 않는다」로 고정함.
- 하네스 시작 경로 practice-free_talk · 게이트 테스트 112 passed. dev DB 기준선 그대로(19·144·0·0).
<!-- SECTION:NOTES:END -->
