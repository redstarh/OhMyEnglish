# 배치 B3 회차 — TS-23 · TS-24 · TS-25 · TS-26

## 1. 환경과 격리 — 회차 첫 절에 적는 사실

| 항목 | 값 (이 회차에 직접 재서 얻음) |
|---|---|
| 리포 | `/Users/redstar/MyProject/OhMyEnglish` · 브랜치 `design/first-vertical-slice` |
| HEAD (회차 시작) | `ced8df0` |
| HEAD (회차 끝) | `61f67c4` — **회차 중 움직였음**. §1-1 이 그 영향을 가름 |
| 측정 시각 | `2026-09-19 05:44 UTC` ~ `06:2x UTC` (= `14:44 KST` ~ `15:2x KST`) |
| DB | homebrew `postgresql@17` `:5432` · 스키마 `ohmyenglish` · `SHOW TimeZone` = `UTC` |
| `users.timezone` | `Asia/Seoul` (1행 · 고정 사용자 `00000000-…-0001`) |
| 백엔드 | `:8002` `{"status":"ok"}` · `WORKER_ENABLED=false` · `VOICE_ADAPTER=stub` |
| 프런트 | `:3000` HTTP 200 · 브라우저는 `http://localhost:3000` 으로만 열었음 (`H-CA`) |
| 유료 호출 | 이 회차가 낸 것은 **0건** — §1-3 이 근거와 대조를 가짐 |

### 1-1. 회차 중 HEAD 가 움직였음 — 영향 없음을 기계로 가렸음

회차 시작 `ced8df0` → 회차 끝 `61f67c4`. 그 사이 커밋 셋이 들어왔음(`214eed5` · `5c6a71c` ·
`61f67c4` — 전영역 회차 배선과 배치 B1 의 `TS-30` 마무리).

⛔ **각 측정이 어느 커밋에 대한 것인지 가려야 하는 자리임**(§2-6). 가린 방법은 경로 대조임:

```
git diff --stat ced8df0..61f67c4 -- app db docs scripts   # 출력 0줄
git diff --name-only ced8df0..61f67c4 | sed 's#/.*##' | sort -u   # backlog · tests 뿐
```

즉 그 셋은 **원장 파일과 B1 회차 산출물만** 건드렸고 앱 코드·마이그레이션·요구사항 문서는
한 줄도 바뀌지 않았음. 그래서 이 회차의 모든 측정은 `ced8df0` 과 `61f67c4` 에서 같은 코드에
대한 것이고, 판정을 나눠 적을 필요가 없음.

⚠️ 그 커밋 하나(`61f67c4`)의 메시지가 *「TS-30 AC#3 을 승인된 실물 호출 1건으로 닫았음」* 임 —
§1-3 에서 내 것이 아니라고 가려낸 `vocab` 호출 1건의 출처가 그쪽 기록으로 교차 확인됐음.

⛔ **호출자의 전제 하나가 낡았음** (§3 의 재검증 규약): 착수 지시가 HEAD 를 `74fb5c0` 으로
적었으나 실측은 `ced8df0` 임. 그 사이 배치 B1 (`81e150e`) 과 B2 (`ced8df0`) 가 들어왔음. 이 회차의
모든 판정은 `ced8df0` 에 대한 것임.

### 1-2. 공유 인스턴스 판정 — 공유임

§2-6 을 직접 돌려 확인했음.

- `lsof -ti:8002` 와 `lsof -ti:3000` 이 둘 다 pid 를 냈음 — 두 프로세스는 호출 세션의 것이고
  이 회차는 죽이거나 다시 띄우지 않았음.
- `find app/backend app/frontend -newermt '-30 minutes'` 가 0건 — 회차 시작 시점에 다른 주체가
  소스를 고치고 있지 않았음.
- `git log --oneline -3` 이 회차 시작과 끝에서 같았음 — 커밋도 늘지 않았음.

공유 규칙 셋의 적용:

1. ⛔ **전역·공유 상태를 승인 없이 바꾸지 않았음.** `users.timezone` 을 바꾸면 `TS-24` AC#1 의
   판별력이 생기는데, 그것이 1행짜리 공유 값이라 **바꾸지 않고 호출자에게 승인을 요청했음**
   (§5 의 미결 1건). 회차 끝까지 답이 오지 않아 그 AC 를 `차단됨` 으로 남겼음.
