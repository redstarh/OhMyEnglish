# 회차 2026-09-19-b8 — 즉시 드릴 화면 관측(TS-36 AC#3)과 R2 규칙 기준선 잔여(TS-4)

## 1. 회차 식별

| 항목 | 값 |
|---|---|
| 대상 | `/Users/redstar/MyProject/OhMyEnglish` · 브랜치 `design/first-vertical-slice` |
| 착수 HEAD | `e482afa` |
| 종료 HEAD | `b96e2be` (`origin` 대비 ahead 1) |
| 범위 | `TS-36` AC#3 · `TS-4` 의 미체크 AC 둘(#4·#6). 다른 TS 를 건드리지 않았음 |
| 실행 수단 | Orca 내장 브라우저 · HTTP(`curl`·`urllib`) · dev DB 직접 조회 · 회차 드라이버 2종 |
| 실물 유료 호출 | **0건** — `llm_calls` 에 회차 창(11:44Z 이후) 0행, 마지막 호출은 08:37Z (`evidence/00-no-paid-calls.txt`) |

### 1-1. 회차 중 HEAD 가 움직였음 — 앱 코드는 안 바뀌었음

착수 시 `e482afa` 였고 끝에 `b96e2be` 였음. 그 커밋이 건드린 파일은 셋이고 **전부 원장 md** 임:

```
backlog/tasks/task-249 - 검증 회차: 즉시 드릴 경로의 화면 관측과 회귀 기준선 잔여.md
tests/agent/backlog/tasks/ts-36 - A18 · 추가 학습 진입과 즉시 드릴 — source=additional.md
tests/agent/backlog/tasks/ts-4 - 결과 조회 API 가 여섯 세션 상태를 규약대로 응답한다.md
```

뒤의 둘에 들어간 변경은 **상태 한 줄뿐**임(`Blocked`→`In Progress` · `To Do`→`In Progress`). ⇒
`app/**` 무변경이므로 **이 회차의 모든 측정은 같은 앱 코드에 대한 것**임. 각 측정을 커밋별로
가를 필요가 없음.

⚠️ 내가 `TS-36`·`TS-4` 를 처음 읽은 시점에는 아직 `Blocked`·`In Progress`(갱신 07:05·08:12)로
보였음. 즉 그 커밋은 내 첫 읽기와 거의 같은 순간에 들어왔음. **원장 갱신은 내가 읽은 뒤 다시
읽어 덮어쓰기를 피했음.**

## 2. 환경 — 착수 지시의 전제를 하나씩 그 자리에서 다시 쟀음

| 전제 | 재는 명령 | 결과 |
|---|---|---|
| 백엔드 `:8002` 가 떠 있음 | `lsof -nP -iTCP:8002 -sTCP:LISTEN -t` | 참 — pid `73225` |
| `/health` 200 | `curl -o /dev/null -w '%{http_code}'` | 참 — `200` |
| 프런트 `:3000` 이 떠 있음 | `lsof -nP -iTCP:3000 -sTCP:LISTEN -t` | 참 — pid `98298` |
| 우리 표는 스키마 `ohmyenglish` | `select current_schema()` | 참 — `ohmyenglish` |
| 마이그레이션 031 적용 | `information_schema.columns` · `pg_constraint` | 참 — `learning_sessions.focus_pattern_key`(nullable) · `learning_sessions_focus_pattern_key_not_blank` |
| 워커가 꺼져 있음 | `analysis_jobs` 상태 분포 · 최신 `created_at` | 참 — `pending`·`running` **0건**, 최신 job 은 `2026-09-18 03:56:57Z` 로 회차보다 앞섬 |
| 사용자 타임존 | `select timezone from users` | `Asia/Seoul` · 오늘(KST) `2026-09-19` |
| 다른 주체가 DB 를 쓰는 중이 아님 | `pg_stat_activity` | 백엔드 풀과 내 `psql` 뿐 |

### 2-1. ⛔ 전제 정정 하나 — `/tmp/omy-backend.log` 는 이 회차의 관측 수단이 아니었음

착수 지시가 로그를 `/tmp/omy-backend.log` 로 알려 주었으나 **그 파일의 mtime 은 14:52 KST 로
회차(20:52 KST)보다 6시간 앞섬.** 회차 중 한 줄도 늘지 않았고 `WebSocket`·`GET /api` 줄이 0건임 ⇒
지금 떠 있는 백엔드의 출력이 그 파일로 가지 않음.

