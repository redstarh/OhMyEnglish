# 회차 — `TASK-61.5`: 한국어 명령의 침묵을 원인까지 좁혀 닫았음

세션 `ohmyenglish-65` · 2026-09-15 KST · 결정 정본 **109** · 절차 정본 `tests/harness/browser_leg.md` ·
드라이버 `tests/harness/p_app_path.py`

> 무엇을 재는가: 결정 106 은 이 침묵을 「그대로 둠」으로 정했고 그 근거가 **앱이 고칠 수 없다는
> 전제**였음. 이 회차는 ① 그 전제를 계측으로 검사하고 ② 틀렸으면 고쳐 ③ 고침이 실물에서 듣는지와
> ④ 영어·종료 경로가 회귀하지 않는지를 봄.

---

## 0. 스택과 상한

| 무엇 | 값 |
|---|---|
| DB | 검증 전용 `ohmyenglish_t618`(`schema_migrations` **22**) · **계획 1행을 dev DB 에서 옮겨 심었음**(A2 · 질문 5개) |
| 백엔드 | `:8012` · 래퍼 `/tmp/t618_app.py` — CORS origin 교체 + **`NovaEventTranslator.translate` 를 감싸 수신 이벤트를 로그로 남김** |
| 프론트 | 사본 `/tmp/fe-t618r`(`:3001`) · `node_modules` 하드링크 복사(`H-BU`) |
| 브라우저 | 전용 Chrome `:9333`(152.0.7977.83) |
| 상한 | Nova **7세션** · Claude **0회**. ⚠️ 앞 회차들의 2세션보다 큼 — 원인 가르기(2) · 고침 검증(2) · 프롬프트 재고침(2) · 종료 회귀(1) 이고 각 단계가 앞 단계의 결과에 의존해 한 번에 묶을 수 없었음 |

⛔ **계측을 앱 코드가 아니라 래퍼에 얹었음.** `translate` 는 처리한 이벤트를 로깅하지 않으므로 기존
로그로는 「어댑터가 무엇을 받았는가」를 알 수 없었음. ⚠️ **첫 계측 판은 출력이 0건이었음** — 전용
로거 + `info` 를 썼고 uvicorn 로깅 설정에서 전파되지 않았음. 어댑터 자신의 로거 + `warning` 으로
바꿔 얻었음.

---

## 1. 원인 — 계측으로 확정했음

**침묵 세션(`c7957d75`)의 `toolUse` 뒤 이벤트 전부** (`trace-before-silent.txt`):

```
TRACE toolUse {'role': 'TOOL', 'toolName': 'request_session_control', ...}
TRACE contentEnd {'type': 'TOOL', 'stopReason': 'TOOL_USE', ...}
TRACE usageEvent {}
```

⇒ assistant `TEXT`·`AUDIO` 가 **0건**. 앱이 버린 것이 아님 — `_on_audio_output` 은 base64 실패만
버리고 그 warning 도 0건이었음.

**고침 뒤 같은 자리** (`trace-after-speaking.txt`):

```
TRACE toolUse ... / TRACE contentEnd {'stopReason': 'TOOL_USE'} / TRACE usageEvent ×4
TRACE contentStart {'role': 'ASSISTANT', 'type': 'TEXT', ...}
TRACE textOutput {'role': 'ASSISTANT', ...}
TRACE contentStart {'role': 'ASSISTANT', 'type': 'AUDIO', ...}
TRACE audioOutput #325
```

⇒ **결과를 돌려보내자 모델이 그 턴을 이어 말했음.** 근본 원인은 「앱이 `toolResult` 를 보내지
않아 `stopReason: TOOL_USE` 로 닫힌 턴을 모델이 이어갈 수 없었던 것」임. 정본은 결정 109 임.

⛔ **그 한계를 설계서가 스스로 적어 뒀음** — `2026-08-27-pronunciation-echo-design.md` F6 이
*"1회 관측이다. 다중 턴에서도 안전한지는 미검증"* 이라 적고 §9 미결 1 로 남겼음. 이 회차가 그
미관측 구간이었음.

---

## 2. 관측 — 세션 일곱을 표로

