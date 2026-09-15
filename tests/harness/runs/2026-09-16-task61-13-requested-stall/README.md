# 회차 — `TASK-61.13`: 종류를 답한 뒤 `confirmed` 까지 가는 비율

세션 `ohmyenglish-42` · 2026-09-16 KST · 기준선 커밋 `b93d49f` · 코드 변경 0건 ·
절차 정본 `tests/harness/browser_leg.md` · 드라이버 `tests/harness/p_app_path.py`

> 무엇을 재는가: `TASK-61.13` AC#1 임. 앞 회차(`runs/2026-09-16-task61-12-unspecified-mode` §3)가
> **1회** 관측한 모양 — 코치가 「we will do pronunciation practice … Repeat after me」라 말했는데
> 제어 이벤트의 stage 가 `requested` 에 머물러 앱이 세션을 갈지 않은 것 — 의 크기를 센다.
> ⛔ **이 회차는 측정만 함.** 앞 회차가 다음 회차의 findings 를 만드는 사슬이 두 번 이어졌으므로
> (`61.10` → `61.12` → `61.13`) 라운드를 더 돌지 않고 크기만 재고 멈추는 것이 이 회차의 규율임.

⚠️ `harness_runs` 회차를 열지 않았음 — 검증 전용 DB 를 통째로 `drop` 하므로 `browser_leg.md` §3 의
목적(공유 DB 에서 삭제 범위를 좁히는 것)이 성립하지 않음. 공유 dev DB 는 손대지 않았음(§4).

---

## 0. 스택과 상한

| 무엇 | 값 |
|---|---|
| DB | 검증 전용 `ohmyenglish_t6113`(`schema_migrations` **22** · `users` 1 — 마이그레이션 시드) · 계획을 심지 않음 |
| 백엔드 | `:8012` · 래퍼 `/tmp/t6113_app.py`(CORS `:3001` + 제어 이벤트 계측) · `VOICE_ADAPTER=nova` · `WORKER_ENABLED=false` |
| 프론트 | 사본 `/tmp/fe-t6113`(`:3001`) · `node_modules` 하드링크 복사 **6.198초**(`H-BU`) · 픽스처 66건을 사본의 `public/harness/` 에 둠 |
| 브라우저 | 전용 Chrome `:9333`(**152.0.7977.83**) · fake media stream |
| 드라이버 | `--wav <학습>,<모드요청>,<종류답변>[,<예>] --next-wait-ms 30000 --quiet-ms 1200 --settle-ms 25000 --settle-timeout-ms 240000 --walk-timeout-ms 60000` |
| 상한 | Nova **9세션**(팔 6개 · 갈린 팔은 세션 2개) · Claude **0회** |

**계측 하나를 앞 회차에서 이어받고 한 줄을 더했음** — 래퍼가 `NovaEventTranslator.translate` 를 감싸
제어 이벤트의 `command`·`stage`·`target`·`heard` 와 원본 `toolUse` 페이로드를 남김. 더한 것은
**줄마다 ISO 시각**임. 앞 회차는 한 파일에 여러 팔이 순서로 쌓여 **팔 귀속을 순서로 추정**해야 했고,
이번에는 시각으로 가름(아래 표의 시각이 `control-events.log` 의 값임).

⛔ **`recv.voice_command` 로 판정하지 않음** — 그것은 프레임 수이고 어느 명령·어느 stage 인지
구별하지 못함(앞 회차가 이 유도를 정정한 자리).

### 픽스처 — 새로 만든 것 0건

전부 기존 것을 씀: `vc13_learning_en` · `vc15_learning_ko` · `vc23_modeonly_en` · `vc24_modeonly_ko` ·
`vc25_kind_en` · `vc26_kind_ko` · `vc18_yes_ko`.

---

## 1. 팔 6개 — 넷은 「학습 → 종류를 말하지 않은 모드 요청 → 종류 답변」, 둘은 그 뒤에 「예」를 더함

