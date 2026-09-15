# 회차 — `TASK-61.10`: 「모드 변경」이 「추가 학습」 명령으로 수행되는가

세션 `ohmyenglish-42` · 2026-09-16 KST · 계약 정본 결정 **111** · 구현 커밋 `6e04887` ·
절차 정본 `tests/harness/browser_leg.md` · 드라이버 `tests/harness/p_app_path.py`

> 무엇을 재는가: 결정 111 은 「모드 변경은 별도 명령이 아니고 `start_additional` 의 `target` 이
> 수행함」임. 단위 테스트가 확인한 것은 **지시문 문면**뿐이고(`test_nova.py` 의
> `..._folds_mode_change_...`), **모델이 그 발화를 그 명령으로 부르는지는 실물만 잴 수 있음.**
> ⇒ 이 회차가 그 자리를 밟음.

⚠️ **`harness_runs` 회차를 열지 않았음** — 검증 전용 DB 를 통째로 `drop` 하므로 `browser_leg.md`
§3 의 목적(공유 DB 에서 삭제 범위를 좁히는 것)이 성립하지 않음. 공유 dev DB 는 손대지 않았음(§4).

---

## 0. 스택과 상한

| 무엇 | 값 |
|---|---|
| DB | 검증 전용 `ohmyenglish_t6110`(`schema_migrations` **22** · `users` 1 · `shadowing_items` 1 — 전부 마이그레이션 시드) · 계획을 심지 않음 |
| 백엔드 | `:8012` · 래퍼 `/tmp/t6110_app.py`(CORS origin 만 `:3001`) · `VOICE_ADAPTER=nova` · `WORKER_ENABLED=false` |
| 프론트 | 사본 `/tmp/fe-t6110`(`:3001`) · `node_modules` 하드링크 복사 **6.4초**(`H-BU`) · 픽스처를 사본의 `public/harness/` 에 둠 |
| 브라우저 | 전용 Chrome `:9333`(**152.0.7977.83**) · fake media stream |
| 드라이버 | `--wav <학습>,<명령>[,<확인>] --next-wait-ms 30000 --settle-ms 25000` |
| 상한 | Nova **5세션**(ARM-EN 2 · ARM-KO 2 · ARM-ASK 1) · Claude **0회** |

### 픽스처 — 셋을 새로 만들었음

```bash
say -v Yuna     -o /tmp/z6110.aiff "오 마이 잉글리시, 발음 연습 모드로 바꿔 줘."   # vc21_mode_ko
say -v Samantha -o /tmp/z6110.aiff "Oh My English, switch to pronunciation mode."  # vc22_mode_en
say -v Samantha -o /tmp/z6110.aiff "Oh My English, change the practice mode."      # vc23_modeonly_en
afconvert -f WAVE -d LEI16@16000 -c 1 /tmp/z6110.aiff tests/harness/fixtures/voice/<id>.wav
```

학습 발화와 확인 발화는 기존 것을 씀 — `vc13_learning_en` · `vc15_learning_ko` · `vc18_yes_ko` ·
`vc20_yes_en`. ⚠️ **`vc23` 은 종류를 말하지 않는 요청임** — 내가 더한 절의 뒤쪽 절반(「어느 것인지
말하지 않았으면 먼저 물음」)을 재는 유일한 팔임.

### 해석 규칙

| 결과 | 읽는 법 |
|---|---|
| 세션이 **둘** 열리고 둘째의 `mode` 가 학습자가 말한 종류 | AC#3 충족 — 모드 변경이 이 명령으로 수행됨 |
| 세션이 하나만 열림 + 확인 발화 0행 | 확인을 받지 않았으므로 **정상** — 갈리지 않는 것이 계약임 |
| 「추가 학습 대상 … 알 수 없어」 warning ≥ 1 | 모델이 `target` 없이 불러 페이로드가 버려짐 ⇒ 명령이 조용히 사라진 것 |
| 확인 없이 세션이 갈림 | ⛔ 심각 — `CONFIRMATION_REQUIRED` 가 무력화된 것 |

---

## 2. 관측 — 종류를 말한 두 팔은 성립하고, 말하지 않은 팔에서 되묻지 않았음

| # | 관측 | ARM-EN | ARM-KO | ARM-ASK |
|---|---|---|---|---|
| 1 | `recv.session_started` | **2** | **2** | **1** |
| 2 | `recv.voice_command` | 2 | 2 | 1 |
| 3 | 결과 화면 URL 의 세션 | 둘째 `79d213e6` | 둘째 `4cbe8029` | 같은 세션 `6dc35aac` |
| 4 | 둘째 세션의 `learning_source` | **`additional`** | **`additional`** | — |
| 5 | 둘째 세션의 `mode` | **`pronunciation`** | **`pronunciation`** | — |
| 6 | 확인 발화 기록 | `command_confirmation` 1행 | 1행 | **0행** |

**세션 표**(teardown 직전):

```
8c6db34e | completed | speaking       | recommended   ← ARM-EN 첫 세션
79d213e6 | completed | pronunciation  | additional    ← ARM-EN 새 세션
08d1e3f3 | completed | speaking       | recommended   ← ARM-KO 첫 세션
4cbe8029 | completed | pronunciation  | additional    ← ARM-KO 새 세션
6dc35aac | completed | speaking       | recommended   ← ARM-ASK (갈리지 않았음)
```

