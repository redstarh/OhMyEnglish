---
id: TASK-84
title: '판정 대기: 발음 문제가 business_expression 패턴으로 기록되는 것이 결함인가'
status: Done
assignee: []
created_date: '2026-09-10 00:21'
updated_date: '2026-09-10 13:49'
labels: []
dependencies: []
ordinal: 87000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-82 AC#4(P6) 회차의 관측이다. p2m(발음만 나쁘고 문법은 완전히 옳은 픽스처)이 앱 경로에서 i finished the la porte en chaille de lesseps with my team. 으로 전사됐고, 분석기가 그 전사문에서 business_expression_unclear_work_noun 패턴을 만들고 복습 과제까지 예약했다. ⛔ 분석기의 판정 자체는 발명이 아니다 — reason 이 「지금 부분은 영어 단어로 전달되지 않았습니다」로 입력 상태를 명시하고, analysis.py:159 가 빈 findings 를 명시로 허용하므로 형식 압력도 아니다. 남는 사실은 종단 결과다: 학습자의 발음 문제가 pronunciation_intonation 이 아니라 business_expression 카테고리로 기록되고 그 카테고리의 복습 주기를 탄다. 정본은 tests/harness/runs/2026-09-10-task82-p5-p6.md §4-2 다. ⚠️ TASK-74(보조 신호에서 복습 시계를 돌릴지)와 인접하지만 다르다 — 그쪽은 korean_transcript 신호에 재료가 없다는 문제이고 이쪽은 재료가 «다른 카테고리로» 들어간다는 문제다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 사용자 판정을 받는다 — 이 기록이 의도된 거동인지, 발음 기원 오류를 구별해야 하는지
- [x] #2 판정과 근거를 docs/design 에 남기고 원장에 상태를 두 벌 쓰지 않는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
판정 2026-09-10 (사용자): 결함임 — 구별이 필요함. 정본은 docs/design/2026-09-10-pronunciation-origin-error-attribution.md §2 다. 구현 소유자는 TASK-88 이고 이 태스크에 의존을 걸었음. ⚠️ 이 태스크는 판정만 소유하므로 판정과 기록이 끝나 닫음 — 구현 상태를 여기에 두 벌 쓰지 않음.
<!-- SECTION:NOTES:END -->
