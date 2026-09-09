---
id: TASK-53
title: '결함: 제거된 frontend-verifier 를 가리키는 살아 있는 배선을 재지정한다'
status: To Do
assignee: []
created_date: '2026-09-09 08:15'
labels: []
dependencies: []
ordinal: 56000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-09 테스트 회차에서 관측. 사용자 지시로 .claude/agents/frontend-verifier.md 를 제거했는데(백업 ~/.claude/backups/agents-2026-09-09/) 그 에이전트를 실행 주체로 지목하는 문서가 남아 있다. 진행 중인 TASK-30 이 AC#4·5·6 의 위임 대상으로 그것을 적고 있어 회차를 그대로 돌리면 존재하지 않는 주체를 부른다. 대체 수단은 셋이고 선택은 이 태스크 소유자가 한다 — ① superpowers-chrome:browser-user 에 browser_leg.md 를 실어 위임(CDP 유지) ② app-test-agent + Orca 로 절차 재작성(기전 변경) ③ browsing 스킬로 세션이 직접 관측. tests/harness/browser_leg.md 자체는 그 이름을 담지 않아 절차 본문은 손댈 필요가 없다(직접 grep 확인).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 TASK-30 노트의 위임 대상을 실재하는 주체로 바꾼다
- [ ] #2 docs/ops/review-and-decision-protocol.md 의 실행 주체 문장을 고친다
- [ ] #3 회차 기록(tests/harness/runs/**)과 완료 태스크(TASK-37)의 노트는 고치지 않는다 — 그 시점 사실이다
- [ ] #4 재배선 후 command grep -rn frontend-verifier 로 살아 있는 배선이 0건임을 확인한다(회차 기록·설계서 이력 제외)
<!-- AC:END -->
