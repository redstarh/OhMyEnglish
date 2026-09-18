---
id: TASK-191
title: '실행: analysis_jobs 처리 방침을 적용한다'
status: Done
assignee: []
created_date: '2026-09-18 02:29'
updated_date: '2026-09-18 03:59'
labels: []
dependencies:
  - TASK-190
ordinal: 252000
---

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 정한 방침대로 큐를 처리한다
- [x] #2 처리 뒤 상태 집계를 직접 돌려 적는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 실행 2026-09-18 — pending 62건을 failed 로 표시했음

`begin; update … where status='pending'; commit;` 한 트랜잭션으로 처리했고 `last_error` 에 이유와
되살리는 방법(`status` 를 `pending` 으로 되돌린다)을 적었음.

| 확인 | 값 |
|---|--:|
| 변경 전 pending | **62** |
| `last_error like 'TASK-191:%'` | **62** — 내가 표시한 것만 |
| 기존 하네스 failed 보존 | **2** (`E2E-S…` · `harness: C3c…`) |
| failed 합계 | **64** |

## ⛔ 검증에서 내 예측이 틀렸음 — 「집을 게 없으니 비용 0」이 아니었음

방침의 실효를 코드로만 믿지 않으려고 `WORKER_ENABLED=true` 백엔드를 `:8015` 에 잠깐 띄웠음.
표시한 62건은 **그대로 failed 로 남았음**(워커가 집지 않음 ✅). 그런데 **`done` 이 44 → 47 로 늘었음.**

기전: **워커 기동이 「끝난 세션의 미등록 발화」를 찾아 job 을 새로 등록함.** 등록된 3건이
`analyze_utterance` 이고 세션 `d127dece` 의 픽스처 문장 셋(`I usually go to gym after work.` 등)임.
⇒ 큐가 비어 있어도 워커를 켜면 호출이 난다.

| 관측 | 값 |
|---|---|
| 실측 토큰 (`llm_calls` `purpose=analysis`) | **3건 · 입력 9,227 · 출력 1,024** |
| 1차 단가 환산 | 약 **$0.07** |
| `error_patterns` | **9건 · 최신 2026-09-08** — **변화 없음** (오염 없음) |
| 큐 최종 | failed **64** · done **47** · **pending 0** |

⚠️ **TASK-190 의 비용 추정을 이 실측으로 정정함**: `spike` 평균(입력 4,126 · 출력 1,132)으로 62건을
약 $3 이라 적었으나, 분석 실측은 **1건당 입력 3,076 · 출력 341** 이라 62건이면 약 **$1.5** 임.
⛔ 그 추정을 인용할 때 $3 이 아니라 이 값을 씀.

⛔ **이 사건이 TASK-193 의 근거를 강화함** — 하네스 세션의 발화가 워커 기동만으로 큐에 들어오므로,
teardown 이 걷지 않으면 계속 쌓임. 함정으로도 등재했음(`H-CD`).
<!-- SECTION:NOTES:END -->
