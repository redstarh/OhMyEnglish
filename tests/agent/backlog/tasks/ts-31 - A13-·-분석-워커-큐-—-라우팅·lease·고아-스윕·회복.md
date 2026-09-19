---
id: TS-31
title: A13 · 분석 워커 큐 — 라우팅·lease·고아 스윕·회복
status: Done
assignee: []
created_date: '2026-09-19 05:19'
updated_date: '2026-09-19 06:34'
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
- [x] #1 _HANDLERS 표에 없는 job 종류가 조용히 흘러가지 않고 큐에 사유를 남김 (TASK-225)
- [x] #2 lease 를 잃은 뒤에는 결과를 커밋하지 않음 — jobs.LeaseLost 경로가 성립함 (TASK-224)
- [x] #3 고아 스윕이 정지 중 세션의 .part 파일을 지우지 않음 (TASK-223)
- [x] #4 회복 스윕이 running 상태로 시한을 넘긴 job 을 되돌림
- [x] #5 job 5종이 전부 표에 있고 claim 쿼리가 failed 를 집지 않음 (코드를 읽어 확인 · H-CD)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
배치 B4 회차(2026-09-19 · runs/2026-09-19-b4/) 에서 AC 5건 전건을 쟀음. HEAD 는 착수 997c728 · 종료 95d5dfe 이고 그 사이 변경은 다른 배치의 테스트 원장 커밋 1건뿐이라 앱 소스는 무변경임.

- AC#1: dispatch 가 표에 없는 종류에 last_error 'no handler for job type: b4_bogus_job_type' 을 남김. before 값이 null 이어서 관측력도 함께 보였음.
- AC#2: complete 가 LeaseLost 를 올리고(올바른 토큰에서는 done — 양성 대조) 실제 호출자 process_scenario 가 임대를 잃은 상태에서 무대 행을 0건 그대로 두었음. LeaseLost 를 잡는 다섯 자리가 모두 broad except 앞임.
- AC#3: paused·active 세션의 .pcm.part 가 남고 끝난 세션의 고아 2건이 지워졌음(양성 대조).
- AC#4: 만료된 running job 이 다시 집히며 attempts 1→2 · lease 재발급. 시한 안이면 안 집힘(음성 대조). attempts 소진 + 만료는 reaper 가 failed 로 닫음.
- AC#5: DB CHECK 의 5값과 _HANDLERS 키 5개가 동일. failed 를 claim 하지 않고, 같은 행을 pending 으로 바꾸면 집힘(관측력 증명).

⛔ 워커 루프를 켜지 않았고 유료 모델 호출 0건임(llm_calls 회차 창 내 0). claim 을 부른 자리는 전부 롤백되는 트랜잭션이고 커밋한 행은 내 표지 사용자의 것뿐이며 끝에 지웠음.
⚠️ recover_while_idle·flush_ended_sessions 는 부르지 않았음 — 보존 픽스처 세션을 파괴하는 경로임(H-AT ②). TASK-227 이 고친 「연결 1건으로 회복 셋」은 이 회차가 재지 않았음.
<!-- SECTION:NOTES:END -->
