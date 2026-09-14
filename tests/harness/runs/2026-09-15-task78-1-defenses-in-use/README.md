# 회차 — `TASK-78.1` AC#2: 오염 방어가 실사용에서 도는가

세션 `ohmyenglish-65` · 2026-09-15 KST 착수 · 태스크 `TASK-78.1`(AC#2) ·
실물 세션은 결정 40 이 사전 승인함 · 브라우저 레그 절차 정본 `tests/harness/browser_leg.md`

> AC#2 가 요구하는 것은 하나임 — *"오염 방어가 실사용에서 도는 것을 먼저 관측한다 — 결정
> 82·95·98·99 의 이행이 방금 끝났고 아직 관측되지 않았다"*.
>
> 이 회차가 겨냥하는 것은 `runs/2026-09-15-task81-app-leg` §7 의 재현임. 그 회차는 같은 스택에서
> `sound_check` 가 빈칸이고 복습 시계가 하루 뒤로 전진하는 것을 관측했고, 그 뒤에 결정 98 의 확장이
> 들어갔음. 즉 조건을 그대로 두고 코드만 새 것으로 두는 대조임.

---

## 0. 상한과 해석 규칙 — 돌리기 전에 적음

### 스택 — 공유 자원을 건드리지 않음

| 무엇 | 값 |
|---|---|
| DB | 검증 전용 `ohmyenglish_t781`(소유자 `ohmy` · 마이그레이션 024 까지) |
| dev 와의 차이 | dev DB 는 023 임(회차 전 직접 조회) — 이 스택의 `signal_source` 값역이 넓음 |
| 백엔드 | `:8012` · 래퍼 `/tmp/t781_app.py`(사본 프론트 origin 을 CORS 에 더함 · 앱 코드를 고치지 않음) · `VOICE_ADAPTER=nova` · `WORKER_ENABLED=false` |
| 프론트 | 사본 `/tmp/fe-t781`(`.env.local` 이 `:8012` 를 가리킴) · `next dev --port 3001` · 픽스처 둘을 사본의 `public/harness/` 에 둠 |
| 브라우저 | 전용 Chrome `:9333` · `--user-data-dir=/tmp/chrome-t781` · fake media stream |
| 드라이버 | `p_app_path.py --port 9333 --url http://localhost:3001/ --wav pq13.wav,pq13a.wav` — 모드를 주지 않는 일반 세션 |
| 공유 자원 | `:3000` · `:8002` · 공유 dev DB · 다른 세션의 Chrome(`:9222`)을 건드리지 않음 |

dev DB 회차 전 기준선(이 턴에 직접 조회): `learning_sessions=17` · `pronunciation_attempts=7` ·
`error_patterns=9` · `session_plans=6` · `utterances=128` · `review_tasks=15`.

### 조건 — `TASK-81` ARM-3 과 같게 둠

| 무엇 | 값 |
|---|---|
| 오디오 | `pq13.wav`("My blother will allive ealy tomollow molning." · /r/→/l/) → `pq13a.wav`(정답판) |
| 심은 키 | `f_as_p` — 그 오디오에 /f/ 가 없으므로 코치가 그 소리를 코칭할 근거가 없음 |
| 계획 | 검증 전용 DB 에서 계획 job 을 돌려 `focus=[pronunciation_f_as_p]` 를 얻음 |

### 하네스가 제품 규약을 우회한 개입 둘 — 숨기지 않고 적음

1. `next_review_at` 을 SQL 로 당겨 계획의 due 목록에 걸리게 함. `review.py` 가 그 컬럼의 유일한
   writer 라는 규약을 하네스가 우회한 것이고, 검증 전용 DB 에서만 돌림.
2. `summarize_session` · `summarize_week` job 의 `available_at` 을 30일 뒤로 밀어 계획 job 만 집히게 함.

### 상한

| 무엇 | 수 |
|---|--:|
| Nova 세션 | 2 (본 1 + 예비 1). 중간에 늘리지 않음 |
| Claude 계획 호출 | 2 (본 1 + 계약 거부 재시도 1 — `TASK-129` 회차에 그 거부가 실측됐음) |

### 해석 규칙 — 관측 넷과 읽는 법

관측 A(판정): `pronunciation_attempts.sound_check` 의 값. B(시계): `error_patterns.next_review_at` 이
전진했는가. C(화면): 결과 화면에 `기록만 했어요 · 복습에는 쓰지 않아요` 가 있는가.
D(로그): `코치가 말하지 않은 소리로 기록된 발음 시도 N건을 복습에서 제외했다` warning.

| A 의 값 | 읽는 법 |
|---|---|
| `mismatched` + B 전진 없음 + C 있음 + D 있음 | AC#2 충족 — 방어 넷이 실사용에서 함께 돌았음 |
| `mismatched` 인데 C 또는 D 가 없음 | 결함 후보로 보고함. 배제는 됐고 그 사실이 학습자·운영자에게 도달하지 않은 것임 |
| `mismatched` 인데 B 가 전진함 | 결함 후보로 보고함(`TASK-116.1` 의 재계산이 실사용에서 안 도는 것임). AC#2 를 닫지 않음 |
| `matched` | 코치가 키와 겹치는 것을 인용했음. 검사는 돌았고 배제 경로는 미관측이므로 AC#2 를 닫지 않고 그 사실을 적음 |
| 빈칸(판정 못 함) | 결정 98 의 확장이 실사용에서도 판정을 못 내는 것임. 결함 후보로 보고하고 AC#2 를 닫지 않음 |
| 코칭 0 (`pronunciation` 프레임 0) | 조건이 성립하지 않음 — 판정하지 않고 예비 1회를 씀 |
| `session_failed` | 환경 고장이라 판정하지 않음 |

범위 밖 하나를 미리 적음: 결정 99(분석 기원 행의 3줄 카드)는 `WORKER_ENABLED=false` 라
`transcript_analysis` 행이 생기지 않으므로 이 회차가 판정하지 않음. 그 방어는
`runs/2026-09-15-task88-1-analysis-row-screen` 이 화면으로 관측했음.

표본 1 로 비율을 말하지 않음. 이 회차가 답하는 것은 「실사용 경로에서 한 번이라도 도는가」임.

### AC#1 과의 경계 — 이 회차가 문턱을 정하지 않음

`TASK-78.1` AC#1 은 tool 도착률·`target_sound` 실림률의 문턱을 수치로 못박는 일이고 결정 50 1항이
돌린 뒤에 문턱을 정하는 것을 금지함. 이 회차는 그 문턱을 정하지 않고, 관측된 도착률을 사실로만
적음. AC#1 은 이 회차의 수치를 보고 맞추지 않아야 함 — 그 판단의 주체가 이 회차가 아님.

---

## 1. 결과 — 방어 넷이 실사용 경로에서 함께 돌았음

Nova 1세션을 씀(상한 2 · 예비 1회를 쓰지 않았음) · Claude 계획 1회(거부 0) · `session_failed` 0.

| 무엇 | 값 |
|---|---|
| `recv` | `session_started 1` · `final 4` · `pronunciation 1` · `speech_start 2` · `speech_end 2` · `interrupted 1` · `session_ended 1` |
| 픽스처 재생 | `plays[0]` 210ms · `plays[1]` 8,845ms · 문턱 관측 `{heardAgentAudio: true, audioAtGate: 107, finalAtGate: 2, waitedMs: 8636}` — 둘째가 코치의 턴 뒤에 흘렀음 |
| 학습자 전사문 ① | *"my brother will early really tomorrow morning"* |
| 코치 발화 ① | *"I hear you say "my brother will early really tomorrow morning." Let's focus on the word "early." Say just this word for me: early."* |
| 학습자 전사문 ② | *"my brother will arrive early tomorrow morning."* |
| 코치 발화 ② | *"Great! You said "early" clearly. Now tell me about your breakfast today. …"* |
| 세션 | `e712e8f5-f8df-4a4f-bbd7-490225e6d3d0` |

관측 넷 — 넷 다 직접 조회하거나 직접 열어서 얻었음.

| | 관측 | 값 |
|---|---|---|
| A | `pronunciation_attempts` 새 행 | `target_form=early` · `spoken_form=early` · `target_sound=f_as_p` · `outcome=correct` · `signal_source=nova_tool` · `sound_check=mismatched` |
| B | `error_patterns.pronunciation_f_as_p` | `frequency=1` · `last_seen_at` 이 심은 시도 시각 그대로 · `next_review_at=2026-09-15 21:59:29Z` — 회차 전에 하네스가 `now()-1h` 로 당겼던 값이 제품 경로의 재계산으로 심은 시도 기준값으로 돌아왔음. 새 시도는 이력에 들어가지 않았음 |
| B' | `review_tasks` | 1행 그대로 · `review_stage=1` · `status=pending` · `due_at=2026-09-15 21:59:29Z` — 단계가 오르지 않았음 |
| C | 결과 화면 (`shot-results.png` · 내가 직접 열어 봤음) | 발음 카드에 `시범 문장 early` · `내 발화 early` · `✓ 좋아요` 아래에 `기록만 했어요 · 복습에는 쓰지 않아요` 가 있음 |
| D | 백엔드 로그 | `코치가 말하지 않은 소리로 기록된 발음 시도 1건을 복습에서 제외했다 (세션 e712e8f5…)` warning 1건 |

§0 의 해석 규칙 첫 행에 그대로 해당함 — `mismatched` · B 전진 없음 · C 있음 · D 있음.

## 2. 대조 — 같은 조건에서 코드만 새 것임

`runs/2026-09-15-task81-app-leg` §7 은 같은 스택·같은 픽스처·같은 심은 키로 돌린 회차임.

| 무엇 | ARM-3 (결정 98 이전) | 이 회차 (결정 98 이후) |
|---|---|---|
| 코치가 코칭한 것 | `early` 의 /r/ 계열(*"er-lee"*) | `early` (같은 낱말) |
| `sound_check` | 빈칸 (`sound_check_verdict` 가 `None`) | `mismatched` |
| 복습 시계 | `next_review_at` 이 하루 뒤로 전진 | 전진하지 않음 |
| 화면 | `✓ 좋아요` 만 | `✓ 좋아요` + 배제 문구 |
| 로그 | 배제 warning 없음 | warning 1건 |

즉 결정 98 이 넓힌 문턱이 실사용에서 판정을 냈고, 그 판정이 `TASK-116.1` 의 재계산과
결정 95 의 화면 문구까지 이어졌음.

## 3. 판별력 — 이 관측이 반증될 수 있었나

같은 발화를 그대로 두고 키만 바꿔 `sound_check_verdict` 를 직접 돌렸음.

| 키 | 판정 | 읽는 법 |
|---|---|---|
| `f_as_p` (심은 키) | `mismatched` | 관측값과 같음 |
| `r_as_l` · `l_as_r` (코치가 실제로 다룬 소리) | `None` | 정상 기록을 배제하지 않음 — 검사가 키에 반응함 |
| `th_as_s` | `mismatched` | 코치 발화에 없는 소리는 어긋남으로 감 |
| 인용이 없는 발화 | `None` | 증명할 수 없으면 배제하지 않음 |

즉 「무엇을 넣어도 `mismatched`」가 아님. 그리고 ARM-3 이 같은 조건에서 빈칸을 냈으므로 반대
결과가 실제로 나온 적이 있음.

## 4. 부수 관측 셋

1. 코치가 문장 전체 인용과 낱말 인용을 한 발화에 함께 썼음. `TASK-116.5` 가 겨냥한 「문장 인용만」
   모양이 아니고 낱말 인용이 판정을 살렸음 — 그 태스크의 막힌 세션 비율(2/59)을 늘리지 않음.
2. 세션 화면의 `✓ 좋아요` 배지는 배제 전에 페인트됨. 검사가 세션 종료에서 도는 설계이므로 정상이고,
   결과 화면이 그 사실을 정정함. 학습자가 세션 도중에는 「복습에 쓰지 않는다」를 알 수 없음.
3. ASR 이 오류를 부분적으로만 정규화했음 — `blother` 는 `brother` 로 정규화하고 `allive ealy` 는
   `early really` 로 왜곡했음. 코치가 텍스트에서 `early` 를 문제로 고른 근거가 그것임.

## 5. AC#1 에 넘기는 사실 — 문턱을 정하지 않음

이 세션의 tool 도착 1/1 · `target_sound` 실림 1/1(표본 1). 결정 100 의 표에 더할 값이지만
문턱은 이 회차가 정하지 않음(§0 마지막 절).

## 6. 정리와 무변경 확인 — 직접 돌려 얻은 값

| 무엇 | 확인 |
|---|---|
| `:9333` · `:3001` · `:8012` | 전부 HTTP `000` |
| 검증 전용 DB | `drop database ohmyenglish_t781` 완료 · 남은 DB 는 `ohmyenglish` · `_smoke` · `_test` 뿐 |
| `/tmp` 사본 | `fe-t781` · `chrome-t781` · `t781_app.py` 삭제(부재 확인) |
| 공유 dev DB | 회차 전후가 같음 — `17 · 7 · 9 · 6 · 128 · 15` |
| 다른 세션의 Chrome | `:9222` 가 여전히 200 — 종료 대상에 넣지 않았음 |
| 공유 스택 | `:3000` · `:8002` 를 건드리지 않았음(회차 전후 리스너 0) |
| 리포 | 앱 코드·프론트 코드를 고치지 않았음. 픽스처 둘은 `/tmp` 사본의 `public/harness/` 에만 두었음 |
| 실물 사용 | Nova 1세션 · Claude 계획 1회 |

## 7. 판정

| AC | 판정 |
|---|---|
| `TASK-78.1` AC#2 | 충족 — 오염 방어(결정 98 검사 · `TASK-116.1` 배제 · 결정 95 화면 · 운영 로그)가 실사용 경로에서 한 번에 함께 돌았음 |
| `TASK-78.1` AC#1 | 열려 있음 — 문턱을 수치로 못박는 판단이고 이 회차가 하지 않았음 |
| `TASK-78.1` AC#3 | 열려 있음 — AC#1 이 전건임 |
| 결정 99 (분석 기원 3줄 카드) | 이 회차의 범위 밖(§0) — 판정하지 않음 |
