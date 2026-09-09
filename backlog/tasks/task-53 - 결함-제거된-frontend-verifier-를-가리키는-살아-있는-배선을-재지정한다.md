---
id: TASK-53
title: '결함: 제거된 frontend-verifier 를 가리키는 살아 있는 배선을 재지정한다'
status: Done
assignee: []
created_date: '2026-09-09 08:15'
updated_date: '2026-09-09 08:19'
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
- [x] #1 TASK-30 노트의 위임 대상을 실재하는 주체로 바꾼다
- [x] #2 docs/ops/review-and-decision-protocol.md 의 실행 주체 문장을 고친다
- [x] #3 회차 기록(tests/harness/runs/**)과 완료 태스크(TASK-37)의 노트는 고치지 않는다 — 그 시점 사실이다
- [x] #4 재배선 후 command grep -rn frontend-verifier 로 살아 있는 배선이 0건임을 확인한다(회차 기록·설계서 이력 제외)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-09 완료. 살아 있는 배선 둘을 고쳤다.

① docs/ops/review-and-decision-protocol.md 의 리뷰어 표 — 「frontend-verifier 에이전트」를 「실행체 + 작업 세션이 직접(tests/harness/c*_*.py)」으로 바꾸고, 왜 대체 에이전트로 갈아 끼우지 않았는지를 절로 남겼다. 근거는 정의 부재가 아니라 실측된 유실이다: 위임이 두 번 중 한 번 죽었고(회차 2 · H-AO) 실행체는 판정이 순수 함수라 게이트가 브라우저 없이 판별력을 고정한다(test_c1_gates 15 passed · test_c5_gates 11 passed).
② TASK-30 노트에 재지정을 적었다 — AC#4·#5·#6 은 회차 1 에서 그 에이전트로 이미 닫혔고 그 기록은 그 시점 사실이므로 고치지 않았다.

⛔ 고치지 않은 일곱: tests/harness/runs/2026-09-06-* 셋 · docs/design/2026-09-05-…plan.md · 2026-09-08-ac11-5-live-test-request.md · 2026-09-08-tasks-md-archive.md · TASK-37 노트. 전부 그 시점 사실이다(H-AL 부류).

검사: git ls-files | xargs command grep -n 으로 재확인해 실행 주체로 지목하는 배선이 0건임을 확인했다. 남은 참조는 이력 또는 재지정 설명뿐이다. ⚠️ command grep 을 쓴 이유는 H-AU 다(셰임이 무시 대상을 빠뜨린다).

⚠️ app-test-agent 는 사용자 여정 검증에 쓰고 하네스 단정 판정에는 쓰지 않는다 — 둘은 겹치지 않는다. 서브에이전트로 부르면 샌드박스 보장이 없다는 것도 그 절에 적었다.
<!-- SECTION:NOTES:END -->
