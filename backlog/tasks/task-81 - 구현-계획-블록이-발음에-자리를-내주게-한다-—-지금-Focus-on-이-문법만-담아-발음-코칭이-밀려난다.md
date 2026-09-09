---
id: TASK-81
title: '구현: 계획 블록이 발음에 자리를 내주게 한다 — 지금 Focus on 이 문법만 담아 발음 코칭이 밀려난다'
status: To Do
assignee: []
created_date: '2026-09-09 23:01'
labels: []
dependencies: []
ordinal: 84000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-78 AC#1 이 통제 대조로 확정했다. 정본은 tests/harness/runs/2026-09-10-task78-app-path.md 다. ⛔ 결정 50 의 순서 ① 이 이것이고 소유 태스크가 없어서 등록했다(handoff 가 다음 걸음으로 적었으나 가리킬 ID 가 없었다). 실측: 앱이 어댑터에 넘기는 조립 프롬프트(4,545자)를 --prompt-file 로 실어 같은 오디오 3회 → 코칭 0회 · toolUse 0. 기반 프롬프트(2,339자) 팔은 11회 중 코칭 3회 · tool 이 온 회차 3. 변수는 계획·무대 블록 하나다. 브라우저 레그 2회도 같은 방향이고 발화가 거의 글자까지 일치했다. 계획 블록이 Focus on 을 article_missing_before_noun 과 business_expression_verb_noun_collocation 로, 무대를 주말 계획으로, 힌트 시점을 관사·동사 누락으로 고정한다. ⚠️ known_sounds=['an_as_a'] 가 프롬프트에 이미 실리는데 Focus on 에는 들어가지 않는다 — 계획 파이프라인이 발음 패턴을 알면서 초점에 안 넣는다. ⛔ TASK-75 와 다른 층이다: 그쪽은 규칙 9 게이트(기반 프롬프트)이고 이쪽은 계획 블록이다. 둘을 한 태스크로 묶지 않는다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 발음 패턴이 복습 예정일에 걸릴 때 계획의 Focus on 에 그것을 싣는다 — 또는 다른 방법을 고르고 그 근거를 적는다. ⛔ 발명하지 않고 build_plan_prompt·build_system_prompt 의 기존 재료로 한다
- [ ] #2 실물 왕복으로 판정한다 — 단위 테스트로는 이 거동을 잴 수 없다(TASK-75 가 같은 제약을 적었다). 고친 조립 프롬프트를 --prompt-file 로 실어 같은 오디오로 재고 코칭 도착 여부를 회차 기록에 남긴다
- [ ] #3 ⛔ 문법 초점을 없애지 않는다 — 계획은 학습자의 오류 패턴에서 나온 것이고 규칙 9 의 Grammar first 는 B-2 결정의 구현이다. 발음에 자리를 내주는 것과 문법을 밀어내는 것을 가른다
- [ ] #4 고친 뒤 앱 경로(브라우저 레그)에서 코칭이 실제로 나는지 확인한다 — 스파이크만으로 닫지 않는다(결정 50 이 그것을 명시했다)
<!-- AC:END -->
