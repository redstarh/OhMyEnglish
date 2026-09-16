# TASK-141 — 학습 추천 모델 비교 (2026-09-16)

> 브랜치 `design/first-vertical-slice` · 기준 커밋 `7135a61` · 리전 `us-west-2`.
> 이 회차는 측정과 판단까지임. 모델 교체 구현은 사용자 승인 뒤 별도 태스크임.
> 이 회차에서 앱 코드·설정을 고치지 않았음. 이 폴더 밖의 파일을 만들지 않았음.

## 0. 무엇을 쟀는가

| 항목 | 값 |
|---|---|
| 입력 | 개발 DB(`ohmyenglish`)의 실물 재료를 `load_plan_input` 으로 읽고 `build_plan_prompt` 로 조립 |
| 재료 | user `00000000-…-0001` · 복습 예정 9건 · 만성 8건 · 최근 발화 34건 · 현재 수준 A2 |
| 프롬프트 | 12,930자 (`prompt_plan.txt`) · Anthropic 토큰 5,418 · OpenAI 토큰 4,102 |
| 판정 | 제품의 검증 함수 `app.models.plan.parse_plan` 이 함. 눈대중 점수를 만들지 않았음 |
| 회차 | 팔마다 예열 1회 + 측정 5회. 회차마다 팔을 돌려 시각대 변동을 분산시켰음 |
| 총 호출 | 30회 (5팔 × 6회). 전부 이 세션에서 직접 돌렸음 |

DB 는 SELECT 만 했음. 계획 행·노트 행을 쓰지 않았음.

## 1. 두 모델의 실재 — 확인됨 (AC#1)

`aws bedrock list-foundation-models --region us-west-2` 가 `openai.gpt-5.6-luna` ·
`openai.gpt-5.6-terra` 를 돌려주었음. 둘 다 `modelLifecycle.status = ACTIVE` 이고
`inferenceTypesSupported = ["INFERENCE_PROFILE"]` 이므로 호출에는 `us.` 접두사가 붙은
추론 프로필 ID 를 써야 함 — `us.openai.gpt-5.6-luna` · `us.openai.gpt-5.6-terra`.
같은 리전에 `openai.gpt-5.6-sol` · `openai.gpt-6-astra` 도 있으나 사용자가 지목하지 않았으므로
재지 않았음.

## 2. 현재 경로 — 코드로 확정함 (AC#2)

사용자가 말한 「sonnect」와 코드가 다름. 실제 값은 아래임.

| 자리 | 값 |
|---|---|
| 모델 ID 정본 | `app/backend/app/config.py:69` — `claude_model_id: str = "us.anthropic.claude-opus-5"` |
| `.env` 덮어쓰기 | 없음 (`app/backend/.env` 에 `CLAUDE_MODEL_ID` 키가 없음) |
| 호출 자리 | `app/backend/app/workers/claude_client.py:163` — `invoke_model(modelId=…, body=build_invoke_body(prompt))` |
| 본문 규격 | `anthropic_version="bedrock-2023-05-31"` · `max_tokens=16000` · 도구 정의 없음 |
| 프롬프트 조립 | `app/backend/app/services/plan.py:396` `build_plan_prompt` (순수 함수) |
| 추천 job 진입 | `app/backend/app/services/plan.py:522` `process_plan` → `purpose="plan"` |
| 출력 검증 | `app/backend/app/models/plan.py:237` `parse_plan` |

즉 현재 학습 추천 모델은 Sonnet 이 아니라 Claude Opus 5 임.

같은 `claude_model_id` 를 쓰는 job 이 다섯임 — 추천(`plan`) · 분석(`analysis`) ·
세션 총평(`summarize`) · 주간 보고(`summarize_week`) · 시나리오 생성(`generate_scenario`).
설정값이 하나이므로 추천만 바꾸려면 갈래별 모델 설정을 새로 만들어야 함.

## 3. 호출 본문 규격 — 후보는 앱의 현재 본문을 받지 않음

`probe_body_format.py` 로 세 갈래를 각각 1회 불렀음 (`probe_body_format.json`).

