---
id: TASK-85
title: '결함: 복습 due 테스트가 시한폭탄이다 — 고정 T0 에 오프셋을 더해 「미래」를 만든다'
status: Done
assignee: []
created_date: '2026-09-10 04:14'
updated_date: '2026-09-10 04:17'
labels: []
dependencies: []
ordinal: 88000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-10 04:13 UTC 에 게이트에서 터졌음. tests/unit/test_review.py 의 test_due_list_returns_only_patterns_whose_review_is_due 가 실패함.

기전: T0 = 2026-09-01T12:00:00+09:00 이 고정 날짜이고 그 테스트가 article_future 의 next_review_at 을 T0 + 9일로 넣어 「미래」를 표현함. 그 값이 UTC 2026-09-10 03:00 이고 지금이 04:13 이라 과거가 됐음. load_due_reviews 는 clock_timestamp() 로 판정하므로 그 행이 due 목록에 들어오고 단정이 깨짐.

⛔ 내 변경과 무관함을 판별했음 — git stash 로 그 턴의 편집을 빼고 돌려도 같은 실패가 재현됐음.

⚠️ 같은 부류가 그 파일에 더 있을 수 있음. T0 + 오프셋으로 미래를 만드는 자리를 전수로 봐야 함. 고정 T0 자체는 그 파일의 설계임(시각을 테스트가 정한다) — 문제는 「미래」를 고정 기준으로 표현한 것임.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 터진 단정을 고친다 — 「미래」를 고정 T0 오프셋이 아니라 판정 기준(clock_timestamp)에 상대적으로 표현한다
- [x] #2 같은 부류를 전수로 찾아 함께 고친다 — T0 에 오프셋을 더해 미래를 만드는 자리
- [x] #3 무력화로 판별력을 확인한다 — 고친 뒤에도 미래 항목이 목록에서 빠지는 것을 잰다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-10 고침 완료.

AC#1 — article_future 의 next_review_at 을 T0 + 9일에서 datetime.now(T0.tzinfo) + 9일로 바꿨다. 판정 기준이 clock_timestamp() 라 흐르는 시각이므로 기대값도 흐르는 시각에 상대적이어야 한다.

AC#2 전수 확인 — 시한폭탄이 되는 자리는 clock_timestamp() 로 판정하는 함수에 값을 넣는 곳뿐이다. load_due_reviews 사용처 셋을 다 봤고 나머지 둘은 안전하다: test_review.py 의 다른 자리는 clock_timestamp() + interval '150 milliseconds' 를 쓰고 test_pronunciation_review.py 는 datetime.now(...) - timedelta(days=10) 을 쓴다. 둘 다 현재 시각 기준이다.
⚠️ T0 + 오프셋 자체는 그 파일에 많지만 대부분 순수 함수의 계산 결과를 비교하는 자리라 흐르는 시각과 무관하다. 고정 T0 는 그 파일의 설계이고 문제는 「미래」를 고정 기준으로 표현한 것이었다.
⚠️ 비대칭을 주석에 적었다 — 「과거」는 고정 T0 로 안전하다(이미 지난 시각이라 더 지날 뿐이다). 그래서 article_older 는 그대로 뒀다.

AC#3 무력화 — load_due_reviews 의 next_review_at <= clock_timestamp() 를 is not null 로 바꾸니 그 테스트가 FAIL 했다. 즉 고친 뒤에도 「미래 항목이 목록에서 빠진다」는 판별력이 살아 있다. 같은 회차에서 pronunciation_pattern_enters_the_due 는 통과했다 — 그 테스트는 과거 항목만 넣어 미래 제외를 재지 않는다.

⛔ 내 변경과 무관함을 판별했다 — git stash 로 그 턴의 편집(TASK-75)을 빼고 돌려도 같은 실패가 재현됐다. 그 판별을 먼저 하지 않으면 남의 결함을 내 변경 탓으로 돌리거나 그 반대가 된다.

게이트: pytest 899 passed · ruff check exit 0 · format 34 files already formatted · ty check 통과 · 게이트 밖 ruff 0건 · format 101 files.
<!-- SECTION:NOTES:END -->
