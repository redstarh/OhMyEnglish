---
id: TASK-141
title: '검토: 학습 추천 모델을 openai-5.6-luna·terra 와 현재 모델로 비교해 바꿀지 판단한다'
status: In Progress
assignee: []
created_date: '2026-09-16 06:11'
updated_date: '2026-09-16 06:13'
labels:
  - caps-req
dependencies: []
priority: high
ordinal: 195000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 지시(2026-09-16): openai-5.6-luna·openai-5.6-terra 를 현재 학습 추천 모델과 품질·속도로 비교해 최적을 고른다. 같은 AWS SSO·Bedrock API 를 쓴다. 별도 검토 Agent 가 측정을 수행하고 산출물은 tests/harness/runs/2026-09-16-model-comparison/ 에 남긴다. 이 태스크는 측정과 판단까지이고 모델 교체 구현은 승인 뒤 별도 태스크다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 두 모델 이름이 Bedrock 에 실재하는지 list-foundation-models 출력으로 확인한다
- [ ] #2 현재 학습 추천 경로의 실제 모델 ID 와 프롬프트 조립 자리를 코드로 확정한다
- [ ] #3 같은 입력으로 모델마다 최소 5회 호출해 지연 중앙값·출력 토큰을 잰다
- [ ] #4 추천 산출물의 스키마 준수와 품질을 기계 판정 가능한 기준으로 비교한다
- [ ] #5 권고와 근거, 바꿀 때 깨질 수 있는 것을 보고서에 적고 사용자 결정을 받는다
<!-- AC:END -->