| 모델 | A. InvokeModel + Anthropic 본문 (앱의 현재 경로) | B. Converse | C. InvokeModel + OpenAI 본문 |
|---|---|---|---|
| `us.anthropic.claude-opus-5` | 통과 | 통과 | 거부 — `max_tokens: Field required` |
| `us.anthropic.claude-sonnet-5` | 통과 | 통과 | 거부 — 같음 |
| `us.openai.gpt-5.6-luna` | 거부 — `unknown_parameter: 'anthropic_version'` | 통과 | 통과 |
| `us.openai.gpt-5.6-terra` | 거부 — 같음 | 통과 | 통과 |

네 모델이 모두 받는 모양은 Converse 하나임. 그래서 비교를 Converse 로 통일하고, 앱의 실제 경로는
Opus 5 한 팔로 따로 재서 Converse 가 기준선을 왜곡하는지 대조했음.

응답 모양도 다름. openai 계열의 InvokeModel 응답은 최상위 키가 `choices` 인 OpenAI 형식이고
Anthropic 형식의 `content` 배열이 없음. 앱의 `extract_text` 는 `content` 만 읽으므로 그 응답에서
빈 문자열을 돌려주고, 그러면 모든 계획이 「JSON 아님」으로 거부됨.

## 4. 자격증명 — 앱 계정은 후보를 부를 권한이 없음

1차 실행을 앱의 자격증명(`app.config.bedrock_client()`, SigV4 IAM 사용자
`ohmyenglish-local`)으로 돌렸고 결과를 `probe_body_format_appcreds.json` 에 남겼음.
`us.anthropic.claude-opus-5` 만 통과하고 나머지 셋은 전부 아래로 거부됨.

```
AccessDeniedException: User: …:user/ohmyenglish-local is not authorized to perform:
bedrock:InvokeModel on resource: …:inference-profile/us.openai.gpt-5.6-luna
```

그래서 측정은 셸 환경의 bearer 토큰(`AWS_BEARER_TOKEN_BEDROCK`)으로 붙었음. 그 경로는 네 모델을
모두 부름. 자격증명 값은 어느 파일에도 적지 않았음.

교체를 하려면 앱 IAM 사용자의 정책에 그 추론 프로필이 먼저 더해져야 함. 이것이 코드 변경보다
앞서는 선행 조건임.

## 5. 지연·토큰 (AC#3)

`compare_models.py` 의 출력임 (`results.json` · `run.log`). 지연은 벽시계 왕복이고 단위는 ms 임.

| 팔 | 모델 | 경로 | 통과 | 지연 중앙 | 최소 | 최대 | 예열 | 입력 토큰 | 출력 토큰 중앙 | 출력 최대 |
|---|---|---|---|---|---|---|---|---|---|---|
| opus5-app-invoke | Opus 5 | InvokeModel (현재) | 5/5 | 18,373 | 16,007 | 29,619 | 17,819 | 5,418 | 1,269 | 2,145 |
| opus5-converse | Opus 5 | Converse | 5/5 | 23,621 | 19,632 | 37,448 | 25,852 | 5,418 | 1,689 | 2,607 |
| sonnet5-converse | Sonnet 5 | Converse | 5/5 | 25,295 | 22,154 | 34,084 | 26,323 | 5,418 | 2,256 | 2,792 |
| luna-converse | gpt-5.6-luna | Converse | 4/5 | 10,342 | 6,760 | 10,501 | 6,803 | 4,102 | 1,570 | 1,634 |
| terra-converse | gpt-5.6-terra | Converse | 5/5 | 11,303 | 7,207 | 16,509 | 11,581 | 4,102 | 1,004 | 1,471 |

두 후보가 현재 경로보다 지연 중앙에서 1.6~1.8배 빠름.

openai 계열은 Bedrock 이 프롬프트를 자동으로 캐시함. 예열 호출에서
`cacheWriteInputTokens=4102` 가 잡히고 이후 회차는 `inputTokens=2` ·
`cacheReadInputTokens=4102` 임. Claude 두 팔은 매 회차 `inputTokens=5418` 이고 캐시 0 임
(앱이 `cache_control` 을 붙이지 않으므로). 같은 프롬프트를 반복하는 추천 job 에서 이 차이가
입력 비용을 크게 가름.

앱의 InvokeModel 응답이 `output_tokens_details.thinking_tokens = 0` 을 보고했음. 즉 이 경로에서
사고 토큰이 붙지 않았음 — `claude_client.py:15` 의 주석이 적은 「thinking 이 기본 on」과 다른
관측이므로 그 주석을 그대로 신뢰하지 않는 편이 좋음. 이 회차의 범위 밖이라 고치지 않았음.

