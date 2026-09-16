# 회차 — `TASK-61.16`·`61.17`: 갈림을 화면이 말하는가, 새 표지가 성립하는가

세션 `ohmyenglish-42` · 2026-09-16 KST · 구현 커밋 `aeb7df2`(표면) · `32d73b3`(표지) ·
절차 정본 `tests/harness/browser_leg.md` · 드라이버 `tests/harness/p_app_path.py`

> 무엇을 재는가 셋: ① 표지가 없어 버린 명령을 화면이 말하는가(결정 113) ② 확인 대기를 화면이
> 말하는가 ③ 새 표지(「헤이」·「헬로」)로 명령이 성립하는가(결정 114). 그리고 결정 114 가 알고 받은
> **대가(학습 발화가 표지를 얻는 오탐)**를 함께 센다.
>
> ⛔ **이 회차가 닫는 것은 넷이다** — `TASK-61.16` AC#5 · `TASK-61.13` AC#3 · `TASK-61.15` AC#4 ·
> `TASK-61.17` AC#4. 세 태스크의 「고치면 관측한다」가 같은 표면을 가리키므로 한 회차로 닫는다.

---

## 0. 스택과 상한

| 무엇 | 값 |
|---|---|
| DB | 검증 전용 `ohmyenglish_t6116`(`schema_migrations` **22**) · 계획·리포트를 심지 않음 |
| 백엔드 | `:8012` · 래퍼 `/tmp/t6116_app.py` · `VOICE_ADAPTER=nova` · `WORKER_ENABLED=false` |
| 프론트 | 사본 `/tmp/fe-t6116`(`:3001`) · **고친 프론트 코드가 들어간 사본**임 |
| 브라우저 | 전용 Chrome `:9333`(**152.0.7977.83**) |
| 상한 | Nova **9세션**(팔 9개 · 갈린 팔 1) · Claude **0회** |

⚠️ **중간에 백엔드를 한 번 재기동했음** — 회차 중에 `해이` 표기를 값역에 더했고(§3-①) `--reload` 가
없어 재기동하지 않으면 낡은 지시문·코드를 잰다. 재기동 뒤 `pid 94207` 로 health 200 을 확인했음.

### 픽스처 넷을 새로 만들었음

```bash
say -v Samantha "Hey, end the session."                    # vc33_hey_end_en
say -v Yuna     "헤이, 발음 연습 모드로 바꿔 줘."           # vc34_hey_mode_ko
say -v Samantha "Hello, my name is Jin and I work at a bank."  # vc35_hello_learning_en (오탐 측정용)
say -v Yuna     "헤이, 학습 종료해 줘."                     # vc36_hey_end_ko
afconvert -f WAVE -d LEI16@16000 -c 1 …
```

---

## 1. 관측 — 팔 아홉

| 팔 | 무엇을 밟나 | 제어 이벤트 | warning | 화면 |
|---|---|---|---|---|
| `s1-ignored-end-en` | 표지 없는 `end` | **0건**(모델이 tool 을 안 불렀음) | 0 | 알림 없음 — 조건이 안 만들어짐 |
| `s2-ignored-report-en` | 표지 없는 `show_report` | `show_report/requested` | **1** | ✅ **「리포트 요청을 알아듣지 못했어요…」** |
| `s3-nextq-silent-en` | 표지 없는 `next_question` | `next_question/requested` | **1** | ✅ **알림 없음**(설계대로) |
| `s4-hey-end-en` | 새 영어 표지 | 0건(모델이 확인 질문에서 멈춤) | 0 | 발화가 **`voice_command`** 로 저장됨 ⇒ 표지 인식됨 |
| `s5-hey-mode-ko` | 새 한국어 표지 | `requested`→`confirmed` | **2** | ✅ **「연습 변경을 알아듣지 못해…」** (§3-① 의 발견) |
| `s5b-heyfix-mode-ko` | 같은 팔을 고친 뒤 | `requested`→`confirmed` | **0** | 세션이 **갈렸음**(`pronunciation`·`additional`) |
| `s6-hello-learning-en` | 「Hello, my name is Jin…」 | 0건 | 0 | ⚠️ 발화가 **`voice_command`** 로 저장됨(오탐 1/1) |
| `s7-ignored-end-yes-en` | 표지 없는 `end` + 「예」 | `end/confirmed` | **1** | ✅ **「학습 종료를 알아듣지 못해…」** |
| `s8-pending-end-ko` | 표지 있는 `end` · 확인 없음 | `end/requested` | 0 | ✅ **「학습 종료를 확인하고 있어요… 아직 종료되지 않았어요.」** |

