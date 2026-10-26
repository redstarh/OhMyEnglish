---
id: TASK-286
title: '신규 기능: Grammar in Use BASIC 문법 코스 (학습 화면·목록 화면)'
status: Done
assignee: []
created_date: '2026-10-25 23:16'
updated_date: '2026-10-26 00:11'
labels: []
dependencies: []
ordinal: 351000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
어샷영어 Grammar in Use BASIC Day 1~6 영상(단원 113개)을 이어 듣고, 단원 문법 패턴으로 새로 쓴 문장을 한 문장씩 따라 말하는 코스. 스토리보드 v3(/tmp/ohmyenglish-giu-storyboard.html) 기준. 영상 스크립트 원문·변형문은 저장하지 않음.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 설계서가 docs/design/ 에 있음
- [x] #2 단원 113개마다 새로 쓴 연습 문장이 콘텐츠 파일에 있음
- [x] #3 백엔드: 진도 저장·따라 하기 판정·이력 API 와 테스트가 통과함
- [x] #4 프런트: 목록 화면(Day 목록·날짜별 히트맵)과 학습 화면(자동/수동 모드)이 동작함
- [x] #5 app-test-agent 통합 테스트를 돌리고 결과를 보고함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-26 구현 9bd2de3 · 수정 9c67008.
- 회차 b1(샌드박스 런처): S7 PASS · S8 FAIL(D1 완료 날짜 UTC) · S1~S6·S9 차단(샌드박스가 Chrome 기동을 막음). D2(플레이어 준비 전 getCurrentTime TypeError) 보고.
- codex 리뷰: HIGH 2(마이크 획득 경합 · 완료 뒤 주기 저장이 끝 위치를 다시 씀) · MEDIUM 1(본문을 다 읽은 뒤 413). 5건 모두 9c67008 에서 고침, 회귀 테스트 2건 추가.
- 게이트(9c67008): pytest 1473 passed · ruff 0 · ruff format ok · ty 0 · tsc 0 · eslint 오류 0(기존 경고 1).
- b1 이 만든 진도 행 2개(day 2·6)는 b2 기준선을 위해 지웠음.
- 회차 b2: 화면 시나리오를 위해 app-test-agent 를 서브에이전트로 돌림(OS 샌드박스 없음).

- 회차 b2(서브에이전트, 실제 헤드리스 Chrome): S1·S2·S5·S6·S9 PASS · S3·S4·S10 PASS(합성 마이크 — 헤드리스 Chrome 의 오디오 getUserMedia 가 끝나지 않는 환경 제약) · S8 PASS(D1 은 판별 불가 시각, pytest 회귀 테스트가 판별함) · D2 고쳐짐을 판별 절차로 확인. 새 결함 0건.
- 미검증으로 남은 것: 실제 Nova 전사로 「내가 말한 문장」을 받는 경로(스택이 stub) · 실제 마이크 장치 경로.
- 테스트가 만든 진도 행(day 2·6)은 지워 사용자가 처음부터 시작하게 했음.
<!-- SECTION:NOTES:END -->