⚠️ **그리고 그 파일에 남은 내용이 오독을 유발했음.** 마지막 줄들이
`계획 b3000000-…-b1 를 읽을 수 없어 계획 없이 시작한다` 인데, 이것을 내 세션의 것으로 읽으면
「계획이 없어 지시문 초점 대체 분기가 아예 돌지 않았다」로 판정하게 됨. `session_plans` 를 직접
조회해 그 계획 id 가 **지금 DB 에 없고**(6행 전부 다른 id · 최신은 `26586108…` 이고 `focus` 가
정상 배열임) 그 줄이 앞 회차(B3)의 것임을 확인해 갈랐음.

⇒ **대신 쓴 관측 수단은 `/tmp/omy-frontend.log`** 임(mtime 이 회차 중 갱신됨). 이것이 §5 의
판정을 가른 결정적 증거가 됐음.

## 3. 착수 시 원장 상태 (회귀 기준선)

| 시나리오 | 착수 상태 | 체크된 AC | 미체크 AC |
|---|---|---|---|
| `TS-36` | `Blocked` | #1 · #2 | **#3** |
| `TS-4` | `In Progress` | #1 · #2 · #3 · #5 · #7 | **#4 · #6** |

⛔ 회차 전체 목록을 기준선으로 뜨지 않았음 — 범위가 이 둘로 못 박혀 있어 다른 TS 를 읽지
않았기 때문임. **그러므로 이 회차는 「전체 회귀 판정」을 하지 않았고, 위 두 줄만이 비교 대상임.**

## 4. `TS-4` — R2 규칙 4 와 우선순위를 앱 경로로 관측했음 ⇒ `Done`

드라이버: `ts4_r2_rules_driver.py`. 격리 사용자(`b8000000-…-00b8`)로 세션 셋을 심고
`GET /api/sessions/<id>/results` 를 두드렸음. 워커를 켜지 않았고 job 상태 조합은 행을 직접 심어
만들었음(`H-CD`).

| 이름 | 세션 `status` | job `total|non_terminal|failed` | 기대 | 실제 | HTTP |
|---|---|---|---|---|---|
| `D-rule4` | `completed` | `2|0|1` | `partial_failure` | **`partial_failure`** | 200 |
| `E-rule1-vs-3` | `failed` | `2|1|0` | `connection_failed` | **`connection_failed`** | 200 |
| `F-control-rule3` | `completed` | `2|1|0` | `analyzing` | **`analyzing`** | 200 |

증거: `evidence/TS-4-r2-rules-observed.txt` · 응답 본문 원본 `evidence/TS-4-{이름}-body.json`.

**AC#4 — 규칙 4 의 「성공분 교정을 포함한다」를 긍정으로 보였음.** `D-rule4` 가
`partial_failure` 이면서 `corrections` **1건**을 실었고, 그 교정은 `done` job 이 달린 발화의
occurrence 임(`pattern_key=b8_article_missing` · 원문 `go to gym` → 교정 `went to the gym`).
앞 회차가 본 `partial_failure` 세션은 `corrections` 가 0건이어서 이 절반을 보이지 못했음 —
그 공백이 이 회차로 메워졌음.

**AC#6 — 규칙 1 이 규칙 3 을 이기는 것을 관측했음.** `E-rule1-vs-3` 은 두 규칙을 **동시에**
만족함(세션 `status='failed'` + non-terminal job 1건). 응답은 `connection_failed` 이고
`corrections` 키가 부재임.

### 4-1. ⛔ 판별력 — `F` 가 없으면 `E` 의 결과가 아무것도 말하지 않음

`E` 가 `connection_failed` 인 것만으로는 **「우선순위가 지켜졌다」와 「내 seed 가 애초에
non-terminal job 을 만들지 못했다」를 가를 수 없음.** 그래서 `F-control-rule3` 를 `E` 와
**세션 `status` 한 값만** 다르게(`failed`→`completed`) 심었음. `F` 가 `analyzing` 을 낸 것이
그 job 구성이 규칙 3 에 실제로 닿는다는 증명이고, 같은 구성에서 `E` 가 `connection_failed` 인 것이
우선순위의 관측임(§7-7 · §7-9).

