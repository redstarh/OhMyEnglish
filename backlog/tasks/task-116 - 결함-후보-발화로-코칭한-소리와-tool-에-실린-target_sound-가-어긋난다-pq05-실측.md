---
id: TASK-116
title: '결함 후보: 발화로 코칭한 소리와 tool 에 실린 target_sound 가 어긋난다 (pq05 실측)'
status: To Do
assignee: []
created_date: '2026-09-11 17:14'
updated_date: '2026-09-11 17:23'
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
- [x] #2 어긋남의 기전을 가른다 — 모델이 소리 줄의 키를 그대로 복사하는지, 스스로 고른 소리를 키로 바꾸지 못하는지
- [x] #3 고칠 자리를 정한다 — 지시문(규칙 10 이 target_sound 를 계획 키로 강제한다)인지 기록 경로인지
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-12 KST **기전을 코드로 확정했음 — Nova 를 쓰지 않았음.**

AC#2(기전): 어긋남은 모델의 실수가 아니라 **지시의 결과** 임. nova.py:235 의 소리 줄이 「and put "{sound}" in target_sound both times」로 **계획이 준 키를 강제** 함. 즉 모델이 다른 소리를 코칭해도 target_sound 에는 계획의 키가 실림. 같은 방향을 미는 자리가 하나 더 있음 — nova.py:442 의 놓친 소리 목록이 「reuse that exact key as target_sound instead of inventing a new one」을 요구함.

⚠️ 그 지시는 «의도된 것» 임 — 반복 오류를 한 키로 묶으려는 것이고(규칙 10 본문이 그 이유를 적음) 그 목적 자체는 유효함. 결함은 「코칭한 소리와 다를 때」에만 생김.

AC#3(고칠 자리): **지시문** 임(기록 경로가 아님). 두 갈래가 있고 둘 다 문면 변경임:
① 전용 세션은 「위에 이름 붙인 그 소리만 코칭하라」로 좁힘 — 못 들으면 그렇다고 말하게 함. 전용 모드의 뜻과 맞음.
② 키 규칙을 조건부로 바꿈 — 「코칭한 소리가 계획의 그 소리일 때만 그 키를 쓰고, 다르면 그 소리의 키를 새로 만들라」.

⛔ **AC#1(재현률)을 Nova 로 세는 것의 값어치가 낮아졌음** — 기전이 「지시가 강제한다」이므로 비율은 「모델이 계획과 다른 소리를 고르는 빈도」와 같음. 그것을 세는 것보다 문면을 고쳐 재는 것이 값이 큼. ⇒ AC#1 은 열어 두되 **고친 판과 함께** 재는 것을 권고함.

⛔ **TASK-111 과 «같은 변경 묶음» 임** — 둘 다 전용 지시문의 문면을 고치는 일이고, 그 지시문은 test_nova.py 의 바이트 대조 게이트로 **실측 문면에 묶여 있음**(4/4 의 근거). 즉 어느 쪽을 고쳐도 회차를 다시 돌려야 하므로 **한 번에 고치고 한 번에 재는 것**이 맞음.
<!-- SECTION:NOTES:END -->
