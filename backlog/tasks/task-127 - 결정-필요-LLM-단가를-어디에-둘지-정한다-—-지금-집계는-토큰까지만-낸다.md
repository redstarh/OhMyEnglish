---
id: TASK-127
title: '결정 필요: LLM 단가를 어디에 둘지 정한다 — 지금 집계는 토큰까지만 낸다'
status: Done
assignee: []
created_date: '2026-09-12 02:49'
updated_date: '2026-09-12 03:08'
labels: []
dependencies: []
ordinal: 132000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-126 이 llm_calls 집계를 열었으나 금액을 내지 않음(그 태스크 AC#4 가 그것을 금지했음). ⛔ 단가를 행에 저장하지 않는 것은 이미 정해진 것임(결정 66 · 시점·리전에 따라 바뀌므로 읽을 때 곱함). 남은 것은 «읽을 때 쓰는 단가를 어디에 두는가» 임. 후보: ① Settings 환경변수(모델별 단가 4~6개) ② 리포 안 상수 표(모델·리전·시점 주석과 함께) ③ 금액을 아예 내지 않고 토큰만 봄. ⚠️ Nova 는 speech·text 단가가 갈리므로 후보 ①·②는 값이 넷 이상임(015 가 그 분해를 담는 이유). ⚠️ 단가는 공개 문서 값이라 이 리포가 «관측» 할 수 없음 — 사람이 넣어야 하고 그래서 결정 항목임.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 단가의 자리를 정하고 근거를 적는다 — ⛔ 값을 코드가 추측해 넣지 않는다(공개 문서 값이므로 사람이 준다)
- [x] #2 정한 자리에 값이 없을 때의 거동을 정한다 — 금액 열을 비우는지, 표시를 생략하는지. ⛔ 0 으로 표시하지 않는다(0 원이라는 주장이 됨)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-12 세션 ohmyenglish-f4 — 사용자 결정 69 로 닫았음(AskUserQuestion 으로 직접 받음). 결정 정본은 docs/ops/captain-instruction-register.md 「결정 69」임.

AC#1: 단가의 자리를 «두지 않기로» 정했음. 근거는 그 결정 절이 소유함 — 단가는 공개 문서 값이라 이 리포가 관측할 수 없고, 값의 이력 없이 곱하면 지난달 토큰에 이달 단가를 곱하게 되며 그 오류는 조용함(그것이 Settings 환경변수 안을 기각한 근거임).

AC#2: 「값이 없을 때의 거동」 = 금액 열을 만들지 않고 그 사실과 이유를 출력에 적음. ⛔ 0 으로 표시하지 않음. 이미 구현돼 있고 문면을 결정 69 로 갱신했음(scripts/usage_report.py · models/usage.UsageRollup docstring).

⛔ 다시 열 조건을 결정에 못박았음 — 손으로 곱해 보는 일이 반복되면 기각한 ①(리포 상수 표 + effective_from)로 감. 그때도 Settings 환경변수는 고르지 않음.
<!-- SECTION:NOTES:END -->