**ARM-KO 의 발화 기록** — 한국어에서도 코치가 말했음(결정 109 의 고침이 살아 있음):

```
user  | learning             | 저는 보통 지하철로 출근해요
agent | learning             | That is a useful sentence for daily life. Can you tell me …
user  | voice_command        | 오마이잉글리시 발음 연습 모드로 바꿔주세요
agent | learning             | Okay, I will switch to pronunciation practice mode. Let's start …
user  | command_confirmation | 네 해주세요
```

백엔드 로그: 「추가 학습 대상 … 알 수 없어」 **0건** · 「표지가 없는 턴의 음성 명령…」 **0건**.
⇒ 세 팔 모두 표지가 살고 페이로드가 버려지지 않았음.

**화면**(`shot-en-session.png` — 직접 열어 확인했음): 「**발음 연습으로 시작했어요. 오늘 다룰
소리는 대화에서 듣고 고를 거예요.**」 + 「대화를 기다리는 중…」 + 「학습 종료」.
⇒ 결과 화면을 거치지 않고 **발음 연습 세션**이 열렸음(결정 110 ③ 과 같은 모양).

---

## 3. 판정 — `PASS`. AC#3 을 닫음. ⚠️ 미충족 관측 둘을 함께 남김

**흡수가 성립했음** — 「발음 연습 모드로 바꿔 줘」·「switch to pronunciation mode」가 **두 언어에서
2/2** 로 `start_additional` 을 부르고 새 세션의 `mode` 를 `pronunciation` 으로 정했음. 별도 명령을
만들지 않고 PRD:82 의 항목이 수행됐음.

### ⚠️ 미충족 ① — 확인을 「질문」으로 묻지 않고 예고로 말했음 (두 팔 모두)

규칙 13 은 `start_additional` 에 **먼저 소리로 물을 것**을 요구하는데 코치는
*"Okay, I will switch to pronunciation mode."* 로 **예고**하고 연습 문장을 바로 냈음.
⛔ **계약은 깨지지 않았음** — 확인 게이트를 앱이 갖고(`CONFIRMATION_REQUIRED`) 학습자의 「네」가
오기 전에는 세션이 닫히지 않았음. 그러나 **학습자에게는 「이미 바뀌었다」로 들림.**
⚠️ 앞 회차(`2026-09-16-task61-8-additional-learning`)에서는 *"Sorry, I need your confirmation
before I start."* 라 물었음 — 즉 같은 문면에서 거동이 갈렸고 **표본이 작아 기전으로 단정하지 않음.**

### ⚠️ 미충족 ② — 종류를 말하지 않은 요청에서 되묻지 않았음 (ARM-ASK)

내가 더한 절의 뒤쪽 절반이 이 **1회 관측에서 성립하지 않았음.** 코치는 어느 연습인지 묻지 않고
*"Do you want to end today's session and start a new practice session?"* 로 예·아니오 확인을
물었음. 그리고 **페이로드가 버려지지 않았으므로**(warning 0건) 모델이 값역 안의 `target` 을
**스스로 골랐음**.

⇒ **학습자가 「예」라고만 답하면 자기가 고르지 않은 모드로 열릴 수 있음.** 이 회차는 확인 발화를
흘리지 않았으므로 그 뒤를 관측하지 않았음. **후속 태스크로 등재했음**(`TASK-61.12`).

> ⚠️ **2026-09-16 정정 — 위 단정의 유도가 그때는 부족했음.** 「모델이 `target` 을 스스로 골랐음」을
> **warning 0건**으로 유도했는데 warning 0 은 「tool 을 애초에 안 불렀음」과도 양립함. 실제로 쓸 수
> 있는 근거는 `recv.voice_command` 프레임이 제어 이벤트에서만 나온다는 것이고, 그 프레임조차
> **어느 명령·어느 `target`** 인지는 구별하지 못함.
> ⇒ **결론 자체는 뒤에 실측으로 확인됐음** — `TASK-61.12` 회차가 어댑터 계측으로
> `start_additional / requested / target='conversation'` 을 **3/3** 관측했음
> (`runs/2026-09-16-task61-12-unspecified-mode/control-events.log`). **결론은 유지하고 유도만 정정함.**
> ⛔ 그리고 **「예라고만 답하면 엉뚱한 모드로 열린다」는 재현되지 않았음** — 그 회차 `yes-en` 팔에서
> 코치가 다시 되물었고 `confirmed` 가 오지 않아 세션이 갈리지 않았음.

⛔ **이 미충족이 결정 111 을 뒤집지 않음** — 종류를 말한 경로가 흡수의 본체이고 그것이 2/2 로
성립했음. 미충족은 「종류를 말하지 않은 경로」 하나임.

---

## 4. teardown — 이 턴에 직접 돌린 출력

| 대상 | 결과 |
|---|---|
| `:8012` · `:3001` · `:9333` | 전부 HTTP **000** |
| 검증 전용 DB | `dropdb ohmyenglish_t6110` 성공 · 남은 DB 는 `ohmyenglish` · `ohmyenglish_smoke` · `ohmyenglish_test` |
| `/tmp` 사본 | `fe-t6110` · `chrome-t6110` · `t6110_app.py` · 회차 로그 · `z6110.aiff` 삭제 |
| 공유 dev DB | 손대지 않았음 — `schema_migrations` **22** 로 기준선과 같음 |
| 리포에 남긴 것 | 픽스처 셋(`vc21`~`vc23`) · 이 회차 디렉터리 |
