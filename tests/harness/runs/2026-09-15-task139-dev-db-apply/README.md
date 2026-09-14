# 회차 — dev DB 에 마이그레이션 024 를 적용하고 실사용 경로를 관측함 (`TASK-139`)

세션 `ohmyenglish-65` · 2026-09-15 KST · 사용자가 이 세션에 직접 지시함(결정 103) ·
절차 정본은 `db/migrations/011_shadowing_items.sql` 머리주석의 5단계

> ⛔ 이 회차는 **공유 dev DB 를 파괴적으로 만졌음.** 아래 §3 이 예상 밖 부작용 둘과 그 복원을 갖고
> 있음 — 숨기지 않고 적음.

---

## 1. 5단계 절차 — 단계마다 직접 돌린 출력

| 단계 | 무엇 | 출력 |
|--:|---|---|
| ① | `pg_dump -n public -T 'harness_*'` | `/tmp/ohmy-dev-backup-before-024-20260915-074242.sql` · **119,128 바이트** · `CREATE TABLE` 17개 · `harness_` 문자열 **0건**(제외가 실제로 걸렸음) · exit 0(파이프에 걸지 않았음) |
| ② | 표별 행 수 기록 | 17표 · `/tmp/before024.json` — `learning_sessions=17` · `utterances=128` · `error_patterns=9` · `review_tasks=15` · `pronunciation_attempts=7` · `analysis_jobs=57` · `pattern_attempts=19` · `schema_migrations=21` |
| ③ | `scripts/migrate.py` | exit 0 · 출력 없음(이미 적용된 파일에 조용한 성공이라 ④가 필수임) |
| ④ | 재조회 대조 | `schema_migrations` **21 → 22** · 최대 `024_pronunciation_signal_from_transcript_analysis.sql` · **다른 표 열여섯의 행 수 무변경** |
| ⑤ | 어긋남 | 적용 자체에서 0건 — 멈출 사유가 없었음 |

