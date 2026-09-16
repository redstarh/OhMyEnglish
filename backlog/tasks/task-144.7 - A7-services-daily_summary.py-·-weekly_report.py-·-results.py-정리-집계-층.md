---
id: TASK-144.7
title: 'A7: services/daily_summary.py · weekly_report.py · results.py 정리 (집계 층)'
status: Done
assignee: []
created_date: '2026-09-16 15:27'
updated_date: '2026-09-16 15:44'
labels: []
dependencies: []
parent_task_id: TASK-144
ordinal: 205000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
R3(효율) 리뷰가 이 세 파일에서 발견을 냈는데 계획서 §4 의 묶음 여섯에 이 파일들이 빠져 있었다 — 계획 대비 어긋난 첫 지점이다. 파일 겹침 0을 유지하려면 별 묶음이 필요하다. 대상: 요청 1건에 같은 timezone 조회가 두 번 나가는 자리(daily_summary) · users 표를 두 번 읽는 자리(weekly_report).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## A7 적용 (2026-09-17 · 적용 에이전트 AA + 리드 보정)

에이전트가 한 것 둘(둘 다 동작변경 아님): jsonb 보정 한 줄을 _load_jsonb 헬퍼로 뽑아 두 자리가
부르게 함(근거 주석을 헬퍼 docstring 으로 옮김) · process_weekly 가 users 를 두 번 읽던 것을
_last_week_start_for_timezone(사설)로 한 번으로 줄임. 공개 함수 last_week_start 는 그대로 둠.

⛔ **리드가 잡은 것 하나 — 에이전트가 ty 게이트를 돌리지 않았음.** _load_jsonb 의 반환형을 object 로
두어 순회 자리에서 ty 가 not-iterable 로 실패했음. 반환형을 Any 로 바꾸고 그 이유를 docstring 에
적었음(두 호출자가 다르게 좁힌다 · cast 를 넣으면 좁히는 책임이 흩어진다).

내가 직접 확인한 것: 두 SQL 이 같은 계산임(date_trunc('week', now() at time zone …) - 7일 · 한쪽은
users 조인 · 다른 쪽은 타임존 인자). 게이트: weekly 테스트 20 passed(전·후 같음) · ruff exit 0 ·
ty exit 0.
<!-- SECTION:NOTES:END -->
