# 회차 — `TASK-61.6`: 「주간 리포트 보기」가 실사용에서 도는가

세션 `ohmyenglish-65` · 2026-09-15 KST · 계약 정본 결정 107 · 구현 커밋 `b30bd77` ·
절차 정본 `tests/harness/browser_leg.md` · 드라이버 `tests/harness/p_app_path.py`

> 무엇을 재는가: 단위·통합 테스트가 확인한 것은 **어댑터가 tool 을 받으면 무엇을 하는가**이고,
> 이 회차가 재는 것은 **실물 Nova 가 그 tool 을 확인 없이 한 번 부르는가**와 **화면이 세션을 유지한 채
> 리포트를 그리는가**임. 둘째 것이 이 조각의 계약이라 회차 없이는 닫을 수 없음(결정 107 ②).

---

## 0. 상한과 해석 규칙 — 돌리기 전에 적음

### 스택

| 무엇 | 값 |
|---|---|
| DB | 검증 전용 `ohmyenglish_t616r`(`schema_migrations` **22**) · 주간 리포트 **1행**을 심었음(아래 §1) |
| 백엔드 | `:8012` · 래퍼 `/tmp/t616r_app.py`(CORS origin 만 `:3001` 로 돌림) · `VOICE_ADAPTER=nova` · `WORKER_ENABLED=false` |
| 프론트 | 사본 `/tmp/fe-t616r`(`:3001`) · 픽스처를 사본의 `public/harness/` 에 둠 |
| 브라우저 | 전용 Chrome `:9333`(**152.0.7977.83**) · fake media stream |
| 드라이버 | `p_app_path.py --port 9333 --url http://localhost:3001/ --wav <명령>,<학습> --next-wait-ms 6000 --settle-ms 25000` |
| 계측 | `instrument.js` sha256 `cbc19fb69a89eb7868420a9ea1b9245103518dfeaebddec29fcfea3ee19b55ac`(44,552 B) · 드라이버가 페이지 안에서 대조함 |
| 공유 자원 | 공유 dev DB · `:3000` · `:8002` · 다른 세션의 Chrome(`:9222`)을 건드리지 않았음 |

### 픽스처 — 이 회차에서 만들었음

macOS TTS 로 만들고 16kHz·모노로 변환했음. 생성 명령을 그대로 적음(다시 만들 수 있어야 함):

```bash
say -v Samantha -o /tmp/x.aiff "Oh My English, show my weekly report."   # vc09_report_en
say -v Samantha -o /tmp/x.aiff "I had a busy week at work."              # vc10_learning_en
say -v Yuna     -o /tmp/x.aiff "오 마이 잉글리시, 주간 리포트 보여줘."     # vc11_report_ko
say -v Yuna     -o /tmp/x.aiff "이번 주는 회사 일이 많았어요."             # vc12_learning_ko
afconvert -f WAVE -d LEI16@16000 -c 1 /tmp/x.aiff tests/harness/fixtures/voice/<id>.wav
```

### 팔 둘과 상한

| 팔 | 흘리는 픽스처 | 무엇을 재는가 |
|---|---|---|
| ARM-KO | `vc11_report_ko` → `vc12_learning_ko` | 한국어 명령이 tool 로 오고 **확인 없이** 화면이 리포트를 그리는가 · 세션이 유지되는가 |
| ARM-EN | `vc09_report_en` → `vc10_learning_en` | 같은 것을 영어로 (결정 105 의 표지 인식 회귀도 함께 관측함) |

상한: Nova **2세션**(팔 둘 · 예비 0) · Claude **0회**. 넘기지 않았음.

### 해석 규칙

| 결과 | 읽는 법 |
|---|---|
| `voice_command` 프레임이 **1건**만 오고 화면에 패널이 뜨고 세션이 안 닫힘 | AC#3 충족 |
| `voice_command` 가 2건 이상(`confirmed` 가 옴) | 모델이 확인 절차를 붙인 것 ⇒ 규칙 13 의 「without asking for confirmation」이 안 먹은 결함 후보 |
| tool 이 아예 안 옴 | 전사문을 먼저 읽어 **표지가 어떻게 전사됐는지** 가름(결정 105 의 대가) |
| 세션이 닫힘 | ⛔ 심각 — 되돌릴 수 있다는 전제가 무너진 것. 코드 결함 |
| 명령 뒤 학습 발화가 `command_confirmation` 으로 저장됨 | ⛔ 확인 절차를 타 버린 것 — 결정 107 ③ 위반 |

⚠️ 표본 1 로 비율을 말하지 않음. 각 팔이 답하는 것은 「한 번이라도 그렇게 되는가」임.

---

## 1. 쓴 것 — 상한을 넘기지 않았음

Nova **2세션**(`58ac4d9c` 한국어 · `a5ec264e` 영어) · Claude **0회** · 픽스처 넷 신설.

심은 리포트 1행: `week_start=2026-09-14`(월요일) · `timezone=Asia/Seoul` · `computed_at` 채움
(그래서 `analyzed=true` — 유도는 `services/weekly_report.py:463`) ·
`metrics`= 세션 4 · 오류 7 · 패턴 3종 + 상위 패턴 3건 · `insights` 2건.

---

## 2. 관측 — 두 팔 모두 계약대로 돌았음

