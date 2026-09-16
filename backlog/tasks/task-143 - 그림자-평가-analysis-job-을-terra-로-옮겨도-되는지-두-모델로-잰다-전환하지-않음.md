---
id: TASK-143
title: '그림자 평가: analysis job 을 terra 로 옮겨도 되는지 두 모델로 잰다 (전환하지 않음)'
status: Done
assignee: []
created_date: '2026-09-16 14:28'
updated_date: '2026-09-16 14:32'
labels: []
dependencies: []
ordinal: 197000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
결정 121 이 학습 추천만 terra 로 옮겼다. analysis 도 옮길지 판단하기 위해 제품을 바꾸지 않고 두 모델을 같은 입력으로 재는 회차다. ⛔ 문턱을 «먼저» 못박는다(결정 50 1항의 교훈): ① 스키마 통과율 — terra 가 90% 이상이고 Opus 5 보다 10%p 이상 낮지 않다 ② 오탐 — 오류 없는 문장 셋에서 findings 0건이 Opus 5 와 같다 ③ 검출 — 오류 문장 여덟에서 findings 1건 이상인 수가 Opus 5 보다 1건 이상 적지 않다. 입력은 tests/harness/inject_errors.py 의 E1·E3(오류 여덟)과 E5(정상 셋)이고 프롬프트는 제품의 build_prompt, 판정은 제품의 parse_analysis 가 한다. 실패 비용의 실체는 DB CHECK 가 아니라 조용한 유실이다 — 검증 실패는 report_failure 로 최대 5회 재시도 뒤 그 발화의 분석이 사라진다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 문턱 셋을 돌리기 전에 문서에 적는다 — 결과를 보고 고치지 않는다
- [x] #2 같은 프롬프트로 Opus 5·terra 를 각각 11회 호출하고 원문을 남긴다
- [x] #3 제품의 parse_analysis 로 기계 판정해 통과율·오탐·검출을 표로 낸다
- [x] #4 문턱 대조 결과와 권고를 사용자에게 올린다 — 전환은 이 태스크가 하지 않는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 결과 — 문턱 셋 전부 충족 (2026-09-16 · 호출 22회)

정본: tests/harness/runs/2026-09-16-task143-analysis-shadow/README.md · 원문 raw/ 22건.

Opus 5 와 terra 가 스키마 통과 11/11(둘 다 100%) · 정상 문장 오탐 0건(둘 다) ·
오류 문장 검출 8/8(둘 다). 지연 중앙값은 6,490ms → 2,445ms(2.7배) 이고 토큰도 적음.
카테고리 집합은 8문장 중 7문장 일치, 다른 한 자리는 Opus 5 가 더 맞아 보임(word_order 대 verb_form).

⛔ 전환하지 않았음 — AC#4 대로 사용자 결정 사항임. 권고는 「바로 옮기지 말고 묶은 전사문 + 기존
패턴을 실은 프롬프트로 한 회차 더」임. 이 회차는 한 문장씩·패턴 없이 쟀고 제품의 실제 호출은
여러 발화를 묶고 기존 패턴을 함께 싣기 때문임.
<!-- SECTION:NOTES:END -->
