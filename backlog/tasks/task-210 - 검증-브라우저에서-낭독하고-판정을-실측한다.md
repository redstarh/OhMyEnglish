---
id: TASK-210
title: '검증: 브라우저에서 낭독하고 판정을 실측한다'
status: To Do
assignee: []
created_date: '2026-09-18 05:54'
updated_date: '2026-09-18 06:25'
labels: []
dependencies:
  - TASK-209
ordinal: 271000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
결정 131 · 설계서 전체. ⛔ localhost:3000 으로 열고 ?mode= 쿼리를 쓰지 않는다(H-CA·H-CC). ⛔ 회차 뒤 teardown_session.py 로 세션을 걷는다(TASK-193).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 일부러 한 낱말을 빼고 읽어 그 낱말이 빠짐으로 표시되는 것을 본다
- [ ] #2 두 번째 조회가 전사를 다시 하지 않는 것을 확인한다
- [ ] #3 회차 뒤 큐가 늘지 않은 것을 확인한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## ⛔ 착수 전에 볼 것 — `TASK-206` 이 실물로 확인하지 못한 둘

1. **프레임을 다 보낸 «뒤» 이벤트를 읽는 순서가 흐름 제어에 걸리지 않는가.** 스텁에서는 걸리지 않고
   그 순서라야 보낸 프레임 수가 결정적이어서 그렇게 뒀음. 소켓 계층은 보내기와 읽기를 동시에 하므로
   리듬이 다름. 걸리면 동시 형태로 바꾸고 프레임 수 단정을 다시 설계해야 함.
2. **파일이 갑자기 끝나도 Nova 가 final 전사문을 내는가.** VAD 가 침묵으로 판정을 닫으므로 끝에
   침묵을 덧붙여야 할 수 있음. ⛔ 필요하다는 증거를 이 회차가 만든 뒤에 붙임.
<!-- SECTION:NOTES:END -->
