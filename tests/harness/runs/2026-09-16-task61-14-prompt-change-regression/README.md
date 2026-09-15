# 회차 — `TASK-61.14`: 문면 변경(`9048522`) 뒤 나머지 음성 명령 셋이 그대로 성립하는가

세션 `ohmyenglish-42` · 2026-09-16 KST · 기준선 커밋 `b93d49f`(코드 변경 0건) ·
절차 정본 `tests/harness/browser_leg.md` · 드라이버 `tests/harness/p_app_path.py`

> 무엇을 재는가: `TASK-61.12` 의 고침이 규칙 13 의 근거절을 「추측하지 마라 + **답할 때까지 tool 을
> 부르지 마라**」로 바꿨음. 그 문장은 `start_additional` 자리에 쓴 것이지만 **지시문은 네 명령이
> 공유함** ⇒ tool 호출을 넓게 억제했는지 실물로 확인함. `TASK-61.13` 이 관측한 정지(`requested` 에서
> 멈춤)가 그 억제의 한 모양일 수 있다는 것이 이 회차를 연 이유임.
>
> **대조 기준은 앞 회차 셋임** — `runs/2026-09-15-task61-6-report-command` ·
> `runs/2026-09-15-task61-7-next-question` · `runs/2026-09-15-task61-3-voice-command-app-leg`.

⚠️ `harness_runs` 회차를 열지 않았음 — 검증 전용 DB 를 통째로 `drop` 하므로 `browser_leg.md` §3 의
목적이 성립하지 않음. 공유 dev DB 는 **읽기만** 했음(§4).

---

## 0. 스택과 상한

| 무엇 | 값 |
|---|---|
| DB | 검증 전용 `ohmyenglish_t6114`(`schema_migrations` **22** · `users` 1) · 아래 「심은 것」 참조 |
| 백엔드 | `:8012` · 래퍼 `/tmp/t6114_app.py`(CORS `:3001` + 제어 이벤트 계측) · `VOICE_ADAPTER=nova` · `WORKER_ENABLED=false` |
| 프론트 | 사본 `/tmp/fe-t6114`(`:3001`) · `node_modules` 하드링크 복사(`H-BU`) · 픽스처 66건 |
| 브라우저 | 전용 Chrome `:9333`(**152.0.7977.83**) · fake media stream |
| 상한 | Nova **10세션**(팔 10개 · 갈린 팔 0) · Claude **0회** |

### 심은 것 — ⛔ 앞 회차와 조건을 맞추기 위한 것임

앞 회차 둘은 **데이터를 심고** 돌렸다(리포트 1행 · 계획 1행). 처음 6팔은 심지 않고 돌렸으므로
**패널이 그린 값**과 **계획 질문 2**를 대조할 수 없었고, 그래서 심은 뒤 세 팔을 다시 돌렸다.
⛔ **대조 기준을 결과에 맞춰 고치지 않고 조건을 맞추는 쪽을 골랐다.**

- **주간 리포트 1행**: `week_start` = `date_trunc('week', (now() at time zone 'Asia/Seoul'))::date`
  = **2026-09-14**(월요일) · `timezone='Asia/Seoul'` · `computed_at` 채움 ·
  `metrics` = 세션 4 · 오류 7 · 패턴 3종 + 상위 패턴 3건 · `insights` 2건.
  ⚠️ 달력 날짜를 `current_date` 로 구하지 않고 **사용자 타임존으로 변환해** 구했다(전역 DB 규약).
- **계획 1행**: 공유 dev DB 의 최신 `session_plans` 한 행을 **읽어서** 옮겼음(`target_level` A2 ·
  질문 5개 · `focus` 2개). ⚠️ **앞 회차가 쓴 것과 같은 행임** — 질문 1이
  `What do you eat in the morning?` · 질문 2가 `Tell me one thing you need at work today …` 로
  `task61-7` README 의 값과 글자 그대로 같다. 그래서 대조가 성립한다.
  매달 자리로 `learning_sessions` 더미 1행(`speaking`·`completed`)을 만들었다 —
  `_PREPARED_PLAN_SQL` 이 세션을 조인하므로 필요하다.

