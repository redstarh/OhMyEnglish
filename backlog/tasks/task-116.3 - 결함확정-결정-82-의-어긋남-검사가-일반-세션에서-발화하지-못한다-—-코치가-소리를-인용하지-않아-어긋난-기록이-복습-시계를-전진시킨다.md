---
id: TASK-116.3
title: >-
  결함(확정): 결정 82 의 어긋남 검사가 일반 세션에서 발화하지 못한다 — 코치가 소리를 인용하지 않아 어긋난 기록이 복습 시계를
  전진시킨다
status: In Progress
assignee: []
created_date: '2026-09-14 15:00'
updated_date: '2026-09-14 15:44'
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
- [x] #1 회차 절차로 재현한다 — 일반 세션에서 sound_check 가 비고 복습 시계가 전진하는 것을 다시 관측한다
- [x] #2 검사가 발화하지 못하는 조건을 코드로 특정한다 — sound_check_verdict 의 「소리 인용」 요구와 일반 세션 코치 발화의 실측을 대조한다
- [ ] #3 방향을 사용자 판단으로 올린다 — 인용이 없을 때도 배제할지는 제품 판단이다. ⛔ 잘못된 배제가 더 비싸다는 결정 82 의 전제를 뒤집는 것이므로 팀리드가 정하지 않는다
- [ ] #4 정한 방향을 구현하고 반대 방향 두 단정으로 지킨다 — 인용 없는 어긋남과 정상 기록이 서로 다르게 처리되는 것을 각각 단정한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-15 — 결정 97 이 이 태스크를 「다음 수단」으로 지목했음(plan.py:320 은 고치지 않음). 즉 이 축의 우선순위가 관측 후보에서 실행 대상으로 올랐음.

2026-09-15 브라우저 레그에서도 확인됐음(runs/2026-09-15-task81-app-leg §7). 코치가 early 의 er-lee 를 코칭했는데 기록된 target_sound 는 f_as_p 이고 outcome 이 correct 였음. sound_check 는 빈칸이고 sound_check_verdict 를 직접 돌려 None 을 얻었음 — 코치가 발음 표기를 인용했는데도 판정하지 못했음. ⇒ 한 번도 내지 않은 소리의 복습 일정이 「맞음」으로 전진했고 화면에는 ✓ 좋아요 배지가 붙었음. 재료가 일반 세션 3/3 + 브라우저 1/1 로 늘었음.

회차 2026-09-15 (세션 ohmyenglish-65) — 정본은 tests/harness/runs/2026-09-15-task116-3-verdict-condition/README.md 임. Nova·Claude 를 쓰지 않았음(비용 0).

AC#1 재현됨: 브라우저 레그 ARM-3 의 실측 코치 발화를 제품 writer 로 다시 흘렸더니 sound_check 가 비고 복습 예정일이 전진한 채 남았음. ⇒ 원인이 모델의 변덕이 아니라 코드의 문턱임이 확정됐음.

AC#2 특정됨: 문턱은 pronunciation.py 의 _QUOTED_SOUND_RE 이고 「따옴표로 감싼 1~3자 영문 토큰」을 요구함. 일반 세션 코치의 인용은 early(5자) · er-lee(하이픈) · 문장 전체라 토큰이 0개가 됨. 상한 3 의 근거는 TASK-128.3 회차(소리는 th·er·f · 낱말은 4자 이상)이므로 설계 의도임.

⛔ 판별력을 반대 방향으로 쟀음: 같은 발화에 The er sound 한 조각만 더하면 mismatched 로 표시되고 복습 예정일이 물러남(제품 로그도 남). 즉 기제는 작동하고 입력의 모양이 무력화함.

⛔ AC#3 은 사용자 판단으로 올림 — 후보 셋과 대가를 회차 §4 에 적었음.
<!-- SECTION:NOTES:END -->
