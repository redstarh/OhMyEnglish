# 회차 — `TASK-61.8`: 「추가 학습」 명령이 세션을 갈아 여는가

세션 `ohmyenglish-65` · 2026-09-16 KST · 계약 정본 결정 **110** · 구현 커밋 `ab99533` ·
절차 정본 `tests/harness/browser_leg.md` · 드라이버 `tests/harness/p_app_path.py`

> 무엇을 재는가: 이 명령은 **지금 세션을 닫고 새 세션을 연다**. 단위·통합 테스트가 확인한 것은
> 「확인을 거쳐 세션이 닫히고 프레임에 `target` 이 실린다」까지이고, **새 세션이 그 `target` 대로
> 열리는지는 화면이 하는 일**이라 회차만 잴 수 있음(결정 110 ③).

---

## 0. 스택과 상한

| 무엇 | 값 |
|---|---|
| DB | 검증 전용 `ohmyenglish_t620`(`schema_migrations` **22** · `shadowing_items` **1** 시드) · 계획을 심지 않음 |
| 백엔드 | `:8012` · 래퍼 `/tmp/t620_app.py`(CORS origin 만 `:3001`) · `VOICE_ADAPTER=nova` · `WORKER_ENABLED=false` |
| 프론트 | 사본 `/tmp/fe-t620`(`:3001`) · `node_modules` 하드링크 복사(`H-BU`) |
| 브라우저 | 전용 Chrome `:9333`(152.0.7977.83) |
| 드라이버 | `--wav <학습>,<명령>,<확인>` · `--next-wait-ms 30000 --settle-ms 25000` |
| 상한 | Nova **4세션**(팔 둘 × 각 2 — 이 명령은 한 팔이 세션 둘을 만듦) · Claude **0회** |

⚠️ **한 팔이 세션 둘을 만들므로 계측의 `startedSessionId` 는 첫 세션만 잡음**(first-wins ·
드라이버 규약 「한 문서에 세션 하나」). ⇒ **둘째 세션은 DB 와 스크린샷으로 관측했음.**

### 픽스처 — 이 회차에서 만들었음

```bash
say -v Yuna     -o /tmp/z.aiff "오 마이 잉글리시, 쉐도잉 추가 학습."      # vc17_additional_ko
say -v Yuna     -o /tmp/z.aiff "네, 해 주세요."                          # vc18_yes_ko
say -v Samantha -o /tmp/z.aiff "Oh My English, start shadowing practice." # vc19_additional_en
say -v Samantha -o /tmp/z.aiff "Yes, please do."                          # vc20_yes_en
afconvert -f WAVE -d LEI16@16000 -c 1 /tmp/z.aiff tests/harness/fixtures/voice/<id>.wav
```

⚠️ 기존 확인 픽스처(`vc02`·`vc04`)를 쓰지 않았음 — 그 문면이 「종료해 주세요」라서 이 명령의 확인
답으로 쓰면 모델이 종료로 읽을 수 있음.

### 해석 규칙

| 결과 | 읽는 법 |
|---|---|
| 세션이 **둘** 열리고 둘째의 `learning_source='additional'` | AC#3 충족 — 명령이 새 세션의 진입을 정했음 |
| `target` 이 `mode` 로 반영됨(예: `shadowing`) | 인자 경로까지 성립 |
| 세션이 하나만 열림 | 화면이 결과 화면으로 갔거나 새 세션을 못 연 것 ⇒ 결함 |
| 확인 없이 닫힘 | ⛔ 심각 — `CONFIRMATION_REQUIRED` 가 무력화된 것 |

---

## 2. 관측 — 두 팔 모두 세션을 갈아 열었음

| # | 관측 | ARM-KO | ARM-EN |
|---|---|---|---|
| 1 | `recv.session_started` | **2** | **2** |
| 2 | `recv.voice_command` | **2**(requested·confirmed) | **2** |
| 3 | 종료 클릭 전 `recv.session_ended` | 1 (첫 세션) | 1 |
| 4 | 결과 화면 URL 의 세션 | **둘째** `fc36a4b6` | **둘째** `1c150a6c` |
| 5 | 둘째 세션의 `learning_source` | **`additional`** | **`additional`** |
| 6 | 둘째 세션의 `mode` | `speaking` (아래 ⚠️) | **`shadowing`** |
| 7 | 쉐도잉 클립 | — | **실렸음**(`shadowing_item_id` 채워짐) |
| 8 | 확인 발화 기록 | `command_confirmation` 1행 | 1행 |