### 4-2. 단위 검사를 이 AC 의 근거로 쓰지 않았음

`unit/test_results.py` 의 두 검사가 같은 두 규칙을 덮고 있음. ⛔ 그것으로 체크하지 않은 것은
이 시나리오의 값어치가 **앱 경로(HTTP) 관측**이라서임 — `TS-4` 노트가 앞 회차에 세운 규약을
그대로 따랐음.

### 4-3. AC#7 — 심은 행을 회차 끝에 지웠음

격리 사용자와 딸린 행 전부를 지우고 **다시 읽어** 확인했음:
`users` 잔여 0 · `learning_sessions` 잔여 0 · `error_patterns` 잔여 0 ·
전체 `users` 1 · 전체 `learning_sessions` 27 — 착수 기준선과 같음(`evidence/TS-4-cleanup-verified.txt`).

⇒ **`TS-4` 의 AC 일곱이 전부 체크됨. 상태를 `Done` 으로 올림.**

## 5. `TS-36` AC#3 — 화면에서 실제로 본 것

전제를 먼저 만들었음: 결과 화면의 그 절은 `dailyPatterns.length > 0` 일 때만 렌더되고 그 값은
`GET /api/daily-summary` 의 **오늘(KST)** 행에서 옴. 착수 시 오늘 행은 **없었고** 가장 최근 행이
`2026-09-06` 이었음 ⇒ `ts36_daily_seed.py` 로 오늘 행 1건을 심었음.

고른 패턴은 `verb_tense_past_simple_for_past_events` 임. ⛔ **준비된 계획의 초점 둘
(`pronunciation_an_as_a` · `article_missing_before_noun`)과 겹치지 않는 것**을 고른 것이 그 선택의
전부임 — 겹치면 초점이 바뀌었는지를 가를 수 없음.

브라우저는 `http://localhost:3000/results/5c0c614b-…` 로 **쿼리 없이** 열었고(`H-CA` — `127.0.0.1`
을 쓰지 않았음), 하이드레이션은 `main` 노드의 React 내부 키 2개(`__reactFiber$…`·`__reactProps$…`)로
판정했음. 그 문서에 마이크 대체본(220Hz 오실레이터 + `createMediaStreamDestination`)을 먼저 심고
`orca click` 으로 링크를 눌렀음.

### 5-1. 요소 텍스트와 주소 — 직접 읽은 값

| 무엇 | 본 값 |
|---|---|
| 절 제목(`h2`) | `오늘 무엇을 틀렸는지` |
| 카드 본문 | `원문: Yesterday I go to the office` / `교정문: Yesterday I went to the office` / `어제 일이므로 과거형 went 를 사용합니다.` / `오늘 2번 나왔어요` |
| 링크 텍스트 | **`이 패턴으로 연습하기`** |
| 링크 `href` | **`/?source=additional&pattern=verb_tense_past_simple_for_past_events`** |
| 접근성 스냅샷 | `paragraph > link "이 패턴으로 연습하기" [ref=e3]` |

증거: `evidence/TS-36-results-screen-card.json` · `evidence/TS-36-daily-summary-after-seed.json`.
⚠️ **스크린샷은 얻지 못했음** — `orca screenshot` 이
`Screenshot timed out — the browser tab may not be visible` 로 실패했음(앞 회차 B5 와 같은 증상).
판정은 `eval` 로 읽은 DOM 텍스트·접근성 스냅샷·DB 로 했으므로 판정에는 영향이 없고, **사람이
나중에 볼 보조 증거만 없음.**

### 5-2. 눌렀을 때 일어난 일

| 관측 | 값 |
|---|---|
| 이동 방식 | **같은 문서 안의 클라이언트 이동** — 클릭 뒤에도 `window.__b8` 이 살아 있었음 |
| 마이크 대체본이 불렸음 | `__b8.gum = 1` · `AudioContext.state = "running"` · 오류 0건 |
| 최종 주소 | `http://localhost:3000/results/3fa98802-aac3-49df-99dc-efc1ba4d3fc4` (세션이 열리고 끝까지 가서 결과 화면으로 넘어갔음) |
| 세션 수 | 27 → **28** (정확히 1건) |

열린 세션 행:

