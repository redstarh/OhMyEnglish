---
id: TASK-115
title: '픽스처 결함: pq04 의 문장이 모델을 코딩 조수 역할로 끌어당긴다 — 발음 축을 잴 수 없다'
status: To Do
assignee: []
created_date: '2026-09-11 17:14'
labels: []
dependencies: []
ordinal: 120000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-12 KST 실측(runs/2026-09-12-task114-mild-band-dedicated.md §2.5). pq04 의 문장이 「I want to review the code with you.」인데 전용 모드 세션에서 코치가 발음을 다루지 않고 «코딩 조수» 로 답했음 — 「I can't directly view or execute code, I can help you go through it step by step…」 두 번. pronunciation_attempts 0행임. ⇒ 그 문장의 «내용» 이 발음 축에 다른 변수를 들여옴. ⛔ pq04 를 덮지 않음 — PQ 정본과 TASK-90 회차가 그 ID 로 인용하므로 새 ID 로 만들어야 함. ⚠️ /r/→/l/ 축은 이 회차에서 «시험되지 못했음» — 실패 원인이 소리가 아니라 문장이라 그 소리는 아직 미지임.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 문장을 바꾼 새 픽스처를 만든다 — 도구·화자·lang_code 는 그대로(Qwen3-TTS Sohee en)이고 오류는 /r/→/l/ 하나만 담는다
- [ ] #2 그 문장이 모델을 다른 역할로 끌지 않는 것을 «문면으로» 먼저 검토한다 — code·review·debug 같은 도구 지시로 읽히는 낱말을 피한다
- [ ] #3 정답판을 함께 만든다(이름 규약: 오류판 ID + a)
- [ ] #4 전용 모드 1회로 코칭이 나는지 확인하고 PQ 정본에 등록한다
<!-- AC:END -->
