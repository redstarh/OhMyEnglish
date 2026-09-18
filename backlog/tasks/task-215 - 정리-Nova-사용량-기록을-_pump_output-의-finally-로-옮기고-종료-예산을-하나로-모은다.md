---
id: TASK-215
title: '정리: Nova 사용량 기록을 _pump_output 의 finally 로 옮기고 종료 예산을 하나로 모은다'
status: Done
assignee: []
created_date: '2026-09-18 07:50'
updated_date: '2026-09-18 19:06'
labels: []
dependencies: []
ordinal: 276000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
/simplify 고도 각도(2026-09-18). TASK-204 의 고침은 방향이 맞고 깊이가 반 칸 얕다 — 기록을 close()(호출자 수명)에 매어 둔 채 2초 시간 상한으로 스트림 수명과 화해시켰다. _pump_output 의 finally 가 「스트림이 소진됐다」를 아는 유일한 지점이고 이미 put_nowait(None) 로 그것을 쓴다. 거기서 기록하고 close() 쪽은 멱등 백스톱으로 남기면 _FINAL_USAGE_DRAIN_SECONDS 가 정확성에서 빠진다. ⚠️ 지금 한 종료 경로에 예산이 셋이다 — session.DRAIN_TIMEOUT=1.0 · _FINAL_USAGE_DRAIN_SECONDS=2.0 · CLOSE_TIMEOUT_SECONDS=5.0. 검증은 test_nova.py 의 _LateUsageStream 대역으로 되고 실물이 필요 없다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 기록을 _pump_output 의 finally 로 옮기고 close() 는 멱등 백스톱으로 둔다
- [x] #2 _FINAL_USAGE_DRAIN_SECONDS 를 없애거나 그대로 둘 근거를 적는다
- [x] #3 종료 예산 셋 가운데 무엇이 종료 시간을 소유하는지 한 자리에 적는다
<!-- AC:END -->
