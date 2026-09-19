---
id: TASK-225
title: 워커 job 라우팅을 표로 바꾸고 누락 분기를 테스트가 잡게 한다
status: Done
assignee: []
created_date: '2026-09-19 01:02'
updated_date: '2026-09-19 01:52'
labels: []
dependencies: []
ordinal: 286000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
정리 회차(TASK-222) 에서 세 갈래가 지목했고 codex 가 테스트 공백을 확인했음. analysis_worker.py:220-239 가 job 종류를 if/elif 로 갈라내고 나머지 전부를 process_analysis 로 보낸다. 그래서 analyze_utterance 는 라우팅 어디에도 이름으로 적히지 않고, 새 종류를 더하며 분기를 빼먹으면 그 job 이 5회 재시도 뒤 영구히 failed 로 굳는다 — 크래시도 사용자 오류도 없이 기능만 조용히 멈춘다. ⛔ 그 사고가 실제로 있었음: 2026-09-14 에 누군가 SUMMARIZE_WEEK 분기를 지웠는데 21건이 통과했고, 그래서 test_worker.py 에 그 분기만 라우팅 테스트가 생겼다. ⚠️ scenario·summarize 두 분기는 같은 공백이 지금도 열려 있다(그 테스트들은 process_scenario·process_summary 를 직접 불러 run_worker 를 우회함). 깊은 변경: job_type→handler 매핑 하나를 두고 analyze_utterance 를 명시 키로 넣고, 표에 없는 종류는 report_failure 로 보낸다. 그러면 analysis.py:564 의 종류 가드가 죽고 네 자리의 경고 주석이 한 자리로 접힌다. ⚠️ 라우팅을 표로 바꾸는 것 자체가 codex 가 지목한 회귀 위험 1번이므로 테스트를 먼저 세운다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 다섯 종류 전부에 run_worker 경유 라우팅 테스트가 있다
- [x] #2 라우팅이 표 한 자리에 있고 analyze_utterance 가 명시 키다
- [x] #3 표에 없는 종류가 report_failure 로 간다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 고친 것 (2026-09-19)

`analysis_worker` 의 if/elif 라우팅을 표 `_HANDLERS` 하나로 바꿨고 `analyze_utterance` 를 **명시 키**로 넣었음(이전 판은 `else` 로만 도달해 이름이 어디에도 없었음). 표를 읽는 `dispatch` 를 공개로 두었고, 표에 없는 종류는 `report_failure` 로 「no handler for job type: <종류>」를 남김. 분기 넷에 흩어져 있던 경고 주석을 표 한 자리로 접었고 종류별 사실 둘(총평은 모든 세션 · 주간은 조건부)은 남겼음.

## 단정 넷을 더했음

- `test_worker_routes_a_scenario_job_to_process_scenario` · `…_summary_job_to_process_summary` — `run_worker` 경유. 이전에는 이 둘만 라우팅 단정이 없었음(단위 테스트가 `process_*` 를 직접 불러 우회함)
- `test_every_db_job_type_has_a_handler` — **DB CHECK(`analysis_jobs_job_type_check`) 의 값역과 표의 키를 대조함.** 마이그레이션으로 여섯 번째 종류를 더하고 표를 잊으면 이 단정이 먼저 깨짐. 라우팅 단정 넷은 「있는 종류」만 재므로 그 사고를 못 잡음
- `test_a_job_type_without_a_handler_is_reported_to_the_queue` — 값역 밖 종류는 DB CHECK 가 행을 막으므로 `ClaimedJob` 의 종류만 바꿔 `dispatch` 를 직접 부름

## 변이로 판별력을 쟀고, 그 중 한 번은 내 단정이 약한 것을 드러냈음

⑴ 무대·총평 분기를 도달 불가로 바꾸니 새 라우팅 단정 둘이 실패했음(done 수렴 타임아웃).
⑵ 표에서 주간 키를 빼니 `test_every_db_job_type_has_a_handler` 와 주간 라우팅 단정이 실패했음.
⑶ ⛔ **표 미탐색 시 `process_analysis` 로 폴백시키는 변이는 내 단정을 그대로 통과했음** — `process_analysis` 의 종류 가드가 「is not an analysis job: summarize_decade」를 남겨 「사유에 종류 이름이 있다」가 성립했음. 그래서 단정을 **「라우팅이 낸 사유인지」**(`no handler for job type`)로 바꿨고, 같은 변이에서 이제 실패함.

## `analysis.py` 의 종류 가드는 남겼음 (태스크 설명과 다른 판단)

설명은 「그 가드가 죽는다」고 적었으나 남기는 쪽을 골랐음. 근거 둘: 그 함수는 `scripts/smoke_analysis.py` 등 워커 밖 호출자가 직접 부름 · `test_pipeline.py::test_job_of_a_non_analyze_kind_is_reported_as_failed` 가 그 층을 따로 잼. 변이 ⑶ 이 그 가드의 문면을 실제로 관측한 자리이기도 함.

## 게이트 (직접 돌림)

`pytest` **1408**(직전 1404 · 새 단정 4건) · `ruff` 0 · `ruff format` 305 files · `ty` 0.
<!-- SECTION:NOTES:END -->
