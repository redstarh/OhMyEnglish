# 일일 오류 요약 표 설계 — TASK-1

> 절차의 정본은 `docs/ops/data-first-design-convention.md` 임. 이 문서는 그 6단계 가운데
> 3~5단계의 산출물과 마이그레이션 번호·적용 절차를 담음. 1~2단계의 조회 결과는 아래 §2 임.
>
> 요구사항 정본은 `docs/PRD.md` §13 임. 태스크 상태는 Backlog.md `TASK-1` 이 소유함.
> 이 문서에 요구사항 문면을 복제하지 않고 가리키기만 함.
>
> 작성 2026-09-11 · 브랜치 `design/first-vertical-slice`.

---

## 1. 결정과 그 대가

사용자가 접근 B 를 골랐음(2026-09-11). 즉 새 표 `daily_error_summary` 를 만들고 학습자 화면이
그것을 읽음. 소비자는 「오늘 무엇을 틀렸는지」를 보는 학습자 화면이고 범위는 설계와 구현임.

기각한 접근 둘을 함께 남김.

| 접근 | 기각 사유 |
|---|---|
| A — 표 없이 읽을 때 집계 | 마이그레이션 0건이라 비용이 가장 낮지만 과거 날짜의 값이 고정되지 않음. 인수기준 #3 이 표 스키마와 마이그레이션 번호를 요구하는 것과도 어긋남 |
| C — `learner_notes` 재사용 | 한 표가 계획 입력과 학습자 화면 두 계약을 지게 됨. `plan.py` 가 이미 그 표를 기간 요약으로 씀 |

이 결정이 뒤집는 것을 조용히 덮지 않음. `docs/design/2026-08-25-learning-coach-agent-design.md`
§6.1 은 만성 지표의 산정을 조회 시 계산으로 두고 롤업 표를 채택하지 않았음. 그 근거는
「단일 사용자 규모에서 결과가 같고 갱신 시점·신선도 관리만 늘어난다」였음.

그 근거가 이 표에는 그대로 적용되지 않음. 이유가 하나 있고 코드로 확인했음.

- `services/analysis.py` 의 `_UPSERT_PATTERN_SQL` 이 `target_form` 을 가장 최근 분석의 값으로
  갱신함. 즉 조회 시 계산은 과거 날짜의 요약에도 최신 목표 형태를 붙임. 「그날 무엇을
  분석했는지」의 기록으로는 틀린 값임.
- `services/analysis.py` 의 `_DELETE_OCCURRENCES_SQL` 이 재분석에서 그 발화의 발생 행을 지우고
  다시 넣음. 조회 시 계산은 그 재분석 결과로 과거 날짜를 다시 씀.

반면 §6.1 의 근거 가운데 「갱신 시점·신선도 관리가 늘어난다」는 이 표에도 그대로 남음. 그 비용을
어디서 치르는지 §4 가 지목함.

정직하게 적어 둘 한계 하나. `error_patterns` 를 삭제하거나 `pattern_key` 를 바꾸는 코드는 지금
없음(`grep` 으로 확인 — 갱신되는 것은 `target_form` 하나임). 따라서 스냅샷의 값어치는 「패턴이
병합·삭제되어도 과거가 고정된다」가 아니고 위 두 자리에 한정됨.

## 2. 1~2단계 — 기존 스키마 확인과 CREATE 판정

개발 DB `ohmyenglish` 를 직접 조회했음(2026-09-11).

- 표 18개 — `analysis_jobs` · `error_occurrences` · `error_patterns` · `harness_pattern_baseline` ·
  `harness_review_task_baseline` · `harness_runs` · `harness_sessions` · `learner_notes` ·
  `learning_scenarios` · `learning_sessions` · `pattern_attempts` · `pronunciation_attempts` ·
  `review_tasks` · `schema_migrations` · `session_plans` · `shadowing_items` · `users` ·
  `utterances`. 달력 날짜 1행을 담는 표는 없음.
- 적용 이력 — `001 · 003 · 004 · 005 · 006 · 007 · 009 · 010 · 011`. 다음 빈 번호는 012 임.
  002 와 008 은 영구 결번이므로 되살리지 않음(결정 27).
- `error_occurrences` 는 `user_id` 를 직접 갖지 않음. 소유자는 `pattern_id` 를 거쳐
  `error_patterns.user_id` 로 가거나 `utterance_id` 를 거쳐 `learning_sessions.user_id` 로 감.
- `users.timezone` 은 `not null default 'Asia/Seoul'` 이고 CHECK 가 없음.

판정은 CREATE 임. 그 개념을 담을 표가 없고 기존 표에 컬럼을 더해 담을 자리도 아님. 규약 §2 가
새 표를 위험이 낮은 형태로 분류함 — 없던 것이 생길 뿐임.

