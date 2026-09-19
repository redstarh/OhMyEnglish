---
id: TASK-224
title: '결함 후보: lease 를 잃은 뒤에도 결과를 커밋하는 job 호출부 셋'
status: Done
assignee: []
created_date: '2026-09-19 01:02'
updated_date: '2026-09-19 01:44'
labels: []
dependencies: []
ordinal: 285000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
정리 회차(TASK-222) 고도 지적 2. services/jobs.complete 는 「lease 가 더 이상 우리 것이 아니다」를 bool 로 돌려주는데, 다섯 호출부 중 셋(session_summary.py:133 · scenario_generator.py:274 · weekly_report.py:340)이 그 값을 보지 않아 남의 job 에 쓴 결과를 그대로 커밋한다. 나머지 둘(analysis.py:340 · plan.py:110)은 각자 사설 _LeaseLost 예외를 만들어 결과 쓰기까지 롤백한다. ⚠️ session_summary._store 의 독스트링은 「재시도가 총평을 다시 만들어 덮는 것」을 그 한 트랜잭션이 닫는다고 적었으나, lease 를 잃은 갈래에서는 그 덮어쓰기가 그대로 일어난다 — 트랜잭션은 있고 게이트만 없다. ⚠️ plan.py:112 는 재사용 불가의 이유를 「그쪽이 private 이라서」로 적었는데 그 근거는 스스로 만든 것이다. 깊은 변경: complete 가 bool 대신 jobs.LeaseLost 를 올리게 하면 사설 예외 2벌이 1벌로 줄고 미검사 반환값 3이 0이 된다(총 장치 순감). ⛔ 동작변경=예. complete 의 bool 을 단정하는 테스트 호출부가 있으면 함께 옮긴다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 lease 판정이 services/jobs 한 자리로 올라간다
- [x] #2 사설 _LeaseLost 두 벌이 사라진다
- [x] #3 lease 를 잃은 갈래에서 결과가 커밋되지 않는 것을 테스트가 잡는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 고친 것 (2026-09-19)

`jobs.complete` 가 `bool` 대신 `jobs.LeaseLost` 를 올림. 사설 예외 두 벌(`analysis._LeaseLost` · `plan._LeaseLost`)이 사라졌고(`grep _LeaseLost` **0건**), 판정을 버리던 세 자리(`session_summary._store` · `scenario_generator.process_scenario` · `weekly_report._store`)에 `except LeaseLost` 를 **broad `except` 보다 앞에** 두어 결과가 롤백되고 `report_failure` 가 불리지 않게 했음.

## 결함이 실물이었음 (고치기 전에 셋을 먼저 실패시켰음)

- 총평: 모델 응답이 `learning_sessions.summary` 에 커밋됨
- 주간: `weekly_reports` 행이 커밋됨
- 무대: `AssertionError … assert [<Record … title='A stage whose lease was stolen'>] == []` — 제목에 unique 가 없어 **중복 무대**가 실제로 남음

세 단정 전부 「상태가 `running` 그대로이고 `last_error` 가 비어 있다」를 함께 재어 `report_failure` 미호출도 잼.

## 함께 옮긴 것

기존 `bool` 단정 아홉 자리를 새 계약으로 옮겼음(`test_jobs.py` 여덟 · `test_utterances.py` 하나). 이름 하나를 바꿨음 — `test_complete_and_fail_return_false_for_unknown_job` → `test_complete_raises_and_fail_returns_false_for_unknown_job`. ⚠️ `fail_or_retry` 는 `bool` 로 남겼음(이 태스크의 범위가 `complete` 임).

## 게이트 (직접 돌림)

`pytest` **1404**(직전 1401 · 새 단정 3건) · `ruff` 0 · `ruff format` 305 files · `ty` 0. 프런트는 건드리지 않았음.

## TASK-226 으로 넘긴 관찰 1건

`session_summary._store` 와 `weekly_report._store` 의 `bool` 반환을 **양쪽 호출부가 모두 버림** — 이제 그 값이 알리는 것이 없으므로 `None` 으로 줄일 수 있음. 동작변경 없음이라 정리 묶음의 몫으로 넘겼음.
<!-- SECTION:NOTES:END -->
