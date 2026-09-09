---
id: TASK-57
title: '결함(LOW): partial_failure 안내 문구에 문체 두 개가 섞여 있다'
status: Done
assignee: []
created_date: '2026-09-09 08:33'
updated_date: '2026-09-09 13:46'
labels: []
dependencies: []
ordinal: 60000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-09 사용자 여정 회차에서 관측. app/frontend/app/results/[sessionId]/page.tsx:30 의 PARTIAL_FAILURE_NOTICE 가 일부 발화는 분석하지 못했다 — 재시도되지 않습니다 로 앞은 해라체, 뒤는 합쇼체다. 같은 화면의 다른 문구는 ~어요·~습니다 로 통일돼 있다(:39·:48·:54-56·:173). 관측 경로는 b2f0d169(partial_failure) 를 여는 것이다. 메인이 그 줄을 직접 열어 확인했다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 한 문장 안의 문체를 통일한다 — 예: 분석하지 못한 발화가 있습니다 — 재시도되지 않습니다
- [x] #2 같은 화면의 다른 문구와 어투가 어긋나지 않는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-09 완료. `PARTIAL_FAILURE_NOTICE` 를 「분석하지 못한 발화가 있습니다 — 재시도되지 않습니다」로 고쳤음 — AC1 이 든 예시 그대로임. 앞뒤가 모두 합쇼체이고 같은 화면의 다른 문구(`표시할 교정이 없습니다.` · `결과를 불러오는 중입니다...`)와 어긋나지 않음(AC2).

⛔ 문구를 인용한 곳을 같은 커밋에서 함께 고쳤음 — 이 리포의 지배 실패 모드가 「본문을 고치고 그것을 설명하는 문장을 안 고친다」임:
- tests/harness/c3_results_screen.py 의 `PARTIAL_NOTICE` (게이트 상수 — 낡으면 브라우저 다리가 이 문구를 못 찾음)
- docs/design/2026-08-24-first-vertical-slice-design.md 두 곳(§5.5 서술 · Given/When/Then)
- docs/design/2026-08-25-phase1-implementation-plan.md 의 결과 화면 항목
- docs/design/2026-08-25-first-slice-acceptance-criteria.md U2
- docs/ops/2026-08-26-test-harness.html C3c 행
각 자리에 「TASK-57 이 고쳤다」와 이전 문구를 함께 남겼음 — 조용히 덮으면 다음 세션이 이전 문구를 되살림.

⛔ 회차 기록·증거 사본은 고치지 않았음(tests/harness/runs/2026-09-06-* · tests/agent/runs/* · .harness/evidence/r5-*). 그것은 그 시점의 관측이라 지우거나 고치면 기록이 파괴됨.

증거 — 수정 후 브라우저로 직접 봤음. b2f0d169(partial_failure) 화면의 직계 <p> 판독: ['부분 실패', '분석하지 못한 발화가 있습니다 — 재시도되지 않습니다', '← 학습 시작 화면으로']. 스크린샷 .harness/evidence/c3-partial_failure.png 을 내가 열어서 확인했음. C3 판정 PASS 58건 전건 — 그 안에 「부분 실패 안내는 그 상태에서만 뜬다」가 새 문구로 참인 것이 들어 있음.
<!-- SECTION:NOTES:END -->
