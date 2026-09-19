---
id: TASK-248
title: '결함: 코치가 여는 따옴표 뒤에 공백을 넣어 소리를 인용하면 sound_check 검증 신호가 사라진다'
status: Done
assignee: []
created_date: '2026-09-19 08:49'
updated_date: '2026-09-19 08:51'
labels: []
dependencies: []
ordinal: 312000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
회차 B7(2026-09-19 · tests/agent/runs/2026-09-19-b7/result.md §5-1)이 실물 세션에서 관측했음. 재현 3단계: ① mode=pronunciation 실물 세션을 돌려 코치가 소리를 인용하게 함 ② 그 세션의 pronunciation_attempts.sound_check 를 읽음 ③ 같은 코치 발화를 services/pronunciation.sound_check_verdict 에 직접 넣어 본다. 기대: 코치가 소리를 인용했으면 matched 또는 mismatched 가 남는다(결정 82 가 세운 검증 신호). 실제: sound_check 가 NULL 임. 코치가 「" th"」처럼 «여는 따옴표 뒤에 공백»을 넣어 인용한 자리가 그 회차에 12곳이었고, _QUOTED_TOKEN_RE 가 따옴표 바로 뒤에 글자가 오기를 요구해 토큰을 하나도 뽑지 못했음. 같은 글에서 그 공백만 없애면 matched 가 나옴(회차 증거 evidence/09-sound-check-probe.txt 가 세 입력의 대조를 가짐). ⚠️ 잘못된 배제를 내지는 않음 — 그 함수의 계약이 「어긋났다만 증명한다」이고 None 은 안전한 쪽임. 잃는 것은 어긋남을 잡을 기회 자체임. ⚠️ 간헐임 — 모델의 인용 문체에 달렸고 B6 은 matched, B7 은 NULL 로 실제로 갈렸음. 심각도 MEDIUM(정확성 손실이 아니라 검증 신호 손실). 시나리오: TS-34.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 여는 따옴표 뒤에 공백이 있어도 인용된 소리 토큰을 뽑는다
- [x] #2 그 변화가 잘못된 배제를 늘리지 않는다 — 기존 통과 사례의 판정이 바뀌지 않음
- [x] #3 회차 B7 의 코치 발화 문면으로 재현 검사가 있고 고치기 전 코드에서 실패함
<!-- AC:END -->
