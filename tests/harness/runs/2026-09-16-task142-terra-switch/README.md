# 회차 — `TASK-142`: 학습 추천 job 을 terra 로 옮긴 뒤 실제로 도는가

세션 `ohmyenglish-43` · 2026-09-16 KST · 결정 121 · 구현 커밋은 이 폴더를 담은 커밋의 부모다

> 무엇을 재는가 셋: ⑴ openai 계열 응답의 **실제 모양** ⑵ 그 모델을 부를 수 있는 **자격증명 경로**
> ⑶ 추천 job 이 terra 로 **끝까지 도는가**(계획 저장 · 토큰 기록).
> ⛔ 추정으로 쓴 값이 없다 — 아래 셋 다 이 세션에서 직접 돌린 출력이다.

---

## 1. 응답의 모양 — `probe_openai_shape.py` (terra 1회 호출)

정본은 `openai_shape.json` 이다. 앱이 고쳐야 할 자리가 이 넷에서 나왔다.

| 무엇 | Anthropic (기존) | openai 계열 (실측) |
|---|---|---|
| 텍스트 | `content[]` 의 text 블록 | **`choices[0].message.content`** |
| 예산 절단 | `stop_reason="max_tokens"` | **`finish_reason="length"`** (정상은 `stop`) |
| 거부 | `stop_reason="refusal"` | **`message.refusal`** |
| 토큰 | `usage.input_tokens`·`output_tokens` | **`usage.prompt_tokens`·`completion_tokens`** |

⚠️ 본문 규격도 다르다 — `anthropic_version` 을 실으면 `unknown_parameter` 로 거부되고 출력 상한의
키는 `max_completion_tokens` 다(모델 비교 회차 §3 의 표가 그 근거다).

## 2. 자격증명 — bearer 키 경로 (사용자 지시)

앱의 SigV4 IAM 사용자로는 terra 를 부를 수 없다. **이 턴에 직접 확인했다**:
`us.openai.gpt-5.6-terra` → `AccessDeniedException` · `us.anthropic.claude-opus-5` → 통과.

사용자가 *"zshrc 내의 Bedrock API Key 로 권한 획득해서 진행해"* 로 정했고, 그 키가 `.env` 값과
**같은 값**임을 해시 앞 8자로 확인했다(값은 어디에도 적지 않았다).

⛔ **boto3 로는 그 키를 쓸 수 없었다 — 실측 둘.**

1. 클라이언트 생성 시점에 환경변수를 올리고 지우면 **호출 시점**에 `NoCredentialsError` 다
   (토큰은 호출 시점에 읽힌다).
2. 토큰 provider 를 클라이언트에 직접 꽂아도 환경의 SigV4 가 이겨 `AccessDenied` 가 났다.
   자격증명을 비우면 다시 `NoCredentialsError` 였다.

⇒ 그래서 이 경로만 **HTTPS 직접 호출**이다(`invoke_openai_model`).
⛔ **환경변수를 만지지 않는다** — bearer 를 프로세스 환경에 올리면 boto3 의 Bedrock 호출 전부가
그것을 쓰고 **Nova 양방향이 403 으로 죽는다**(`config.prepare_bedrock_credentials` 가 SigV4 준비 후
그 값을 지우는 이유). 토큰은 인자로만 흐른다.

## 3. 종단 — 추천 job 이 terra 로 돌았다

`p_plan_job_end_to_end.py` 가 앱의 job 경로를 그대로 탔다(`claim_next` → `process_plan` →
`session_plans` insert). 검증 전용 DB `ohmyenglish_t142`(`schema_migrations` **23** · 회차 뒤 drop).
심은 것은 **끝난 세션 1건 · 학습 발화 3건 · 초점 후보 2건**이고 계획은 심지 않았다.

출력 정본은 `plan_job_end_to_end.json` 이다.

| 무엇 | 값 |
|---|---|
| job | `status=done` · `attempts=1` · `last_error=null` |
| 계획 | `target_level=A2` · `source=agent` · 질문 **4** · 초점 **2** |
| 지시문 키 | `contexts` · `focus` · `hint_timing` · `sentence_length` · `target_level` (다섯) |
| `llm_calls` | `us.openai.gpt-5.6-terra` · `purpose=plan` · 입력 **1085** · 출력 **479** |

⇒ 세 자리의 분기가 모두 실제로 걸렸다: 본문 규격(거부되지 않았다) · 텍스트 추출(`parse_plan` 이
통과했다) · usage 키(**토큰이 비지 않았다**).

⚠️ **첫 실행은 실패했고 그것을 남긴다** — 초점 후보 0건이라 job 이 `no focus candidates yet` 으로
되돌아갔다(모델과 무관한 조건 미충족). 후보 둘을 심고 다시 돌려 위 결과를 얻었다.

## 4. 이 회차가 말하지 않는 것

- **질문 수가 4다.** 모델 비교 회차가 openai 계열에서 일관되게 4를 관측했고(Claude 는 5) 이번에도
  4였다. `session_plans.questions` 의 CHECK 는 3~5 이므로 계약 위반이 아니지만 **프롬프트가 Claude
  위에서 다듬긴 것**이라는 사실은 그대로 남는다(결정 121 이 받아들인 대가).
- **표본 1건이다.** 콜드스타트·발음 패턴 있는 사용자·수준 상승 케이스는 재지 않았다.
- **IAM 권한을 부여하지 않았다.** 사용자가 bearer 경로를 골랐으므로 `ohmyenglish-local` 은 여전히
  이 프로필을 부를 수 없다 — ⛔ **키가 없는 환경에서는 추천 job 이 `RuntimeError` 로 즉시 실패한다**
  (그 실패는 「키가 없다」를 그 자리에서 말한다).
