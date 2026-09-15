# 회차 — `TASK-61.7`: 「다음 문제」가 드릴 예산을 이기는가

세션 `ohmyenglish-65` · 2026-09-15 KST · 계약 정본 결정 108 · 구현 커밋 `abf3210` ·
절차 정본 `tests/harness/browser_leg.md` · 드라이버 `tests/harness/p_app_path.py`

> 무엇을 재는가: 이 명령은 **앱이 하는 일이 기록뿐**이라(결정 108 ④) 효과가 전부 코치의 거동에 있음.
> 단위 테스트가 확인할 수 있는 것은 문면과 파싱까지이고, **「명령 뒤에 코치가 다른 질문을 하는가」는
> 회차만 잴 수 있음.** 그리고 그 질문이 `_DRILL_INSTRUCTION` 의 exchange 최소값을 **깨고** 와야 함.

---

## 0. 상한과 해석 규칙 — 돌리기 전에 적음

### 스택

| 무엇 | 값 |
|---|---|
| DB | 검증 전용 `ohmyenglish_t617`(`schema_migrations` **22**) · **계획 1행을 dev DB 에서 옮겨 심었음**(아래 §1) |
| 백엔드 | `:8012` · 래퍼 `/tmp/t617_app.py`(CORS origin 만 `:3001`) · `VOICE_ADAPTER=nova` · `WORKER_ENABLED=false` |
| 프론트 | 사본 `/tmp/fe-t617`(`:3001`) · `node_modules` 는 **하드링크 복사**(`H-BU`) · 픽스처를 사본의 `public/harness/` 에 둠 |
| 브라우저 | 전용 Chrome `:9333`(**152.0.7977.83**) · fake media stream |
| 드라이버 | `p_app_path.py --wav <학습>,<명령> --next-wait-ms 30000 --settle-ms 20000 --settle-timeout-ms 90000 --walk-timeout-ms 60000` |
| 계측 | `instrument.js` sha256 `cbc19fb69a89eb7868420a9ea1b9245103518dfeaebddec29fcfea3ee19b55ac`(44,552 B) |
| 공유 자원 | 공유 dev DB 를 **읽기만** 했음(계획 한 행) · `:3000` · `:8002` · `:9222` 를 건드리지 않았음 |

⚠️ **`--next-wait-ms` 를 크게 둔 이유가 앞 회차와 반대임** — 앞 회차(`task61-6`)는 코치가 침묵하는
팔에서 둘째 픽스처를 흘리려고 **작게** 뒀지만, 이번에는 **코치의 질문 1 을 들은 뒤에** 명령을 흘려야
「질문이 바뀌었다」를 잴 수 있음. 대기 조합이 관측을 정한다는 것이 같은 사실의 두 방향임.

### 픽스처 — 이 회차에서 만들었음

```bash
say -v Samantha -o /tmp/y.aiff "I usually take the subway to work."   # vc13_learning_en
say -v Samantha -o /tmp/y.aiff "Oh My English, next question."        # vc14_next_en
say -v Yuna     -o /tmp/y.aiff "저는 보통 지하철로 출근해요."           # vc15_learning_ko
say -v Yuna     -o /tmp/y.aiff "오 마이 잉글리시, 다음 문제."           # vc16_next_ko
afconvert -f WAVE -d LEI16@16000 -c 1 /tmp/y.aiff tests/harness/fixtures/voice/<id>.wav
```

### 팔 둘과 상한

| 팔 | 흘리는 픽스처 | 무엇을 재는가 |
|---|---|---|
| ARM-EN | `vc13_learning_en` → `vc14_next_en` | 코치가 계획 질문 1 을 낸 뒤 명령이 오면 **질문 2** 로 넘어가는가 |
| ARM-KO | `vc15_learning_ko` → `vc16_next_ko` | 같은 것을 한국어 명령으로 |

상한: Nova **2세션** · Claude **0회**. 넘기지 않았음.

### 해석 규칙

| 결과 | 읽는 법 |
|---|---|
| 명령 뒤 코치 발화가 **계획의 다음 질문**이면 | AC#3 충족 — 결정 108 ③ 이 실물에서 성립함 |
| 명령 뒤 코치가 **같은 질문을 계속하면** | 드릴 예산이 이긴 것 ⇒ 규칙 13 의 우선순위 문면이 안 먹은 결함 후보 |
| 명령 뒤 코치 발화가 **아예 없으면** | 결정 106 의 침묵 ⇒ **이 명령에서는 기능이 성립하지 않음**(코치가 수행 주체이므로) |
| 화면이 무엇인가 표시하면 | 결정 108 ② 위반 — 화면은 아무것도 하지 않아야 함 |

---

## 1. 쓴 것 — 상한을 넘기지 않았음

Nova **2세션**(`34dbf010` 영어 · `6aaeb5f9` 한국어) · Claude **0회** · 픽스처 넷 신설.

**계획은 dev DB 의 최신 `session_plans` 한 행을 그대로 옮겼음** — 실제 모델이 만든 유효한 모양을
쓰는 것이 손으로 조립하는 것보다 정확함. 옮긴 것: `target_level` **A2** · 질문 **5개** ·
`focus` 2개(`pronunciation_an_as_a` · `article_missing_before_noun`).
⚠️ `focus_pattern_ids` 는 FK 가 없어 dev 값을 그대로 넣을 수 있었음(배열이라 FK 를 못 검).
⚠️ `learning_sessions.mode` 는 **not null 이고 기본값이 없어** `speaking` 을 명시해야 했음.

