---
id: TASK-91
title: '실행: P계층 p2 쌍 이월분 — P2·P3·P7 (4차수가 p1 쌍으로만 닫은 것)'
status: To Do
assignee: []
created_date: '2026-09-10 13:59'
labels: []
dependencies: []
ordinal: 94000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-37(5차수)이 P8 과 p2 쌍을 이월분으로 남겼고 TASK-82 가 P1·P4·P5·P6 만 닫았다. 남은 것은 P2·P3·P7 의 p2 쌍이다. ⚠️ N계층은 이월분이 아니다 — 5차수가 N6·N7·N8·N11·N12·N13 을 전부 PASS 로 닫았고(runs/2026-09-09-run-5.md:16) N9·N10 은 태스크 설명이 일부러 뺀 것이다. handoff 이전 판이 「N계층도 열려 있다」고 적었던 것은 낡은 서술이었다.

⛔ P2 는 이번 회차가 이미 재료를 가졌다 — TASK-82 P6 세션의 p2m 전사문이 i finished the la porte en chaille de lesseps with my team. 이고 p2a 전사문은 i finished the report and shared the results with my team. 이다. 즉 문자 단위로 동일하지 않다. 4차수가 p1 쌍에서 얻은 「전사문이 동일하다 → 앱은 발음 오류를 인지하지 못한다」가 p2 쌍에서는 성립하지 않는다. 정본은 runs/2026-09-10-task82-p5-p6.md §4-1 이다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 P2: p2a 와 p2m 의 전사문을 문자 단위로 대조해 판정한다. 이번 회차 재료로 충분한지 먼저 판단하고 부족하면 세션을 새로 만든다. ⛔ 4차수의 p1 쌍 결론을 뒤집는 것이 아니라 쌍에 따라 갈린다는 것을 적는다
- [ ] #2 P3: p2m 에 대해 agent 가 발음을 지목하는지 관측한다. ⛔ 발음 코칭 기저율이 앱 경로에서 0/n 이고 원인이 미확정이므로 한 회차의 0건을 신호로 쓰지 않는다
- [ ] #3 P7: p2a 세션과 p2m 세션의 결과 화면을 대조한다. ⛔ 스크린샷 2장이 바이트 동일이면 판정 불가다 — 4차수가 그 함정에 걸렸다(세션 식별자가 보이는 캡처를 받는다)
- [ ] #4 회차 전에 browser_leg.md §8-0 의 새 절차대로 error_patterns 의 next_review_at·mastery_score 와 review_tasks 를 파일로 뜬다 — 분석 워커를 지나가면 복습 시계가 움직인다(H-AY)
<!-- AC:END -->