2. 내 자료는 **식별자로** 격리했음 — 심은 행의 id 를 전부 `b3000000-…` 로 두어 정리에서 정확히
   가려냈음. 포트·data_dir 격리는 하지 않았음(호출자가 소유한 프로세스를 쓰라는 지시였음).
3. 상태 판정에 boolean 을 쓰지 않고 **식별자를 대조**했음 — 세션 종료 job 을 셀 때
   `analysis_jobs.session_id` 를 내가 만든 세션 uuid 와 직접 맞췄음. 개수만 세면 옆 배치가 만든
   세션의 job 을 내 것으로 읽음.

⚠️ **같은 시각 배치 `b1-base-results` 가 `/api/vocab/lookup` 을 마무리하는 중이었음** —
`/api/vocab` 은 건드리지 않았음.

### 1-3. 공유라는 것이 수치로 관측됐음 — 유료 호출 1건이 내 것이 아님

⛔ **「내 회차가 유료 호출 0건」과 「DB 의 유료 호출 수가 변하지 않음」은 다른 사실이고, 이 회차에서
실제로 갈렸음.**

| 시각 (UTC) | `llm_calls` | 무엇 |
|---|---|---|
| `05:47:22` | 33 | 내 WS 세션 **직전** |
| `05:5x` | 33 | 내 WS 세션 3회 **직후** — 스텁 어댑터라 호출이 없음 |
| `06:02:57` | **34** | 정리 뒤 |

늘어난 1건을 조회했더니 `purpose='vocab'` · `called_at=2026-09-19 05:59:59` 였음. 그것은
`POST /api/vocab/lookup` 의 호출이고 **이 배치는 그 엔드포인트를 두드리지 않았음** — 같은 시각
`TS-30` 을 마무리하던 배치 `b1-base-results` 의 것임.

⚠️ 이것이 §2-6 이 경고한 오염의 실물 형태임. 그래서 이 회차는 유료 호출 여부를 **총계가 아니라
`purpose` 와 시각으로** 판정했음. 총계만 봤다면 내 회차가 유료 호출을 냈다고 잘못 적었을 것임.

## 2. 착수 시 원장 상태 (회귀 비교의 기준선)

`BACKLOG_CWD=$T backlog task list --plain` 을 회차 시작에 떠서
`evidence/00-ledger-at-start.txt` 에 남겼음. 이 배치가 맡은 넷은 시작 시점에 전부
`In Progress` 이고 **AC 는 하나도 체크되지 않은 상태**였음 — 즉 이 넷에 대해서는 **이 회차가
기준선임.** 회귀(새로 실패·고쳐짐·여전히 실패)를 판정한 척하지 않음.

| 시나리오 | 착수 시 | 회차 끝 |
|---|---|---|
| `TS-23` | `In Progress` · AC 0/3 | `In Progress` · AC 2/3 |
| `TS-24` | `In Progress` · AC 0/3 | `Blocked` · AC 2/3 |
| `TS-25` | `In Progress` · AC 0/3 | `Blocked` · AC 2/3 |
| `TS-26` | `In Progress` · AC 0/3 | `Done` · AC 3/3 |

## 3. 판정 기준의 우선순위를 실제로 어떻게 썼나

지시받은 순서는 ① TS 태스크의 AC 문면 → ② `docs/PRD.md` §11·§13·§14·§15 → ③ `docs/design/**`
→ ④ 코드임. 이 회차에서 ①과 ④가 **정면으로 갈린 자리가 둘** 있었고, 그 둘은 §6 의 결함으로
넘겼음. 나머지는 ①과 ②가 일치해 갈림이 없었음.

## 4. 판정표