**값역 확인**(AC#3): `signal_source` CHECK 가 이제 넷임 —
`nova_tool` · `korean_transcript` · `agent_reprompt` · **`transcript_analysis`**.

## 2. 실사용 경로 관측 (AC#4)

앞 회차(`runs/2026-09-15-task139-analysis-row-real-path`)가 024 검증 전용 DB 에서 **코드와 화면**을
확인했으므로, 이 회차는 **dev DB 에서 그 저장이 실제로 받아들여지는지**를 봄.

| 무엇 | 값 |
|---|---|
| 입력 | `p2m` 의 실측 전사문 — 앞 회차의 `seed.py.txt` 를 그대로 재사용함 |
| 세션 | `ccb165b7-6d72-4d94-b92c-12bc82260cf6`(회차 뒤 삭제함) |
| job | `p5_worker_leg.py guard` → `claim` · `status=done` · `attempts=1` · Claude 분석 **1회** |
| 새 행 | `pronunciation_attempts` 1행 · `signal_source=transcript_analysis` · `outcome=incorrect` · `target_form=the report` · `spoken_form=the la porte en chaille de lesseps` · `target_sound` 빈칸 |

⇒ **적용 전에 `CheckViolationError` 로 거부됐던 그 삽입이 지금은 통과함.** 그 거부는 같은 날
`TASK-139` 등록 때 트랜잭션 롤백으로 재현해 뒀음.

⚠️ **화면은 이 회차에서 다시 보지 않았음** — 앞 회차가 실물 행으로 3줄 카드를 이미 관측했고, 화면을
보려면 합성 세션을 dev DB 에 **남겨 둬야** 하는데 그것은 학습자의 실제 학습 이력에 가짜 세션을
남기는 일임. ⇒ 관측을 둘로 갈랐음: **DB 수용은 dev DB · 화면은 024 검증 DB.** 그 갈림을 여기 적음.

## 3. 예상 밖 부작용 둘 — 그리고 복원

⛔ **합성 전사문이 학습자의 «문법» 패턴 복습 시계를 움직였음.** 발음 축이 아니라 `store_attempts`
경로임 — 전사문 `i finished …` 가 기존 패턴 `verb_tense_past_simple_for_past_events` 의 재시도로
채점됐음.

| 무엇 | 회차가 바꾼 값 | 백업의 값(복원 대상) |
|---|---|---|
| `error_patterns.next_review_at` | `2026-09-17 22:43:38` | **`2026-09-12 23:59:37.666124+00`** |
| `review_tasks` `ede30660`(1단계) | `done` · `completed_at=2026-09-14 22:43:38` | **`pending` · `completed_at=null`** |
| `review_tasks` `62a1fb73`(2단계) | 새로 생김 | **없음** ⇒ 삭제 |
| `pattern_attempts` | 19 → 20 | **19** ⇒ 세션 삭제의 연쇄로 사라짐 |
| `daily_error_summary` | 0 → 1행(`2026-09-15` · `Asia/Seoul` · 0/0/[]) | **0행** ⇒ 삭제 |

⚠️ **이것이 `browser_leg.md` §8 의 경고가 그대로 재현된 자리임** — *"스냅샷이 보지 않는 컬럼은 대조도
하지 않는다"*. 나는 ②에서 **행 수만** 떴고 `next_review_at`·`status` 를 뜨지 않았음. 되돌릴 값을 준
것은 ①의 `pg_dump` 였음(그 덤프가 전 데이터를 담음). ⛔ **다음 회차는 되돌릴 대상을 먼저 정하고
그 컬럼을 뜨는 순서로 함** — 덤프에 의존한 것은 운이 좋았던 것임.

**복원 순서**: 세션 삭제(연쇄로 발화·발음 기록·job 삭제) → 2단계 과제 삭제 → 1단계 과제 `pending`
복원 → 패턴 `next_review_at` 복원 → `daily_error_summary` 행 삭제 → `p5_worker_leg restore`
(내 job 이 세션과 함께 지워져 되돌릴 것이 없었고, `available_at < 2001` 행 **0건**으로 확인함).

## 4. 무변경 확인 — 백업 덤프와 «행 단위» 대조

전 17표를 id 키로 전 컬럼 대조했음. 어긋남으로 남은 것은 **비교기의 표기 차이 11건뿐**임 —
덤프의 `\n` 이스케이프(발화 5건) · 배열 표기 `{a,b}` ↔ 파이썬 리스트(계획 6건). 값은 같음.

| 표 | 행 수 | 표 | 행 수 |
|---|--:|---|--:|
| `users` | 1 | `learning_sessions` | **17** |
| `utterances` | **128** | `error_patterns` | **9** |
| `error_occurrences` | 24 | `pattern_attempts` | **19** |
| `review_tasks` | **15** | `pronunciation_attempts` | **7** |
| `session_plans` | 6 | `analysis_jobs` | **57** |
| `learner_notes` | 7 | `llm_calls` | 4 |
| `learning_scenarios` | 30 | `shadowing_items` | 1 |
| `daily_error_summary` | **0** | `weekly_reports` | 0 |
| `schema_migrations` | **22** | | |

`schema_migrations` 22 만 백업 시점과 다르고 **그것이 이 회차의 목적**임.
⚠️ `llm_calls` 가 4 로 그대로임 — 하네스가 `usage_sink` 를 주입하지 않아 이 회차의 Claude 1회가
그 표에 남지 않음(제품 결함이 아님 · 앞 회차들이 같은 것을 적었음).

## 5. 판정

| AC | 판정 |
|---|---|
| `TASK-139` AC#1 | 충족 — 사용자가 이 세션에 「이 세션이 직접 적용」을 직접 지시함(결정 103). 다른 세션의 승인을 근거로 쓰지 않았음 |
| AC#2 | 충족 — 5단계로 적용하고 단계마다 출력을 위에 남겼음 |
| AC#3 | 충족 — CHECK 값역에 `transcript_analysis` 가 있음 |
| AC#4 | 충족 — dev DB 에서 그 삽입이 실제로 받아들여지는 것을 관측했음. ⚠️ 화면은 앞 회차의 실물 행 관측으로 갈라 둠(§2) |

⇒ 다음 실사용 세션에서 발음 기원 오류가 나오면 그 발화의 분석이 통째로 유실되는 일은 **더 이상
일어나지 않음.**
