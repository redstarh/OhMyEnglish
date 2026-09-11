---
id: TASK-116
title: '결함 후보: 발화로 코칭한 소리와 tool 에 실린 target_sound 가 어긋난다 (pq05 실측)'
status: To Do
assignee: []
created_date: '2026-09-11 17:14'
labels: []
dependencies: []
ordinal: 121000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-12 KST 실측(runs/2026-09-12-task114-mild-band-dedicated.md §2.5). pq05 는 의도가 eaji(=easy 의 /z/→/dʒ/)인데 코치는 process 의 어말 s 를 다뤘음(「the "s" sound in "process" … should sound like a "z"」). 그런데 tool 의 target_sound 에는 «계획이 준» z_as_j 가 실렸음. ⇒ 학습자가 들은 코칭과 기록된 소리가 다름. ⚠️ 그 결과 복습 큐가 「연습하지 않은 소리」를 전진시킬 수 있음 — review.py 는 target_sound 로 매칭하므로 어긋난 키가 그대로 이력이 됨. ⛔ 이것은 TASK-97 이 소유한 축(payload 의 질)의 «새 형태» 임 — 그쪽은 target_form 이 무너진 전사인 것이고 이쪽은 target_sound 가 실제 코칭과 다른 것임. 표본 1회이므로 결함 후보로 등록함.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 재현률을 먼저 센다 — 같은 픽스처로 몇 회 중 몇 건이 어긋나는지(1회 관측을 비율로 읽지 않는다)
- [ ] #2 어긋남의 기전을 가른다 — 모델이 소리 줄의 키를 그대로 복사하는지, 스스로 고른 소리를 키로 바꾸지 못하는지
- [ ] #3 고칠 자리를 정한다 — 지시문(규칙 10 이 target_sound 를 계획 키로 강제한다)인지 기록 경로인지
<!-- AC:END -->