| 시나리오 | AC | 판정 | 근거 |
|---|---|---|---|
| `TS-23` | #1 계획 부재·실패에도 학습이 시작됨 | **통과** | PRD R11-5 · AC11-3 |
| `TS-23` | #2 초점 1~2개·질문 3~5개·난이도·이유를 함께 줌 | **미확인** | AC 문면과 `/next-plan` 계약이 갈림 → `TASK-231` |
| `TS-23` | #3 직전 세션 종료가 `plan_next_session` 을 등록함 | **통과** | 설계서 §3.1 |
| `TS-24` | #1 오류 요약이 사용자 타임존 기준으로 갈림 | **차단됨** | 판별력 부재 — §5 |
| `TS-24` | #2 완료 판정이 시나리오 1개로 성립함 | **통과** | PRD R14-1·R14-2·R14-5 · AC14-1·AC14-3 |
| `TS-24` | #3 기록 없는 날이 오류가 아니라 빈 결과 | **통과** | PRD R13-7 |
| `TS-25` | #1 연속 학습일이 사용자 타임존 기준으로 성립함 | **통과** | PRD R15-2·R15-3·R15-6 · AC15-1·AC15-2·AC15-4 |
| `TS-25` | #2 화면 `/history` 가 목록을 읽을 수 있게 냄 | **통과** | PRD R15-4·R15-5 |
| `TS-25` | #3 기록 0건일 때 빈 목록 안내 | **차단됨** | 전제를 세울 수 없음 — §5 |
| `TS-26` | #1 주간 리포트 응답이 규약대로 나옴 | **통과** | 설계서 §3 · `services/weekly_report.py` |
| `TS-26` | #2 화면 `/history/weekly` 가 렌더함 | **통과** | PRD §15.3 톤 계약 유지 확인 |
| `TS-26` | #3 데이터 없을 때 오류가 아니라 빈 결과 | **통과** | `api/daily.py` 의 404 금지 규약 |

요약: **통과 8 · 미확인 1 · 차단 2** (AC 12개 기준). **실패 0건** — 프로그램이 기대와 다르게
동작한 자리는 이 회차에서 관측되지 않았음.

## 5. 측정 상세 — 무엇을 어떻게 재서 참·거짓을 갈랐나

### 5-1. TS-23 AC#1 — 계획을 읽을 수 없어도 학습이 시작됨 · 통과

전제를 만드는 방법이 관건이었음. 기존 계획 6건은 **내가 만든 행이 아니라 지울 수 없으므로**,
내 세션(`8021ef05…`)에 붙은 계획 1건을 **계약 위반 모양으로** 심어 최신 1건이 되게 했음
(`_PREPARED_PLAN_SQL` 이 `order by created_at desc limit 1`). `instruction` 을
`{"focus":"이것은 배열이 아님"}` 으로 두어 `SessionInstruction` 검증이 깨지게 했고, DB 의
CHECK 넷(focus 1~2 · questions 3~5 · target_level 값역 · reason 비지 않음)은 만족시켰음.

관측 셋:

1. `GET /api/sessions/next-plan` → **HTTP 200** `{"reason":null,"target_level":null}`.
   404 도 500 도 아님 — 계획 부재가 오류로 번역되지 않음(`evidence/11`).
2. 같은 상태에서 `/ws/session` 을 새로 열었더니 **18 프레임**이 왔고 그 안에
   `session_started` → `final`·`partial`·`audio` 9회 → `session_ended` 가 들어 있었음
   (`evidence/12`). 즉 학습이 그냥 시작되고 정상 종료까지 갔음.
3. 백엔드 로그에 문서가 약속한 경고가 도착했음 — *「계획 b3000000-…-b1를 읽을 수 없어 계획 없이
   시작한다」* + pydantic 검증 오류 5건(`evidence/13`).

⚠️ **심은 계획 행은 곧바로 지웠고** `/next-plan` 이 원래 이유 문장으로 돌아온 것을 확인했음.

### 5-2. TS-23 AC#2 — 미확인 (결함 `TASK-231`)

저장된 계획 쪽은 PRD R11-2 의 네 요소를 **전부** 갖고 있음. 6건 전수 측정:
초점 패턴 `2`개 · 질문 `5`개 · `target_level` `A2` · `reason` 길이 74~100자 · `source` `agent`.
값역은 DB 가 못박고 있음(`session_plans_focus_len` 1~2 · `session_plans_questions_len` 3~5 ·
`session_plans_target_level_check` · `session_plans_reason_not_blank`).

그런데 `GET /api/sessions/next-plan` 은 `reason` 과 `target_level` **둘만** 내림. 초점 패턴과
질문을 내리지 않는 것이 **의도된 계약**이고 그 근거가 코드에 적혀 있음 — *「질문을 미리 보여주면
학습자가 답을 준비해 즉흥 발화 연습이 무의미해진다」*(캡틴 결정).