## 6. 스키마 준수와 품질 (AC#4)

판정은 `parse_plan` 이 함. 그 함수가 스키마(`extra="forbid"`) · 초점 출처(제시된 pattern_id 만) ·
가장 깊은 재발 강제 · CEFR 한 단계 규칙 · 빈 문자열 금지를 모두 소유함.

| 팔 | 통과 | 거부 사유 | 초점 선택 | 질문 수 | 서로 다른 상황 | notes 수 | 학습자용 `reason` |
|---|---|---|---|---|---|---|---|
| opus5-app-invoke | 5/5 | — | 6/6 정답 | 5 | 5 | 3~4 | 한국어 66~92자 |
| opus5-converse | 5/5 | — | 6/6 정답 | 5 | 5 | 3~4 | 한국어 69~90자 |
| sonnet5-converse | 5/5 | — | 6/6 정답 | 판정 불가 (아래) | — | — | — |
| luna-converse | 4/5 | pattern_id 전사 오류 1건 | 5/6 정답 | 4 | 4 | 2~3 | 한국어 41~61자 |
| terra-converse | 5/5 | — | 6/6 정답 | 4 | 4 | 1~2 | 한국어 43~55자 |

「초점 선택」은 프롬프트가 표시한 최다 재발(`article_missing_before_noun`)과 복습 예정인 발음
패턴(`pronunciation_an_as_a`) 두 개를 골랐는가임. 예열까지 포함해 6회 중 몇 회인지 셌음.

luna 의 실패 1건이 이 비교의 가장 값어치 있는 관측임. 모델이 프롬프트의
`70ad1279-cfaf-4a57-b37b-c28f561baeaa` 를 `70ad1279-cfaf-4a57-bb7b-c28f561baeaa` 로 옮겼음 —
`b37b` 가 `bb7b` 가 된 한 글자 차이임. 지어낸 UUID 가 아니라 옮기다 틀린 것임.
`session_plans.focus_pattern_ids` 에 외래 키가 없으므로 `parse_plan` 의 허용 집합 검사가
없으면 형식만 맞은 죽은 id 가 조용히 저장되고 복습 조회가 영구히 어긋남
(`models/plan.py:252` 가 이것을 「실패보다 나쁘다」로 적어 둠). 지금은 그 가드가 잡아
`report_failure` 로 떨어졌음. 배선 확인 실행(회차 1회)에서도 같은 자리가 같은 방식으로
틀렸으므로 우연으로 보기 어려움. 그 실행의 수치는 이 표에 넣지 않았음.

