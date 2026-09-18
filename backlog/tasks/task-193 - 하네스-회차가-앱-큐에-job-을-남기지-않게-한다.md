---
id: TASK-193
title: 하네스 회차가 앱 큐에 job 을 남기지 않게 한다
status: Done
assignee: []
created_date: '2026-09-18 03:56'
updated_date: '2026-09-18 05:39'
labels: []
dependencies: []
ordinal: 254000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-190 조사에서 드러난 구조 문제. 회차가 돌 때마다 analysis_jobs 에 job 이 쌓이고 teardown 이 걷지 않아 62건이 모였다. H-AC 가 경고한 「하네스가 앱 데이터를 만진다」와 같은 부류이고, 그것을 처리하면 테스트 문장이 error_patterns·복습 과제에 섞인다. ⛔ teardown 이 계산하지 말고 자기가 만든 job 만 표시하거나 걷는 형태여야 한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 회차가 만든 job 을 식별하는 방법을 정한다
- [x] #2 teardown 이 그것만 처리하고 앱 데이터를 계산하지 않는다
- [x] #3 회차를 한 번 돌려 큐가 늘지 않는 것을 확인한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 결과 (2026-09-18)

### AC#1 — 식별은 회차가 기록한 `session_id` 하나로 끝남

`analysis_jobs` 가 `utterances`·`learning_sessions` 양쪽에서 `on delete cascade` 로 매달려 있음
(`db/migrations/001_initial_schema.sql:139-140`). ⇒ **job 을 따로 식별할 필요가 없고** 회차가 이미
기록하는 `walk.startedSessionId` 하나로 대상이 확정됨. 시각창·개수 차이 같은 계산이 필요 없음.

### AC#2 — `tests/harness/teardown_session.py` 를 만들었음

`--from-observation`(정본 · `p_app_path.py --out` 이 쓴 JSON) 또는 `--session-id`(수동 회차)로
세션 하나를 받아 그 세션에 매달린 것만 지우고 개수를 보고함. 앱 데이터를 계산하지 않음.
세션이 없으면 다른 세션을 찾지 않고 `SystemExit` 으로 멈춤. `error_patterns`·`review_tasks` 는
갱신된 기존 행이라 지우지 않고 그 사실을 출력에 남김.
가리키는 자리 둘을 함께 고쳤음 — `p_app_path.py` 머리말이 실행체를 지목하게 했고,
`browser_leg.md` §8 이 **ID 가 있으면 시각창 경로를 쓰지 말라고** 앞에 못박게 했음.

### AC#3 — 반증 가능한 형태로 확인했음 (두 번 재현)

⚠️ **브라우저 회차 대신 기전을 직접 태웠음** — 이유는 `H-CC`·`H-CD` 임(브라우저 레그는 마이크 대체가
필요하고 워커를 켜면 Bedrock 비용이 남). 대신 **큐를 실제로 늘리는 두 경로를 다 지나갔음**:

| 단계 | `analysis_jobs` |
|---|--:|
| 시작 | 111 |
| 세션 생성 + 발화 + 종료 | **114** (종료가 job 3건을 그 자리에서 등록함) |
| `flush_ended_sessions` (워커 스윕과 같은 함수) | **115** (`analyze_utterance` 1건) |
| `teardown_session.py` | **111** (`utterance_jobs_deleted` 1 · `session_jobs_deleted` 3 · 세션 1) |
| 스윕 재실행 | **111** · 새로 등록 **0건** · 세션 잔여 **0행** |

⛔ **판별력**: 스윕이 실제로 1건을 등록한 것(`flushed=1`)이 단정의 전건임 — teardown 이 no-op 이면
115 에서 멈춰 FAIL 이 남. 첫 회차에서 내 단정이 실제로 FAIL 을 냈고(「+1」로 가정했으나 +4 였음)
그 FAIL 이 아래 사실을 드러냈음.

### ⛔ 실측이 `H-CD` 의 서술을 넓혔음 — 큐가 자라는 자리가 워커만이 아님

회차 하나가 남기는 job 은 **넷**이고 그 가운데 **셋은 워커와 무관**함 —
`plan_next_session`·`summarize_session`·`summarize_week` 는 **세션 종료가 그 자리에서** 등록함.
워커 기동이 등록하는 것은 넷째 `analyze_utterance` 하나임. ⇒ 「워커를 안 켜면 안전하다」가 틀렸음.
그 정정을 `docs/ops/pitfalls.md` 의 `H-CD` 행에 남겼음.

### 게이트

`ruff` 0 · `ruff format` **297 files** · `ty` 0 · `pytest` **1361 passed** — 넷 다 exit 0.
프런트는 건드리지 않았으므로 `tsc`·`eslint`·`next build` 는 돌리지 않았음.
<!-- SECTION:NOTES:END -->
