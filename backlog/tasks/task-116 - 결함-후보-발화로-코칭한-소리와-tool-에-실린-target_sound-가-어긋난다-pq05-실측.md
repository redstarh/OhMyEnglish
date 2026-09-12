---
id: TASK-116
title: '결함(확정): 발화로 코칭한 소리와 tool 에 실린 target_sound 가 어긋나고 복습 일정이 오염된다'
status: In Progress
assignee: []
created_date: '2026-09-11 17:14'
updated_date: '2026-09-12 14:20'
labels: []
dependencies:
  - TASK-128
priority: high
ordinal: 121000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-12 KST 실측(runs/2026-09-12-task114-mild-band-dedicated.md §2.5). pq05 는 의도가 eaji(=easy 의 /z/→/dʒ/)인데 코치는 process 의 어말 s 를 다뤘음(「the "s" sound in "process" … should sound like a "z"」). 그런데 tool 의 target_sound 에는 «계획이 준» z_as_j 가 실렸음. ⇒ 학습자가 들은 코칭과 기록된 소리가 다름. ⚠️ 그 결과 복습 큐가 「연습하지 않은 소리」를 전진시킬 수 있음 — review.py 는 target_sound 로 매칭하므로 어긋난 키가 그대로 이력이 됨. ⛔ 이것은 TASK-97 이 소유한 축(payload 의 질)의 «새 형태» 임 — 그쪽은 target_form 이 무너진 전사인 것이고 이쪽은 target_sound 가 실제 코칭과 다른 것임. 표본 1회이므로 결함 후보로 등록함.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 재현률을 먼저 센다 — 같은 픽스처로 몇 회 중 몇 건이 어긋나는지(1회 관측을 비율로 읽지 않는다)
- [x] #2 어긋남의 기전을 가른다 — 모델이 소리 줄의 키를 그대로 복사하는지, 스스로 고른 소리를 키로 바꾸지 못하는지
- [x] #3 고칠 자리를 정한다 — 지시문(규칙 10 이 target_sound 를 계획 키로 강제한다)인지 기록 경로인지
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-12 KST TASK-128.3 회차에서 오염이 재현됐음 — 닫지 않음. 검증 DB 조회: pronunciation_f_as_p frequency=2 · next_review_at=2026-09-13 (연습하지 않은 소리로 복습 시계가 전진). 어긋남 재현률은 발화 대조로 2/3(B2·B3 이 er 을 코칭하고 f_as_p 를 기록) 이고 나머지 1건(B1)은 발화와 기록이 맞았으나 «둘이 함께» 틀렸음(코치가 없는 /f/ 를 발명) ⇒ 발화·기록 일치를 건강 지표로 쓸 수 없음. 회차 정본: tests/harness/runs/2026-09-12-task128-sound-as-candidate.md §1.
<!-- SECTION:NOTES:END -->
