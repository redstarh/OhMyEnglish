# 회차 — `TASK-61.12`: 종류를 말하지 않은 모드 변경 요청에 코치가 되묻는가

세션 `ohmyenglish-42` · 2026-09-16 KST · 기준선 커밋 `cf91207` · 고침 커밋은 이 회차 뒤에 옴 ·
절차 정본 `tests/harness/browser_leg.md` · 드라이버 `tests/harness/p_app_path.py`

> 무엇을 재는가: `TASK-61.10` 회차가 **1회** 관측한 것을 크기로 바꾸고, 문면을 고친 뒤 다시 잰다.
> ⛔ **이 회차의 값어치는 계측 하나에 걸려 있음** — `recv.voice_command` 는 프레임 수라서 「tool 이
> 불렸다」까지만 말하고 **어느 명령에 어느 `target` 이 실렸는지는 구별하지 못함.** 그래서 래퍼에서
> `NovaEventTranslator.translate` 를 감싸 제어 이벤트를 남겼음(`control-events.log`).

---

## 0. 스택과 상한

| 무엇 | 값 |
|---|---|
| DB | 검증 전용 `ohmyenglish_t6112`(`schema_migrations` **22**) · 계획을 심지 않음 |
| 백엔드 | `:8012` · 래퍼 `/tmp/t6112_app.py`(CORS `:3001` + **제어 이벤트 계측**) · `VOICE_ADAPTER=nova` · `WORKER_ENABLED=false` |
| 프론트 | 사본 `/tmp/fe-t6112`(`:3001`) · `node_modules` 하드링크 복사(`H-BU`) |
| 브라우저 | 전용 Chrome `:9333`(152.0.7977.83) |
| 상한 | Nova **10세션** · Claude **0회** |

⚠️ **문면을 고친 뒤 백엔드를 재기동했고 P5 를 직접 돌려 통과를 확인했음**(`pid 92736 · 소스 49건 →
통과`). `--reload` 가 없어 재기동하지 않으면 **낡은 지시문을 재게 됨.**

### 픽스처 — 셋을 새로 만들었음

```bash
say -v Yuna     "오 마이 잉글리시, 연습 모드 바꿔 줘."   # vc24_modeonly_ko — 종류를 말하지 않음
say -v Samantha "Pronunciation practice, please."       # vc25_kind_en  — 되물음에 답함
say -v Yuna     "발음 연습으로 해 주세요."               # vc26_kind_ko  — 되물음에 답함
```

기존 것을 씀 — `vc13_learning_en` · `vc15_learning_ko` · `vc23_modeonly_en` · `vc20_yes_en`.

---

## 2. 관측

### 2-1. 「어느 종류인가」를 되물었는가 — 코치의 발화로 셈

| 문면 | 팔 | 되물음 |
|---|---|---|
| **기준선**(`cf91207`) | `base-en-1` · `base-en-2` · `base-ko-1` · `base-ko-2` | **0 / 4** |
| **고친 뒤** | `fix-en-1` · `fix-en-2` · `yes-en` · `answer-en` · `answer-ko` | **3 / 5** |

기준선에서 나온 말 두 개 — **스스로 고른 종류를 말로 밝혔음**:

```
base-ko-1  I will switch to extra conversation practice now. Do you want to talk about …
base-ko-2  I will switch to conversation practice mode. Let's have a conversation about …
```

고친 뒤에 나온 말 — **값역 넷을 읽어 주며 되물었음**:

```
fix-en-1  Sorry, I need you to tell me which kind of practice you want. Do you want
          conversation, scenario intake, pronunciation, or shadowing practice?
yes-en    I need to know which kind of practice you want. You can say "conversation
          practice", … Which one do you choose?
```

