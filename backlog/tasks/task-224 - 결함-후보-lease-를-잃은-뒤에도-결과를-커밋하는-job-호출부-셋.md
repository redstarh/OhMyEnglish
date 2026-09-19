---
id: TASK-224
title: '결함 후보: lease 를 잃은 뒤에도 결과를 커밋하는 job 호출부 셋'
status: To Do
assignee: []
created_date: '2026-09-19 01:02'
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
- [ ] #1 lease 판정이 services/jobs 한 자리로 올라간다
- [ ] #2 사설 _LeaseLost 두 벌이 사라진다
- [ ] #3 lease 를 잃은 갈래에서 결과가 커밋되지 않는 것을 테스트가 잡는다
<!-- AC:END -->