| 열 | 값 |
|---|---|
| `id` | `3fa98802-aac3-49df-99dc-efc1ba4d3fc4` |
| `mode` | `speaking` (즉시 드릴은 말하기 세션이라는 계약과 일치) |
| `learning_source` | `additional` |
| `started_via` | `ui` |
| **`focus_pattern_key`** | **`verb_tense_past_simple_for_past_events`** |
| `status` · 발화 · job | `completed` · 6 · 3 |

⇒ 착수 지시가 관측하라고 적은 흐름 **①②③ 가운데 ①②③ 의 앞 세 자리가 전부 성립했음**:
카드가 뜨고 · 링크가 `?source=additional&pattern=` 로 가고 · 세션 행에 그 패턴이 남았음.

### 5-3. ⛔ 네 번째 자리는 앱 경로에서 관측되지 않음 — 그래서 AC#3 을 체크하지 않았음

남은 것은 「준비된 계획이 있으면 **지시문의 초점이 그 패턴으로 바뀜**」임. 이것을 앱 경로에서
관측할 표면을 찾지 못했음. 확인해 본 표면 넷:

1. `session_started` 이벤트 — 싣는 것은 `session_id`·`pronunciation_focus`·`shadowing` 뿐임.
2. `StubVoiceAdapter.instructions` — 값을 **보관만** 하고 밖으로 내보내지 않음(setter 없는 property).
3. `GET /api/sessions/next-plan` — `load_prepared_plan` 이 읽은 **저장된** 계획의
   `reason`·`target_level` 이고, 소켓이 만든 `model_copy` 사본이 아님.
4. `session_plans` 행 — 다음 계획은 워커가 쓰고 워커는 꺼져 있음.

⚠️ **로그도 아님** — 초점 대체 지점(`api/ws.py`)에 로그가 없고, 착수 지시가 알려 준
`/tmp/omy-backend.log` 는 §2-1 처럼 이 회차에 한 줄도 늘지 않았음.

그래서 이 자리의 유일한 근거는 **통합 검사**임. 남의 「통과했다」를 근거로 쓰지 않으려고
직접 돌렸음:

```
cd app/backend && ./.venv/bin/pytest -q -k "pattern_entry_records_the_choice"
1 passed, 1422 deselected in 0.48s
```

⛔ **그 통과로 AC#3 을 체크하지 않음.** 근거는 `TS-4` 노트가 이미 세운 규약과 같음 —
이 시나리오의 값어치는 앱 경로 관측이고 통합 검사는 그 층(`/ws/session` 소켓 밖의 화면·브라우저)을
덮지 않음. 그리고 초점 대체는 **AC#3 의 부수 조건이 아니라 구성 요소**임: `TASK-241` 노트가
*「기록만 남고 지시문이 안 바뀌면 코치는 다른 것을 연습시키는데 「경로가 있다」로 보인다」* 로
그 자리를 못 박았음.

⇒ **AC#3 미체크 · `TS-36` 은 `Blocked` 로 둠.** 「기능이 없다」가 아니라 **「그 절반을 밖에서 볼
수단이 없다」**가 막은 것이고, 그 수단의 부재 자체를 결함으로 올렸음(§6 · `TASK-250`).

## 6. 두 진입 경로 대조 — ⛔ 착수 지시의 전제가 이 환경에서 성립하지 않았음

착수 지시는 *「주소창에 `/?pattern=…` 을 직접 치면 새 문서 로드라 대체본이 죽고 「마이크 권한을
요청하는 중입니다...」에서 멈춤」* 을 전제로 주고 그러지 말라고 적었음. **그 전제는 재현되지
않았음.**

`orca goto` 로 주소를 직접 열었을 때(대체본 없음):

| 관측 | 값 |
|---|---|
| `getUserMedia` | `function getUserMedia() { [native code] }` — **대체본이 없는 원본** |
| `window.__b8` | `undefined` (대체본 미설치 확인) |
| 결과 | 세션 `df9e04d5-…` 가 열려 **`completed`·발화 6건**으로 끝나고 결과 화면까지 갔음 |
| `focus_pattern_key` | `verb_tense_past_simple_for_past_events` |

⇒ 이 Orca 브라우저의 `getUserMedia` 는 **대체본 없이도 resolve 함.** 즉 `H-CC` 가 적은 정지
증상은 이 환경에서 나타나지 않고, **두 진입 경로의 결과가 같음**(같은 세션 행 모양 · 같은
`focus_pattern_key`). 주소를 공유하거나 새로 고쳐도 걸리는 자리가 아님.