| 팔 | 픽스처 | 왜 넣었나 |
|---|---|---|
| `a1-en` · `a2-en` | `vc13`,`vc23`,`vc25` | 앞 회차 `answer-en`(성립)의 표본을 늘림 |
| `a3-ko` · `a4-ko` | `vc15`,`vc24`,`vc26` | 앞 회차 `answer-ko`(정지)의 표본을 늘림 |
| `a5-ko-yes` · `a6-ko-yes` | `vc15`,`vc24`,`vc26`,`vc18` | 정지가 **학습자의 명시적 「예」로 풀리는가** |

⚠️ **`a6-ko-yes` 는 넷째 픽스처가 흐르지 않았음** — 종류 답변에서 세션이 갈려 그 자리에서 끝났음
(`plays` 의 index 는 0·1·2 와 새 세션의 0 재생). 즉 **입력은 `a3`·`a4` 와 같은 세 발화임.**
넷째가 실제로 흐른 팔은 `a5-ko-yes` 하나임(`plays` 4건 · `speech_start` 4).

---

## 2. 관측

### 2-1. 팔별 — 제어 이벤트와 세션이 갈렸는지

| 팔 | 코치의 응답 모양 | 제어 이벤트(UTC) | `session_started` | 세션 |
|---|---|---|---|---|
| `a1-en` | 종류를 **되물었음** | `22:41:03` requested/conversation → `22:41:13` **confirmed/pronunciation** | **2** | `7f2c8dd1`(speaking) → `57b30681`(**pronunciation·additional**) |
| `a2-en` | 되물었음 | `22:42:03` requested/conversation → `22:42:12` requested/pronunciation → `22:42:13` **confirmed/pronunciation** | **2** | `d341fb20` → `cee8a737`(**pronunciation·additional**) |
| `a3-ko` | 스스로 `conversation` 을 골라 **예고했음** | `22:43:01` requested/conversation → `22:43:09` requested/pronunciation | **1** | `914800f7` 하나 |
| `a4-ko` | 예고했음 | `22:44:00` requested/conversation → `22:44:07` requested/pronunciation | **1** | `c49a88a6` 하나 |
| `a5-ko-yes` | 예고했음 | `22:45:08` requested/conversation → `22:45:15` requested/pronunciation | **1** | `b122bae3` 하나 |
| `a6-ko-yes` | 되물었음 | `22:46:13` requested/conversation → `22:46:20` **confirmed/pronunciation** | **2** | `a8a0ad81` → `a69c9121`(**pronunciation·additional**) |

제어 이벤트 **13건** 전부 `command='start_additional'` 임 · 백엔드 warning 은 둘 다 **0건**
(`표지가 없는 턴의 음성 명령…` · `추가 학습 대상 … 알 수 없어`).

### 2-2. 크기 — AC#1 이 물은 비율

| 모집단 | `confirmed` 도달 |
|---|---|
| 이 회차 6팔 | **3 / 6** |
| 앞 회차의 같은 모양 2팔(`answer-en` 성립 · `answer-ko` 정지)을 합친 8팔 | **4 / 8** |

⛔ **표본 8이고 비율을 기전으로 단정하지 않음.**

### 2-3. 무엇이 성립과 정지를 가르는가 — 되물었는가

| 코치의 응답 모양 | 팔 | `confirmed` |
|---|---|---|
| 종류를 되묻거나 질문으로 물음 | `a1` · `a2` · `a6` · 앞 회차 `answer-en` | **4 / 4** |
| 종류를 스스로 골라 예고함 | `a3` · `a4` · `a5` · 앞 회차 `answer-ko` | **0 / 4** |

⚠️ **언어와 엉켜 있음** — 예고한 4팔이 전부 한국어 표지 팔임. 다만 **`a6` 가 한국어인데 되묻고
성립했으므로 언어 단독으로는 설명되지 않음.** 반대 짝(영어 표지 팔이 예고하는 경우)은
두 회차 5팔에서 한 번도 나오지 않아 **관측이 그것을 배제하지 못함.**

### 2-4. 정지가 명시적 「예」로 풀리는가 — 아니오 (1/1)

`a5-ko-yes` 에서 학습자가 「네 해주세요.」를 말한 뒤에도 **`confirmed` 는 0건**이고 세션이 갈리지
않았음. 코치는 그 「예」를 확인으로 받지 않고 **다음 연습 문장으로 넘어갔음**:

