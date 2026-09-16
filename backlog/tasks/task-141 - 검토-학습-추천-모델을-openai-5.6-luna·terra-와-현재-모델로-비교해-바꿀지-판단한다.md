---
id: TASK-141
title: '검토: 학습 추천 모델을 openai-5.6-luna·terra 와 현재 모델로 비교해 바꿀지 판단한다'
status: Done
assignee: []
created_date: '2026-09-16 06:11'
updated_date: '2026-09-16 06:43'
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
- [x] #1 두 모델 이름이 Bedrock 에 실재하는지 list-foundation-models 출력으로 확인한다
- [x] #2 현재 학습 추천 경로의 실제 모델 ID 와 프롬프트 조립 자리를 코드로 확정한다
- [x] #3 같은 입력으로 모델마다 최소 5회 호출해 지연 중앙값·출력 토큰을 잰다
- [x] #4 추천 산출물의 스키마 준수와 품질을 기계 판정 가능한 기준으로 비교한다
- [x] #5 권고와 근거, 바꿀 때 깨질 수 있는 것을 보고서에 적고 사용자 결정을 받는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 측정 결과 (2026-09-16 · 이 세션에서 직접 돌린 30회 호출)

산출물: tests/harness/runs/2026-09-16-model-comparison/ (README.md 가 정본)

두 모델은 us-west-2 에 실재함 — us.openai.gpt-5.6-luna · us.openai.gpt-5.6-terra (둘 다 INFERENCE_PROFILE 전용).
현재 추천 모델은 Sonnet 이 아니라 us.anthropic.claude-opus-5 임 (config.py:69 · .env 덮어쓰기 없음).

지연 중앙 / 통과 (실물 프롬프트 12,930자 · 팔당 예열 1 + 측정 5):
- opus5 InvokeModel (현재 경로) 18,373ms · 5/5
- opus5 Converse 23,621ms · 5/5
- sonnet5 Converse 25,295ms · 5/5
- luna Converse 10,342ms · 4/5
- terra Converse 11,303ms · 5/5

luna 의 실패 1건은 pattern_id 를 한 글자 틀리게 옮긴 것임 (b37b -> bb7b). parse_plan 의 허용 집합 검사가
막았음. 그 가드가 없으면 죽은 UUID 가 focus_pattern_ids 에 저장됨.

교체의 선행 조건 둘: 앱 IAM 사용자에게 후보 추론 프로필 권한이 없음(AccessDenied 실측) ·
openai 계열이 앱의 anthropic_version 본문을 거부함(unknown_parameter). 응답 추출기·usage 키·
stop_reason 도 함께 옮겨야 함. claude_model_id 하나가 다섯 job 을 덮음.

권고: Opus 5 유지. 비용을 줄이려면 openai 계열보다 Sonnet 5 가 변경 범위가 훨씬 작음.
AC#5 는 사용자 결정을 받아야 닫힘.

## 결정 121 — terra 로 교체 (2026-09-16 사용자 결정)

사용자 답변 원문: 「Opus 5는 영어 학습 용으로 너무 과하고, luna 나 terra 중에서 결정하자,
결정하려는 이유는 답변이 간결하고 빠르기 때문이야. terra로 변경해」.

⇒ 권고(Opus 5 유지)를 사용자가 뒤집었음. 이유는 품질 상한이 아니라 «간결·속도» 임.
luna 가 아니라 terra 인 것은 스키마 통과 5/5(luna 4/5)와 짝이 맞음.

내가 직접 확인한 것 셋: 현재 모델이 config.py:69 의 us.anthropic.claude-opus-5 이고 .env 덮어쓰기
0건임 · openai.gpt-5.6-luna·terra·sol 이 us-west-2 에 ACTIVE 임 · luna 의 실패가 원문에서
UUID 한 글자 전사 오류임(prompt 는 …b37b… · 응답 1건이 …bb7b…).

교체 구현은 TASK-142 가 소유함. 이 태스크는 측정과 판단까지이므로 여기서 닫음.
<!-- SECTION:NOTES:END -->
