---
id: TS-24
title: A6 · 일일 오류 요약과 완료 판정 — daily-summary
status: Done
assignee: []
created_date: '2026-09-19 05:18'
updated_date: '2026-09-19 06:13'
labels: []
dependencies: []
ordinal: 24000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
영역 A6. 대상: GET /api/daily-summary. 근거: PRD §13·§14. ⛔ 날짜 경계는 사용자 타임존으로 갈림 — UTC 자정부터 09시 KST 사이에 current_date 가 하루 이르다는 함정을 반드시 검사에 넣음.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 그날의 오류 요약이 사용자 타임존 기준으로 갈림 (UTC 자정~09시 KST 구간을 직접 재현)
- [x] #2 일일 학습 완료 판정이 시나리오 1개 기준으로 성립함 (PRD §14)
- [x] #3 기록이 없는 날의 응답 경계가 오류가 아니라 빈 결과로 나옴
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
회차 2026-09-19-b3 (HEAD ced8df0). AC#2·#3 통과. AC#1 은 차단됨 — 측정 시각(05:44~06:2x UTC)에 current_date 와 KST 날짜가 같아 판별력이 없고, daily_error_summary 의 쓰기 경로는 분석 워커에서만 돌아 유료 호출 없이 지나갈 수 없음. users.timezone 임시 변경 승인을 호출 세션에 요청했으나 회차 끝까지 답이 오지 않았음. ⛔ 「0건 관측」을 결함으로 올리지 않았음. 다만 같은 날짜 경계 요구(R14-3)는 ended_at=2026-09-16 15:10+00 세션을 함정 구간에 심어 통과 확인했음. 상세는 result.md §5-4·§6-1.

AC#1 차단을 풀어 통과로 닫았음 (2026-09-19 06:11 UTC · 호출 세션이 users.timezone 임시 변경을 승인함). 축 둘로 갈랐고 유료 호출은 0건임(llm_calls 34 → 34 · 워커를 켜지 않았음).

축 B (공유 상태를 건드리지 않음) — ended_at=2026-09-18 15:30:00+00 인 완료 세션을 심었음. 그 값의 UTC 날짜는 2026-09-18 이고 KST 날짜는 2026-09-19 임(함정 구간 15:00~24:00 UTC = 00:00~09:00 KST). /api/daily-summary 의 completed_today 가 false → true · completed_scenarios 가 0 → 1 로 움직였음. ended_at::date(UTC) 를 썼다면 2026-09-18 ≠ 오늘(2026-09-19) 이라 세지 않았을 것임.

축 A (승인받은 users.timezone 변경) — daily_error_summary 에 2026-09-19(occ 91) 과 2026-09-18(occ 82) 두 행을 심고 같은 엔드포인트를 두 번 읽었음. Asia/Seoul 에서 summary_date=2026-09-19 · occurrence_count=91 이었고, Pacific/Midway(UTC-11) 로 바꾸자 summary_date=2026-09-18 · occurrence_count=82 · patterns[0].target_form=「Midway 날짜 쪽」 으로 «다른 행» 이 나왔음. 그 사이 current_date 는 2026-09-19 로 그대로였음 — 즉 「오늘」이 컬럼에서 오고 current_date 에서 오지 않음. /api/history 의 days[0] 도 2026-09-18 로 함께 움직여 두 엔드포인트가 같은 「오늘」을 씀.

승인 조건 넷을 지킨 기록: ⑴ 원값 Asia/Seoul 을 먼저 읽어 남겼음 ⑵ 복원 뒤 값을 «읽어» 확인했고 엔드포인트가 2026-09-19/91 로 돌아온 것도 확인했음 ⑶ ALTER DATABASE·ALTER SYSTEM 을 쓰지 않았고 범위는 ohmyenglish.users.timezone 행 값 하나임 ⑷ 저장된 timestamptz 를 변환해 UPDATE 하지 않았음. 공유 상태 노출 창은 06:11:57.092909 → 06:11:57.38278 = 290밀리초임.

⚠️ 이 회차가 재지 못한 절반: daily_error_summary 의 «쓰기» 경로(_UPSERT_SQL)는 분석 워커에만 있어 지나가지 않았음. 정적 대조만 남겼음 — 그 SQL 의 앵커가 (u.created_at at time zone $3)::date 이고 $3 를 timezone_of(conn,user_id) 가 채움(daily_summary.py:55·70·304). 그리고 daily_summary·weekly_report·learner_time 의 current_date 언급 4건은 전부 「쓰지 않는다」는 주석이고 실제 사용 0건임(evidence/33). ⛔ 정적 대조는 측정이 아니므로 그 사실을 함께 적었음.

증거: evidence/30~35 · 상세는 result.md §11.
<!-- SECTION:NOTES:END -->
