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
2026-09-12 KST **기전을 코드로 확정했음 — Nova 를 쓰지 않았음.**

AC#2(기전): 어긋남은 모델의 실수가 아니라 **지시의 결과** 임. nova.py:235 의 소리 줄이 「and put "{sound}" in target_sound both times」로 **계획이 준 키를 강제** 함. 즉 모델이 다른 소리를 코칭해도 target_sound 에는 계획의 키가 실림. 같은 방향을 미는 자리가 하나 더 있음 — nova.py:442 의 놓친 소리 목록이 「reuse that exact key as target_sound instead of inventing a new one」을 요구함.

⚠️ 그 지시는 «의도된 것» 임 — 반복 오류를 한 키로 묶으려는 것이고(규칙 10 본문이 그 이유를 적음) 그 목적 자체는 유효함. 결함은 「코칭한 소리와 다를 때」에만 생김.

AC#3(고칠 자리): **지시문** 임(기록 경로가 아님). 두 갈래가 있고 둘 다 문면 변경임:
① 전용 세션은 「위에 이름 붙인 그 소리만 코칭하라」로 좁힘 — 못 들으면 그렇다고 말하게 함. 전용 모드의 뜻과 맞음.
② 키 규칙을 조건부로 바꿈 — 「코칭한 소리가 계획의 그 소리일 때만 그 키를 쓰고, 다르면 그 소리의 키를 새로 만들라」.

⛔ **AC#1(재현률)을 Nova 로 세는 것의 값어치가 낮아졌음** — 기전이 「지시가 강제한다」이므로 비율은 「모델이 계획과 다른 소리를 고르는 빈도」와 같음. 그것을 세는 것보다 문면을 고쳐 재는 것이 값이 큼. ⇒ AC#1 은 열어 두되 **고친 판과 함께** 재는 것을 권고함.

⛔ **TASK-111 과 «같은 변경 묶음» 임** — 둘 다 전용 지시문의 문면을 고치는 일이고, 그 지시문은 test_nova.py 의 바이트 대조 게이트로 **실측 문면에 묶여 있음**(4/4 의 근거). 즉 어느 쪽을 고쳐도 회차를 다시 돌려야 하므로 **한 번에 고치고 한 번에 재는 것**이 맞음.

2026-09-12 KST 실측 — 회차 정본: tests/harness/runs/2026-09-12-task111-116-selfcontained-key.md §1 KEY 팔 · §2.

고친 것(V3): 소리 줄의 «put {sound} in target_sound both times» 를 «조건부» 로 바꿨음 — 코칭한 소리가 위에 이름 붙인 그 소리면 그 키를, 다른 소리를 코칭했으면 실제로 코칭한 소리의 짧은 키를 쓰게 함. 갈래 ②를 골랐고 ①(그 소리만 코칭하라)은 «코치가 무엇을 코칭하는지» 를 바꾸는 제품 요구사항 변경이라 넣지 않았음 — 사용자 판단 사안임. ⛔ ②가 ①을 막지 않음.

⛔ AC#1 을 닫지 못했음. 이 회차는 조건부 규칙을 «시험하지 못했음».
KEY 팔(pq05→pq05a · z_as_j · 3회): 코치가 세 번 다 process 의 어말 s 를 코칭했고 기록은 z_as_j x3 였음(signal_source 전부 nova_tool · next_review_at 섰음). 그런데 그것을 「어긋남」으로 읽을 수 없음 — 코치가 그 소리를 «should sound like a z» · «similar to the s in easy» 로 설명했고 심은 낱말(easy)까지 지목했음. 즉 코치 스스로 그것을 /z/ 로 부르므로 기록된 z_as_j 와 어긋나지 않음. ⇒ 조건절(「코칭한 소리가 다르면」)이 발동했는지 자체를 가를 수 없음.
⛔ §0 이 미리 적은 세 행(맞음 · 다시 어긋남 · 계획의 그 소리를 코칭) 어디에도 억지로 끼워 넣지 않았음. 「막았다」도 「막지 못했다」도 적지 않음 — 사후 재해석을 막기 위해 §0 을 먼저 적은 것이므로.