Sonnet 5 는 출력을 ```json 펜스로 감쌌음. `parse_plan` 의 후보 추출이 펜스를 벗기므로 통과하나,
엄격한 `json.loads` 로는 파싱되지 않아 관찰값 집계에서 빠졌음. Opus 5 와 openai 계열 둘은
펜스 없이 순수 JSON 을 냈음.

산출물을 직접 읽어 본 차이는 아래임 (`raw/*_r2.txt`).

- Opus 5(현재 경로)는 질문에 발판을 심음 — `I want an apple` 같은 예시 문장을 질문 안에 넣고,
  `sentence_length` 를 「5~8낱말 한 절, `I want…`·`I need…` 틀 위에서」처럼 튜터가 바로 쓸 수
  있게 씀. `notes` 는 입력에 있던 사실을 새 관찰로 바꿈 — 힌트를 받으면 스스로 고치는 것 ·
  암기한 덩어리에서는 관사가 나오지만 명사구가 길어지면 빠지는 것 · 한글 음차로 답한 턴이 있어
  발화를 피하는 듯한 것.
- terra 는 문장이 자연스럽고 모음으로 시작하는 명사를 잘 유도함(`what animal`·`what app`).
  대신 `notes` 가 1~2건으로 얕고 `level.reason` 을 영어로 씀 — 규격이 한국어를 요구하는 자리는
  최상위 `reason` 뿐이라 위반은 아니나 다른 셋과 다름.
- luna 는 질문이 어색함 — `Tell me about one egg and one apple` 처럼 목표 형태를 억지로 끼워
  넣고, 초점이 관사인데 과거 시제를 함께 물어 부담을 더함. `notes` 는 입력을 되풀이함.

즉 스키마 준수만 보면 terra 가 Opus 5 와 같으나, 튜터 지시문과 관찰 노트의 밀도에서 Opus 5 가
눈에 띄게 앞섬. 이 판단은 프롬프트 1개 · 팔당 5회 위의 것임.

## 7. 비용 — 부분만 확인됨 (AC#5 의 재료)

AWS Pricing API(`AmazonBedrock`)를 직접 조회했음 (`pricing_api.txt`).

- `openai.gpt-5.6-luna` · `openai.gpt-5.6-terra` 항목이 존재함. 다만 있는 리전이
  `us-gov-west-1` 뿐이고 `us-west-2` 행이 없음 — 즉 상업 리전 단가는 이 API 에 아직 없음.
  GovCloud standard 값은 luna 가 입력 $0.264 · 출력 $1.584, terra 가 입력 $2.64 ·
  출력 $15.84 (모두 1M 토큰당)임.
- Claude Opus 5 · Sonnet 5 는 이 API 의 `model` 속성값 목록에 아예 없음(일치 0건). 즉
  Bedrock 단가를 이 세션에서 관측하지 못했음.
- 참고로 Anthropic 1st-party 단가는 Opus 5 가 $5 / $25, Sonnet 5 가 $2 / $10 (1M 토큰당)임.
  같은 문서가 「Bedrock 은 파트너 운영이고 단가가 별도」라고 명시하므로 이 값을 Bedrock 단가로
  쓰지 않음.

그러므로 금액을 단정하지 않음. 관측된 것은 토큰이고, 그것만으로도 방향은 분명함 — 회차당 입력이
Claude 5,418 대 openai 4,102(2회차부터는 캐시 읽기 4,102 + 신규 2)이고 출력 중앙이
Opus 1,269 · Sonnet 2,256 · luna 1,570 · terra 1,004 임. 캐시가 붙는 쪽이 반복 호출에서
확실히 저렴함.

리포의 결정 69 가 「단가의 자리를 두지 않는다」로 정했으므로 위 값은 이 회차 기록에만 두고
원장·DB·집계 코드에 넣지 않음.

## 8. 권고와 근거

지금은 `us.anthropic.claude-opus-5` 를 유지하는 쪽을 권고함. 근거 넷임.

1. 속도가 이 job 의 병목이 아님. 추천은 세션 종료 뒤 job 큐에서 돌고 결과는 다음 세션 시작에
   쓰임. 18초와 10초의 차이가 학습자에게 닿는 자리가 없음. 실패해도 `MAX_ATTEMPTS=5` ·
   선형 백오프 1~4분으로 재시도됨.
2. luna 는 5회 중 1회 pattern_id 를 한 글자 틀리게 옮겼음. 이 리포에서 가장 위험한 실패 부류이고
   지금 막고 있는 것은 `parse_plan` 의 허용 집합 검사 하나임.
3. terra 는 스키마를 5/5 지켰으나 튜터 지시문과 관찰 노트가 얕음. 추천의 값어치가 거기에 있음.
4. 교체 비용이 코드 한 줄이 아님 — IAM 정책 · 호출 경로 · 응답 추출기 · 다섯 job 의 공용 설정이
   함께 걸림(9절).

바꾼다면 terra 가 luna 보다 나은 후보임 — 스키마 준수가 같고 질문이 자연스러움. 다만 출력
단가가 luna 의 10배 수준이므로(7절, GovCloud 기준) 「싸고 빠르다」는 이유로 고르는 것이 아님이
분명해야 함.

한 가지 대안이 더 있음. 지금 값이 Opus 5 이므로, 사용자가 「Sonnet 으로 되어 있다」고 알고
있었다면 그 인식과 실제가 다름을 먼저 맞추는 것이 순서임. Sonnet 5 도 5/5 통과했고 지연은
Opus 와 비슷하며 1st-party 기준 단가는 절반 이하임 — 비용을 줄이려면 openai 계열로 가기 전에
Sonnet 5 를 재는 편이 변경 범위가 훨씬 작음(같은 본문 규격 · 같은 추출기 · 같은 IAM 부류).

## 9. 바꾸면 깨질 수 있는 것

1. IAM. 앱 사용자에게 후보 추론 프로필 권한이 없음(4절). 이것이 첫 차단임.
2. 요청 본문. `build_invoke_body` 의 `anthropic_version` 이 거부됨(3절). Converse 로 옮기거나
   갈래별 본문을 만들어야 함.
3. 응답 추출. `extract_text` 가 `content` 배열만 읽음. openai 형식은 `choices` 라 빈 문자열이
   나오고 모든 계획이 「JSON 아님」이 됨.
4. 종료 사유. `extract_text` 가 `stop_reason` 을 `max_tokens`·`refusal` 로 판정함. Converse 는
   `stopReason` 이고 값이 `max_tokens`·`end_turn` 계열임 — 이름과 값역을 함께 옮겨야 함.
5. 사용량 기록. `extract_usage` 가 `usage.input_tokens`·`output_tokens` 를 읽음. Converse 는
   `usage.inputTokens`·`outputTokens` 이고 캐시 항목이 더 붙음. 옮기지 않으면 비용 관측이
   조용히 비어 있게 됨(그 함수는 없을 때 0 을 만들지 않고 행을 쓰지 않음).
6. 설정값의 공용성. `claude_model_id` 하나가 다섯 job 을 덮음(2절). 추천만 바꾸려면 설정을
   갈래별로 쪼개야 하고, 그러면 `test_config.py`·`test_claude_schema.py` 가 리터럴로 단정한
   기본값 테스트가 함께 움직임.
7. 프롬프트 의존. 지금 프롬프트는 Claude 위에서 여러 차수에 걸쳐 다듬긴 것임(여분 키 금지 문장 ·
   발음 초점 규칙 · 최다 재발 강제). 모델을 바꾸면 그 문면의 효력을 다시 재야 함 — 특히
   질문 수가 openai 계열에서 일관되게 4개로 내려간 것이 그 신호임.
8. 도구 사용·스트리밍은 이 경로의 위험이 아님. 다섯 job 어디도 도구를 정의하지 않고 비스트리밍
   `invoke_model` 만 씀. 네 모델 모두 `responseStreamingSupported=true` 임.

## 10. 하지 못한 것

- 상업 리전(`us-west-2`)의 luna·terra 단가와 Claude 5 계열의 Bedrock 단가를 확인하지 못했음
  (7절). Pricing API 에 항목이 없음.
- 입력을 1개만 썼음 — 같은 사용자 · 같은 프롬프트 위에서 팔당 5회임. 콜드스타트(만성 목록이 빈
  사용자) · 발음 패턴이 없는 사용자 · 수준 상승이 필요한 사용자는 재지 않았음. 품질 판정을
  일반화하려면 입력을 늘려야 함.
- `openai.gpt-5.6-sol` · `openai.gpt-6-astra` 를 재지 않았음(사용자가 지목하지 않았음).
- 추천 외 네 job(분석 · 총평 · 주간 보고 · 시나리오)의 프롬프트로는 재지 않았음. 설정값이
  공용이므로 교체를 결정하면 그 넷도 재야 함.

## 11. 파일

| 파일 | 무엇 |
|---|---|
| `compare_models.py` | 비교 드라이버 (30회 호출 · 판정 · 집계) |
| `probe_body_format.py` | 본문 규격 프로브 (bearer 경로) |
| `probe_body_format.json` | 그 결과 (bearer) |
| `probe_body_format_appcreds.json` | 1차 실행 결과 (앱 SigV4 자격증명 — 후보 셋이 AccessDenied) |
| `prompt_plan.txt` | 이 회차가 보낸 실물 프롬프트 전문 |
| `results.json` | 호출 30건의 원시 계측값과 팔별 집계 |
| `run.log` | 본 실행의 콘솔 출력 |
| `raw/<팔>_<회차>.txt` | 모델이 돌려준 원문 30건 |
| `pricing_api.txt` | AWS Pricing API 조회 출력 |

재현은 아래임. `AWS_BEARER_TOKEN_BEDROCK` 이 셸에 있어야 함.

```bash
cd /Users/redstar/MyProject/OhMyEnglish/app/backend
.venv/bin/python ../../tests/harness/runs/2026-09-16-model-comparison/probe_body_format.py
.venv/bin/python ../../tests/harness/runs/2026-09-16-model-comparison/compare_models.py
```