즉 AC 문면의 「함께 줌」의 주체를 **엔드포인트**로 읽으면 성립하지 않고, **계획**으로 읽으면
성립함. PRD 는 엔드포인트가 질문을 노출할 것을 요구하지 않음(R11-2 는 계획의 내용이고 R11-3 은
추천 이유만 화면에 요구함). ⛔ **그래서 이 AC 를 체크하지 않았음** — 어느 쪽이 정본인지는 사람이
정할 일이라 결함으로 넘겼음(§8). 기대값을 내려 통과시키지 않았음.

### 5-3. TS-23 AC#3 · TS-26 job 등록 — 통과, 양방향으로 가려냄

`/ws/session` 을 세 번 열어 `end_session` 을 보냈음. 매번 `session_ended` 를 받았고 세션 행이
`status='completed'` 로 닫혔음. 그 세션 id 로 `analysis_jobs` 를 조회한 결과:

| 회 | 세션 | 등록된 job |
|---|---|---|
| 1 | `8021ef05…` | `plan_next_session` · `summarize_session` · `summarize_week` |
| 2 | `ce52432c…` | `plan_next_session` · `summarize_session` · `summarize_week` |
| 3 | `fa0eebdf…` | `plan_next_session` · `summarize_session` — **`summarize_week` 없음** |

3회차에 `summarize_week` 가 빠진 것이 **결함이 아니라 가드의 동작**임. 2회차와 3회차 사이에
지난 주(`2026-09-07`) 리포트를 심었고, `_ENQUEUE_WEEK_SQL` 의 `not exists` 가 그것을 보고
등록을 건너뛰었음. 전체 `summarize_week` 수가 `11 → 12 → 12` 로 움직인 것이 그 A/B 임.
⛔ **이 A/B 를 하지 않았으면 3회차의 「0건」을 결함으로 올렸을 것임**(§7-7 이 경고하는 형태).

### 5-4. TS-24 AC#2 — 시나리오 1개로 완료 판정 · 통과

앱 경로(`/ws/session`) 로 시나리오가 붙은 세션 1건을 정상 종료시켰음. `/api/daily-summary` 가
`completed_today` `false → true` · `completed_scenarios` `0 → 1` 로 움직였음
(`evidence/01`→`evidence/05`). **값이 움직인 것이 내 관측력의 증명임.**

음성 대조 둘을 이어서 심었음 — 둘 다 **오늘 KST 에 끝난** 세션임:

| 심은 것 | 기대 | 관측 |
|---|---|---|
| `status='failed'` · 시나리오 있음 | 세지 않음 (AC14-3) | `completed_scenarios` 가 `1` 로 그대로 |
| `status='completed'` · 시나리오 **없음** | 세지 않음 | 같음 |
| `status='completed'` · 시나리오 있음 1건 추가 | `2` 로 늘고 판정은 그대로 (R14-5) | `completed_scenarios=2` · `completed_today=true` |

### 5-5. TS-25 AC#1 — 날짜 경계를 함정 구간에 직접 심어 가름 · 통과

⛔ **이것이 이 배치의 핵심 함정이고, 판별되는 자료를 직접 만들어 가렸음.**

`ended_at = 2026-09-16 15:10:00+00` 인 완료 세션 1건을 심었음. 그 값의
**UTC 날짜는 `2026-09-16`** 이고 **KST 날짜는 `2026-09-17`** 임(DB 로 직접 확인함). 심기 전
`/api/history` 의 `2026-09-17` 줄은 `learned=false` · `completed_scenarios=0` 이었음 — 빈
기준선이라 판별력이 있었음.

심은 뒤 관측:

- `2026-09-17` → `learned=true` · `completed_scenarios=1`
- `2026-09-16` → `learned=false` · `completed_scenarios=0` (그대로)
- 연속 학습일 `current` `2 → 3` · `longest` `2 → 3`

즉 집계가 `current_date`(UTC) 가 아니라 `users.timezone` 으로 날짜를 그었음. `current_date` 를
썼다면 그 세션은 `2026-09-16` 줄에 들어갔을 것임.

같은 방향의 **기존 자료**도 대조로 남겨 둠: `ended_at` 의 UTC 날짜가 `2026-09-17` 인 세션 8건이
`/api/history` 의 `2026-09-18` 줄에 `2026-09-18` 끝난 2건과 합쳐 `10` 으로 나옴.
`2026-08-24` UTC 세션도 `2026-08-25` 줄에 있음.

