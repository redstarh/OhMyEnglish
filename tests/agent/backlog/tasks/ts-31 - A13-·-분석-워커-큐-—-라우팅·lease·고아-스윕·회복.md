---
id: TS-31
title: A13 · 분석 워커 큐 — 라우팅·lease·고아 스윕·회복
status: To Do
assignee: []
created_date: '2026-09-19 05:19'
labels: []
dependencies: []
ordinal: 31000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
영역 A13. 대상: workers/analysis_worker.py 의 _HANDLERS 표(job 5종) · services/jobs.py 의 claim·lease. ⛔ 이 갈래가 TASK-223·224·225·227 로 고친 자리라 회귀 확인의 값어치가 가장 큼. ⛔ 워커를 관측용으로 잠깐 켜지 않음(H-CD) — 켜야 하면 analysis_jobs 와 llm_calls 를 켜기 전후로 세어 증거로 남김.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 _HANDLERS 표에 없는 job 종류가 조용히 흘러가지 않고 큐에 사유를 남김 (TASK-225)
- [ ] #2 lease 를 잃은 뒤에는 결과를 커밋하지 않음 — jobs.LeaseLost 경로가 성립함 (TASK-224)
- [ ] #3 고아 스윕이 정지 중 세션의 .part 파일을 지우지 않음 (TASK-223)
- [ ] #4 회복 스윕이 running 상태로 시한을 넘긴 job 을 되돌림
- [ ] #5 job 5종이 전부 표에 있고 claim 쿼리가 failed 를 집지 않음 (코드를 읽어 확인 · H-CD)
<!-- AC:END -->
