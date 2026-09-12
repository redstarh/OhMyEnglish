---
id: TASK-120
title: >-
  픽스처: 「코칭한 소리가 계획의 소리와 «다른 소리»」인 경우를 만드는 픽스처가 필요하다 — pq05 로는 TASK-116 을 시험할 수
  없다
status: To Do
assignee: []
created_date: '2026-09-12 00:08'
labels: []
dependencies: []
ordinal: 125000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-12 KST 실측(runs/2026-09-12-task111-116-selfcontained-key.md §2). KEY 팔 3회에서 코치가 세 번 다 process 의 어말 s 를 코칭했고 기록은 심은 키 z_as_j 였다. ⛔ 그런데 그것을 「어긋남」으로 읽을 수 없다 — 코치가 그 소리를 «should sound like a z» · «similar to the s in easy» 로 설명했고 심은 낱말(easy)까지 지목했다. 즉 코치 스스로 그것을 /z/ 로 부르므로 기록된 z_as_j 와 어긋나지 않는다. ⇒ 조건부 키 규칙(TASK-116 V3)의 조건절이 발동했는지 자체를 가를 수 없다. 뿌리는 픽스처다: pq05 문장 «It is eaji to understand the new process.» 는 의도한 소리(/z/ in easy)와 눈에 띄는 대안(process 의 s)이 «같은 /s/~/z/ 축» 이고, 게다가 ASR 이 eaji 를 easy 로 복원해 전사문에 오류가 남지 않는다. TASK-115 가 pq04 를 같은 부류(문장이 다른 변수를 들여옴)로 대체한 것과 같다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 의도한 소리와 눈에 띄는 대안이 «다른 소리»인 문장을 고른다 — 두 소리가 같은 축(/s/~/z/ 같은 유성·무성 짝)에 있지 않아야 한다
- [ ] #2 Qwen3-TTS 로 오류판과 정답판 짝을 만들고 scenarios-PQ-qwen-phoneme.md 에 규약대로 등록한다 (⛔ pq05 를 덮지 않는다 — 앞 회차들이 그 ID 로 인용한다)
- [ ] #3 그 픽스처로 전용 모드 회차를 돌려 코치가 코칭한 소리와 target_sound 가 맞는지 본다 — 상한과 해석 규칙을 돌리기 전에 적는다
- [ ] #4 결과로 TASK-116 AC#1 을 닫거나, 지시문으로 못 막는다는 것을 확정해 기록 경로(코드) 안을 TASK-97 축과 합친다
<!-- AC:END -->
