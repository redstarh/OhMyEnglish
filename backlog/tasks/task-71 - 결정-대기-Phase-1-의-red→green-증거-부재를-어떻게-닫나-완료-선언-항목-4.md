---
id: TASK-71
title: '결정 대기: Phase 1 의 red→green 증거 부재를 어떻게 닫나 (완료 선언 항목 4)'
status: Awaiting Decision
assignee: []
created_date: '2026-09-09 14:23'
updated_date: '2026-09-09 14:23'
labels: []
dependencies: []
ordinal: 74000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-09 TASK-47 의 6항목 대조에서 드러났음. 근거는 docs/design/2026-09-09-phase1-completion-audit.md §4 임.

AC 문서 「완료 선언 규칙」 항목 4 가 「각 W/R/G AC 테스트의 red→green 증거 — 구현 전 실패 확인」을 요구함.

찾은 것: Phase 1 구현 창(de61434~5c6c92c)의 커밋 중 본문에 red 증거를 담은 것은 4건이고 전부 fix: 임 — 3d823ae(pool 경쟁) · e002f79(attempts 상한 좀비 job) · fb3754d(쓰기 원자성·문장 시계·seq 경쟁) · 5c6c92c(게이트웨이 실패 경로). fb3754d 는 red 출력을 값으로 적었음(백오프 red: 정확히 120초 · seq 경쟁 red: UniqueViolation).

못 찾은 것: W/R/G AC 테스트를 도입한 feat: 커밋 본문의 red 기록임. 다섯 개를 직접 열어 확인했음 — 1351c0b(W3·W4·W5) · e6f58a7(W1·W6) · e96ab01(W2) · 7d453e4(R1~R3) · bac4144(G1~G4). 그리고 docs/design/2026-08-25-phase1-implementation-plan.md 의 체크박스가 36개 전부 미체크임.

⛔ 사후에 만들 수 없는 증거임 — 2026-08 에 일어난 red 를 지금 다시 관측할 수 없음. 그래서 이 항목은 「더 일하면 닫히는 것」이 아니고 사람의 결정이 필요함.

선택지 둘:
① Phase 1 코드에 대해 이 항목을 면제하고 그 사실과 근거를 기록함. 캡틴 결정 B-7 이 미충족을 셋(W-live·E2E-S·실물 마이크)으로 지목할 때 이 항목을 들지 않았다는 것이 면제를 시사하지만, 명시적으로 면제한 기록은 아님.
② 지금 리포가 널리 쓰는 뮤테이션 KILL 확인을 이 항목의 등가 증거로 인정함. red→green 의 목적이 「테스트가 결함을 실제로 잡는다」를 보이는 것이었으므로 목적이 같음. 이 경로를 고르면 W/R/G 테스트에 뮤테이션 확인을 붙이는 후속 작업이 생김.

⛔ 어느 쪽이든 결정을 기록해야 함 — 기록 없이 넘기면 다음 세션이 같은 대조를 다시 하고 같은 자리에서 막힘.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 선택지 둘 중 하나로 결정을 받고 docs/ops/captain-instruction-register.md 에 등록한다
- [ ] #2 면제를 고르면 AC 문서 「선언 자리」 표의 항목 4 에 면제와 근거를 적는다
- [ ] #3 등가 증거를 고르면 어느 테스트에 뮤테이션 확인을 붙일지 목록을 만들어 태스크로 등록한다
<!-- AC:END -->
