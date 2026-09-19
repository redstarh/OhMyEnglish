---
id: TS-26
title: A8 · 주간 리포트 — weekly-report 와 summarize_week job
status: Done
assignee: []
created_date: '2026-09-19 05:18'
updated_date: '2026-09-19 06:02'
labels: []
dependencies: []
ordinal: 26000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
영역 A8. 대상: GET /api/weekly-report · 화면 /history/weekly · job summarize_week. 워커는 꺼 둔 채 시드 데이터로 읽기 경로를 잼.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 주간 리포트 응답이 규약대로 나옴
- [x] #2 화면 /history/weekly 가 리포트를 렌더함
- [x] #3 데이터가 없을 때의 경계가 오류가 아니라 빈 결과로 나옴
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
회차 2026-09-19-b3 (HEAD ced8df0). AC 셋 전부 통과. 응답 계약·order by week_start desc·analyzed 두 경로·화면 렌더·빈 결과 경계를 각각 재서 확인했음. summarize_week 등록 가드도 A/B 로 가렸음(지난 주 리포트가 있으면 등록하지 않음 — 11→12→12). ⚠️ 이 회차가 재지 못한 것: job 의 «처리» 절반(process_weekly)은 워커가 꺼져 있어 지나가지 않았음. 이 DB 에서 summarize_week 는 done 이 0건이고 weekly_reports 는 회차 시작에 0행이었음 — 실사용 경로를 한 번도 끝까지 지나간 적이 없음. 그 failed 10건은 전부 TASK-191 의 사람 손 표시이고 제품 실패가 아님. 상세는 result.md §5-7.
<!-- SECTION:NOTES:END -->
