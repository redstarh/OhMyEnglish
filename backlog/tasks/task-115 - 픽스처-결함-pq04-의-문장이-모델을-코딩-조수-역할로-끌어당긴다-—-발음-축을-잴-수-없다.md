---
id: TASK-115
title: '픽스처 결함: pq04 의 문장이 모델을 코딩 조수 역할로 끌어당긴다 — 발음 축을 잴 수 없다'
status: Done
assignee: []
created_date: '2026-09-11 17:14'
updated_date: '2026-09-11 17:22'
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
- [x] #1 문장을 바꾼 새 픽스처를 만든다 — 도구·화자·lang_code 는 그대로(Qwen3-TTS Sohee en)이고 오류는 /r/→/l/ 하나만 담는다
- [x] #2 그 문장이 모델을 다른 역할로 끌지 않는 것을 «문면으로» 먼저 검토한다 — code·review·debug 같은 도구 지시로 읽히는 낱말을 피한다
- [x] #3 정답판을 함께 만든다(이름 규약: 오류판 ID + a)
- [x] #4 전용 모드 1회로 코칭이 나는지 확인하고 PQ 정본에 등록한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-12 KST 닫음. 정본은 runs/2026-09-12-task115-pq13-replacement.md 임.

만든 것: pq13(My blother will allive ealy tomollow molning. · 4.40s) + pq13a(정답판 · 4.08s). 16kHz·16bit·mono. 도구·화자·lang_code 는 그대로(Qwen3-TTS Sohee en)이고 오류는 /r/→/l/ 하나만 담았음. ⛔ pq04 를 덮지 않았음.

문장 선정: 도구 지시로 읽히는 낱말(code·review·debug·run·file)을 0개로 두고 일상 문장으로 했음. /r/ 이 다섯 자리에 있음.

측정: 전용 모드 2회 전부 코칭. 「I noticed a small pronunciation issue with the 'r' sound in 'arrive.'」이고 혀 위치까지 말했음. pronunciation_attempts 2행 · target_sound 둘 다 r_as_l · signal_source 둘 다 nova_tool.

⇒ **pq04 의 실패 원인이 문장 내용이었음이 확정됨** — 같은 소리·도구·모드에서 문장만 바꿔 0/1 → 2/2 로 갈렸음. 그 규율(문장이 모델을 다른 역할로 끌 낱말을 담지 않는다)을 PQ 정본 §4.6 에 넣었음.

⚠️ 관측 둘을 함께 적었음: outcome 에 pending 이 그대로 저장된 것은 003 CHECK 의 정상 값이고 이 회차 세션이 --timeout 으로 끝나 수렴 경로를 밟지 않았음(그것으로 「수렴 실패」를 판정하지 않음) · ASR 이 오철자를 완전히 복원했는데도 코칭이 났음.

⚠️ 규율 어긋남 하나를 적었음 — 상한 2회를 명령줄에 적고 돌렸고 회차 기록으로 옮긴 것은 1회차 뒤임.
<!-- SECTION:NOTES:END -->