| # | 관측 | ARM-KO | ARM-EN |
|---|---|---|---|
| 1 | `recv.voice_command` | **1** | **1** |
| 2 | `recv.session_ended`(종료 클릭 **전**) | **0** | **0** |
| 3 | 화면에 「주간 리포트」 패널 | **떴음** (스크린샷) | **떴음** (스크린샷) |
| 4 | 패널이 그린 값 | `학습 4회 · 오류 7건 · 패턴 3종` + 상위 패턴 3건 | 같음 |
| 5 | 학습자 명령 발화의 `utterance_type` | `voice_command` | `voice_command` |
| 6 | 명령 **뒤** 학습 발화의 유형 | **`learning`** | **`learning`** |
| 7 | 코치 발화(`recv.audio`) | **88** | **51** |
| 8 | 표지 전사 | `오마이잉글리시` | **`oh my english`** |
| 9 | `recv.final` | 3 (user 2 + agent 1) | 3 |

전사문과 코치 발화(DB 원문):

- ARM-KO: `오마이잉글리시 주간 리포트 보여줘` → `이번 주는 회사 일이 많았어요` →
  코치 `이번 주는 회사 일이 많았어요. 그럼, 어떤 일이 많았나요? …`
- ARM-EN: `oh my english, show my weekly report.` → `i had a busy week at work.` →
  코치 **`Here is your weekly report.`** + `Tell me about your week at work. What did you do?`

DB 집계(teardown 직전 · 검증 전용 DB): `learning_sessions` **2** · `utterances` **6** ·
`voice_command` **2** · **`command_confirmation` 0** · `learning` **4**.

백엔드 로그: `표지가 없는 턴의 음성 명령…` warning **0건** · `확인을 거쳐 … 닫는다` **0건**.

---

## 3. 판정 — `PASS`. AC#3 을 닫음

- **확인 절차를 타지 않는 것이 관측됐음**: `voice_command` 가 팔마다 **1건**뿐이고
  `command_confirmation` 행이 **0건**임. 그리고 명령 뒤 학습 발화가 **`learning`** 으로 남았음 —
  종료 명령이라면 그 자리가 `command_confirmation` 이 됐을 것이고, 그것이 이 단정의 판별력임
  (통합 테스트 `test_a_report_command_runs_at_once_and_keeps_the_session_open` 과 같은 형태).
- **세션이 유지됐음**: 종료 클릭 전 `session_ended` 가 0 이고 화면에 「학습 종료」 버튼과 대화가
  그대로 있음(스크린샷). 결정 107 ②의 전제가 실물에서 성립함.
- **화면이 데이터를 그렸음**: 심은 리포트의 세 수와 상위 패턴 3건이 패널에 그대로 나왔음.
- **영어 코치가 규칙 13 의 문면대로 말했음**: `Here is your weekly report.` 는 그 규칙이 예시로 준
  문장임 — 지시문이 실물 거동을 만든 것이 관측됐음.

⚠️ **결정 106 의 대가를 이 명령이 지지 않는다는 것도 관측됐음.** 한국어 팔에서 코치는 명령에 대한
답을 따로 하지 않았지만(응답은 학습 발화에 대한 것임) **패널은 떴음.** 확인 발화가 필요 없으므로
학습자가 무엇을 듣지 못해도 기능이 성립함 — 결정 107 이 예측한 그대로임.

---

## 4. 알게 된 것 — 다음 회차가 다시 잃지 않게 적음

1. ⛔ **`node_modules` 를 심볼릭 링크로 이은 프론트 사본은 Next 16 이 거부함.**
   실측 오류: `Symlink [project]/node_modules is invalid, it points out of the filesystem root`
   이고 `:3001` 이 HTTP **000** 이었음. **하드링크 복사(`cp -Rl`)가 답이고 436 MB 를 6.5초에 옮겼음.**
   ⚠️ 하드링크라 사본의 파일을 고치면 원본도 바뀜 — `node_modules` 를 고치지 않는 한 안전하고
   `.next` 는 사본에 따로 생김.
2. ⚠️ **`--next-wait-ms 6000` 은 둘째 픽스처를 「코치 턴 전」에 흘림.** 두 발화가 화면에서 한 줄로
   병합됐지만(`page.tsx` 의 I-8 병합) **DB 는 두 행으로 갈렸음.** 즉 화면 병합과 저장은 다른 층이고,
   유형 판정은 저장 층에서 봐야 함. ⛔ **그 대신 「명령 턴 하나에 코치가 소리로 답하는가」는 이
   조합으로 가를 수 없음** — 그것을 재려면 명령 픽스처 **하나만** 흘리는 팔이 필요함.
3. ⚠️ **영어 표지가 이번엔 `oh my english` 로 정확히 전사됐음.** 결정 105 가 적은 것은
   「6회 중 1회」였음. ⛔ **그 비율을 이 관측으로 갱신하지 않음** — 표본이 다르고(문장이 다름)
   한 번의 성공은 비율이 아님. 대가의 크기를 세는 자리는 그대로 앱의 warning 건수임(이번 회차 0건).
4. **공유 dev DB 는 손대지 않았음**: 회차 뒤 `schema_migrations` **22** · `learning_sessions` **17**
   로 handoff 의 기준선과 같음.

---

## 5. teardown — 이 턴에 직접 돌린 출력

| 대상 | 결과 |
|---|---|
| `:8012` · `:3001` · `:9333` | 전부 HTTP **000** |
| 검증 전용 DB | `dropdb ohmyenglish_t616r` 성공 · 남은 DB 는 `ohmyenglish` · `ohmyenglish_smoke` · `ohmyenglish_test` |
| `/tmp` 사본 | `fe-t616r` · `chrome-t616r` · `t616r_app.py` · `x*.aiff` 삭제 확인(`No such file or directory`) |
| 리포에 남긴 것 | 픽스처 넷(`tests/harness/fixtures/voice/vc09~vc12`) · 이 회차 디렉터리 |