계획이 실제로 실리는 것을 세션 전에 확인했음 — `GET /api/sessions/next-plan` 이 그 이유 문장을 냄.

---

## 2. 관측

| # | 관측 | ARM-EN | ARM-KO |
|---|---|---|---|
| 1 | `recv.voice_command` | **1** | **1** |
| 2 | `recv.final` | **4** | **3** |
| 3 | 명령 **앞** 코치 질문 | 계획 질문 1 (`What do you eat in the morning?`) | 같은 질문 1 (영어로) |
| 4 | 명령 **뒤** 코치 질문 | **계획 질문 2** (`Tell me one thing you need at work today — like email, idea, answer, or extra hour.`) | ⛔ **없음** |
| 5 | 명령 발화의 `utterance_type` | `voice_command` | `voice_command` |
| 6 | 화면 변화 | **없음**(스크린샷) | **없음**(스크린샷) |
| 7 | `recv.audio` | 207 | 130 (질문 1 의 것) |
| 8 | `recv.interrupted` | 1 | 1 |

⛔ **ARM-EN 의 4 가 이 회차의 핵심임** — 코치가 *"Okay, let's move to the next question."* 이라 말하고
**계획의 둘째 질문을 축자로** 냈음. 그 질문은 심은 계획의 두 번째 항목과 같음. 즉 명령이
`_DRILL_INSTRUCTION` 의 exchange 최소값을 **깨고** 다음 질문으로 넘겼음.

DB 집계(teardown 직전 · 검증 전용 DB): `learning_sessions` **3**(계획을 매단 것 1 + 회차 2) ·
`utterances` **7** · `voice_command` **2** · **`command_confirmation` 0**.
백엔드 로그: `표지가 없는 턴의 음성 명령…` warning **0건**.

---

## 3. 판정 — ARM-EN `PASS` · ARM-KO 는 **명령이 도착하지만 기능이 성립하지 않음**

- **영어는 계약대로 돌았음.** 결정 108 ③ 의 우선순위 문면이 실물 거동을 만들었고, 결정 108 ②
  (화면은 아무것도 하지 않음)도 지켜졌음.
- ⛔ **한국어는 tool 은 오고 기록도 남지만 코치가 다음 질문을 말하지 않았음.** `voice_command` 프레임
  1건과 `voice_command` 발화 1행이 있는데 그 뒤 `agent` 발화가 **0건**임(`recv.final` 이 3 에서 멈춤).
  이것은 **결정 106 이 그대로 두기로 한 「한국어 + tool 호출」 침묵의 재현**임 — 새 결함이 아님.

### ⛔ 이 회차가 새로 알아낸 것 — 결정 106 의 대가가 **명령마다 다름**

결정 106 을 정할 때 본 대가는 「한국어 종료는 확인 안내를 듣지 못해 쓰기 어렵다」 하나였음.
이 회차와 앞 회차(`task61-6`)를 나란히 놓으면 그 대가의 크기가 **명령을 누가 수행하는가**로 갈림:

| 명령 | 수행 주체 | 한국어에서 | 근거 회차 |
|---|---|---|---|
| 주간 리포트 보기 | **화면** | **성립함** — 코치가 침묵해도 패널이 뜸 | `runs/2026-09-15-task61-6-report-command` |
| 다음 문제 | **코치** | ⛔ **성립하지 않음** — 말하지 않으면 아무 일도 일어나지 않음 | 이 회차 ARM-KO |
| 종료 | 코치(확인) | 쓰기 어려움 | 결정 106 |

⇒ **남은 명령의 한국어 가용성은 「수행 주체가 화면인가 코치인가」로 미리 판정할 수 있음.**
그 판단이 `TASK-61.5`(결정 106 파킹)의 값어치를 바꿈 — 화면이 수행하는 명령만 열면 그 결함을
피할 수 있고, 코치가 수행하는 명령을 열려면 그 결함을 먼저 닫아야 함.

⚠️ **표본을 늘려 비율을 말하지 않음.** 이 관측은 결정 106 의 0/4 에 한 건을 더한 것이고,
조건(「한국어 + tool 호출」)이 같으므로 **재현으로 읽는 것까지가 정확함.**

---

## 4. teardown — 이 턴에 직접 돌린 출력

| 대상 | 결과 |
|---|---|
| `:8012` · `:3001` · `:9333` | 전부 HTTP **000** |
| 검증 전용 DB | `dropdb ohmyenglish_t617` 성공 · 남은 DB 는 `ohmyenglish` · `ohmyenglish_smoke` · `ohmyenglish_test` |
| `/tmp` 사본 | `fe-t617` · `chrome-t617` · `t617_app.py` · `y*.aiff` 삭제 |
| 공유 dev DB | **읽기만 했음** — 회차 뒤 `schema_migrations` **22** · `learning_sessions` **17** · `session_plans` **6** 으로 기준선과 같음 |
| 리포에 남긴 것 | 픽스처 넷(`vc13`~`vc16`) · 이 회차 디렉터리 |