AC15-2·AC15-4 도 함께 성립했음:

- 착수 기준선이 `current=1` · `today_done=false` 였음 — 마지막 학습일이 어제일 때 현재 연속일이
  `0` 이 아니라 어제까지의 값을 유지함(AC15-2).
- 오늘 완료를 2건으로 늘려도 `current` 가 `3` 에서 움직이지 않았음 — 하루에 여럿을 마쳐도 1일임
  (AC15-4).

### 5-6. TS-25 AC#2 — 화면 · 통과 (판정은 스냅샷과 `get`·`is` 로 함)

`http://localhost:3000/history` 를 Orca 내장 브라우저로 열어 접근성 스냅샷을 떴음
(`evidence/17`). ⛔ **스크린샷을 판정 근거로 쓰지 않았음** — 이 회차에서는 탭이 보이지 않아
`Page.captureScreenshot` 이 타임아웃으로 실패했고, 그것이 판정을 막지 않았음.

DOM 에 도달한 것(전부 클라이언트에서만 렌더되는 문구라 하이드레이션도 함께 증명함):

- `"3일 연속 학습 중이에요"` — API 의 `current=3` · `today_done=true` 와 일치
- `"최장 연속 3일"`
- 날짜 30줄. 그 가운데 사실 서술이 **셋으로 갈려** 나왔음:
  `2026-09-19` → `"오류 7건 · 패턴 2종"` / `2026-09-18` → `"분석 기록 없음"` /
  `2026-09-17` → `"오류 없음"`
- `get --element e1 --what text` → `"학습 히스토리"` · `is --element e2 --what visible` → `true`

⚠️ 셋으로 갈린 것이 PRD R13-7 이 요구한 구별이 **화면까지** 도달했다는 증거임 —
「분석이 돌고 오류 0건」과 「그날 학습이 없었다」와 「학습은 했는데 요약이 없다」가 서로 다른
문구로 나옴.

### 5-7. TS-26 AC#1·#2·#3 — 통과

`weekly_reports` 가 회차 시작에 **0행**이었음. 그래서 AC#3 은 손대기 전에 이미 재졌음:
`GET /api/weekly-report` → **HTTP 200** `{"week_start":null,"analyzed":false,"metrics":{},"insights":{}}`
(`evidence/01`). 404 가 아니고 키도 빠지지 않았음.

AC#1 을 가리려고 리포트 **둘**을 심었음 — `2026-08-31`(session_count 11) 과
`2026-09-07`(session_count 22). 응답은 `2026-09-07` 쪽이 나왔음(`evidence/14`). 즉
`order by week_start desc` 가 실제로 걸림 — 한 행만 심었으면 이것을 가릴 수 없었음. 응답 모양도
계약과 같았음: `metrics{session_count · occurrence_count · pattern_count · top_patterns[{category ·
pattern_key · target_form · occurrences}]}` · `insights{improving · next_scenarios}`.

`analyzed` 의 두 경로도 갈렸음: `computed_at` 이 null 인 행을 심으면
`{"week_start":"2026-09-14","analyzed":false,…}` 로 **week_start 는 있고 analyzed 만 false** 임
(`evidence/16`). 행이 없을 때(`week_start` 도 null) 와 다른 답임.

AC#2 는 심은 리포트로 화면을 열어 확인했음(`evidence/19`):
`"9월 7일 ~ 9월 13일"` · `"학습 22회 · 오류 9건 · 패턴 2종"` ·
`"an + vowel noun — 6회 (grammar)"` · `"went — 3회 (grammar)"` · `"관사 붙이기가 나아지고 있음"` ·
`"호텔 체크인"`. 심은 값과 전부 일치함. **점수·등급·달성률 문구는 하나도 나오지 않았음** —
PRD §15.3 의 톤 계약이 화면에서 유지됨.

심은 리포트를 지워 0행으로 되돌린 뒤 같은 화면을 다시 열었더니
`"아직 만들어진 주간 리포트가 없어요. 한 주 학습이 쌓이면 만들어져요."` 가 나왔음
(`evidence/21`). AC#3 의 화면 절반임.