새 픽스처는 만들지 않았음 — `vc01`~`vc04` · `vc09`~`vc16` 을 그대로 씀.

---

## 1. 팔 10개

| # | 팔 | 픽스처 | 심은 것 | 제어 이벤트 | `voice_command` 프레임 |
|--:|---|---|---|---|---|
| 1 | `report-en` | `vc09`,`vc10` | 없음 | `show_report/requested` | **1** |
| 2 | `report-ko` | `vc11`,`vc12` | 없음 | `show_report/requested` | **1** |
| 3 | `next-en` | `vc13`,`vc14` | 없음 | `next_question/requested` | **1** |
| 4 | `next-ko` | `vc15`,`vc16` | 없음 | `next_question/requested` | **1** |
| 5 | `end-en` | `vc01`,`vc02` | 없음 | `end/requested` → `end/confirmed` | **0** — ⛔ 표지 없음으로 앱이 버림 |
| 6 | `end-ko` | `vc03`,`vc04` | 없음 | `end/requested` → `end/confirmed` | **2** |
| 7 | `report-en-seeded` | `vc09`,`vc10` | 리포트 | `show_report/requested` | **1** |
| 8 | `next-en-seeded` | `vc13`,`vc14` | 계획 | `next_question/requested` | **1** |
| 9 | `next-ko-seeded` | `vc15`,`vc16` | 계획 | `next_question/requested` | **1** |
| 10 | `end-en-2` | `vc01`,`vc02` | — | `end/requested` → `end/confirmed` | **2** |

제어 이벤트 **13건**(`control-events.log` · 줄마다 ISO 시각). 발화 유형 집계:
`voice_command` **9** · `command_confirmation` **2** · `learning` **46**.
⚠️ 명령 발화가 10건이 아니라 **9건**인 이유는 팔 5의 표지가 인식되지 않아 그 발화가 `learning` 으로
저장됐기 때문임(§3-①).

---

## 2. 앞 회차와의 대조

| 명령 | 앞 회차가 관측한 것 | 이 회차 | 판정 |
|---|---|---|---|
| `show_report` | `voice_command` **1**(EN·KO) · 종료 클릭 전 `session_ended` **0** · 화면에 「주간 리포트」 패널 · 값 `학습 4회 · 오류 7건 · 패턴 3종` + 상위 3건 · 명령 뒤 학습 발화는 `learning` | **같음** — 팔 1·2·7 에서 프레임 1건 · `session_ended` 0 · 팔 7 스크린샷에 패널과 **같은 값 셋**(`a report 3회` · `an hour 2회` · `went 2회`) | 무회귀 |
| `next_question` | `voice_command` **1**(EN·KO) · **영어 팔**은 명령 뒤 계획 질문 2 · 한국어 팔은 ⛔ 없음 · 화면 변화 없음 | 팔 8(영어)이 계획 질문 1 → **계획 질문 2** 로 앞 회차와 글자 그대로 같은 이동 · 팔 9(한국어)도 **계획 질문 2** 가 났음 | 무회귀 (한국어는 §3-③) |
| `end` | 확인 뒤 세션 종료 | 팔 6·10 에서 `requested` → `confirmed` → 종료 클릭 **전** `session_ended` **1** | 무회귀 |

⇒ **문면 변경이 tool 호출을 억제하지 않았음.** 10팔 전부에서 모델이 그 명령의 tool 을 불렀고
(제어 이벤트 13건), 앱까지 도착하지 못한 것은 **한 팔**뿐이며 그 원인은 문면이 아니라 표지 ASR 임.

---

## 3. 판정 — `PASS`(무회귀). ⚠️ 부수 관측 셋을 함께 남김

### ① 영어 표지의 ASR 이 여전히 불안정함 — 2회 중 1회

같은 픽스처(`vc01_cmd_en`)가 팔 5 에서 `all my english and the session.` · 팔 10 에서
`oh my english and the session.` 로 전사됐음. 앞 것은 표지가 없어 앱이 명령을 버렸음
(백엔드 warning **2건** · `session.py:418` 의 결정 104(D5) 게이트). ⇒ **결정 105 의 대가가 그대로임.**

