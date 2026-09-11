---
id: TASK-99
title: '결함: error_patterns.frequency 를 두 writer 가 서로 덮는다 — 발음 시도 2건이 1건으로 세진다'
status: In Progress
assignee: []
created_date: '2026-09-10 22:13'
updated_date: '2026-09-11 11:42'
labels: []
dependencies: []
ordinal: 102000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-11 TASK-94(P8) 회차가 실측했다. 정본은 tests/harness/runs/2026-09-11-task94-p8.md §4 다. 같은 컬럼에 writer 가 둘이다 — 발음 경로는 pronunciation_attempts 시도 수를 세고(pronunciation._RECOUNT_PATTERN_FROM_ATTEMPTS_SQL · 앵커 resolved_at) 문법 경로는 error_occurrences 행 수를 센다(analysis._RECOUNT_PATTERN_SQL · 앵커 utterances.created_at). 개수를 가른 조건(시도 2 대 occurrence 1)에서 문법 재계산이 frequency 를 2 에서 1 로 내리고 last_seen_at 을 과거로 옮기는 것을 독립 2회 재현했다. ⚠️ 도달성은 재지 않았다 — 프롬프트에 발음 키를 싣는 경로는 막혀 있고(analysis.load_existing_patterns 가 category <> UNJUDGEABLE_CATEGORY 로 제외 · G-8) 남은 것은 모델이 _PATTERN_KEY_RULES 규칙 2 를 어겨 pronunciation_ 접두 키를 지어내는 것이다. 앱 쪽 검증은 없고 _UPSERT_PATTERN_SQL 이 on conflict (user_id, pattern_key) 로 발음 행을 집으며 category 를 갱신하지 않는다. ⛔ 앱 코드 수정이라 구현 세션 몫이다. ⚠️ 부수: pronunciation.link_pattern 주석이 이 구멍의 근거로 「_EXISTING_PATTERNS_SQL 에 카테고리 필터가 없다」를 지목하는데 그 서술이 낡았다 — 필터가 있다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 도달성을 먼저 판정한다 — 모델이 pronunciation_ 접두 pattern_key 를 지어내는지 실물 분석 회차로 관측한다. 도달하지 않으면 잠재 결함으로 등급을 내리고 그 근거를 적는다
- [ ] #2 고치는 층을 고르고 근거를 적는다 — 후보는 upsert 에서 발음 카테고리 행을 문법 경로가 집지 못하게 하는 것과 두 재계산이 카테고리로 갈리게 하는 것이다. ⛔ 새 추상화를 만들지 않는다
- [ ] #3 last_seen_at 도 함께 다룬다 — frequency 만 고치면 앵커가 서로 다른 두 값이 같은 컬럼을 계속 덮는다
- [ ] #4 pronunciation.link_pattern 의 낡은 주석을 정정한다 — _EXISTING_PATTERNS_SQL 에 카테고리 필터가 이미 있다
<!-- AC:END -->