⚠️ **이 회차가 재지 못한 것을 명시함**: `summarize_week` job 의 **처리** 절반
(`process_weekly` → 실제 metrics 계산) 은 워커가 꺼져 있어 지나가지 않았음. 즉 AC#1 이 확인한
것은 **응답 계약**이고, 그 숫자가 앱 자신의 계산에서 나온 것은 아님. 이 DB 에서
`summarize_week` 는 `done` 이 **0건**이고 `weekly_reports` 는 회차 시작에 0행이었음 — 즉 이
기능은 실사용 경로를 **한 번도 끝까지 지나간 적이 없음.** 그 `failed` 10건의 `last_error` 는
전부 `TASK-191` 의 사람 손 표시(*「하네스·회차 산출물이라 처리하지 않음」*)이고 제품 실패가
아님. 그래서 결함으로 올리지 않고 관측으로 남김.

## 6. 차단 목록 — `실패` 와 섞지 않음

### 6-1. TS-24 AC#1 — 오류 요약의 타임존 경계

**막은 것이 무엇인지**: 이 회차의 시각(`05:44~06:2x UTC` = `14:44~15:2x KST`) 에는
`current_date`(UTC) 와 KST 날짜가 **같음**(둘 다 `2026-09-19`). 그래서 `/api/daily-summary` 를
그냥 두드리면 「`users.timezone` 컬럼을 읽었다」와 「`current_date` 를 읽었다」가 같은 답을 내
**어느 쪽인지 가리지 못함.** 판별 구간(`15:00~24:00 UTC`)까지 9시간 남았음.

판별력을 만드는 길이 둘이고 둘 다 막혔음:

1. **쓰기 경로** — `daily_error_summary` 는 `refresh_summary_for_utterance` 만 쓰고 그것은
   분석 워커에서만 돎. 워커를 켜면 내 스텁 세션이 만든 `analyze_utterance` job 이 처리돼 유료
   호출이 나고 픽스처 문장이 공유 dev DB 의 `error_patterns` 를 오염시킴(함정 `H-CD`).
   지시가 금지한 자리라 켜지 않았음.
2. **`users.timezone` 임시 변경** — 1행짜리 전역 공유 값이라 §2-6 규칙 1 에 걸림.
   바꾸지 않고 호출자에게 승인을 요청했고 **회차 끝까지 답이 오지 않았음.**

⛔ **「0건 관측」을 결함으로 올리지 않았음**(§7-7). 내 관측 수단이 그 신호를 잡을 수 있음을
증명하지 못했으므로 `실패` 가 아니라 `차단됨` 임.

⚠️ **다만 같은 날짜 경계 요구는 통과 판정을 받았음** — `R13-3`·`R14-3`·`R15-6` 이 같은 것을
요구하고, §5-5 가 그 함정 구간에 자료를 직접 심어 `users.timezone` 기준으로 갈리는 것을
확인했음. 갈리지 않는 것이 관측된 자리는 없음.

**기존 자료로도 못 가린 이유를 남김**: 유일한 `daily_error_summary` 행(`2026-09-06`) 의 근거
발화 3건은 UTC 날짜와 KST 날짜가 **같음**. 경계를 넘는 발생은 실재하지만
(`2026-08-25`/`08-24` 2건 · `2026-09-01`/`08-31` 6건 · `2026-09-03`/`09-02` 6건 ·
`2026-09-09`/`09-08` 4건) 그 날짜들에는 요약 행이 없음 — `daily_error_summary` 가
`2026-09-11` 에 생겼고 백필하지 않기로 한 결정 때문임.

### 6-2. TS-25 AC#3 — 기록 0건일 때의 빈 목록 안내

**전제를 세울 수 없음.** `/api/history` 의 `days` 는 `generate_series` 로 **항상 30줄**을 내므로
목록이 빌 수 없음. 이것은 결함이 아니라 R15-5 가 요구한 것임 — 학습이 없던 날이 보이지 않으면
연속이 어디서 끊겼는지 알 수 없음.

「기록 0건」에 가장 가까운 상태는 `streak.current === 0` 이고 그때 화면이
`"지금 이어지는 연속 학습일은 없어요"` 를 냄(코드에 있음). 그 상태에 닿으려면 **마지막 완료
학습일을 그저께보다 이르게** 만들어야 하고, 그것은 이 회차가 만들지 않은 완료 세션들을 지우는
일임 — 지시가 금지한 자리라 하지 않았음.