### ② ⛔ 새 결함 — 버려진 명령 뒤에 코치가 지시문과 내부 추론을 소리로 냈음 (팔 5)

팔 5 에서 코치가 학습자에게 이렇게 말했음(전사문 원문 · `end-en.json` 의 `walk.lines`):

```
Okay, the session has been ended as requested. … and I confirmed by calling the end command
with stage "confirmed." … Wait, but the tool call was already made, and the app closes the
session. The instruction says: "The app closes the session only on 'confirmed', so never skip
that second call." … But looking back, the tool call was made, and now the tool_ results show …
```

즉 **지시문 문장이 그대로 학습자에게 읽혔고**, 세션은 닫히지 않았는데 「종료됐다」고 말했음
(그 팔 `recv.session_ended` 는 종료 클릭 전까지 **0**, `audio` **1189** · `final` **20**).

**기전은 코드로 확인했음(추측이 아님)**: 「받았다」를 보내는 자리와 「실행한다」를 판정하는 자리가
**다른 층**임.

| 층 | 하는 일 | 자리 |
|---|---|---|
| 어댑터 | 번역기가 이벤트를 만들면 `{"status":"accepted","command":…}` 를 Nova 로 돌려줌 | `audio_gateway/nova.py` `_flush_tool_results` |
| 앱 | 표지가 없는 턴이면 **실행하지 않고 버림** | `audio_gateway/session.py:418` |

⛔ **어댑터 자신의 주석이 이 위험을 이미 적어 뒀음** — *"모호한 페이로드에는 결과를 보내지 않는다 …
그때 「받았다」를 돌려주면 모델이 실행됐다고 믿는다"*(`nova.py` `_remember_tool_use` docstring).
그 방어는 **번역기가 버린 경로**만 덮고 **앱이 버린 경로**는 덮지 않음.
⇒ **`TASK-61.15` 로 등재했음.** ⚠️ 표본 1이므로 크기는 그 태스크가 잼.

⚠️ **이것이 `TASK-61.13` 과 같은 부류임** — 「코치의 말과 앱의 상태가 갈린다」의 **두 번째 원인**이고,
결정 112(고치는 자리는 앱)의 근거를 넓힘. 그 태스크 노트에 상호 참조를 남겼음.

### ③ `next_question` 한국어 팔이 앞 회차의 미성립을 재현하지 않았음 — 2/2 로 새 질문이 났음

앞 회차는 한국어 팔에서 명령 뒤 질문이 **없었음**. 이번에는 심지 않은 팔 4와 심은 팔 9 **둘 다**
새 질문이 났고 팔 9 는 **계획 질문 2** 였음.
⛔ **「고쳐졌다」로 적지 않음** — 이 회차와 앞 회차 사이에 문면 말고도 다른 것이 있고(모델
비결정성) 표본이 2임. 적을 수 있는 것은 **그 미성립이 이번에 재현되지 않았다**는 사실뿐임.

---

## 4. teardown — 이 턴에 직접 돌린 출력

| 대상 | 결과 |
|---|---|
| `:8012` · `:3001` · `:9333` | 전부 HTTP **000** |
| 검증 전용 DB | `dropdb ohmyenglish_t6114` 성공 · 남은 DB 는 `ohmyenglish` · `ohmyenglish_smoke` · `ohmyenglish_test` |
| `/tmp` 사본 | `fe-t6114` · `chrome-t6114` · `t6114_app.py` · 회차 로그 삭제 · 잔여 **0건** |
| 공유 dev DB | **읽기만 했음** — 회차 뒤 `learning_sessions` **17** · `schema_migrations` **22** · `session_plans` **6** · `weekly_reports` **0** 으로 기준선과 같음 |
| 리포에 남긴 것 | 이 디렉터리 — 관측 JSON 10 · `control-events.log` · `sessions.tsv` · `utterances.tsv` · 스크린샷 20 |