**세션 표**(teardown 직전):

```
f06e1301 | completed | speaking  | recommended   ← ARM-KO 첫 세션
fc36a4b6 | completed | speaking  | additional    ← ARM-KO 새 세션
3b080788 | completed | speaking  | recommended   ← ARM-EN 첫 세션
1c150a6c | completed | shadowing | additional    ← ARM-EN 새 세션 (클립 있음)
```

**ARM-EN 의 발화 기록** — 확인 절차가 그대로 돌았음:

```
user  | learning             | i usually take the subway to work.
agent | learning             | Good! Let's talk about your work day. What time …
user  | voice_command        | oh my english! start shadowing practice.
agent | learning             | Sorry, I need your confirmation before I start. …
user  | command_confirmation | yes, please do.
```

DB 집계: `learning_sessions` **4** · `learning_source='additional'` **2** · `utterances` **10** ·
`voice_command` **2** · `command_confirmation` **2**.
백엔드 로그: `표지가 없는 턴의 음성 명령…` **0건** · `추가 학습 대상 … 알 수 없어` **0건**.

**화면**(`shot-en-session.png` — 직접 열어 확인했음): 「대화를 기다리는 중…」 상태에 **쉐도잉 패널**
(`A morning routine before work` + 본문 + 「클립 듣기」)이 떠 있고 「학습 종료」 버튼이 있음.
⇒ **결과 화면을 거치지 않고 쉐도잉 세션이 열렸음**(결정 110 ③).

---

## 3. 판정 — `PASS`. AC#3 을 닫음

- **세션을 갈아 여는 계약이 두 언어에서 성립했음**(2/2). 확인 절차·기록 유형·표지 요구가 모두
  첫 조각과 같게 돌았음.
- **`target` 이 새 세션의 진입을 정하는 것까지 관측됐음** — ARM-EN 에서 `mode='shadowing'` 과
  클립 적재가 함께 확인됐음. 이것이 인자 경로의 판별력임.

⚠️ **ARM-KO 에서 `target` 이 `conversation` 으로 떨어졌음 — 결함이 아니라 ASR 임.**
전사문이 `오마이잉글리시 최도인 추가학습` 이었음(「쉐도잉」 → 「최도인」). 모델은 값역 안에서
`conversation` 을 골랐고 앱은 그것을 그대로 반영했음(코치도 *"an additional conversation
practice"* 라 말했음). ⛔ **그래서 이 팔은 「명령이 새 세션을 연다」만 증명하고 「target 이
반영된다」는 증명하지 못함** — 뒤쪽은 ARM-EN 이 증명함. 결정 105 가 적은 대가와 같은 부류이고
크기를 세는 자리도 같음(warning 건수 · 이번 0건).

⚠️ **프론트의 경합 방어는 이 회차가 «간접으로만» 확인했음.** 새 세션이 살아남아 정상 종료됐으므로
이전 소켓의 close 가 새 세션을 죽이지 않았다는 것은 성립하나, 그 방어를 **무력화해 실패를 본 것은
아님.** ⛔ 그래서 「판별력 관측」이 아니라 「거동 관측」으로 적음.

---

## 4. teardown — 이 턴에 직접 돌린 출력

| 대상 | 결과 |
|---|---|
| `:8012` · `:3001` · `:9333` | 전부 HTTP **000** |
| 검증 전용 DB | `dropdb ohmyenglish_t620` 성공 · 남은 DB 는 `ohmyenglish` · `ohmyenglish_test` · `ohmyenglish_smoke` |
| `/tmp` 사본 | `fe-t620` · `chrome-t620` · `t620_app.py` · `z*.aiff` 삭제 |
| 공유 dev DB | 손대지 않았음 — `schema_migrations` **22** 로 기준선과 같음 |
| 리포에 남긴 것 | 픽스처 넷(`vc17`~`vc20`) · 이 회차 디렉터리 |
