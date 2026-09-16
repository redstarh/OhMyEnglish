---
id: TASK-142
title: '구현: 학습 추천 job 의 모델을 terra 로 바꾼다 (결정 121)'
status: Done
assignee: []
created_date: '2026-09-16 06:43'
updated_date: '2026-09-16 07:03'
labels:
  - caps-req
dependencies: []
priority: high
ordinal: 196000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 결정 121: 학습 추천 모델을 us.openai.gpt-5.6-terra 로 바꾼다. 이유는 답변이 간결하고 빠른 것이다(품질 상한이 아니다). 측정 근거는 TASK-141 과 tests/harness/runs/2026-09-16-model-comparison/ 이다. ⛔ 범위는 학습 추천(plan) job 하나다 — claude_model_id 하나가 job 다섯(plan·analysis·summarize·summarize_week·generate_scenario)을 덮으므로 목적별 설정을 도입해 나머지 넷은 Opus 5 에 남긴다. 회차가 관측한 차단·차이: 앱 IAM 사용자 ohmyenglish-local 에 후보 추론 프로필 권한이 없음(AccessDenied) · openai 계열이 anthropic_version 본문을 unknown_parameter 로 거부 · 응답이 choices 형식이라 extract_text 가 빈 문자열 · extract_usage 키가 달라 llm_calls 토큰이 조용히 빔 · stop_reason 값역이 다름 · 추천 질문 수가 5에서 4로 내려감.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 목적별 모델 설정을 도입해 추천 job 만 terra 로 보내고 나머지 넷은 Opus 5 로 남는 것을 단정으로 고정한다
- [x] #2 본문 규격을 모델 계열로 분기한다 — openai 계열에 anthropic_version 을 싣지 않는다
- [x] #3 응답 추출을 분기한다 — choices 형식에서 텍스트가 나오고 parse_plan 이 통과한다
- [x] #4 usage 추출을 분기해 llm_calls 에 입출력 토큰이 실제로 남는 것을 확인한다
- [x] #5 IAM 권한 부여는 사용자 승인 사항이므로 승인을 받고 그 뒤 실물 호출로 확인한다
- [x] #6 종단 확인: 추천 job 이 terra 로 돌아 session_plans 행이 저장되고 화면 계약이 깨지지 않는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 구현 1~4 완료 (2026-09-16 · TDD)

실측으로 규격을 먼저 잼: tests/harness/runs/2026-09-16-task142-terra-switch/openai_shape.json
(terra 1회 호출) — 텍스트는 choices[0].message.content · 종료 사유는 finish_reason(stop/length) ·
거부는 message.refusal · usage 는 prompt_tokens/completion_tokens.

한 것: config 에 plan_model_id(us.openai.gpt-5.6-terra) 추가 · claude_client 에
is_openai_model·body_for·build_openai_invoke_body·model_for_purpose 추가 ·
extract_text·extract_usage 를 계열로 분기 · BedrockClaudeClient 가 목적으로 모델을 고르고
usage 를 «부른 모델»로 적음.

⛔ Converse 로 옮기지 않았음 — 같은 회차가 Opus 5 를 두 경로로 재서 Converse 가 5.2초 느린 것을
관측했고(18.4→23.6초) 지금 옮기는 것은 job 하나이므로 계열 분기가 더 좁은 변경임.

RED 를 먼저 봤음(ImportError → 함수 부재). 게이트: pytest 1271 passed(+9) · ruff · ruff format
49 files · ty 통과.

AC#5 차단 확인(내가 직접 돌림): 앱 자격증명으로 us.openai.gpt-5.6-terra 는 AccessDeniedException,
us.anthropic.claude-opus-5 는 통과. ⇒ 권한 없이는 추천 job 이 5회 재시도 뒤 failed 로 떨어짐.

## AC#5·#6 완료 — bearer 경로로 종단 확인 (2026-09-16)

AC#5 는 IAM 권한 부여가 아니라 사용자 지시대로 bearer 키 경로로 닫혔음: 「zshrc 내의 Bedrock API
Key 로 권한 획득해서 진행해」. 앱 IAM 사용자는 여전히 이 프로필을 못 부름(AccessDenied 직접 관측).

boto3 로 그 키를 쓸 수 없음을 실측 둘로 확인했음(생성 시점 주입 → 호출 시점 NoCredentialsError ·
토큰 provider 주입 → 환경 SigV4 가 이겨 AccessDenied). 그래서 openai 계열만 HTTPS 직접 호출
(invoke_openai_model)이고 ⛔ 환경변수를 만지지 않음 — 올리면 Nova 가 403 으로 죽음.

AC#6 종단: 검증 전용 DB ohmyenglish_t142 에서 앱 job 경로로 돌렸음 —
job status=done attempts=1 · session_plans(A2 · source=agent · 질문 4 · 초점 2) ·
llm_calls 1건(us.openai.gpt-5.6-terra · purpose=plan · 입력 1085 · 출력 479).
⇒ 본문·텍스트·usage 세 분기가 전부 실제로 걸렸음. 회차 정본은
tests/harness/runs/2026-09-16-task142-terra-switch/README.md.

게이트: pytest 1273 passed · ruff · ruff format 49 files · ty 통과.
<!-- SECTION:NOTES:END -->