뿌리는 픽스처임: pq05 문장 «It is eaji to understand the new process.» 는 의도한 소리(/z/ in easy)와 눈에 띄는 대안(process 의 s)이 «같은 /s/~/z/ 축» 이고, ASR 이 eaji 를 easy 로 복원해 전사문에 오류가 남지 않음. ⇒ 「다른 소리」 경우를 이 픽스처는 만들지 못함. TASK-115 가 pq04 를 같은 부류로 대체한 것과 같음.
⇒ TASK-120 을 선행으로 걸었음(판별력 있는 픽스처). ⛔ 상한을 지금 늘리지 않았음 — 7/7 을 썼고 §0 이 늘리지 않는다고 적었음.

⛔ V3 를 「작동한다」의 근거로 인용하지 않을 것. test_nova.py 의 바이트 게이트 독스트링에도 그 경고를 적었음 — 그 게이트에 묶인 수치는 REG 4/4 뿐임.

2026-09-12 KST — «결함 후보» 에서 «확정» 으로 올렸고 제목을 그렇게 고쳤음. 근거는 판별 조건을 세운 회차임: tests/harness/runs/2026-09-12-task120-absent-planted-sound.md.

확정한 사실: 코치가 early 의 er 소리를 코칭했는데(참조 낱말 «er in bird» 까지 댐) 기록은 심은 키 f_as_p x3 였음. 그 문장에 /f/ 가 한 자리도 없으므로 「코치가 그것을 같은 소리로 부른다」가 성립할 수 없음 — pq05 관측을 무력화했던 애매함이 없음. TASK-114 §2.5 의 1회 관측과 방향이 같아 «누적 4/4» 임.

⛔ 심각도가 올라간 이유 — 어긋남이 기록에서 멈추지 않음. error_patterns.f_as_p 의 frequency 1→3 이고 next_review_at 이 섰음. signal_source 가 nova_tool 이라 결정 59 의 필터를 통과함. ⇒ «복습 일정이 연습하지 않은 소리로 전진함». 그래서 priority high 로 올렸음.

⛔ V3(조건부 키 규칙)는 «막지 못함이 실측됨». 되돌리지는 않았음 — 되돌리면 바이트 게이트 때문에 회차를 또 돌려야 하고 REG 4/4 는 V3 가 든 판에서 얻은 값임. 대신 nova.py 주석과 test_nova.py 독스트링에 «3/3 으로 막지 못했음» 을 적었음. ⛔ 그 문장을 「작동한다」의 근거로 인용하지 말 것.

선행을 TASK-120 에서 TASK-123 으로 바꿨음(TASK-120 은 Done). TASK-123 이 재는 것은 «덜어내는» 방향임 — 소리 줄에서 키 강제를 아예 빼는 것. ⛔ 「지시문으로는 못 막는다」로 아직 단정하지 않음 — 더하는 방향만 반증됐음.

2026-09-12 KST — 선행을 TASK-123 에서 TASK-128 로 바꿨음(TASK-123 은 Done). 이유: 결정 70 으로 키 강제를 «아예 빼도» 3/3 으로 계획 키가 실렸음(runs/2026-09-12-task123-118-subtract-key-forcing.md ARM-B). ⇒ 지시문의 두 방향이 모두 반증됐고 이 축은 지시문 밖(기록 경로 또는 제품 요구사항)으로 나갔음. TASK-128 이 그것을 갖고 그 AC#3 이 사용자 결정을 요구함.

2026-09-12 KST TASK-128.3 회차에서 오염이 재현됐음 — 닫지 않음. 검증 DB 조회: pronunciation_f_as_p frequency=2 · next_review_at=2026-09-13 (연습하지 않은 소리로 복습 시계가 전진). 어긋남 재현률은 발화 대조로 2/3(B2·B3 이 er 을 코칭하고 f_as_p 를 기록) 이고 나머지 1건(B1)은 발화와 기록이 맞았으나 «둘이 함께» 틀렸음(코치가 없는 /f/ 를 발명) ⇒ 발화·기록 일치를 건강 지표로 쓸 수 없음. 회차 정본: tests/harness/runs/2026-09-12-task128-sound-as-candidate.md §1.
<!-- SECTION:NOTES:END -->
