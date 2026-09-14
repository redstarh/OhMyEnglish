---
id: TASK-116.3
title: >-
  결함(확정): 결정 82 의 어긋남 검사가 일반 세션에서 발화하지 못한다 — 코치가 소리를 인용하지 않아 어긋난 기록이 복습 시계를
  전진시킨다
status: To Do
assignee: []
created_date: '2026-09-14 15:00'
labels: []
dependencies: []
parent_task_id: TASK-116
ordinal: 169000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
관측 정본은 tests/harness/runs/2026-09-14-task129-plan-review-key/README.md §1 임(TASK-129 회차). 일반 세션 3회에서 target_sound 가 오디오에 없는 키 f_as_p 로 기록됐는데 pronunciation_attempts.sound_check 가 세 행 모두 비어 있었고, error_patterns.frequency 가 4 로 오르고 next_review_at 이 하루 뒤로 서고 review_tasks 가 4행이 됐다. 사유는 계약 그대로다 — sound_check_verdict 는 코치 발화에 소리 인용이 있을 때만 판정하는데 일반 세션의 코치는 낱말(early)만 말했다. 실제 발화로 그 순수 함수를 직접 돌려 세 세션 모두 None 을 확인했다. ⚠️ 전용 모드 회차(TASK-128 ARM-B)에서는 코치가 the er sound 처럼 소리를 인용했기 때문에 그 방어가 발화할 수 있었다 — 즉 결정 82 의 이행이 모드에 따라 유효성이 갈린다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 회차 절차로 재현한다 — 일반 세션에서 sound_check 가 비고 복습 시계가 전진하는 것을 다시 관측한다
- [ ] #2 검사가 발화하지 못하는 조건을 코드로 특정한다 — sound_check_verdict 의 「소리 인용」 요구와 일반 세션 코치 발화의 실측을 대조한다
- [ ] #3 방향을 사용자 판단으로 올린다 — 인용이 없을 때도 배제할지는 제품 판단이다. ⛔ 잘못된 배제가 더 비싸다는 결정 82 의 전제를 뒤집는 것이므로 팀리드가 정하지 않는다
- [ ] #4 정한 방향을 구현하고 반대 방향 두 단정으로 지킨다 — 인용 없는 어긋남과 정상 기록이 서로 다르게 처리되는 것을 각각 단정한다
<!-- AC:END -->