제어 이벤트 **8건** · 표지없음 warning **5건** · 발화 유형 `learning` 40 · `voice_command` 4 ·
`command_confirmation` 1.

### 1-1. 표면이 실제로 갈림을 덮었는가 — 스크린샷을 직접 열어 봤음

| 팔 | 코치가 소리로 한 말 | 같은 순간 화면 |
|---|---|---|
| `s7` | *"Okay, the session has ended. Thank you for talking with me today!"* | 「학습 종료를 알아듣지 못해 세션을 그대로 두었어요」 |
| `s5` | *"Great! Now we are in pronunciation practice mode. … repeat after me"* | 「연습 변경을 알아듣지 못해 지금 세션을 그대로 두었어요」 |
| `s2` | *"Here is your weekly report."* | 「리포트 요청을 알아듣지 못했어요」 |
| `s8` | *"Do you want to end today's session?"* | 「…「네」라고 답하면 종료해요 — 아직 종료되지 않았어요」 |

⇒ **`TASK-61.13` 의 정지(4/8)와 `TASK-61.15` 의 거짓 완료(4/4)가 이제 학습자에게 보인다.**
⛔ **고친 것은 「코치가 틀리게 말하는 것」이 아니라 「학습자가 그것을 알 수 없던 것」이다** —
말과 상태가 갈리는 것 자체는 그대로다(결정 112 가 그렇게 정했다).

---

## 2. 새 표지 — 성립함. 단 한국어는 회차 중에 값역을 늘려야 했음

- **영어**: `s4` 에서 `hey, end the session.` 이 **`voice_command`** 로 저장됐음 ⇒ 앱이 표지로 읽었음.
  ⚠️ 그 팔에서 모델이 tool 을 부르지 않아 명령의 끝(세션 종료)까지는 이 팔이 답하지 않음.
- **한국어**: `s5b` 에서 `requested`→`confirmed` 를 거쳐 새 세션이 **`pronunciation`·`additional`** 로
  열렸음 ⇒ 명령이 끝까지 성립했음.
- ⚠️ **앱 이름 표지를 깨지 않았음**은 단위 단정이 지킨다(`test_the_app_name_wake_phrase_still_works…`).

---

## 3. 회차가 찾은 것 둘

### ① ⛔ ASR 이 「헤이」를 **「해이」**로 적어 명령이 버려졌음 — 회차 중에 고쳤음

`s5-hey-mode-ko` 의 전사문이 `해이 발음 연습 모드로 바꿔줘` 였고 표지 검사가 어긋나 명령이
버려졌음(warning 2 · 세션이 갈리지 않음). ⇒ `_WAKE_FORMS` 에 `해이` 를 더하고 단정을 붙였음
(`잉글리시`·`잉글리쉬` 를 둘 다 받은 것과 같은 규약). 재기동 뒤 `s5b` 에서 warning **0** 이었음.
⛔ **관측하지 않은 표기를 추측으로 넣지 않았음** — 「헬로」계열의 한국어 전사는 아직 관측하지 못했음.