⚠️ AC 문면이 기대하는 「빈 목록 안내」가 `/history` 에 **존재하지 않고 의도적으로 두지 않은 것**
이라는 사실 자체는 결함으로 넘겼음(`TASK-231`). 하이드레이션 판정은 대신 §5-6 의 클라이언트
전용 문구 셋으로 했고 성립했음.

## 7. 결함 · 결정 대기

| ID | 원장 | 현상 |
|---|---|---|
| `TASK-231` | 작업 원장 (`$W`) | 테스트 시나리오 AC 문면 둘이 구현의 문서화된 계약과 어긋나 판정이 갈림 |

⚠️ **이미 등록된 `TASK-230`**(픽스처 세션 둘의 결과 상태가 회차 사이에 바뀌어 `TS-4` 기준선이
낡음) 과 같은 뿌리의 현상은 이 회차에서 관측되지 않았음.

⛔ **이 회차는 코드를 한 줄도 고치지 않았음.** 수정 제안은 `TASK-231` 본문의 「제안」에 적었음.

## 8. 심은 자료와 그 되돌림

| 심은 것 | 되돌림 |
|---|---|
| `learning_sessions` 4건 (`b3000000-…-0001`~`0004`) | 지웠음 |
| `daily_error_summary` 2건 (`…-00a1` · `…-00a2`) | 지웠음 |
| `session_plans` 1건 (`…-00b1`, 계약 위반 모양) | 회차 중 곧바로 지웠음 |
| `weekly_reports` 3건 (`…-00c1`~`00c3`) | 회차 중 전부 지웠음 |
| — | 정리 뒤 대조: `learning_sessions` 27 · `daily_error_summary` 1 · `weekly_reports` 0 · `session_plans` 6 · `utterances` 175 · `analysis_jobs` 분포 — **회차 시작 값과 전부 같음**(`evidence/22`). `b3000000…` 잔여 0건 |
| `/ws/session` 실세션 3건 + 그 자식(발화 18 · job 17) | 지웠음 — FK `on delete cascade` 로 함께 지워짐 |

⛔ **회차가 만들지 않은 행은 하나도 지우거나 고치지 않았음.** 마이그레이션·`ALTER` 계열·
`SET TimeZone`·DB 재시작·자격증명 회전도 하지 않았음.
⚠️ **실세션 3건을 지운 이유**: 워커가 꺼진 동안 그 세션이 남긴 `pending` job 17건이 쌓여 있었고,
누군가 워커를 켜면 픽스처 문장에 유료 호출이 나감(`H-CD` 가 이름 붙인 형태임). 지우는 것이
회차 전 상태로 되돌리는 방향이라 그쪽을 골랐음.

## 9. 증거 파일

전부 `tests/agent/runs/2026-09-19-b3/evidence/` 아래임.

| 파일 | 내용 |
|---|---|
| `00-ledger-at-start.txt` | 착수 시 테스트 원장 상태 |
| `01-baseline-*.json` | 손대기 전 네 엔드포인트 응답 |
| `02-pre-ws-counts.txt` · `04-post-ws-counts.txt` | job·`llm_calls` 전후 대조 |
| `03-ws-end-frames.jsonl` | 1회차 WS 프레임 18건 |
| `05-after-ws-*.json` | 앱 경로 완료 뒤 응답 |
| `06-boundary-history.json` | 날짜 경계 세션을 심은 뒤 `/api/history` |
| `07-negatives-daily.json` · `08-multi-*.json` | 음성 대조와 하루 여러 건 |
| `09-summary-seeded-*.json` | 오류 요약 읽기 경로 |
| `10`·`13-backend-log-*.txt` | 계획 검증 실패 경고의 도착 |
| `11-nextplan-unreadable.txt` · `12-ws-noplan-frames.jsonl` | 계획 부재 폴백 |
| `14`·`16`·`20-weekly-*.json` | 주간 리포트 응답 세 경로 |
| `15-ws-week-guard-frames.jsonl` | `summarize_week` 가드 A/B 의 3회차 |
| `17-history-screen-snapshot.json` · `19`·`21-weekly-*-snapshot.json` | 화면 접근성 스냅샷 |

⚠️ **스크린샷은 없음** — 탭이 보이지 않아 `Page.captureScreenshot` 이 타임아웃했음. 판정은
스냅샷·`get`·`is`·API 응답으로 했으므로 막히지 않았음(§6 의 규약이 스크린샷을 판정 근거로
쓰지 않게 하고 있음).
