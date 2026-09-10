---
id: TASK-83
title: '결함: 분석 워커를 지나가는 하네스 회차는 원상복구가 불가능하다 — 복습 시계에 baseline 이 없다'
status: To Do
assignee: []
created_date: '2026-09-10 00:21'
labels: []
dependencies: []
ordinal: 86000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-82 AC#3·AC#4 회차에서 실측했다. teardown 이 8개 표를 기준선으로 되돌렸고 harness_pattern_baseline drift 도 0 이었으나, 학습자의 복습 시계는 움직인 채 남았다: error_patterns 9→10 · review_tasks 15→17 · 기존 review_task ede30660 이 pending→done(completed_at 이 회차 발화 시각) · 기존 패턴 verb_tense_past_simple_for_past_events 의 next_review_at 이 2026-09-12 23:59:37 로 다시 쓰임. 원인은 스냅샷 스키마의 공백이다 — harness_pattern_baseline 은 id·pattern_key·frequency·last_seen_at 넷만 담고 next_review_at·mastery_score 가 없으며 review_tasks 에는 baseline 표가 아예 없다. 그래서 「drift 0」이 「되돌아왔다」를 뜻하지 않는다. 정본은 tests/harness/runs/2026-09-10-task82-p5-p6.md §6-2 다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 회차 전에 error_patterns 의 next_review_at·mastery_score 와 review_tasks 전체를 파일로 뜨는 절차를 하네스 문서에 못박는다 — 표 스키마를 고치는 것보다 먼저 한다
- [ ] #2 harness_pattern_baseline 에 next_review_at·mastery_score 를 넣을지, review_tasks baseline 표를 만들지 판정한다 — 마이그레이션이므로 별도 승인이 필요하다
- [ ] #3 「drift 0 이 되돌아왔다를 뜻하지 않는다」를 함정으로 등록한다
- [ ] #4 이번에 남은 잔여(패턴 1건·review_tasks 2건·기존 행 2건의 변경)를 어떻게 처리했는지 결론과 근거를 기록한다
<!-- AC:END -->