⚠️ 다만 **기전 차이는 실재함**: 링크 클릭은 같은 문서 안의 이동이라 심어 둔 대체본이 살아남고
(`__b8.gum=1`), 주소 직접 열기는 새 문서라 대체본이 사라짐. 마이크 «내용»을 재는 회차라면 그 차이가
판정을 가름 — 이 회차는 세션이 열리는지를 재므로 갈리지 않았음.

### 6-1. ⛔ 내 드라이버가 만든 가짜 결함 하나를 스스로 걸렀음 — `orca tab create --url` 은 두 번 로드함

`orca tab create --url "<진입 주소>"` 로 열었을 때 **세션이 2건** 생겼음(28→30). 두 번 재현됐음
(30→32). 「직접 진입이 세션을 두 번 연다」로 결함을 올릴 모양이었음.

⛔ 올리기 전에 드라이버를 의심했고(§7-7), `/tmp/omy-frontend.log` 가 갈랐음:

```
GET /history 200            ← orca tab create --url .../history  (같은 주소 2줄)
GET /history 200
GET /?source=additional&pattern=… 200   ← orca goto  (1줄)
GET /results/df9e04d5-… 200
```

`tab create --url` 은 **같은 주소를 두 줄 남김**(`/results/5c0c614b-…` 도 2줄 · `/history` 도 2줄).
`goto` 는 1줄이고 세션도 **정확히 1건**(32→33) 이었음. ⇒ **세션 2건은 `orca tab create --url` 이
문서를 두 번 로드한 드라이버 산물이고 앱 결함이 아님.** 앱은 진입 문서 1회 로드당 세션 1건을
연다(다섯 번의 진입 GET 과 다섯 개의 세션이 1대1로 대응함).

⚠️ **이것을 함정으로 적어 둘 값어치가 있음** — 회차가 「N건 관측」으로 세는 어떤 판정도
`tab create --url` 을 쓰면 2배가 됨. 대안은 중립 주소로 탭을 만들고 **`orca goto` 로 이동하는 것**임.
(`docs/ops/pitfalls.md` 는 내 쓰기 범위 밖이라 여기에만 적음 — 호출 세션이 옮길 자리임.)

## 7. `TS-36` AC#3 의 괄호 인용 — 관측한 것은 경로 B 임

AC#3 의 문면은 *「자주 틀리는 패턴에서 즉시 드릴을 만드는 경로가 성립함
(requirements-summary 「이 문법으로 연습 만들어줘」)」* 임. ⛔ **그 괄호 인용이 가리키는 것은
«말로 하는» 요청(경로 A)이고, 이 회차가 관측한 것은 화면 링크(경로 B)임.**

두 경로를 가른 것은 구현 쪽 문서임 —
`app/frontend/app/results/[sessionId]/page.tsx:179-181` 이
*「문구를 「연습 만들어줘」로 적지 않는다 — 그것은 `PRD.md:70` 이 예시로 든 **말로 하는**
요청이고(경로 A) 이 버튼은 화면에서 누르는 것이다」* 로 적어 두었고, `TASK-233` 노트가 경로 A 를
`TASK-7` 이 범위 밖으로 갈라 둔 쪽으로 명시함.

코드로 확인한 경로 A 의 상태: 음성 명령 여섯 가운데 즉시 드릴에 닿는 것은 `start_additional`
하나이고 그것은 `target` 을 반드시 받는데 `AdditionalTarget` 값역이
`conversation·scenario_intake·pronunciation·shadowing` 넷이라 **패턴 키를 실을 자리가 없음.**
`practice_current_pattern` 은 `app/` 안 0건 그대로임.

⇒ 판정에 쓰지 않고 **결함으로 올렸음**(`TASK-251`). 근거는 판정 우선순위 ③이 ④보다 세다는
것임 — 문서화된 계약이 두 경로를 갈라 두었으므로 경로 B 의 성립을 경로 A 의 성립으로 셀 수 없고,
그 반대로 경로 A 의 부재를 경로 B 의 실패로 셀 수도 없음.

## 8. 등록한 결함

