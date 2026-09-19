---
id: TS-21
title: A3 · 음성 세션 왕복 (실물 Nova) — 실제 음성 1회차
status: Done
assignee: []
created_date: '2026-09-19 05:18'
updated_date: '2026-09-19 07:42'
labels: []
dependencies: []
ordinal: 21000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
영역 A3. 대상: /ws/session + 실물 nova 어댑터. ⛔ 실물 Bedrock 호출이 필요함(사전 승인 범위 · 회차 1건). ⛔ A11 과 같은 회차로 합쳐 비용을 한 번만 씀. 수단: tests/harness/p_readback_leg.py 머리말의 진입 순서. 픽스처 public/harness/readback.wav 는 끝에 침묵 2초가 있어야 함.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 실물 어댑터로 세션 1회가 열려 사용자 음성에 음성 응답이 돌아옴
- [x] #2 그 발화의 전사가 DB 에 남음
- [x] #3 회차가 만든 세션이 teardown_session.py 로 걷혔음
- [x] #4 llm_calls 증가분을 회차 전후로 세어 비용 근거를 남김
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## B6 회차 (2026-09-19 · HEAD a34a143) — 통과

수단: tests/harness/p_app_path.py --port 9333 --wav u1.wav (전용 Chrome · instrument.js sha256 대조 통과).
세션 8c1a4e8b-35f2-45fc-af97-d12f4a9ca748 · mode=speaking · 07:27:49~07:28:03 UTC.

- AC#1: session_started 1 · final 2 · audio 115 · session_failed 0. 화면이 「답변: i usually go to gym after work.」 와 코치의 되물음을 렌더했음.
- AC#2: utterances seq 1 (user · 그 전사문) · seq 2 (agent). learning_sessions 는 completed.
- AC#3: teardown_session.py 를 6건(실물 3 + 스텁 예비 3)에 돌렸음. 회차 뒤 learning_sessions 27 · utterances 175 · analysis_jobs 111 · pronunciation_attempts 7 로 착수 값과 같음. teardown 이 손대지 않는 error_patterns·review_tasks 각 1행(회차가 새로 만든 것)도 지웠음.
- AC#4: llm_calls 34 → 38 (+4) · purpose='nova' 20 → 24 (+4). 회차별로 R1 2건 · R2 1건 · R3 1건이고 토큰까지 result.md §4 의 표가 가짐.

결과: tests/agent/runs/2026-09-19-b6/result.md §5
<!-- SECTION:NOTES:END -->
