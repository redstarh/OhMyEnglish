# 주간 학습 리포트 — 설계

> **소유 태스크**: `TASK-26`(AC#2·#3·#4 · AC#1 은 결정 58 로 이미 닫힘).
> **선행 결정**: **4**(주 시작은 월요일 · **표로 적재한다** — `docs/design/2026-09-06-captain-decisions.md`
> §1 항목 4) · **58**(주 경계는 월요일 · 대장에 등재됨) · **27**(008 은 영구 결번 · 번호는 착수 턴에
> 발급) · **91**(트리거는 세션 종료 · 범위는 셋 다 + 화면까지).
> ⚠️ **결정 4 가 대장에 없어서 결정 58 이 같은 주 경계를 다시 물었다** — 그 누락은 `TASK-136` 이
> 고친다. 이 설계는 **결정 4 가 살아 있다**고 읽는다(캡틴의 답이고 뒤집힌 적이 없다).
> **요구사항**: `PRD.md` §4 항목 4(MVP 범위) · `PRD:117`(주간 화면에 상위 오류 · 개선 패턴 · 다음 주
> 추천 시나리오) · **R11-8**(판단의 주체) · **R13-3**(날짜 경계는 `users.timezone`).

작성 2026-09-14 · 브랜치 `design/first-vertical-slice`

---

## §1. 무엇이 걸려 있었나 — 직접 확인한 사실 다섯

1. **`weekly_reports` 표가 없다.** `docs/database-schema.md` 가 *"아직 SQL 에 없는 테이블"* 절에
   제안 컬럼(`id`·`user_id`·`week_start`·`metrics_json`·`insights`·`plan`)만 두고 있다.
2. **주 경계를 계산하는 코드가 0곳이다.** `users.timezone` 으로 「오늘」을 구하는 자리는 여럿이지만
   (`daily_summary.py:_today_in` 등) 「주」를 구하는 함수는 없다.
   ⛔ `current_date` 를 **조건으로** 쓰는 자리는 리포 전체에 0곳이다(전부 「쓰지 말라」는 주석이다).
3. **적재 대 조회의 선례가 이미 갈려 있다.** 일일 요약(`daily_error_summary`)은 **적재**이고 그 근거가
   *"조회 시 계산의 결과가 시간이 지나면 달라진다"*(재분석이 `target_form` 을 갱신하고 발생 행을
   지우고 다시 넣는다)다. 반대로 연속일·완료·히스토리는 **조회 시 계산**이고 근거가 *"입력이
   불변이라 누적 컬럼은 갱신 누락으로 조용히 틀리는 자리를 만든다"* 다.
4. ⛔ **`mastery_score` 는 판별력이 0이다** — `chronic.py:deepest_recurrence` 주석이 *"패턴 7개가
   전부 `0.00` 이라 어떤 순위도 만들지 못한다"* 로 실측을 적어 뒀다. 「개선 패턴」의 입력으로 쓸 수
   없다.
5. **주간 job 도, 주간 화면도 0곳이다.** `analysis_jobs.job_type` 값역은 넷
   (`analyze_utterance`·`summarize_session`·`plan_next_session`·`generate_scenario`)이고,
   `app/frontend/app/history/` 에는 `page.tsx` 하나뿐이다.

## §2. 요구가 부딪히는 자리 하나 — R11-8 이 가른다

`PRD:117` 이 주간 화면에 **「개선 패턴」**을 요구하는데 **R13-5** 는 *"만성 여부 · **개선 여부** ·
점수는 이 요약의 것이 아님"* 으로 개선 판정을 뺐다. 같은 낱말을 반대로 쓰는 것처럼 보인다.

⇒ **R11-8 이 그것을 가른다**: *"조회는 **사실**(재발 세션 수·재발 일수·지속 기간·휴면 후 재발)을
제공하고 **판단은 학습 분석 Agent** 가 한다"*. 즉
**R13-5 의 금지는 「일일 요약」이라는 산출물에 걸린 것**이고, 판단 자체는 금지된 적이 없다 —
**주체가 제품이 아니라 모델**이어야 한다는 제약이다.
⛔ **그래서 이 설계는 제품이 개선 여부를 «계산하지» 않는다.** 사실을 모아 모델에게 주고 판단을
받아 적재한다. 세션 총평(`TASK-62`)이 같은 모양이다.

## §3. 스키마 — `weekly_reports`

| 컬럼 | 뜻 | 근거 |
|---|---|---|
| `id uuid pk` | | 이 리포의 모든 표와 같다 |
| `user_id uuid not null` → `users(id) on delete cascade` | | `daily_error_summary` 와 같은 형태 |
| `week_start date not null` | 그 주의 **월요일** | 결정 4·58 |
| `metrics jsonb not null default '{}'` | **사실** — 상위 오류·발생 수·패턴 종 수·세션 수 | R11-8 의 「조회는 사실을 제공한다」 |
| `insights jsonb not null default '{}'` | **모델 판단** — 개선 패턴 · 다음 주 추천 시나리오 | R11-8 의 「판단은 Agent 가 한다」 |
| `computed_at timestamptz` | `null` = 아직 계산하지 않았다 | `daily_error_summary.computed_at` 과 같은 규약(§7 의 R13-7 이 같은 구별을 요구한다) |
| `created_at timestamptz not null default now()` | | |

제약 셋:

- `unique (user_id, week_start)` — 재계산이 행을 늘리지 않게 한다(멱등의 뿌리).
- `check (extract(isodow from week_start) = 1)` — ⛔ **결정 4 를 값역으로 새긴다.** Postgres 의
  `date_trunc('week', …)` 가 **월요일**을 주 시작으로 쓰므로 계산과 제약이 같은 경계를 가리킨다
  (ISO 8601). 이 CHECK 가 없으면 일요일 시작으로 계산한 코드가 조용히 섞인다.
- ⛔ **`metrics`·`insights` 에 점수·등급을 담지 않는다.** R13-5·R11-8 의 톤 계약이고
  `TASK-62` 가 총평에서 같은 경계를 **값역으로** 막았다 — 그 방식을 따라 프롬프트가 점수를
  요구하지 않고 출력 규격에 그 키를 두지 않는다.

⚠️ **컬럼 이름이 `database-schema.md` 의 제안과 둘 다르다**: `metrics_json` → **`metrics`**,
`plan` 을 두지 않고 **`insights` 안에** 담는다. 근거 둘 — 이 리포의 jsonb 컬럼은 접미사를 붙이지
않는다(`learning_sessions.summary` · `session_plans.instruction`), 그리고 「다음 주 추천」은 모델의
판단이라 `insights` 와 **같은 호출의 산출물**이므로 두 컬럼으로 나누면 원자성이 두 자리로 번진다.
그 문서를 이 마이그레이션과 **같은 커밋에서** 고친다(010·011 이 세운 규약).

## §4. 주 경계 — `users.timezone` 으로 구한다 (AC#3)

```sql
-- 사용자 타임존의 「지금」에서 지난 주 월요일
(date_trunc('week', now() at time zone u.timezone) - interval '7 days')::date
```

- ⛔ **`current_date` 를 쓰지 않는다.** 전역 규약이고 R13-3 이 같은 것을 요구한다. UTC 자정~09:00
  KST 구간에 `current_date` 가 KST 날짜보다 하루 이르다는 실측이 이 리포에 이미 있다.
- **한 모듈이 소유한다** — `services/weekly_report.py` 에 `_WEEK_START_SQL` 을 두고 다른 자리에서
  주 경계를 다시 계산하지 않는다(`daily_summary.py` 가 「오늘」의 정의를 한 곳에 모은 것과 같다).
- ⚠️ **`date_trunc('week', …)` 가 월요일인 것은 Postgres 의 성질이고 발명이 아니다** — 그래도
  **단정으로 못박는다**: 그 성질이 바뀌면(또는 누가 일요일 기준 계산으로 바꾸면) §3 의 CHECK 와
  이 계산이 조용히 갈린다.

## §5. 적재 대 조회 (AC#2) — 결정 4 를 지키고 근거를 적는다

**표에 적재한다.** 캡틴 결정 4 가 이미 그렇게 정했고, 이 설계가 그 근거를 처음 적는다:

1. **값이 시간이 지나면 달라진다** — 주간 사실은 `error_occurrences` 위에 서고, 재분석이 그 행을
   지우고 다시 넣는다. 일일 요약이 표로 간 이유와 **같은 기전**이다.
2. **모델 호출이 얹힌다** — `insights` 는 Claude 호출의 산출물이라 조회마다 계산하면 화면을 열
   때마다 돈이 나간다. 세션 총평이 같은 이유로 적재다.
3. **반대쪽 선례와 다르다** — 연속일·완료는 불변 입력에서 같은 값이 나오므로 조회로 두었다. 주간은
   그 부류가 아니다.

⚠️ **그래서 `metrics` 도 적재한다** — 사실만 조회로 두면 「그 주의 사실」이 재분석에 따라 변하고
**같은 행의 `insights` 와 어긋난다.** 판단이 근거로 삼은 사실이 사라지면 리포트가 스스로를 설명하지
못한다. 둘을 한 행에 함께 담는 것이 그 어긋남을 막는다.

## §6. job 과 트리거 (결정 91)

- job 종류 **`summarize_week`** 를 값역에 더한다(`summarize_session` 과 같은 어법).
- ⛔ **대상 컬럼은 `session_id` 다** — 그 세션의 종료가 트리거이기 때문이다.
  `analysis_jobs_target_matches_job_type` 이 종류마다 대상을 **상호배타**로 가두므로
  `(job_type='summarize_week' and session_id is not null and utterance_id is null)` 분기를 더한다.
  ⚠️ **`analysis_jobs` 에 컬럼을 더하지 않는 것이 이 선택의 값어치다** — 공용 큐 표에 종류별 컬럼을
  더하면 상호배타 CHECK 가 종류 수만큼 복잡해진다.
  ⇒ **「어떤 주」는 job 이 들고 다니지 않고 워커가 세션 시각과 `users.timezone` 으로 다시 구한다.**
- **세션 종료 트랜잭션에서 「지난 주 행이 없을 때만」 넣는다** — 한 문장의 `insert … select … where
  not exists (select 1 from weekly_reports …)` 다. `enqueue_summarize_session` 과 같은 자리에 붙이고
  같은 트랜잭션을 쓴다.
- ⛔ **워커 분기를 함께 더한다.** 빼면 `else` 가 `process_analysis` 로 보내고 그쪽 가드가
  *"job … is not an analysis job"* 으로 실패시켜 재시도 뒤 영구 `failed` 가 된다 — 018 주석이
  *"이 분기를 빼면 기능이 아예 돌지 않는다"* 로 그 함정을 이미 적었다.
- **멱등** — 저장이 `on conflict (user_id, week_start) do update` 한 문장이고 같은 트랜잭션에서
  job 을 `done` 으로 닫는다(`TASK-62` AC#3 이 세운 형태). 재시도가 두 번 쓰는 유일한 경로다.
- ⚠️ **발화·오류가 0건인 주**는 모델을 부르지 않고 빈 `metrics`·`insights` 를 적고 `computed_at` 을
  세운다 — `{}`(아직 없음)와 「담을 것이 없었음」의 구별을 값의 **모양**에 둔다(총평이 세운 규약).

## §7. API·화면

- `GET /api/weekly-report` — 가장 최근에 계산된 주를 준다. 없으면 **404 가 아니라 200 에 빈 모양**
  (`analyzed: false`)을 준다. `daily.py` 가 같은 규약이고 그 라우터 docstring 이
  *"라우터는 판정을 갖지 않고 서비스가 정한 것을 HTTP 로 옮기기만 한다"* 로 경계를 적어 뒀다.
- 응답 필드: `week_start` · `analyzed`(`computed_at is not null`) · `metrics` · `insights`.
- 화면은 새 라우트 **`app/frontend/app/history/weekly/page.tsx`** 다. `history/page.tsx` 옆에 두는
  이유는 둘 다 「되짚어 보는 화면」이고 PRD §15 가 히스토리를 그 자리로 정했기 때문이다.
- ⛔ **점수·등급·달성률을 그리지 않는다**(PRD §15.3 의 비범위와 R13-5 의 톤 계약).

## §8. 테스트 축

| 축 | 무엇을 재는가 | 어디 |
|---|---|---|
| 스키마 | `week_start` 가 월요일이 아니면 거부 · `(user_id, week_start)` 중복 거부 · job 대상 상호배타 | `tests/unit/test_schema.py` |
| 주 경계 | 사용자 타임존으로 지난 주 월요일을 구한다 — **KST 새벽 구간**에서 UTC 기준과 달라지는 것을 잰다 | `tests/unit/test_weekly_report.py`(신규) |
| 트리거 | 지난 주 행이 없으면 job 이 걸리고, 있으면 걸리지 않는다 | 같은 파일 |
| 워커 | 분기가 `summarize_week` 를 `process_weekly` 로 보낸다 · 빼면 실패한다(무력화로 확인) | `tests/integration/test_worker.py` 이웃 |
| 저장 | 재시도가 행을 늘리지 않는다(멱등) · 0건 주가 빈 모양으로 닫힌다 | `tests/unit/test_weekly_report.py` |
| API | 200 의 필드 · 없을 때 빈 모양 | `tests/integration/` 신규 |
| 화면 | 브라우저 회차 — 프런트 테스트 인프라가 0이다 | 회차 기록 |

## §9. 되돌리기와 위험

- 되돌리기: `drop table weekly_reports` + job 값역·상호배타 CHECK 를 이전 판으로 되돌림.
  ⚠️ **값역 축소이므로 `summarize_week` 행이 하나라도 있으면 실패한다** — 011 이 겪은 형태이고,
  그때 그 행을 어떻게 할지는 데이터 판단이라 스크립트가 조용히 정하지 않는다.
- ⛔ **dev DB 적용은 승인 사안이다** — `TASK-66.9` 와 같은 규약(011 의 5단계)을 따르고, 사용자가
  자리에 없는 동안 돌리지 않는다.
- **모델 호출이 주 1회 늘어난다** — `llm_calls.purpose` 값역에 `summarize_week` 를 더해야 토큰
  기록이 남는다. ⚠️ `TASK-134` 가 **그 값역이 좁아 기록이 조용히 사라진 결함**을 이미 잡았다
  (021). 같은 실패를 반복하지 않으려면 값역 확장을 이 마이그레이션에 **함께** 넣는다.

## §10. 이 설계가 확인하지 못한 것

- **「개선 패턴」의 판별력** — `mastery_score` 를 쓸 수 없으므로 모델에게 줄 사실이 무엇인지는
  계획 단계에서 정한다(후보: 주별 발생 수 추이 · `review_tasks.review_stage` 의 이동 · 휴면 후 재발).
  ⚠️ 데이터가 두 주 이상 쌓이지 않으면 추이 자체가 없다 — dev DB 의 세션 17건이 며칠에 몰려 있어
  **첫 리포트가 빈약할 것**이고 그것은 결함이 아니다.
- **주간 화면의 배치** — 히스토리 화면과 어떻게 이어 보일지는 계획에서 정한다.
- **사람이 읽어 값어치가 있는가** — 모델 출력의 품질은 회차에서 사람이 읽어야 판정된다.
