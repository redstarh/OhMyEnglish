---
id: TASK-29
title: 절차 문서 단정 7건 재설계 — 판별력 미확인분
status: To Do
assignee: []
created_date: '2026-09-06 01:41'
updated_date: '2026-09-06 01:44'
labels:
  - caps-req
dependencies: []
priority: high
ordinal: 29000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
독립 리뷰(codex, 2026-09-06)가 tests/harness/browser_leg.md 의 남은 단정 17건 중 7건에서 거짓 통과 경로를 찾았다: A1-4·A1-5·A1-7·A3-1·A4-1·A4-2·A5-1. 상세와 공통 형태 3개는 docs/design/2026-09-06-review-outcomes.md §4가 소유한다. ⚠️ 문서가 '단정 18건·음성 대조 빈칸 0건'을 품질 근거로 내세운 것이 오판이었다 — 대조가 있다는 지표이고 판별력이 있다는 지표가 아니다. 재설계 전에는 이 7건을 PASS로 보고하지 않는다(문서에 경고를 박았다).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 7건 각각을 재설계한다 — 계수 지점을 효과 지점으로 옮기거나, 내용까지 재거나, 기대값이 0이 될 수 없게 한다
- [ ] #2 각 단정의 대조가 무력화에서 실제로 FAIL을 내는지 확인한다 — 확인하지 않은 것은 '판별력 미확인'으로 적는다
- [ ] #3 A4-1은 corrections가 비지 않은 세션을 primary로 쓴다(0 == 0 통과를 막는다)
- [ ] #4 재설계 후 문서의 경고 블록을 갱신한다 — 남은 미확인 건수를 정확히 적는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2회차(에이전트 재현)에서 절차 결함 2건이 더 나와 이미 고쳤다 — P5 는 glob 이 상대경로라 다른 cwd 에서 소스 0건을 검사하고 통과를 단정했다(1차 정정이 원래보다 더 조용했다) → git 루트 기준 + assert srcs + 검사 개수 출력. P8 은 grep -c 가 0 을 찍고 exit 1 로 끝나 && 나 set -e 아래서 통과가 실패로 읽혔다 → 개수를 변수로 받아 [ -eq 0 ] 으로 판정. 둘 다 잘못된 cwd 에서 재검증했다. 남은 것은 단정 7건의 판별력 재설계다.
<!-- SECTION:NOTES:END -->