⚠️ **이 발견은 표면이 있어서 눈에 보였음** — 고치기 전이라면 warning 만 남고 화면은 침묵했으므로
회차가 「모드가 안 바뀌었다」를 코치의 말만 보고는 알 수 없었다.

### ② ⚠️ 결정 114 의 대가가 실물에서 확인됐음 — 오탐 **1/1**

`s6` 에서 `hello, my name is jin and i work at a bank.` 가 **`voice_command`** 로 저장됐음.
⇒ 그 발화는 **분석·교정에서 빠진다**(`learning` 만 분석 대상임). 코치는 그것을 학습 발화로 다뤘고
tool 을 부르지 않았으므로(제어 이벤트 0건) **아무 명령도 실행되지 않았음** — 즉 안전 쪽이지만
**학습 기록이 하나 사라진다.**
⛔ **표본 1이다.** 그리고 이 자리는 값역을 좁히는 제품 판단이라 이 회차가 정하지 않음 —
결정 114 를 다시 올려야 함(사용자 몫).

### ③ ⚠️ 코치가 지시문과 내부 추론을 소리로 읽는 것이 다시 났음 (`s5b` · `TASK-61.15` 의 그 모양)

`s5b` 의 agent 발화 다섯 줄이 자기 추론이었고 **내가 이번에 더한 규칙 12 문장을 인용**했음:
*"But according to rule 12, a greeting alone is not a command, but in t…"*. `audio` **1004** ·
`partial` **17** 로 그 팔만 유독 길었음.
⛔ **이 회차가 그것을 새 결함으로 등재하지 않음** — 이미 `TASK-61.15` 가 갖고 있고(그 AC#2 는
0/5 로 「이 조건이 결정하지 않는다」를 적었음) 이번 관측이 **그 태스크의 표본을 하나 늘린 것**임.
⚠️ 다만 **내 문면 추가가 그것을 늘렸는지는 이 표본으로 가릴 수 없음** — 같은 낭독이 문면 추가
**전에도** 관측됐음(`runs/2026-09-16-task61-14-…` §3-②).

---

## 4. 판정 — 네 AC 를 닫음

| 태스크 | AC | 근거 |
|---|---|---|
| `TASK-61.16` | AC#5(실물 관측) | §1-1 의 네 팔 · 스크린샷을 직접 열어 봤음 |
| `TASK-61.13` | AC#3(고치면 관측) | `s5` 가 그 정지의 모양에서 표면이 뜨는 것을 보였음 |
| `TASK-61.15` | AC#4(고치면 관측) | `s7`·`s2` 가 버려짐 표면을 보였음 |
| `TASK-61.17` | AC#4(두 언어 관측 + 오탐) | §2 와 §3-② |

⛔ **닫지 않은 것**: `TASK-61.15` AC#3(고치는 자리 — `accepted` 를 뒤로 미룰지)은 그대로 열려 있음.
이 회차가 만든 것은 **알림**이고 어댑터가 「받았다」를 먼저 돌려주는 구조는 바뀌지 않았음.

---

## 5. teardown — 이 턴에 직접 돌린 출력

| 대상 | 결과 |
|---|---|
| `:8012` · `:3001` · `:9333` | 전부 HTTP **000** |
| 검증 전용 DB | `dropdb ohmyenglish_t6116` 성공 · 남은 DB 는 `ohmyenglish` · `ohmyenglish_smoke` · `ohmyenglish_test` |
| `/tmp` 사본 | `fe-t6116` · `chrome-t6116` · `t6116_app.py` · 회차 로그 삭제 · 잔여 **0건** |
| 공유 dev DB | 손대지 않았음 — `learning_sessions` **17** · `schema_migrations` **22** 로 기준선과 같음 |
| 리포에 남긴 것 | 픽스처 넷(`vc33`~`vc36`) · 이 디렉터리(관측 JSON 9 · `control-events.log` · `marker-drop-warnings.log` · `sessions.tsv` · `utterances.tsv` · 스크린샷 18) |