되묻지 않은 둘은 **예·아니오 확인으로 갈아탔음**(`answer-en`: *"Do you want to end today's session
and start a new practice session?"*) 또는 **그대로 골랐음**(`answer-ko`: *"I will switch to
conversation practice mode."*).

### 2-2. tool 을 불렀는가 — 계측이 답한 자리

`control-events.log` 의 제어 이벤트 **5건**(계측을 붙인 뒤의 세 팔):

| 팔 | 이벤트 순서 | 읽는 법 |
|---|---|---|
| `answer-en` | `requested/conversation` → `confirmed/**pronunciation**` | 추측했다가 **학습자의 답으로 정정했음** |
| `yes-en` | `requested/conversation` 하나뿐 | 「예」만으로는 `confirmed` 가 오지 않았음 |
| `answer-ko` | `requested/conversation` → `requested/**pronunciation**` | 정정은 됐으나 `confirmed` 까지 가지 않았음 |

⛔ **「답할 때까지 tool 을 부르지 마라」는 지켜지지 않았음 — 3/3 에서 추측한 `conversation` 으로
`requested` 를 불렀음.** 백엔드 warning 은 둘 다 0건(`추가 학습 대상 …` · `표지가 없는 턴 …`).

### 2-3. 그 추측이 학습자를 해쳤는가 — 아니오 (관측 범위에서)

| # | 관측 | 값 |
|---|---|---|
| 1 | 「예」만 답한 팔에서 세션이 갈렸는가 | **아니오** — `recv.session_started` **1** · 코치가 다시 되물었음 |
| 2 | 종류를 답한 팔에서 무엇으로 열렸는가 | `answer-en` 새 세션 `fd846721` = **`pronunciation` · `additional`** |
| 3 | 열린 세션이 학습자가 말한 종류와 같은가 | **같음** |

⇒ **안전을 지킨 것은 문면이 아니라 앱임.** `start_additional` 이 `CONFIRMATION_REQUIRED` 에 있어
`confirmed` 없이는 세션이 열리지 않고, 유일하게 온 `confirmed` 는 **학습자가 말한 값**을 실었음.

---

## 3. 판정 — AC#1·#2·#3 을 닫음. ⛔ 「고쳤다」로 적지 않고 「확률을 옮겼다」로 적음

- **AC#1(크기)**: 되묻기 **0/4 → 3/5**. ⛔ **결정적이지 않음** — 같은 문면에서 거동이 갈림.
- **AC#2(고치는 자리)**: **문면임.** 앱에는 만들 자리가 없음 — 모델이 `target` 을 **항상 유효하게
  채우므로**(계측 3/3) 앱은 「학습자가 종류를 말했는가」를 알 수 없고, 그것을 알려면 `heard` 문장을
  해석해야 함. 그 판정은 `models/voice_command.py` 의 규약 밖임(표지처럼 접두어 한 줄로 끝나지 않음).
- **AC#3(관측)**: 위 2-1~2-3.

⚠️ **남은 구멍 하나를 `TASK-61.13` 으로 등재했음** — `answer-ko` 에서 코치가 *"Okay, we will do
pronunciation practice. … Repeat after me"* 라 말하고 **발음 연습을 그 자리에서 시작했는데** stage 가
`requested` 에 머물러 **앱은 세션을 갈지 않았음.** 즉 **코치의 말과 앱의 상태가 갈린 채 대화가
이어졌음**(1/1 관측). 학습자에게는 「바뀐 것처럼」 들리고 기록은 `speaking` 세션에 남음.

⚠️ **표본이 작음**(팔당 1~2회). 어느 수치도 기전으로 단정하지 않음.

---

## 4. teardown — 이 턴에 직접 돌린 출력

| 대상 | 결과 |
|---|---|
| `:8012` · `:3001` · `:9333` | 전부 HTTP **000** |
| 검증 전용 DB | `dropdb ohmyenglish_t6112` 성공 · 남은 DB 는 `ohmyenglish` · `ohmyenglish_smoke` · `ohmyenglish_test` |
| `/tmp` 사본 | `fe-t6112` · `chrome-t6112` · `t6112_app.py` · 회차 로그 삭제 |
| 공유 dev DB | 손대지 않았음 — `schema_migrations` **22** 로 기준선과 같음 |
| 리포에 남긴 것 | 픽스처 셋(`vc24`~`vc26`) · 이 회차 디렉터리(관측 JSON 일곱 · `control-events.log`) |
