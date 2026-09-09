---
id: TASK-73
title: W/R/G AC 테스트에 뮤테이션 KILL 확인을 붙인다 (결정 48 의 등가 증거)
status: To Do
assignee: []
created_date: '2026-09-09 14:39'
labels: []
dependencies: []
ordinal: 76000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-09 결정 48 이 만든 작업임. 근거는 docs/design/2026-09-09-phase1-completion-audit.md §4 와 대장의 결정 48 임.

결정 48 이 red→green 의 등가 증거로 뮤테이션 KILL 확인을 인정했음(면제가 아님 — 증거의 형태만 바꿈). 그 기준으로 실제 상태를 재서 얻은 결론은 「기록된 KILL 확인이 사실상 0건」임.

직접 센 것 (grep: 뮤테이션·mutation·KILL·revert-재현·무력화):
- tests/unit/test_utterances.py (W1·W3·W6) — 0건
- tests/unit/test_jobs.py (W3·W4·W5) — 0건
- tests/unit/test_claude_schema.py (W7) — 0건
- tests/unit/test_analysis.py (W2) — 1건인데 SURVIVED 기록임(제거 뮤테이션이 전체 스위트를 통과한다는 사실을 근거와 함께 적은 주석)
- tests/unit/test_results.py (R1~R3) — 1건인데 무력화 둘이 통과한다는 기록임
- tests/integration/test_pipeline.py (W1 후반·W2·W3) — 3건 전부 SURVIVED 기록임
- tests/integration/test_worker.py (W1) — 1건인데 테스트 이름(does_not_kill_the_loop)임
- tests/integration/test_gateway.py (G1~G4) — 4건 중 셋이 테스트 이름(does_not_kill_the_session 류)이고 하나만 실제 뮤테이션 기록인데 그것은 S2-10(슬라이스 2) 범위임
- tests/integration/test_ws.py (G4) — 1건인데 뮤테이션 추론 주석임

⛔ SURVIVED 기록을 KILL 로 세지 않음 — 그것은 반대 방향의 사실임. 다만 그 주석들은 근거와 함께 남긴 것이라 지우지 않고, 「왜 이 자리는 뮤테이션으로 잴 수 없는가」의 근거로 그대로 씀.

⚠️ 개수를 세는 서술로 AC 를 쓰지 않음 — 대상은 AC 항목(W1~W7 · R1~R3 · G1~G4)이고 파일은 그 항목을 담는 자리일 뿐임.

이 태스크가 닫히면 AC 문서 「선언 자리」 표의 항목 4 를 충족으로 올리고, 그 뒤 TASK-70 만 남으면 Phase 1 완료를 선언할 수 있음.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 W1~W7 각 항목의 테스트에 뮤테이션 KILL 확인을 붙이고 어떤 변이를 어떻게 걸었는지 기록한다
- [ ] #2 R1~R3 각 항목에 같은 것을 한다
- [ ] #3 G1~G4 각 항목에 같은 것을 한다
- [ ] #4 뮤테이션이 SURVIVED 하는 자리는 KILL 로 위장하지 않고 그 사실과 이유를 남긴다 — 기존 SURVIVED 주석을 지우지 않는다
- [ ] #5 붙인 뒤 게이트 넷을 다시 재고 AC 문서 「선언 자리」 표의 항목 4 를 갱신한다
<!-- AC:END -->
