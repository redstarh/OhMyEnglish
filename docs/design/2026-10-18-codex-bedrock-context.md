# Codex / Paseo Bedrock GPT context 설정

2026-10-18 · TASK-283

사용자가 Paseo의 Codex 모델 목록 네 모델과 전역 Codex에서 같은 1M context를 사용하도록 요청했다.

## 확인한 AWS 사양

| 모델 ID | AWS 공식 context 사양 |
|---|---:|
| `openai.gpt-6.1-sol` | 1M tokens |
| `openai.gpt-6-astra` | 1,050,000 tokens |
| `openai.gpt-6-luna` | 1,050,000 tokens |
| `openai.gpt-5.6-terra` | 1,050,000 tokens |

확인한 공식 문서:

- https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-openai-gpt-6-1-sol.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-openai-gpt-6-astra.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-openai-gpt-6-luna.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-openai-gpt-56-terra.html
- https://developers.openai.com/codex/config-reference/

## 적용한 설정

`/Users/redstar/.codex/config.toml`의 최상위 공통 설정:

```toml
model_context_window = 1000000
model_auto_compact_token_limit = 900000
```

이 설정에서 참조하는 `/Users/redstar/.codex/model-catalog.json`의 네 모델에 다음 값을 동일하게 적용했다.

```json
{
  "context_window": 1000000,
  "max_context_window": 1000000,
  "effective_context_window_percent": 95
}
```

`effective_context_window_percent`는 기존 95를 유지했다. 따라서 실제 세션에 보고되는 사용 가능 한도는 **950,000 토큰**이다. 자동 요약 시작점은 900,000 토큰이다.

이전 카탈로그에는 네 모델 모두 `context_window=272000`, `max_context_window=872000`으로 등록되어 있었다. 이전 세션에 표시된 258,400 토큰은 272,000의 95%였다.

Paseo 0.11.4의 설치된 Codex provider 구현을 확인했다. Agent마다 `codex app-server`를 실행하고, 별도의 context 설정을 덮어쓰지 않으며, Codex가 보고한 `modelContextWindow`를 UI 사용량 표시기에 전달한다. 따라서 같은 홈 디렉터리를 사용하는 전역 Codex와 Paseo에 공통으로 적용된다.

다른 모델 메타데이터, 기본 선택 모델, 모델 제공자, 자격증명과 무관한 기존 설정은 보존했다.

## 검증

Codex CLI 0.163.0의 별도 `app-server --strict-config --stdio` 프로세스로 검증했다. 사용자 대화 프로세스는 재시작하지 않았다.

`config/read`로 실제 로드된 값 `model_context_window=1000000`, `model_auto_compact_token_limit=900000`을 확인했다. `model/list`에서 네 모델이 모두 존재하는 것을 확인했다.

각 모델에 ephemeral thread를 만들고, 도구 사용을 금지한 짧은 응답 요청을 한 번씩 보냈다.

| 모델 | 실제 제공자 | 응답 | turn 상태 | 보고된 사용 가능 context |
|---|---|---|---|---:|
| GPT-6.1 Sol | amazon-bedrock | OK | completed | 950,000 |
| GPT-6 Astra | amazon-bedrock | OK | completed | 950,000 |
| GPT-6 Luna | amazon-bedrock | OK | completed | 950,000 |
| GPT-5.6 Terra | amazon-bedrock | OK | completed | 950,000 |

네 모델 모두 추가 도구 실행 없이 성공했다. 테스트 프로세스는 종료했다. 이 검증은 설정 로드와 실제 모델 응답 및 context 메타데이터를 확인한 것으로, 1M 토큰에 가까운 대형 입력을 직접 보내는 부하 테스트는 수행하지 않았다.

새로 실행되는 Codex / Paseo Agent부터 설정을 읽는다. 이미 실행 중인 Agent에는 재로드가 필요하며, 기존 대화의 이전 context 숫자가 즉시 바뀌었다고 판정하지 않았다.

## 백업

두 원본 파일을 다음 디렉터리에 백업했다.

`/Users/redstar/.codex/backups/20261018-130028-context-1m/`

파일 내용과 파싱 결과를 검증하고 기존 파일 권한을 유지한 채 교체했다. 복구하려면 해당 디렉터리의 `config.toml`과 `model-catalog.json`을 원래 위치로 되돌린 뒤 Agent를 다시 실행한다.
