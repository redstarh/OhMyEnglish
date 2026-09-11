---
id: TASK-107
title: '구현: 연속 학습일 계산과 학습 히스토리 화면 (TASK-3 설계의 실행)'
status: Done
assignee: []
created_date: '2026-09-11 01:33'
updated_date: '2026-09-11 01:59'
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
- [x] #1 연속 구간 계산을 load_daily_completion 과 «같은 술어» 로 만들고 현재·최장 연속일을 돌려줌 — AC15-1~15-4 를 테스트로 덮음
- [x] #2 일일 경계를 users.timezone 으로 구하고 current_date 를 쓰지 않음 — 자정 경계를 테스트로 덮음
- [x] #3 히스토리 화면이 날짜별 학습 여부와 그날 오류 요약을 함께 보임(AC15-5) · 점수·등급·배지를 쓰지 않음(R15-7)
- [x] #4 설계서 §6 의 미결 둘을 데이터를 보고 닫고 그 판단을 회차·설계서에 적음
- [x] #5 화면을 직접 열어 확인하고 게이트(pytest · ruff · ty · tsc · eslint)를 통과함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-11 구현 완료 (세션 `ohmyenglish-7f`). 설계는 `docs/design/2026-09-11-streak-and-history-design.md`
가, 요구사항은 `docs/PRD.md` §15 가 정본임.

만든 것 셋: `services/daily_summary.load_streak`·`load_history`(gaps and islands · 「학습한 날」의
술어를 `_COMPLETION_SQL` 과 같게 둠) · `GET /api/history`(연속일 + 30일 줄) · 화면 `/history` 와
결과 화면의 진입점.

미결 둘을 닫았음(설계서 §6):
⑴ ⛔ **012 이전 날짜를 백필하지 않음** — 백필한 행은 「그날 받은 교정의 스냅샷」이 아니라 「지금
계산한 값」이고 그것이 `TASK-1` 이 표를 만든 이유를 훼손함. 대신 `learned` 와 `analyzed` 를
서비스·응답·화면 세 층에서 갈라 나르고 화면이 「분석 기록 없음」을 별 상태로 그림.
⑵ 자정 직후 문구를 `today_done` 으로 갈라 씀.

실측 증거:
- 게이트 — pytest **936 passed**(15.8s · 신규 10건) · `ruff`(app·tests·scripts) · `format` · `ty` ·
  프론트 `tsc`·`eslint` 전부 통과.
- 판별력 — 변이 넷으로 확인했음: 어제를 살아있음에서 뺌 → 1건 FAIL · `analyzed` 를 `learned` 로
  뭉갬 → 1건 FAIL · 히스토리 범위·`today_done` 고정 → 1건 FAIL · 최장을 마지막 구간으로 → **처음엔
  잡히지 않았음**(표본에 「앞 구간이 최장」인 경우가 없었음) → 그 표본을 테스트로 더해 잡았음.
- 화면 — 검증 전용 DB·포트로 **직접 봤음**. 「2일 연속 학습 중이에요」·「최장 연속 2일」 ·
  `2026-09-11 · 학습함 · 분석 기록 없음` · `2026-09-10 · 학습함 · 오류 2건 · 패턴 1종` ·
  `2026-09-09`(학습 없음 · muted) 셋이 갈라져 보였음. 오늘 세션을 `failed` 로 바꾸면 문구가
  「어제까지 1일 연속이에요」로 바뀌는 것도 확인했음.
- 공유 dev DB 무변경(세션 17 · 요약 0).

⚠️ 관측 하나: 기본 30일을 다 그려서 학습이 없던 날이 길게 이어짐. 그대로 뒀음 — 끊긴 자리가
보이는 것이 R15-5 의 요구이고, 접거나 달력 모양으로 바꾸는 것은 별 판단임.
<!-- SECTION:NOTES:END -->