| 세션 | 언어 | 계획 | 코드 상태 | 명령 뒤 코치 발화 |
|---|---|---|---|---|
| `4ed4ea1d` | 한국어 | **없음** | 고침 전 | **1회** (`walk-ko-noplan.json`) |
| `c7957d75` | 한국어 | 있음 | 고침 전 | ⛔ **0회 — 침묵** (`walk-ko-before.json`) |
| `43f0e300` | 한국어 | 있음 | `toolResult` | **1회** · 계획 둘째 질문 |
| `af8a8594` | 영어 | 있음 | `toolResult` | ⚠️ **2회 — 중복** (`walk-en-duplicate.json`) |
| `0faeae61` | 영어 | 있음 | + 규칙 13 | **1회** (`walk-en-after.json`) |
| `5a81cc14` | 한국어 | 있음 | + 규칙 13 | **1회** · 계획 둘째 질문 (`walk-ko-after.json`) |
| `834c5089` | 영어 종료 | 있음 | + 규칙 13 | **확인 질문 1회** — 회귀 없음 (`walk-end-regression.json`) |

**중복 발화와 그 고침**: `toolResult` 만 넣었을 때 영어에서 코치가 같은 요청을 두 번 말했음
(agent 발화 2행). 원인이 분명함 — 규칙 13 이 「소리로 먼저 말하고 tool 을 부르라」고 해서 tool
**앞**에 이미 말했고, 이제 결과를 받아 **또** 말한 것임. ⇒ 규칙 13 을 명령별로 갈랐음:
**확인이 필요한 종료는 먼저 말하고**(결정 104 D3 유지) **확인이 없는 둘은 tool 을 먼저 부르고
결과를 받은 뒤 한 번만 말함.**

**종료 회귀 팔의 발화 기록**(DB):

```
user  | voice_command        | oh my english and the session.
agent | learning             | Do you want to end today's session?
user  | command_confirmation | yes please end it now.
status = completed
```

⇒ 결정 102 ③(음성 확인)과 결정 104 D3(소리로 먼저 묻기)이 **둘 다 살아 있음.**
⚠️ ASR 이 `end` 를 `and` 로 들었으나 표지가 살아 tool 이 왔음 — 결정 105 가 적은 대가의 또 한 예임.

DB 집계(teardown 직전 · 검증 전용 DB): `learning_sessions` **8**(계획 매단 것 1 + 회차 7) ·
`utterances` **33** · `voice_command` **7** · `command_confirmation` **1**.

---

## 3. 판정 — AC#2·#3 충족. 결정 106 의 전제가 정정됐음

- **AC#2**: 고친 뒤 한국어 명령에서 코치가 소리로 말하는 것을 관측했음(2/2 — `43f0e300`·`5a81cc14`).
- **AC#3**: 영어가 회귀하지 않았고(1/1) 종료 경로도 확인 절차를 그대로 탐(1/1). **오히려 중복
  발화가 사라졌음.**
- ⛔ **결정 106 의 「앱이 고칠 수 없다」가 틀렸음이 확정됐음.** 그 판단은 프롬프트와 음성 합성만
  후보로 두었고 **프로토콜 층(`toolResult`)을 보지 않았음.**

⚠️ **정직하게 적을 애매함 하나** — 영어 팔(`0faeae61`)의 명령 뒤 질문이 계획의 **첫** 질문이었음
(앞선 관측들은 둘째 질문이었음). 첫 코치 발화가 계획 질문을 변형해 물었고 모델이 어디까지
진행했다고 보는지가 흔들리는 것으로 보임. ⛔ **표본 1 이라 기전으로 단정하지 않음** — 이 회차가
답한 것은 「중복이 사라졌는가」이고 그것은 분명함. 「어느 질문으로 가는가」는 별 물음임.

⚠️ **계획 유무가 침묵을 갈랐다는 관측도 남김**(계획 없음 1회 발화 · 계획 있음 침묵). 고침 뒤에는
**계획이 있어도** 말하므로 그 조건은 이제 결과를 바꾸지 않음. ⛔ 기전은 미확정임.

---

## 4. teardown — 이 턴에 직접 돌린 출력

| 대상 | 결과 |
|---|---|
| `:8012` · `:3001` · `:9333` | 전부 HTTP **000** |
| 검증 전용 DB | `dropdb ohmyenglish_t618` 성공 · 남은 DB 는 `ohmyenglish` · `ohmyenglish_smoke` · `ohmyenglish_test` |
| `/tmp` 사본 | `fe-t618r` · `chrome-t618r` · `t618_app.py` 삭제 |
| 공유 dev DB | **읽기만 했음** — 회차 뒤 `schema_migrations` **22** · `learning_sessions` **17** · `session_plans` **6** 으로 기준선과 같음 |
