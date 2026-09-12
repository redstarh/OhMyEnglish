---
id: TASK-126
title: '구현: llm_calls 를 읽는 집계와 비용 보고 CLI — 지금 쓰기만 하고 읽는 경로가 0건이다'
status: Done
assignee: []
created_date: '2026-09-12 02:43'
updated_date: '2026-09-12 02:49'
labels: []
dependencies: []
ordinal: 131000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-60·TASK-124 가 쓰기를 닫았으나 그 값을 읽는 경로가 하나도 없음(API·화면·집계 0건). 사용자 결정(2026-09-12 AskUserQuestion): 「보는 경로를 만듬」 — 읽는 함수 + 갈래·기간별 집계를 먼저 닫고 화면은 나중에 붙임. ⚠️ 표를 만들고 읽는 쪽이 없는 상태를 만들지 않는다는 이 리포의 규약(012 머리말)이 있으므로 소비자를 같은 커밋에 넣음 — 화면 대신 ops CLI.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 사용자 타임존 달력 날짜로 집계한다 — ⛔ current_date·date.today() 를 쓰지 않고 users.timezone 을 SoT 로 변환한다(전역 시각 규약 3항). 그 규약을 어기면 깨지는 테스트를 둔다
- [x] #2 갈래(purpose)별로 호출 수·합계 토큰·speech/text 분해를 낸다 — Nova 는 분해가 단가를 가르므로 합계만 내지 않는다
- [x] #3 소비자를 같은 커밋에 넣는다 — scripts 의 보고 CLI 가 그 값을 출력하고 실물 dev DB 에서 한 번 돌려 출력을 회차·노트에 남긴다
- [x] #4 ⛔ 금액을 계산하지 않는다 — 단가를 어디에 둘지는 이 태스크가 정하지 않고 결정으로 남긴다(단가는 시점·리전에 따라 바뀜)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-12 세션 ohmyenglish-f4 — 사용자 결정(「보는 경로를 만듬」)으로 닫았음.

AC#1: services/usage.load_usage_summary 가 users.timezone 을 «함수 안에서» 읽어 (called_at at time zone $1)::date 로 묶음. ⛔ 타임존을 인자로 받지 않는 이유: 인자면 호출자가 하드코딩·호스트 시각을 넘길 수 있고 그 어긋남이 조용함. 사용자가 없으면 LookupError 임(조용한 UTC 폴백 금지). 규약 위반을 잡는 테스트를 뒀고 뮤테이션으로 확인했음 — at time zone 을 빼면 2026-09-11 23:30 UTC 행이 09-11 로 묶여 깨짐(KST 로는 09-12).

AC#2: (날짜 × purpose)로 호출 수·합계 토큰·speech/text 분해를 냄. ⛔ 분해를 coalesce 로 0 으로 만들지 않음 — sum() 이 전부 NULL 이면 NULL 이고 그것이 「분해 없음」임(Claude 행). 뮤테이션 넷 전부 실패로 잡힘(at time zone 제거 · coalesce 0 · UTC 폴백 · 갈래 합치기).

AC#3: 소비자를 같은 커밋에 넣었음 — scripts/usage_report.py. 실물 dev DB 출력(직접 돌림):
  2026-09-12 nova  1회 입력 216 출력 0 · 분해 입력 150/66 출력 0/0
  2026-09-12 spike 3회 입력 12,378 출력 3,396 · 분해 없음(-)
  합계 호출 4건 · 입력 12,594 · 출력 3,396
⚠️ spike 3건은 이 세션이 배선 확인·타임아웃 측정으로 쓴 것임 — 「제품이 쓴 비용」이 아님.

AC#4: 금액을 내지 않음. CLI 가 그 사실과 이유를 출력에 적음. 단가의 자리는 TASK-127(Awaiting Decision)으로 세웠음.

게이트 다섯: pytest 1004 passed(13.57s) · ruff check 0 · format --check 0 · 게이트 밖 ruff 0 · ty 0. ⚠️ 게이트 밖 format --check 에 남은 1건은 동료 세션 파일임.
<!-- SECTION:NOTES:END -->
