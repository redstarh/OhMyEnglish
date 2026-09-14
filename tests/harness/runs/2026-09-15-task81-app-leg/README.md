# 회차 — `TASK-81` AC#4: 계획이 발음을 초점으로 잡을 때 **브라우저 레그**에서 코칭이 나는가

세션 `ohmyenglish-65` · 2026-09-15 KST · 태스크 `TASK-81`(AC#1~#3 은 이미 충족) ·
실물 세션은 **결정 40** 이 사전 승인함 · 브라우저 레그 절차 정본 `tests/harness/browser_leg.md`

> AC#4 가 요구하는 것은 하나임 — *"고친 뒤 앱 경로(브라우저 레그)에서 코칭이 실제로 나는지 확인한다
> — 스파이크만으로 닫지 않는다(결정 50)"*.
>
> ⚠️ **기록의 규율 — ARM-1 은 이 문서를 쓰기 «전»에 돌렸음.** 그래서 ARM-1 의 해석 규칙은 사후에
> 적은 것이고, **ARM-2 의 규칙만 돌리기 전에 선언한 것임.** 숨기지 않고 여기 적음.

---

## 0. 스택 — 공유 자원을 건드리지 않음

| 무엇 | 값 |
|---|---|
| DB | 검증 전용 **`ohmyenglish_t81`**(소유자 `ohmy` · 마이그레이션 024 · 표 17개) |
| 백엔드 | **`:8012`** · 래퍼 `/tmp/t81_app.py`(사본 프론트 origin 을 CORS 에 더함) · `VOICE_ADAPTER=nova` · `WORKER_ENABLED=false` · `{"status":"ok"}`(⛔ `version` 키 없음 — StockAgent 아님) |
| 프론트 | **사본** `/tmp/fe-t81`(`cp -Rc` 2.9초) · `.env.local` 이 `:8012` 를 가리킴 · `next dev --port 3001` · `front=200` |
| 브라우저 | **전용 Chrome 152.0.7977.83** — `--remote-debugging-port=9333 --user-data-dir=/tmp/chrome-t81 --use-fake-ui-for-media-stream --use-fake-device-for-media-stream --autoplay-policy=no-user-gesture-required`(함정 `H-BD` 의 레시피) |
| 드라이버 | `p_app_path.py --port 9333 --url http://localhost:3001/ --wav <픽스처>` — 「학습 시작」을 CDP 실제 입력으로 누름(일반 세션) |
| 공유 자원 | `:3000`·`:8002`·공유 dev DB·다른 세션의 Chrome(`:9222`)을 **건드리지 않음** |

⛔ **`:9222` 의 Chrome 은 다른 세션(`realtime-meeting`)이 쓰고 있어 전용 인스턴스를 따로 띄웠음** —
그 탭을 `Page.navigate` 로 빼앗지 않음.

**dev DB 회차 전 기준선**(`TASK-129` 회차와 같은 값을 다시 확인): `learning_sessions=17` ·
`pronunciation_attempts=7` · `error_patterns=9` · `session_plans=6` · `utterances=128` ·
`review_tasks=15`.

### 하네스 개입 둘 — `TASK-129` 회차와 같음

1. `next_review_at` 을 SQL 로 당겨 계획의 due 목록에 걸리게 했음(`review.py` 가 그 컬럼의 유일한
   writer 라는 규약을 하네스가 우회한 것임).
2. `summarize_*` job 둘의 `available_at` 을 30일 뒤로 밀어 계획 job 만 집히게 했음.

### 상한

| 무엇 | 수 |
|---|--:|
| Nova 세션 | **2**(ARM-1 · ARM-2). ⛔ 중간에 늘리지 않음 |
| Claude 계획 호출 | ARM 마다 1회(브라우저 레그 §9 의 「실물 Claude 상한 1회」를 팔마다 지킴) |

---

## 1. ARM-1 — 짝이 맞는 픽스처(`pq06` · 심은 키 `th_as_s`) · **코칭 0 · tool 0**

**계획이 발음을 초점으로 잡았음**(`session_plans` 1행 · `source=agent`):
`focus=[pronunciation_th_as_s]` · 힌트 `let the learner finish the whole sentence first, then model
the 'th' sound only if it came out as 's'` · 맥락 다섯이 `Thursday`·`birthday`·`health` 처럼 th 를 담음.

**관통 결과**(`walk.json` · 세션 `79361a6c`):

| 무엇 | 값 |
|---|---|
| `recv` | `session_started 1` · `final 6` · **`pronunciation 0`** · `session_ended 1` · `session_failed 0` |
| 학습자 전사문 | *"i think three scenes are ready for the demo."* |
| 코치 발화 | *"I understand you are talking about three scenes for a demo. What are three things you want to do? Let's focus on talking about your plans for this Thursday first. …"* |
| `pronunciation_attempts` | 새 행 **0** (심은 1행만 남음) |
| 화면 | `shot-session.png` · `shot-results.png` · 결과 화면 URL 로 이동 확인 |

⛔ **혼입 요인이 하나 있고 그것이 이 팔의 판정을 제한함 — ASR 이 오류를 정규화했음.** `pq06` 의 세
오류(`sink sree sings`)가 전사문에서 `think three scenes` 로 왔음. 즉 **코치가 텍스트로는 틀린 발음을
보지 못했음.** 계획의 힌트가 조건절(*"only if it came out as 's'"*)이라 그 조건이 성립하지 않은 것으로
읽힌 것과 일치함.
⚠️ **그러므로 이 팔은 「계획 블록의 고침이 코칭을 못 낸다」를 보이지 않음** — 조건이 애초에 성립하지
않았음. 표본 1 이라 어느 방향으로도 단정하지 않음.

---

## 2. ⛔ ARM-2 의 해석 규칙 — **돌리기 전에 선언함**

조건을 `TASK-129` 회차가 **코칭 3/3 을 얻은 조합**으로 맞춤 — 오디오 `pq13`→(첫 발화 하나만) ·
심은 키 **`f_as_p`**(그 오디오에 /f/ 가 없음) · 검증 전용 DB 를 새로 만들어 후보를 하나로 둠.
그 회차는 **WS 레그**였고 이 팔은 같은 조건을 **브라우저 레그**로 재는 것임.

| 결과 | 읽는 법 |
|---|---|
| 코칭 **남** + `pronunciation` 프레임 ≥1 | AC#4 충족 — 앱 경로(브라우저)에서 코칭이 실제로 남 |
| 코칭 **남** + 프레임 **0** | 코칭은 나고 기록 경로가 안 열린 것 ⇒ AC#4 를 닫지 않고 `TASK-97`·`TASK-116` 축의 재료로 남김 |
| 코칭 **0** | ⛔ **WS 레그(3/3)와 브라우저 레그가 어긋남** ⇒ AC#4 를 닫지 않고 **그 어긋남 자체를 결함 후보로 보고함.** 「스파이크만으로 닫지 않는다」가 요구한 것이 정확히 이 대조임 |
| `session_failed` | 환경 고장이라 판정하지 않음 |

⚠️ **표본 1 로 비율을 말하지 않음.** 이 팔이 답하는 것은 「브라우저 레그에서 한 번이라도 나는가」임.

---

## 3. ARM-2 결과 — **코칭 0 · tool 0.** 그리고 어긋남의 원인 후보가 「레그」가 아님

**계획**(`ohmyenglish_t81b` · `session_plans` 1행): `focus=[pronunciation_f_as_p]` · 힌트가
**조건절 없이** `let the learner finish the sentence first, then model the /f/ sound and ask for one
repeat` 임 — ARM-1 의 조건절 문제는 이 팔에 없음.

| 무엇 | 값 |
|---|---|
| `recv` | `session_started 1` · `final 2` · **`pronunciation 0`** · `session_ended 1` · `session_failed 0` |
| 학습자 전사문 | *"my brother will arrive early tomorrow morning."* (⚠️ `pq13` 의 /r/→/l/ 오류 다섯이 또 정규화됨) |
| 코치 발화 | *"Good morning! I hear you say … Can you tell me what time he will arrive? Also, what would you like to eat or drink today? Try to name coffee, fruit, and one food you like."* |
| `utterances` | agent **1** · user **1** — 즉 **왕복이 한 번**뿐임 |
| `pronunciation_attempts` | 새 행 **0** (심은 1행만) |
| 화면 | `shot-arm2-session.png` · `shot-arm2-results.png` — **내가 직접 열어 봤음** |

**화면에서 직접 본 것**(스크린샷 둘을 열어서 확인): 세션 화면은 `답변:` 한 줄과 `질문:` 한 줄만
담았고 **발음 코칭 문구가 없음** — 코치 발화가 시간·음식 질문으로 이어짐. 결과 화면은
`학습 결과 / 분석 중 / 오늘 학습을 마쳤어요 — 시나리오 2개` 와 링크 둘을 렌더했음.
⚠️ `분석 중` 은 **`WORKER_ENABLED=false` 때문에 정상**임(워커를 끈 상태라 분석이 돌지 않음).
⇒ 사본 프론트(`:3001`)가 래퍼 백엔드(`:8012`)의 결과 조회를 **CORS 로 막히지 않고** 받았음이
화면으로 확인됨.

### ⛔ 미리 적은 표의 「코칭 0」 행을 그대로 적용하면 「레그가 어긋남」이지만, **그 읽기를 채택하지 않음**

§2 가 선언한 대조 조건은 `TASK-129` 회차(WS 레그 · 코칭 3/3)와 **같은 계획·같은 오디오**였음. 그런데
두 레그가 **발화 수에서 다름**을 결과가 드러냄.

| | WS 레그(`TASK-129`) | 브라우저 레그(이 회차) |
|---|---|---|
| 흘린 픽스처 | **둘** — `pq13`(오류) → `pq13a`(정답) | **하나** — 드라이버가 «첫 발화 하나»만 흘림(`p_app_path.py` 머리주석) |
| 학습자 발화 | 2 | 1 |
| 코칭이 난 자리 | **코치의 둘째 턴**(첫 턴은 대화였음) | 둘째 턴이 **존재하지 않음** |

⇒ **어긋남의 원인 후보로 「브라우저 경로」와 「왕복 수」가 남고 이 회차는 둘을 가르지 못함.**
⛔ **그래서 「앱 경로에서 코칭이 안 난다」로 읽지 않음** — WS 레그에서 코칭이 난 자리가 둘째 턴이고
이 팔에는 그 턴이 없음. 표본 2 이고 조건이 한 칸 다름.

## 4. 판정 — AC#4 를 닫지 않음

| AC | 판정 |
|---|---|
| `TASK-81` AC#4 | ⛔ **닫지 않음.** 브라우저 레그 2회에서 코칭 0 · tool 0 이지만, 그 원인이 앱 경로인지 **왕복 수 1회**인지 이 회차가 가르지 못함 |

**다음 수단 후보 둘** — ⛔ 어느 쪽도 내가 고르지 않음(하네스 확장이 내 몫인지가 경계임).

1. `p_app_path.py` 가 픽스처 **둘**을 순서대로 흘리게 확장해 왕복 2회를 만든다 — WS 레그와 조건이
   같아지고 그때 코칭이 나면 AC#4 가 닫힌다. 대가는 **하네스 드라이버를 고치는 것**임.
2. AC#4 를 **WS 레그 증거로 닫는다** — `TASK-129` 회차의 코칭 3/3 이 `/ws/session`(앱의 실제 소켓)을
   지난 관측이고 스파이크가 아님. 대가는 결정 50 이 말한 「브라우저 레그」의 글자를 넓게 읽는 것임.

## 5. 정리와 무변경 확인 — 직접 돌려 얻은 값

| 무엇 | 확인 |
|---|---|
| 전용 Chrome `:9333` · 프론트 사본 `:3001` · 래퍼 백엔드 `:8012` | 전부 종료 — 셋 다 HTTP **`000`**(연결 불가) |
| 검증 전용 DB 둘 | `dropdb ohmyenglish_t81` · `ohmyenglish_t81b` 둘 다 exit 0 · 남은 DB 는 `ohmyenglish`·`_smoke`·`_test` 뿐 |
| `/tmp` 사본 | `fe-t81` · `chrome-t81` · `t81_app.py` 삭제 |
| 공유 dev DB | 회차 전후가 **같음** — `learning_sessions=17` · `pronunciation_attempts=7` · `error_patterns=9` · `session_plans=6` · `utterances=128` · `review_tasks=15` |
| 다른 세션의 Chrome | `:9222` 가 **여전히 살아 있음**(HTTP 200) — 종료 대상에 넣지 않았음 |
| 공유 스택 | `:3000`·`:8002` 를 **건드리지 않았음**(둘 다 이 회차 동안 리스너 0이었음) |
| 실물 사용 | Nova 세션 **2** · Claude 계획 호출 **2**(팔마다 1회 · 거부 0) |
