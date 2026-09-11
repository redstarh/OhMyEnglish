---
id: TASK-107
title: '구현: 연속 학습일 계산과 학습 히스토리 화면 (TASK-3 설계의 실행)'
status: To Do
assignee: []
created_date: '2026-09-11 01:33'
labels: []
dependencies: []
ordinal: 110000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
설계는 docs/design/2026-09-11-streak-and-history-design.md 가, 요구사항은 docs/PRD.md §15 가 정본임. 이 태스크는 그 설계를 코드로 옮김.

범위: ⑴ services/daily_summary.py 에 연속 구간 계산(gaps and islands)과 현재·최장 연속일 ⑵ 조회 엔드포인트 ⑶ 히스토리 화면(새 경로가 유력함 — 지금 히스토리 화면이 없음).

⛔ 「학습한 날」의 술어를 새로 쓰지 않음 — load_daily_completion 과 같은 조건을 씀. 두 곳에서 갈리면 연속일과 완료 문구가 어긋남(R15-1).

⛔ 설계서 §6 의 미결 둘을 이 태스크가 닫음: ⑴ 012 이전 날짜에 daily_error_summary 행이 없어 히스토리에서 「학습은 했는데 요약이 없다」로 보임 — 백필 스크립트를 만들 것인가 화면이 별 상태로 그릴 것인가 ⑵ 연속일 문구가 자정 직후에 「어제까지의 값」임을 오해 없이 쓰기.

⚠️ 실측 기준선(2026-09-11 · 개발 DB): 완료일이 08-25 · 09-01 · 09-03 · 09-06 · 09-09~09-10 이고 최장 연속 2일 · 그 시점 현재 연속 2일임.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 연속 구간 계산을 load_daily_completion 과 «같은 술어» 로 만들고 현재·최장 연속일을 돌려줌 — AC15-1~15-4 를 테스트로 덮음
- [ ] #2 일일 경계를 users.timezone 으로 구하고 current_date 를 쓰지 않음 — 자정 경계를 테스트로 덮음
- [ ] #3 히스토리 화면이 날짜별 학습 여부와 그날 오류 요약을 함께 보임(AC15-5) · 점수·등급·배지를 쓰지 않음(R15-7)
- [ ] #4 설계서 §6 의 미결 둘을 데이터를 보고 닫고 그 판단을 회차·설계서에 적음
- [ ] #5 화면을 직접 열어 확인하고 게이트(pytest · ruff · ty · tsc · eslint)를 통과함
<!-- AC:END -->