## 3. 3단계 — 저장될 데이터

### 3.1 표 정의

```sql
create table daily_error_summary (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users (id) on delete cascade,
  summary_date date not null,
  timezone text not null check (length(btrim(timezone)) > 0),
  occurrence_count integer not null check (occurrence_count >= 0),
  pattern_count integer not null check (pattern_count >= 0),
  patterns jsonb not null,
  computed_at timestamptz not null default now(),
  unique (user_id, summary_date)
);
```

컬럼마다의 근거.

| 컬럼 | 왜 이 모양인가 |
|---|---|
| `id` + `unique (user_id, summary_date)` | 대리키에 자연키 유일 제약을 붙이는 것이 이 리포의 관용임(`error_patterns` 의 `unique (user_id, pattern_key)`). 그 유일 제약이 upsert 의 conflict 대상이고 조회 인덱스도 겸함 |
| `summary_date date` | 달력 날짜라 `timestamptz` 가 아님. 절대 시각을 담는 컬럼이 아니므로 전역 규약의 「이벤트 시각은 `timestamptz`」에 걸리지 않음 |
| `timezone` | 그 날짜를 그은 타임존의 스냅샷임. `users.timezone` 이 나중에 바뀌면 과거 날짜가 어느 경계로 그어졌는지 복원할 수 없음. 저장해 두면 그 사실이 행 안에 남음 |
| `occurrence_count` · `pattern_count` | 화면이 먼저 읽는 두 수임. `patterns` 를 세어 얻을 수 있지만 목록이 상한에 걸려 잘릴 수 있으므로 전체 수를 따로 담음(§3.3) |
| `patterns jsonb` | 패턴별 상세임. 구조는 §3.2 |
| `computed_at` | 이 스냅샷을 만든 시각임. 재분석으로 다시 쓰이면 갱신됨 — 즉 「언제 계산된 값인가」가 행에 남음 |

별도 인덱스를 만들지 않음. 조회는 「이 사용자의 이 날짜 1건」과 「이 사용자의 최근 며칠」 둘이고
유일 제약의 인덱스가 둘 다 받음.

보존 기간은 무기한임. 하루 1행이고 단일 사용자라 연 365행에 그침. 삭제 경로를 만들지 않고
사용자 삭제만 `on delete cascade` 로 따라감.

### 3.2 예시 행 2개

요구사항을 만족하는지 눈으로 확인하기 위한 것임. 값은 개발 DB 의 실제 집계 모양을 따름
(2026-09-09 에 발생 6건·패턴 2종, 2026-09-03 에 발생 9건·패턴 5종이 있음).

```
user_id          | 00000000-0000-0000-0000-000000000001
summary_date     | 2026-09-09
timezone         | Asia/Seoul
occurrence_count | 6
pattern_count    | 2
computed_at      | 2026-09-09 21:14:03+09
patterns         | [
                 |   {"pattern_key": "article_missing_before_singular_noun",
                 |    "category": "article",
                 |    "target_form": "the + 단수 명사",
                 |    "occurrences": 4,
                 |    "example": {"original_span": "I sent report",
                 |                "correction": "I sent the report",
                 |                "reason": "특정 문서를 가리키므로 the 가 필요함"}},
                 |   {"pattern_key": "past_tense_in_work_update",
                 |    "category": "verb_tense",
                 |    "target_form": "동사 과거형",
                 |    "occurrences": 2,
                 |    "example": {"original_span": "Yesterday I work on API",
                 |                "correction": "Yesterday I worked on the API",
                 |                "reason": "어제 일이므로 과거형을 씀"}}
                 | ]
```

```
user_id          | 00000000-0000-0000-0000-000000000001
summary_date     | 2026-09-10
timezone         | Asia/Seoul
occurrence_count | 0
pattern_count    | 0
computed_at      | 2026-09-10 22:40:11+09
patterns         | []
```

두 번째 행이 뜻하는 것은 「그날 분석은 돌았고 오류가 0건이었다」임. 「그날 학습을 하지 않았다」는
행 자체가 없는 것으로 표현됨 — 두 사실이 한 모양으로 뭉개지지 않음.

`patterns` 안의 정렬은 발생 수 내림차순이고 동률은 `pattern_key` 오름차순임. 결정론적이어야
재계산이 같은 값을 만들고, 화면이 판독마다 순서를 바꾸지 않음.

`example` 은 그날 그 패턴의 발생 가운데 하나임. 고르는 규칙은 발화 시각이 가장 이른 것이고
동률은 발생 행의 `id` 순임. 학습자가 「무엇을 틀렸는지」를 알기 위해 필요한 것은 문장 하나이고
전부를 담으면 이 표가 `error_occurrences` 의 사본이 됨.

