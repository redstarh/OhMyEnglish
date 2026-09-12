# 회차 — `TASK-124`: Nova 세션의 토큰이 `llm_calls` 에 실제로 쌓이는지 본다

세션 `ohmyenglish-f4` · 2026-09-12 · 브랜치 `design/first-vertical-slice` · 기준 커밋 `e6bf0ac`
회차 디렉터리: `tests/harness/runs/2026-09-12-task124-nova-usage/`

> **AC#1 은 라이브 없이 닫혔음** — Nova 의 `usageEvent` 모양을 **이미 있는 실물 산출물**에서 찾았음
> (`runs/2026-09-11-task97-tool-payload/B0-r2.json`). 그래서 이 회차가 재는 것은 AC#3 하나임:
> **제품 어댑터를 실물 스트림에 붙였을 때 행이 쌓이는가.**
>
> 사용자 결정 68 이 저장 모양을 정했음(토큰 열 넷 · 마이그레이션 015).

---

## 0. ⛔ 상한과 해석 규칙 — 돌리기 전에 적는다

**Nova 상한 1세션.** ⛔ 늘리지 않음 — 재는 것이 「기록이 되는가」 하나이고 발화 품질·코칭은 이
회차의 대상이 아님. 늘릴 것이면 새 팔을 열고 이유를 여기 적음.

**실행체**: `record_nova_session.py.txt` — 제품 어댑터(`NovaVoiceAdapter`)를 그대로 쓰고 sink 도
제품 것(`services.usage.pool_usage_sink`)을 씀. ⛔ **WS·프론트를 띄우지 않음**: 그 구간은 통합
테스트가 이미 잼(`test_ws_gives_the_adapter_a_usage_sink_that_actually_writes`).

⚠️ **행은 공유 dev DB 의 `llm_calls` 에 쌓임.** 그 표는 이 기능의 **기록 대상**이므로 행이 늘어나는
것이 정상 동작임 — 「공유 DB 무변경」 규약이 말하는 학습 데이터 다섯 표(`learning_sessions` ·
`pronunciation_attempts` · `error_patterns` · `session_plans` · `learner_notes`)는 건드리지 않음.
그 다섯의 행 수를 전후로 대조함.

| 관측 | 읽는 법 |
|---|---|
| 행 **1건** · `purpose=nova` · 합계 둘이 0 보다 큼 · 분해 넷이 채워짐 | AC#3 닫힘 |
| 행이 **2건 이상** | ⛔ 누적 총계를 여러 번 적었다는 신호 — 코드를 고치고 다시 돔 |
| 행 **0건** + 로그에 「usageEvent 없이 끝났다」 | 스트림이 초기화 전에 끊겼음. ⛔ 0 을 적지 않은 것이 설계대로임 — 세션을 다시 돌기 전에 사유를 먼저 봄 |
| 분해가 `None` | 실물 `details.total` 이 오지 않았다는 뜻 — 결정 68 의 전제를 다시 봐야 함 |

⛔ **토큰 «수치» 자체를 판정에 쓰지 않음** — 발화 길이에 따라 달라지므로 「0 보다 큼」만 봄.

## 1. 관측 — Nova 1세션 (실행체 `record_nova_session.py.txt`)

픽스처 `p2m.wav`(97,216바이트 · 약 3초) · 모델 `amazon.nova-2-sonic-v1:0` · `records_usage=True`.

**`purpose=nova` 행이 정확히 1건 쌓였음** — 누적 총계를 여러 번 적지 않았음:

| 열 | 값 |
|---|--:|
| `input_tokens` | **216** |
| `output_tokens` | **0** |
| `input_speech_tokens` | **150** |
| `input_text_tokens` | **66** |
| `output_speech_tokens` | **0** |
| `output_text_tokens` | **0** |

`called_at` 2026-09-12 02:06:18 UTC(`timestamptz`). 학습 데이터 다섯 표는 **전후 무변경**
(`learning_sessions=17` · `pronunciation_attempts=7` · `error_patterns=9` · `session_plans=6` ·
`learner_notes=7`).

⚠️ **받은 포트 이벤트가 `SpeechBoundaryEvent` 1건뿐이었음** — 전사도 오디오 응답도 오지 않았음.
픽스처 뒤에 무음이 없어 endpointing 이 걸리지 않은 것으로 읽힘(이 리포의 스파이크가 무음 프레임을
덧붙였던 것과 같은 자리 — `nova.py` 머리말이 그 대가를 적어 뒀음).

## 2. 판정 — AC#3 을 닫는다. ⛔ 어긋난 조건 하나를 그대로 적는다

- **AC#3 닫힘**: 실물 세션 1회로 행이 쌓이는 것을 직접 조회해 확인했음. 행이 **1건**인 것이
  §0 의 두 번째 갈래(2건 이상 = 누적을 여러 번 적음)를 배제함.
- **분해 넷이 전부 not-null 임** — `output` 쪽도 `None` 이 아니라 `0` 이므로 파서가
  `details.total.output` 을 **실제로 읽었음**. 결정 68 의 전제(분해가 온다)가 실물에서 성립함.
- ⛔ **§0 이 미리 적은 조건 하나가 어긋났음**: 「합계 둘이 0 보다 큼」에서 `output_tokens=0` 이었음.
  ⚠️ **끼워 맞추지 않고 원인을 적음** — 모델이 응답 발화를 하기 **전에** 세션이 끝났고(위 이벤트
  1건) 그래서 출력 토큰이 실제로 0 임. 즉 **기록 경로의 결함이 아님**: 입력 쪽 분해가 정확히
  `150 + 66 = 216` 으로 맞았음.
- ⚠️ **남는 것**: 「응답까지 받은 세션에서 출력 토큰이 채워지는가」는 이 회차가 재지 못했음. 상한
  1세션을 지켰고(§0) 늘리지 않았음 — 그 관측은 **실사용에서 자연히** 쌓임(WS 경로 배선은 통합
  테스트가 이미 지킴). 실사용에서도 계속 0 이면 그때 새 태스크로 세움.