```
agent  Okay, we will do pronunciation practice. … Please repeat after me: "I go to work by subway every day".
user   네 해주세요.
agent  Let us practice this sentence: "I need to finish the report today". Say this sentence after me, please.
```

⚠️ **표본 1임** — 넷째 발화가 실제로 흐른 팔이 하나뿐임(§1).

### 2-5. 그 정지가 무엇을 남기는가 — 발음 드릴이 `speaking` 세션에 남음

`shot-a5-ko-yes-session.png`(직접 열어 봤음): 화면은 **처음 세션의 전사문 그대로**이고 그 안에서
발음 드릴 두 턴이 진행됨. **모드가 바뀌지 않았다는 표시가 화면에 없음** — 학습자에게는 바뀐 것처럼
보이고 들림.

`shot-a5-ko-yes-results.png`: 결과 화면에 「발음 — 관찰된 신호 · (전사문이 한국어로 인식되었습니다)」
가 뜸. 즉 그 드릴의 기록이 **`speaking`·`recommended` 세션에 남았음.**

⚠️ **`pronunciation_attempts` 4행을 이 정지의 결과로 단정하지 않음** — 4행은 **한국어 팔 4개에
각각 1행**이고 드릴이 없었던 `a6` 의 첫 세션에도 있음. `target_form` 이 전부
`KOREAN_TRANSCRIPT_TARGET_FORM`(`services/pronunciation.py:120`) 자리표시자이므로 **한국어 전사에
대한 앱의 의도된 처리**이고 이 회차의 변수와 무관함.

---

## 3. 판정 — AC#1 을 닫음. AC#2·#3 은 열어 둠

- **AC#1(크기)**: 닫음. **4 / 8** 이 `confirmed` 까지 감. 이 회차만으로는 3 / 6.
- **AC#2(고치는 자리)**: ⛔ **닫지 않음 — 설계 판단이고 이 세션의 몫이 아님.** 관측이 가리키는 것만
  적음: ⑴ 정지는 문면을 지키지 않아서가 아니라 **코치가 종류를 스스로 골라 예고한 팔에서만** 났음
  (2-3) ⑵ 그 팔에서는 학습자의 명시적 「예」도 상태를 옮기지 못했음(2-4) ⑶ 앱 쪽에는 그 어긋남을
  드러내는 표면이 없음(2-5). ⚠️ **문면을 더 세게 하는 쪽이 이 셋을 닫는다는 근거는 이 회차에 없음** —
  앞 회차가 문면을 고쳐 되묻기를 0/4 → 3/5 로 옮겼고 그 뒤에도 이 모양이 4팔에서 났음.
- **AC#3(고친 뒤 관측)**: 미착수 — 고침이 없음.

⛔ **다음 라운드를 이 세션에서 돌리지 않음.** handoff 가 걸어 둔 조건대로, 회차가 새 findings 를
만들면 라운드가 아니라 게이트를 바꾸는 자리임. 새 findings 는 2-4 하나임(명시적 「예」가 정지를 풀지
못함) — 그것을 별도 태스크로 쪼개지 않고 `TASK-61.13` AC#2 의 재료로 이 기록에 둠.

---

## 4. teardown — 이 턴에 직접 돌린 출력

| 대상 | 결과 |
|---|---|
| `:8012` · `:3001` · `:9333` | 전부 HTTP **000** |
| 검증 전용 DB | `dropdb ohmyenglish_t6113` 성공 · 남은 DB 는 `ohmyenglish` · `ohmyenglish_smoke` · `ohmyenglish_test` |
| `/tmp` 사본 | `fe-t6113` · `chrome-t6113` · `t6113_app.py` · 회차 로그 삭제 |
| 공유 dev DB | 손대지 않았음 — 회차 전후로 `learning_sessions` **17** · `schema_migrations` **22** 로 같음 |
| 리포에 남긴 것 | 이 디렉터리 — 관측 JSON 6 · `control-events.log` · `sessions.tsv` · `utterances.tsv` · `pronunciation-attempts.tsv` · 스크린샷 12 |