### 3.3 담지 않는 것

- 발생 전체 목록을 담지 않음. `patterns` 는 패턴당 예시 1건까지임.
- 패턴 목록의 상한은 20종임. 그것을 넘으면 상위 20종만 담고 두 개수 컬럼은 전체 수를 유지함.
  단일 사용자 규모에서 넘길 일이 없지만 jsonb 가 무한히 자라는 길을 열어 두지 않음.
- 판정을 담지 않음 — 「만성인가」·「좋아졌는가」를 이 표가 정하지 않음. PRD R11-8 과 같은 경계임.
- 발음 시도를 담지 않음. 발음은 `error_occurrences` 를 만들지 않으므로(`pronunciation.py` 의
  주석이 그 규약을 소유함) 이 표의 집계 대상이 아님. 발음을 함께 보이는 것은 별 요구사항임.

## 4. 4단계 — 읽는 쪽

규약 §3 의 표를 채움. 빈칸이 없어야 코드를 씀.

| 항목 | 답 |
|---|---|
| 무엇을 저장하나 | 사용자 타임존 기준 달력 날짜 1일의 오류 집계 — 발생 수·패턴 수·패턴별 상세와 예시 문장 |
| 어느 표·컬럼에 | `daily_error_summary` 전 컬럼(§3.1) |
| 누가 읽나 | `app/backend/app/services/daily_summary.py` 의 `load_daily_summary` → `app/backend/app/api/daily.py` 의 `GET /api/daily-summary` → `app/frontend/app/results/[sessionId]/page.tsx` 의 「오늘 무엇을 틀렸는지」 절. 셋 다 이 태스크가 만듦 |
| 읽은 값으로 무엇이 달라지나 | 세션 결과 화면에 그날 전체의 오류 요약 절이 그려짐. 세션 1건의 교정만 보이던 화면이 「오늘 무엇을 틀렸는지」를 함께 보임 |
| 읽는 쪽이 아직 없다면 어느 태스크가 소유하나 | 해당 없음 — 읽는 쪽이 이 태스크의 같은 커밋에 들어감 |

쓰는 쪽은 `services/analysis.py` 의 `_replace_occurrences` 임. 그 트랜잭션 안에서 방금 분석한
발화의 날짜 1건을 다시 집계해 upsert 함. 이 자리를 고른 이유 셋.

1. 발생 행이 바뀌는 유일한 자리임. 재분석의 삭제·재삽입도 같은 함수를 지나므로 스냅샷이
   원본과 어긋난 채 남는 경로가 없음.
2. 멱등임. `+1` 로 누적하지 않고 그 날짜를 다시 세므로 재시도가 값을 부풀리지 않음.
   `error_patterns.frequency` 가 이미 같은 규약을 씀.
3. 읽기 경로에 쓰기를 두지 않음. 화면 조회가 표를 갱신하면 판독마다 트랜잭션이 열림.

갱신 범위는 그 발화의 날짜 1건뿐임. 다른 날짜를 건드리지 않음.

## 5. 5단계 — 정합성 판정

| 대조 | 판정 |
|---|---|
| 요구사항 ↔ 표 | 만족함. PRD §13 이 요구하는 네 값(날짜·발생 수·패턴별 상세·예시 문장)이 §3.1 의 컬럼에 자리가 있음 |
| 표 ↔ 코드 | 읽는 코드가 §4 의 세 자리이고 같은 커밋에 들어감. 저장만 되고 읽히지 않는 컬럼이 없음 |
| 설계 ↔ 실제 DB | 이 문서가 있다고 적은 표·컬럼은 §2 의 직접 조회로 확인한 것과 새로 만드는 것 하나뿐임. 적용 뒤 재조회로 다시 대조함(§7) |
| 결정 ↔ 구현 | 접근 B 의 결정이 마이그레이션 012 와 §4 의 세 자리로 착지함. §1 이 뒤집는 결정(§6.1 의 롤업 기각)을 명시했음 |

## 6. 날짜 경계 규약

전역 DB 시각 규약과 규약 §6 을 그대로 따름. 이 표에서 실제로 걸리는 지점만 적음.

- `current_date` 를 쓰지 않음. 서버 세션 타임존의 날짜라 한국 시각 자정부터 오전 9시까지
  하루 이른 값을 냄.
- 날짜의 정본은 `users.timezone` 컬럼임. 호스트 시각도 세션 기본값도 아님.
- 집계의 앵커는 `utterances.created_at`(발화 시각)임. `error_occurrences.created_at`(분석 저장
  시각)을 쓰지 않음 — 새벽에 돌아간 분석이 발화를 다음 날짜로 밀어 넣음. `chronic.py` 와
  `review.py` 가 이미 같은 앵커를 씀.