| ID | 현상 | 시나리오 |
|---|---|---|
| `TASK-250` | 즉시 드릴이 코치의 지시문 초점을 실제로 바꿨는지 **앱 경로에서 확인할 표면이 0곳**임 | `TS-36` AC#3 |
| `TASK-251` | 말로 하는 즉시 드릴 요청(`PRD.md:70` 「이 패턴으로 연습 만들어줘」)이 `TASK-233` 이 닫힌 뒤에도 **소유자가 없음** | `TS-36` AC#3 |

기존 결함 열(`TASK-230`~`TASK-238`·`TASK-248`)과 뿌리가 겹치는지 먼저 봤음. `TASK-233` 이 가장
가깝지만 그것은 **경로가 0곳이던 것**이고 `TASK-241` 이 경로 B 로 닫았음 — 위 둘은 그 뒤에 남은
서로 다른 자리임(하나는 관측 수단의 부재 · 하나는 경로 A 의 소유자 부재). 새로 만든 것이 옳음.

⛔ **새로 실패(회귀) 0건.** 이 회차가 관측한 앱 거동 가운데 이전 회차에 통과했다가 지금 실패한
것은 없음.

## 9. 판정 요약

| 시나리오 | 착수 | 종료 | AC 별 결과 |
|---|---|---|---|
| `TS-4` | `In Progress` (#4·#6 미체크) | **`Done`** | #1·#2·#3·#5·#7 유지 · **#4 신규 확인** · **#6 신규 확인** |
| `TS-36` | `Blocked`→`In Progress` (#3 미체크) | **`Blocked`** | #1·#2 유지 · **#3 미체크 유지** — 네 자리 가운데 셋을 화면에서 봤고 넷째(지시문 초점)를 앱 경로에서 볼 수단이 없음(`TASK-250`) |

⛔ **부분 통과를 통과로 올리지 않았음.** `TS-36` AC#3 은 화면 세 자리가 성립했으나 그것이 AC 의
전부가 아니라서 체크하지 않았음.

## 10. 정리 — 되돌린 것을 다시 읽어 확인했음

| 바꾼 것 | 되돌림 | 확인 방법 |
|---|---|---|
| 격리 사용자 + 세션 3건 + 발화·job·occurrence (`TS-4`) | 전부 삭제 | 다시 읽어 잔여 0 · 전체 `users` 1 · `learning_sessions` 27 (기준선과 같음) |
| `daily_error_summary` 오늘(KST) 행 1건 | 삭제(기준선은 **행 없음**) | 다시 읽어 빈 문자열 · 전체 행 1(=`2026-09-06`) |
| 앱 경로로 연 세션 6건 | `teardown_session.py --session-id` 6회 | `session_deleted: 1` × 6 · `focus_pattern_key is not null` 잔여 **0** · 고아 job 0 · 고아 `pronunciation_attempts` 0 |
| Orca 탭 3개 | 전부 닫음 | `orca tab list` → `tabs: []` |

`error_patterns` 아홉 행의 `frequency` 를 착수 스냅샷과 대조했고 **전부 같음**(7·5·2·3·1·3·2·2·1).
`session_plans` 6행 그대로임. 유료 호출 0건임.

⛔ **백엔드·프런트 프로세스는 건드리지 않았음**(호출 세션의 background 태스크임).

## 11. 계측하지 못한 것

1. **지시문 초점 대체** — §5-3. `TASK-250` 으로 올렸음.
2. **경로 A(말로 하는 요청)** — 실물 Nova 가 금지된 회차라 애초에 관측 불가이고, 코드에 그 자리가
   없다는 것까지만 확인했음. `TASK-251`.
3. **스크린샷** — `orca screenshot` 이 탭 가시성 문제로 실패했음. 판정에는 안 썼음.
4. **`VOICE_ADAPTER=stub` 을 프로세스 환경에서 직접 읽지 못했음** — `.env` 에 그 키가 없고
   샌드박스에서 `ps` 가 막힘. 간접 근거 둘로 대신했음: 세션 6건이 12~45ms 안에 열리고 닫혔음 ·
   `llm_calls` 가 회차 창에서 0건임. **단정하지 않고 이 한계를 적어 둠.**
5. **전체 회귀 판정** — 범위가 두 시나리오라 다른 TS 의 기준선을 뜨지 않았음(§3).