- 그날의 경계는 SQL 안에서 `(u.created_at at time zone $tz)::date` 로 그음. `chronic.py` 의
  재발 일수 계산과 같은 관용임.
- 조회에서 「오늘」을 정할 때도 타임존을 읽어 변환함. 테스트가 시각을 주입할 수 있도록 함수가
  `now` 를 인자로 받고 naive datetime 을 거부함 — `services/recordings.py` 가 같은 규약임.
- 저장된 `timestamptz` 를 변환해 UPDATE 하지 않음. 변환은 읽을 때만 함.

사용자가 없으면 타임존의 정본이 없으므로 조용히 UTC 로 떨어지지 않고 `LookupError` 를 올림.
`load_chronic_metrics` 가 같은 판단을 이미 함.

## 7. 마이그레이션 번호와 적용 절차

번호는 012 임. §2 의 적용 이력 조회가 근거이고, 비어 있는 과거 번호를 되살리지 않음.

파일은 `db/migrations/012_daily_error_summary.sql` 하나임. 값역 변경도 `NOT NULL` 추가도 없고
새 표 생성 한 문장뿐임 — 규약 §2 의 위험 형태 어디에도 들지 않음.

적용은 011 이 세운 5단계를 그대로 씀.

1. `pg_dump -d ohmyenglish -n public -f <파일>` 로 백업함. `-n public` 을 빼면 공유 인스턴스의
   `en_coach` 스키마 권한이 없어 막힘.
   ⛔ **`-U ohmy` 를 붙이면 이제 막힘** — `public` 안에 `redstar` 소유 표 둘이 생겨
   `permission denied for table harness_pattern_baseline` 이 남. 규약 §5 가 적은 명령이 그대로는
   돌지 않고, 함정 `H-BB` 가 그 사실과 대응을 소유함.
2. 표별 행 수를 기록함(적용 후 대조용).
3. `app/backend/.venv/bin/python scripts/migrate.py` 로 적용함.
4. 재조회로 대조함 — 표가 18개에서 19개가 되었는지, 기존 행 수가 하나도 줄지 않았는지.
   명령의 종료 코드로 성공을 판단하지 않음. `migrate.py` 는 조용히 성공함.
5. 어긋나면 멈추고 사용자에게 올림. 스스로 고치지 않음.

코드와 이 마이그레이션은 같은 커밋으로 함께 나감. 한쪽만 나가면 그 사이에 저장 경로가 깨짐.

### 012 적용 실적 — 2026-09-11 직접 조회로 확인함

| 단계 | 결과 |
|---|---|
| 백업 | `/tmp/ohmyenglish-public-before-012-20260911-083237.sql` · `CREATE TABLE` 18 · `COPY public` 18 로 표 18개와 일치 |
| 적용 전 행 수 | 16개 표 기록(`/tmp/rows_before_012.txt`) |
| 적용 | `migrate.py` exit 0 · 출력 없음 |
| 이력 | `schema_migrations` 에 `012_daily_error_summary.sql` 추가 · 9행 → 10행 |
| 표 | `public` 18개 → 19개 · 새 표 컬럼 8개(`computed_at` 이 `timestamp with time zone`) |
| 행 수 대조 | `schema_migrations` 외 **차이 0건** — 기존 데이터 손실 없음 |
| 게이트 | 자동 검사 915건 통과 · `ruff`(안·밖)·`ruff format`·`ty`·프론트 `tsc`·`eslint` 통과 |

## 8. 되돌리기

```sql
drop table daily_error_summary;
delete from schema_migrations where filename = '012_daily_error_summary.sql';
```

되돌리기가 단순한 이유는 이 마이그레이션이 기존 데이터를 건드리지 않기 때문임. 잃는 것은 이
표에 쌓인 스냅샷뿐이고 그것은 `error_occurrences` 에서 다시 계산할 수 있음. 다만 재계산은 위
§1 이 적은 두 자리에서 원래 값과 달라질 수 있음.

## 9. 남는 미결

- 학습자가 오류 기록을 지울 때 이 스냅샷을 어떻게 할지 정하지 않았음. 지금 그 삭제 경로 자체가
  없으므로(PRD §8 의 열람·수정·삭제 요구는 아직 구현되지 않음) 그 태스크가 함께 정해야 함.
- 「오늘 완료 여부」를 같은 화면에 두는 것은 `TASK-2` 가 소유함. 이 표에 담지 않음.
- 여러 날을 한 화면에서 보는 히스토리는 `TASK-3` 이 소유함. 이 표가 그 입력이 될 수 있으나
  조회 함수를 미리 만들지 않음 — 소비자가 생길 때 만듦.
