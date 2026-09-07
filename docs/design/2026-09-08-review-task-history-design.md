# 복습 과제 히스토리 구조 설계 — 번호와 상태가 초기화되지 않게

> **원장**: `TASK-12`. `TASK-3`(연속 학습일과 학습 히스토리 화면)이 이 설계를 선행으로 기다린다.
> **캡틴 결정**: `docs/design/2026-09-06-captain-response-to-status-report.md:35`(항목 19) ·
> 같은 문서 `:96`(미결정 5 종결) — *"번호와 상태가 매번 초기화되지 않도록 히스토리를 기록하는 구조로 설계한다."*
> **뒤집는 대상**: 2026-09-03 캡틴 결정("패턴당 0행 또는 1행 · 지우고 다시 넣는다").
> 그 결정의 근거와 이 설계가 그것을 어디서 반박하는지는 §2에 있다.
>
> ⚠️ **이 문서는 설계만 담는다.** 코드도 마이그레이션 SQL 파일도 만들지 않았다 — 번호와 내용을
> 여기 적기만 한다(§5). 적용은 별도 태스크다.

---

## 1. 현재 재계산의 해부 (AC1) — 무엇을 지우고 무엇을 다시 넣는가

전부 `app/backend/app/services/review.py` 하나가 한다. 이 표에 행을 쓰는 코드는 그것뿐이고
(`docs/database-schema.md:230`이 그렇게 지목한다), **읽는 코드는 앱 전체에 0곳이다** —
직접 확인한 것: `grep -rn "review_tasks" app/`의 결과가 `services/review.py`의 4줄
(`:21`·`:145`·`:149`·`:252`)뿐이다. `load_due_reviews`(`review.py:298`)조차 이 표를 읽지 않고
`error_patterns`를 읽는다(`_DUE_REVIEWS_SQL`, `review.py:131-139`).

### 1.1 심볼 — 지우는 것과 넣는 것

| 심볼 | 위치 | 하는 일 |
|---|---|---|
| `_DELETE_TASKS_SQL` | `review.py:144-146` | `delete from review_tasks where pattern_id = $1` — **그 패턴의 행 전부** |
| `_INSERT_TASK_SQL` | `review.py:148-151` | `(pattern_id, task_type, scenario_context, review_stage, due_at, status)` **1행** |
| `recompute` | `review.py:249-283` | 위 둘을 `:271`·`:273-282`에서 차례로 실행한다 |
| `fold_stages` | `review.py:165-209` | 순수 함수. 이력에서 `ReviewState`(단계·완주·예정일·anchor) 1개를 계산한다 |
| `ReviewState` | `review.py:154-163` | `stage` · `completed` · `next_review_at` · `anchor` · `scenario_context` |
| `recompute_all` | `review.py:373-386` | 사용자의 모든 패턴에 `recompute`를 돈다(백필용) |
| 유일한 호출자 | `services/analysis.py:467` | 분석 워커. `store_attempts` 뒤에 `recompute`를 부른다 |

`recompute`가 넣는 값의 정체는 이 두 줄이다 — `review.py:280`이 `due_at`을
`state.next_review_at or state.anchor`로, `:281`이 `status`를 `"done" if state.completed else "pending"`로
정한다. 그리고 `:272`의 `if state.anchor is not None`이 **행을 아예 만들지 않는 경로**다(틀린 적이 없는 패턴).

### 1.2 그래서 실제로 초기화되는 것 4개

`delete` + `insert`는 같은 논리적 과제를 **다른 행으로** 다시 만든다. 소실되는 것:

| # | 잃는 값 | 왜 복원 불가인가 |
|---|---|---|
| 1 | `id` (uuid PK, `001_initial_schema.sql:116`) | `gen_random_uuid()`가 매번 새 값을 낸다. 화면·API가 이 값으로 과제를 가리키면 재계산마다 링크가 끊긴다 |
| 2 | `created_at` (`001:126`, `default now()`) | 재계산 트랜잭션 시각으로 덮인다 — 과제가 **처음 부여된 시각**이 아니다 |
| 3 | 이전 단계 행 | 2단계로 오르면 1단계 행이 사라진다. "1단계를 언제 완주했는지"가 이 표에 남지 않는다 |
| 4 | 학습자가 손으로 넣은 `status` | `'skipped'`는 CHECK에 있지만(`001:125`) 아무도 쓰지 않는다. **쓰는 순간 다음 재계산이 지운다** |

**실측 증거 (dev DB, 읽기 전용 조회, 2026-09-08)**:

```
select count(distinct id), count(distinct created_at) from review_tasks;
 distinct_ids | distinct_created_at
            7 |                   2
```

7행이 `created_at` **2개**를 공유한다(`2026-09-03 16:19:11.100907+00` 4행 ·
`2026-09-06 14:38:41.573593+00` 3행). 즉 `created_at`은 과제의 나이가 아니라 **재계산 배치의 시각**이다 —
2번이 관측으로 확인된다. 그리고 7행 전부 `status = 'pending'`이고 `review_stage`는 1 또는 2다.

### 1.3 테스트가 이 churn을 못 보는 이유 — 알아 두어야 한다

`tests/unit/test_review.py:317-331`의 `test_recompute_is_idempotent`가 `_task_rows`를 두 번 비교해
멱등을 주장하지만, `_task_rows`(`:203-208`)가 select 하는 컬럼은
`review_stage, status, due_at, scenario_context` **넷뿐이다 — `id`도 `created_at`도 읽지 않는다.**
`tests/integration/test_pipeline.py:796-803`의 `_review_stages`도 `(review_stage, status)`만 본다.
**그래서 id·created_at이 매번 바뀌는데도 스위트는 초록이다.** 지금 무해한 이유가 "설계가 안전하다"가
아니라 "관측하는 사람이 없다"는 것을 이 두 줄이 증명한다.

---

## 2. 번호 안정성 — 자연키 대 대리키 (AC2)

### 2.1 "번호"가 무엇인지 먼저 정한다 — 이것이 내 유도다

캡틴 문구는 *"과제 번호와 상태가 매번 초기화된다"*이고 `TASK-12` 설명은 *"화면이 과제 번호로
완료 표시를 하려면"*이다. §1.2에 비추면 **번호 = 화면·API가 과제 하나를 가리키는 식별자**이고,
지금 그것이 매번 새로 발급되는 값(`id`)이다. `review_stage`(1~3)는 초기화되는 것이 아니라 **재발 시
설계대로 1로 되돌아가는 값**이다(`2026-08-25-learning-coach-agent-design.md:135-137`) — 그것은 버그가 아니다.

→ **학습자에게 보이는 별도의 표시 번호(#1, #2 …)를 만들지 않는다.** 사람이 읽는 좌표는
"**사이클 안의 3단계 중 N단계**"이고, 기계가 가리키는 것은 `id`다. (뒤집으면: §8 질문 3.)

### 2.2 결정 — 자연키가 정체성이고, 대리키는 그 위에서 보존된다

| | 자연키 `(pattern_id, cycle_started_at, review_stage)` | 대리키 `id`(uuid) |
|---|---|---|
| 정체성의 정본 | **이것이다** | 아니다 |
| 어디에 쓰나 | upsert의 conflict target · 재계산의 정합 판정 | 화면·API·미래 이력 표의 FK |
| 왜 | 재계산이 이력에서 **다시 유도**하므로, 같은 사실이 같은 행에 닿는 유일한 방법이 값으로 된 키다 | 외부에 노출할 안정된 손잡이가 필요하다. 자연키는 세 컬럼이라 URL·FK에 부적합하다 |

**핵심**: `recompute`를 `delete`+`insert`에서 **자연키 upsert**로 바꾼다.

```sql
insert into review_tasks (pattern_id, cycle_started_at, review_stage, task_type,
                          scenario_context, due_at, status, completed_at)
values (...)
on conflict (pattern_id, cycle_started_at, review_stage) do update
   set status       = excluded.status,
       completed_at = excluded.completed_at,
       due_at       = excluded.due_at
```

그러면 `id`와 `created_at`이 **살아남는다** — 대리키를 "보존"하는 것이 자연키를 정체성으로 삼은
직접적 결과다. 그리고 `review.py:269-270`이 기록한 함정("한 statement의 delete/insert는 서로의
효과를 못 봐 unique에 부딪힌다")도 함께 사라진다: upsert 한 문장이 그 자리를 대신한다.

### 2.3 사이클 판별자는 **재발 시각**이다 — 카운터가 아니다

`unique(pattern_id, review_stage)`(`001:128`)로는 히스토리를 담을 수 없다. 같은 패턴이 재발하면
1단계가 **다시** 필요한데 그 키가 1단계를 하나만 허용한다. 그래서 사이클 판별자를 키에 넣는다.
후보 둘:

- **(A) `cycle_started_at timestamptz` = 그 사이클을 연 재발 시각.** `_HISTORY_SQL:84-95`의
  `greatest(max(occurrence 발화 시각), max(incorrect attempt 발화 시각))`이 이미 계산하는 값이고,
  `fold_stages`가 `anchor`의 **초기값**으로 쓰는 것이 정확히 이 값이다(`review.py:188`).
- **(B) `cycle_seq smallint` = 몇 번째 재발인가.**

**A를 택한다.** B는 이 설계가 고치려는 병을 새 옷으로 되살린다: 재분석이 **과거** occurrence 하나를
지우면 그 뒤의 모든 사이클 번호가 한 칸씩 **밀린다** — 즉 번호가 다른 과제에 재배정된다.
A에서는 각 사이클이 자기 재발 시각을 들고 있어 남의 번호를 물려받는 일이 없다. 근거가 사라진 사이클은
번호가 밀리는 대신 **`superseded`로 은퇴한다**(§3.3).

시각 규약 확인: `cycle_started_at`은 이벤트 시각이므로 `timestamptz`다. naive `timestamp`를 만들지
않는다. 이 표에 **달력 날짜 컬럼을 만들지 않는다** — "며칠에 완주했는가"는 읽을 때
`users.timezone`으로 변환해 구한다(§4 Boundary · §7).

---

## 3. 상태 이력을 어디에 남기는가 (AC3)

### 3.1 판별 기준은 "재계산이 다시 만들 수 있는가"다

2026-09-03 결정이 삭제를 허용한 근거는 *"완주·재발 여부가 `pattern_attempts`·`error_occurrences`에서
언제든 다시 계산된다"*였다(`review.py:22-24` · `database-schema.md:232-235`). **그 근거는 파생값에
대해서는 지금도 참이다.** 이 설계는 그것을 반박하지 않고, 근거가 **닿지 않는 값 세 개**를 분리한다:
`id` · `created_at` · 학습자가 손으로 만든 상태. 이 셋은 이력에 없으므로 재계산이 복원하지 못한다.

→ 그래서 답은 "같은 표냐 별도 표냐" 중 하나가 아니라 **출처로 갈라는 것**이다:

| 상태의 출처 | 어디에 남기나 | 이유 |
|---|---|---|
| **파생** (단계 완주·재발로 인한 중단) | **같은 표.** `(사이클, 단계)`마다 행이 쌓이고 생애 컬럼이 시각을 담는다 | 재계산이 소유자다. 별도 이력 표에 또 적으면 같은 사실이 두 곳에 갈라져 한쪽이 조용히 낡는다 |
| **학습자 행동** (건너뛰기 등) | **이 표 밖.** 표 생성은 `TASK-3`으로 연기하고, 그때까지 **넣을 수 없게 막는다** | 재계산이 닿는 컬럼에 두면 다음 재계산이 지운다 — §1.2의 4번이 바로 그 사고다 |

### 3.2 파생 이력 — 행이 쌓이고 컬럼이 시각을 담는다

`fold_stages`는 지금 **현재 상태 1개**만 돌려준다(`ReviewState`, `review.py:154-163`). 사다리 전체를
돌려주게 바꾼다 — 순수 함수라는 성질은 그대로 유지된다(DB 없이 검증된다, `review.py:15`).

- `ReviewState`에 `cycle_started_at: datetime | None` 추가 — `anchor`는 **현재 단계의 기준**으로
  이미 의미가 잡혀 있어(`:188`에서 시작하고 `:193`에서 이동한다) 사이클 시작과 다르다. 겸용 금지.
- `ReviewState`에 `ladder: tuple[ReviewStageRow, ...]` 추가. `ReviewStageRow`는
  `stage` · `due_at` · `completed_at | None` 셋을 담는 frozen dataclass다.
  각 단계의 `due_at`은 **그 단계를 촉발한 발화 시각 + `STAGE_DAYS[stage-1]`**이고(`:43`의 1·3·7일),
  `completed_at`은 그 단계를 접은 정답 발화의 시각(열린 단계는 null)이다.
- 기존 필드(`stage`·`completed`·`next_review_at`·`anchor`·`scenario_context`)는 **남긴다** —
  `load_completed_then_relapsed`(`review.py:351-370`)가 `.completed`를 쓰고 `recompute`가 나머지를 쓴다.

`recompute`는 사다리의 행 수만큼 upsert한다. 완주 사이클이면 1·2·3단계 **세 행**이 남고, 진행 중이면
접힌 단계들 + 열린 단계 1행이 남는다. `review.py:280`의 `state.next_review_at or state.anchor` 폴백은
사라진다 — 완주한 3단계 행도 자기 실제 예정일(`2단계 접은 시각 + 7일`)을 갖기 때문이다.

### 3.3 `status`를 파생 전용으로 좁힌다

| 값 | 뜻 | 누가 쓰나 |
|---|---|---|
| `pending` | 열린 단계 (예정일 전이거나 연체) | 재계산 |
| `done` | **이 단계를** 접었다 | 재계산 |
| `abandoned` | 이 단계를 접기 전에 재발이 와서 사이클이 끊겼다 | 재계산 |
| `superseded` | 이 행의 근거가 이력에서 사라졌다(재분석) — 화면에서 감춘다 | 재계산 |
| ~~`skipped`~~ | **뺀다** | — |

⚠️ **`done`의 뜻이 바뀐다.** 지금은 `review.py:281`이 **사이클 완주**에만 `done`을 주고 그때
`review_stage`는 항상 3이다. 새 뜻은 **단계 완주**다. `database-schema.md`와 테스트가 옛 뜻을
박고 있으니 함께 고친다(§6).

**`skipped`를 CHECK에서 빼는 것이 이 설계의 집행 장치다.** 지금 그 값을 쓰는 코드는 0곳이고
dev DB에도 0행이다(실측: `status` 집계가 `pending 7`). 남겨 두면 `TASK-3` 구현자가
`update review_tasks set status='skipped'`를 쓰는 것이 **문서와 컬럼 이름을 따르는 정상 행동**이고,
그 값은 다음 재계산에 조용히 사라진다. 값역에서 막으면 그 시도가 **CHECK 위반으로 즉시 실패**해
학습자 행동을 둘 자리를 의도적으로 만들게 된다. `009_drill_turns.sql:26-28`이 같은 판단을 한다 —
*"docstring은 그 함수를 읽을 이유가 없는 사람을 구속하지 못한다. 스키마는 구속한다."*

**학습자 행동 표를 지금 만들지 않는 이유**: `006`이 `suggested_contexts`를 미리 만든 근거는
*"지금 저장하지 않으면 소급이 불가능하다"*(`006_learning_coach_slice1.sql:14-15`)였다 — **데이터가
그때 흐르고 있었다.** 학습자 건너뛰기는 지금 흐르지 않는다(UI가 없다). 그래서 값역을 발명해
빈 표를 만드는 대신, CHECK로 막고 실제 행동이 정해지는 `TASK-3`에서 만든다.
그때 볼 것: FK를 `on delete cascade`로 둘지 `restrict`로 둘지 — `restrict`가 "학습자 이력이 붙은
과제는 지울 수 없다"를 스키마로 보장하지만, `error_patterns` 삭제가 `review_tasks`로 cascade하므로
(`001:119`) 패턴 삭제를 막는다. **패턴을 지우는 코드는 지금 테스트 정리 1곳뿐이다**
(`tests/integration/test_ws.py:351`) — 그 한 줄이 `restrict`의 비용 전부다.

---

## 4. 4 Lenses 검증

### Contract

- **`recompute`의 사후조건이 바뀐다.** 지금: "그 패턴의 `review_tasks` 행은 0개 또는 1개다"
  (`review.py:21-22`). 앞으로: "그 패턴의 **현재 사이클** 행은 사다리와 정확히 일치하고,
  **과거 사이클 행은 건드리지 않는다**." 이 문장이 새 계약이고 docstring·`database-schema.md`에 박는다.
- **불변조건 2개.** ① `(pattern_id, cycle_started_at, review_stage)`는 유일하다.
  ② `status = 'done'`이면 `completed_at is not null`이다 → CHECK로 강제한다.
  역방향은 강제하지 않는다: `superseded`가 된 행이 완주 시각을 그대로 들고 있어야 "우리가 무엇을
  믿었는지"가 남는다. 그래서 CHECK는 동치가 아니라 **함의**다
  (`status <> 'done' or completed_at is not null`).
- **멱등은 여전히 계약이다.** upsert의 conflict target이 자연키이므로 재실행이 같은 행에 닿는다.
  `id`·`created_at`이 이번에는 **실제로** 불변이고, 그것을 검증하려면 테스트가 그 두 컬럼을
  select 해야 한다(§1.3 · §6).
- **`fold_stages`는 순수 함수로 남는다.** 사다리를 돌려주는 것도 계산이지 IO가 아니다.

### Boundary

- **시간 경계**: `cycle_started_at`·`completed_at`·`due_at` 전부 `timestamptz`다.
  기준 시각은 **발화 시각**이고 `now()`가 아니다(`review.py:17-18` — 재실행마다 예정일이 밀리는 것을 막는다).
- **달력 날짜 경계는 이 표에 들어오지 않는다.** `review.py:18-19`가 *"달력 날짜를 쓰는 곳은 이
  모듈에 없다"*고 적었고 이 설계도 그 성질을 지킨다. `TASK-3`의 "며칠에 완주했는가 · 연속 학습일"은
  **읽을 때** `completed_at at time zone (select timezone from users …)`으로 구한다 —
  `current_date`를 쓰지 않는다. UTC 자정~09:00(KST)에 `current_date`가 하루 이르기 때문이다.
  ⚠️ `users.timezone`이 SoT다. 실측: `text` · `not null` · `default 'Asia/Seoul'`.
- **프로세스 경계**: `recompute`는 호출자의 트랜잭션에서 돈다(`review.py:253`). 사다리 upsert
  여러 건과 과거 사이클 상태 전이가 **한 트랜잭션**에 들어가야 절반만 반영된 사다리가 남지 않는다.
- **표시 경계**: `superseded` 행은 화면에 나가지 않는다. 값으로 상태를 표현했기 때문에
  (`superseded_at is null` 같은 별도 컬럼 대신) 상태로 필터하는 모든 조회가 자연히 이것을 제외한다 —
  읽는 사람이 새 조건을 기억해야 하는 함정을 만들지 않으려고 컬럼이 아니라 값을 골랐다.

### Failure

- **재분석으로 사이클이 사라지면**: 현재 사이클 시작보다 **뒤에 있는** 행은 근거가 없으므로
  `superseded`로 내린다(지우지 않는다 — 미래에 그 행에 붙을 학습자 이력을 cascade로 날리지 않기 위해).
  판정이 시각 비교 하나라 결정론적이다.
- **사다리가 짧아지면**(정답 attempt가 재분석으로 사라짐): 같은 사이클에서 계산된 사다리 길이를
  넘는 단계 행을 `superseded`로 내린다.
- **재발이 오면**: 이전 사이클의 `pending` 행을 `abandoned`로 내린다. 이것이 학습 히스토리 화면이
  "여기서 끊겼다"를 그릴 근거이고, 지금은 그 행이 삭제되어 존재하지 않는다.
- **증가가 무한한가**: 아니다. 패턴당 행 수 = (재발 사이클 수) × (도달 단계 ≤ 3) + superseded 잔재.
  실측 규모는 패턴 8행 · 과제 7행이다. 다만 재분석이 반복되면 `superseded`가 쌓인다 → §7 약점 2.
- **부분 실패**: upsert가 중간에 실패하면 호출자 트랜잭션이 롤백되어 사다리 전체가 이전 상태로 남는다.
  다음 재계산이 이력에서 다시 만든다(멱등).

### Dependency

- **호출 순서 제약은 그대로다**: `store_attempts` → `recompute` (`analysis.py:462-467`).
  이 설계는 그 순서를 바꾸지 않는다.
- **`fold_stages` → `recompute` 방향도 그대로다.** 사다리를 계산하는 쪽이 순수 함수이고 쓰는 쪽이
  DB를 만진다. 단계 정의를 SQL로 내리지 않는다 — `review.py:71-72`가 재귀 CTE를 회피한 이유가 유효하다.
- **`TASK-3`이 이 설계에 의존한다**: 화면이 완료 표시를 붙일 안정된 `id`와 단계별 `completed_at`이
  없으면 히스토리 화면을 그릴 수 없다. 반대 방향 의존은 없다 — 이 설계는 화면을 전제하지 않는다.
- **`error_patterns`는 이 마이그레이션이 건드리지 않는다.** 그래서 `load_due_reviews`(그 표를 읽는다)는
  `review_tasks`가 비어 있는 동안에도 계속 정확하다 — §5의 이관이 안전한 직접적 이유다.
- **008(주간 리포트)과의 접합면**: §5.2를 보라. 순서가 갈라진다.

---

## 5. 마이그레이션 번호와 기존 행 이관 (AC4)

### 5.1 번호는 **010**이다

직접 확인한 것: `ls db/migrations/` → `001 · 003 · 004 · 005 · 006 · 007 · 009`.
그리고 dev DB의 `schema_migrations`에도 **정확히 그 7건**이 있다(읽기 전용 조회). 002는 만들어진
적이 없고 008은 `TASK-26`(주간 리포트)에 예약됐다(`2026-09-06-captain-decisions.md:82-89`).
→ **010**.

### 5.2 ⚠️ 이 설계도 같은 순서 함정을 만든다 — 숨기지 않는다

`scripts/migrate.py:108`이 `sorted(MIGRATIONS_DIR.glob("*.sql"))` 순으로 돌고 `:113-114`가
**이미 적용된 파일을 건너뛴다.** 그래서 008이 비어 있는 채 010이 적용되면:

- **이 DB**: … 007 → 009 → 010 → (나중에) **008**
- **새 DB**: … 007 → **008** → 009 → 010

`009_drill_turns.sql:10-20`이 소유한 기전 그대로이고, **010은 그 갈라짐을 하나 더 늘린다.**
009의 갈라짐이 무해했던 이유는 *"008과 009가 서로 독립일 때뿐"*이라고 그 파일 `:18-20`이 못 박았다.
**010에서는 그 조건이 위험하다**: 주간 리포트는 복습 과제를 **읽을 개연성이 높은** 기능이고,
008이 `review_tasks`에 뷰·인덱스·컬럼을 걸면 010이 바꾼 유일키·값역에 부딪힌다.

→ **008 예약을 011로 옮기는 것을 캡틴에게 올린다**(§8 질문 1). 근거는 유도 1 자신이다:
그 결정의 논리는 *"이미 적용된 것보다 앞으로 정렬되면 순서가 갈라진다"*였고, 009가 적용된 지금
**008은 정확히 그 조건에 해당한다.** 유도 1이 쓰인 시점에는 적용 목록이 `001·003·004·005·006`이라
008이 맨 뒤였다 — 전제가 낡았다. `TASK-26`이 아직 착수 전이면 번호를 옮기는 비용은 0이다.

### 5.3 010이 하는 일

1. `alter table review_tasks add column cycle_started_at timestamptz;` (일단 nullable)
   · `add column completed_at timestamptz;`
2. **기존 7행을 지운다** (`delete from review_tasks`) — 근거는 §5.4.
3. `alter column cycle_started_at set not null` — 표가 빈 뒤이므로 무조건 성공한다.
4. `drop constraint`로 `unique (pattern_id, review_stage)`(`001:128`)를 내리고
   `unique (pattern_id, cycle_started_at, review_stage)`를 건다.
5. `status` CHECK를 교체한다: `in ('pending','done','abandoned','superseded')` — `skipped`를 뺀다(§3.3).
6. CHECK 추가: `status <> 'done' or completed_at is not null` (§4 Contract).
7. `idx_review_tasks_due`(`001:131`, `(status, due_at)`)는 **그대로 둔다.** 읽는 코드가 0곳이라
   지금 인덱스를 발명하지 않는다 — `abandoned`·`superseded`가 이 인덱스에 섞이지만 조회가 생길 때
   그 조회의 모양을 보고 정한다.

### 5.4 기존 행 이관 — **삭제하고 재계산으로 다시 만든다**

`cycle_started_at`이 `not null`이므로 기존 7행에 값을 줘야 한다. 선택지 셋:

| 안 | 판정 |
|---|---|
| SQL로 재발 시각을 백필 | **기각.** `_HISTORY_SQL:84-95`의 `greatest(...)` 로직을 마이그레이션에 복제하게 된다. 두 곳으로 갈라지고 한쪽이 낡는다 |
| 기존 행에 임의값(예: `created_at`) | **기각.** `created_at`은 재계산 배치 시각이다(§1.2 실측) — 사이클 시작이 아니다. 틀린 값을 유일키에 넣는 것이 가장 나쁘다 |
| **삭제 후 `recompute_all`로 재생성** | **채택** |

**삭제가 무손실인 근거 — 전부 직접 확인했다:**

1. **읽는 코드가 0곳이다** (§1: `grep -rn "review_tasks" app/` 결과가 `review.py` 4줄뿐).
2. **재계산 불가능한 값이 행에 없다.** 7행 전부 `status='pending'`이고 `skipped`는 0행이다.
   `created_at`은 이미 배치 시각이라 잃을 정보가 없다. `id`를 참조하는 FK도 조회도 없다.
3. **복원 경로가 실재하고 멱등이다.** `recompute_all`(`review.py:373-386`)이 이력에서만 계산한다.
   2026-09-04에 같은 성격의 백필을 실제로 돌린 전례가 그 docstring에 적혀 있다.
4. **복습 목록은 이 사이 멈추지 않는다.** `load_due_reviews`는 `error_patterns`를 읽고
   010은 그 표를 건드리지 않는다(실측: 패턴 8행 중 7건에 `next_review_at`이 있다).

⚠️ **010이 "지우고 다시 만들기"가 공짜인 마지막 순간이다.** 학습자 행동 이력이 한 번 붙으면
같은 삭제가 되돌릴 수 없는 손실이 된다. 그래서 이관을 지금 하고, 010 이후의 마이그레이션은
`review_tasks`를 비우는 방식을 쓸 수 없다.

**적용 순서(별도 태스크)**: ① 010 적용 → ② `recompute_all`을 사용자별로 1회 실행 →
③ `select count(*), count(distinct cycle_started_at) from review_tasks`로 재생성 확인.
②를 빠뜨리면 표는 빈 채로 남고, 각 패턴이 다시 발생할 때까지 채워지지 않는다
(`review.py:376-379`가 006에서 관측한 그 공백과 같은 기전).

---

## 6. 함께 고쳐야 하는 것 — 이 설계가 깨는 자산

**⛔ 이 설계서는 무엇도 고치지 않았다.** 아래는 010 구현 태스크가 같은 커밋에서 처리할 목록이다.

| 대상 | 무엇이 깨지나 |
|---|---|
| `tests/unit/test_schema.py:79-95` | 표 이름 집합을 **정확히** 비교한다. 010은 표를 만들지 않으니 통과한다 — **`TASK-3`이 이력 표를 만들면 여기가 깨진다**는 것만 알아 둔다 |
| `tests/unit/test_review.py:260` | `[(FINAL_STAGE, "done")]` → 완주 사이클은 세 행 `[(1,'done'),(2,'done'),(3,'done')]`이 된다 |
| `tests/unit/test_review.py:228`·`244`·`280`·`528` | 진행 중 사이클은 접힌 단계 행이 함께 남는다. 예: `:244`는 `[(1,'done'),(2,'pending')]` |
| `tests/unit/test_review.py:317-331`·`539-543` | 멱등 테스트가 `id`·`created_at`을 select 하도록 `_task_rows`(`:203-208`)를 넓힌다 — **그러지 않으면 이 설계의 핵심이 무보호로 남는다**(§1.3) |
| `tests/unit/test_review.py:343` | 근거 없는 패턴은 여전히 0행이다. 그대로 통과한다 |
| `tests/unit/test_review.py:354`·`572` | `scenario_context` 검증. §7 약점 3의 동결 규칙과 함께 본다 |
| `tests/integration/test_pipeline.py:823`·`847`·`874`·`939` | `_review_stages`(`:796-803`)의 기대값이 사다리 전체로 바뀐다 |
| `docs/database-schema.md:212-246` | 표 정의 · `:230`의 유일 writer 서술 · `:232-235`의 "0행 또는 1행" 규약 · `done`의 뜻 |
| `app/backend/app/services/review.py:5-24` | 모듈 docstring이 "지우고 다시 넣는다"를 규약으로 적고 있다 |
| `docs/design/2026-08-25-learning-coach-agent-design.md:146-151` | "재발 시 상위 단계 행은 삭제한다"(공백 1)가 이 설계로 뒤집힌다. **조용히 덮지 말고 뒤집힌 사실과 근거를 함께 남긴다** |

---

## 7. 이 설계의 약점

1. **정체성이 여전히 가변 이력 위에 서 있다.** `cycle_started_at`은 재분석이 그 발화를 지우면
   움직인다. 카운터보다 낫지만(§2.3) **불변은 아니다** — 은퇴한 `superseded` 행에 학습자 이력이
   붙어 있으면 그 이력이 화면에서 갈 곳을 잃는다. 진짜 불변 정체성은 "과제를 발급한 사건"을
   따로 저장할 때만 나오고, 그것은 이 표를 발급 로그와 투영으로 쪼개는 더 큰 변경이다. **하지 않았다.**
2. **`superseded` 잔재가 단조 증가한다.** 정리 정책이 없다. 재분석이 잦으면 쌓인다.
   지금 규모(7행)에서 비용은 0이라 정책을 발명하지 않았지만, 이것은 미룬 결정이다.
3. **`scenario_context`가 과거 행에서 드리프트한다.** 지금 값은 재계산 시점의 **최신** occurrence
   원문이다(`_HISTORY_SQL:96-106`). 사다리 행이 쌓이면 1단계 행의 문맥이 나중 오류의 원문으로
   덮여 "그때 무엇으로 연습했는가"가 틀어진다. → **완화**: upsert의 `do update`에서
   `scenario_context`를 **`status='pending'`인 행에만** 갱신하고 `done`·`abandoned`에서 동결한다.
   완화는 했지만 **열린 행의 문맥은 여전히 바뀐다** — 학습자가 어제 본 문구와 오늘 본 문구가 다를 수 있다.
4. **`abandoned` 판정이 "현재 사이클보다 과거"라는 시각 비교에 의존한다.** 같은 순간에 재발과
   정답이 있는 경계에서 `fold_stages`의 간격 조건에 기대는데, 그 조건이 유일한 방벽이라는 것을
   `review.py:76-80`이 이미 관측해 두었다. 새 상태 하나가 그 방벽에 더 얹힌다.
5. **발음 패턴은 여전히 이 히스토리에 들어오지 않는다.** `next_review_at`이 영구히 null이고
   `review_tasks` 행이 생기지 않는다(`learning-coach-agent-design.md:169-181`, 알고 남긴 축소).
   그래서 히스토리 화면은 발음 복습을 **못 보여준다.** 이 설계는 그 이월을 풀지 않는다.
6. **`010`이 순서 갈라짐을 하나 더 만든다** (§5.2). 008이 `review_tasks`를 건드리면 실제 사고가 된다.

---

## 8. 캡틴에게 물을 것

| # | 질문 | 왜 내가 못 정하나 |
|---|---|---|
| 1 | **008(주간 리포트) 예약을 011로 옮길까?** 유도 1의 논리가 지금은 008에 반대한다(§5.2) | 캡틴 결정(§3 유도 1)을 뒤집는 일이고 `TASK-26`의 번호를 건드린다 |
| 2 | **학습자가 복습 과제를 손으로 "건너뛰기/완료" 표시하는가?** 있으면 `TASK-3`에서 학습자 행동 이력 표가 필요하고, 없으면 파생 이력만으로 끝난다 | 제품 결정이다. 요구사항 어디에도 없다 |
| 3 | **화면에 학습자용 표시 번호(#1, #2 …)가 필요한가**, "3단계 중 2단계"로 충분한가? (§2.1) | 캡틴 문구의 "번호"를 나는 식별자로 읽었다. 표시 번호를 원하면 순번 컬럼이 하나 더 필요하다 |
| 4 | **기존 7행 삭제를 승인하는가?** 무손실 근거는 §5.4에 있고 `recompute_all`이 동등한 행을 복원한다 | DB 행을 지우는 일이고, 되돌리려면 재계산을 다시 돌려야 한다 |
| 5 | **히스토리 화면에 발음 복습이 안 보이는 것을 수용하는가?** (약점 5) | 이월된 축소를 푸는 것은 자매 설계와의 접합면을 넓히는 별개 판단이다 |

---

## 9. 내가 유도한 것 — 9건. 틀렸으면 그 줄만 뒤집으면 된다

| # | 유도 | 뒤집으면 무엇이 달라지는가 |
|---|---|---|
| 1 | **"번호" = 화면·API가 과제를 가리키는 식별자(`id`)**이고 `review_stage`의 1로 되돌아감은 버그가 아니다 (§2.1) | 재발 시 단계가 1로 가는 것 자체를 고쳐야 한다 → 1·3·7일 스케줄의 의미가 바뀐다(설계서 §4.1을 다시 연다) |
| 2 | **자연키가 정체성, `id`는 upsert로 보존되는 손잡이** (§2.2) | 대리키를 정체성으로 삼으면 재계산이 "어느 행이 그 과제인가"를 알 방법이 없어 delete+insert로 돌아간다 |
| 3 | **사이클 판별자는 재발 시각(A), 카운터(B) 아니다** (§2.3) | B를 쓰면 과거 재발 하나가 지워질 때 뒤의 모든 사이클 번호가 밀린다 — 지금의 병이 다른 옷으로 돌아온다 |
| 4 | **파생 이력은 같은 표, 학습자 행동은 이 표 밖** (§3.1) | 한 표에 합치면 재계산이 학습자 상태를 지운다(§1.2의 4번). 파생을 별도 이력 표에 또 적으면 같은 사실이 두 곳으로 갈라진다 |
| 5 | **학습자 행동 표를 지금 만들지 않고 `TASK-3`으로 연기한다** (§3.3) | 지금 만들면 writer 없는 표와 발명한 값역이 남는다. 반대로 연기가 틀렸다면 `TASK-3`이 표를 새로 만드는 마이그레이션을 하나 더 쓴다(비용은 그것뿐) |
| 6 | **`status` CHECK에서 `skipped`를 뺀다** (§3.3) | 남기면 `TASK-3` 구현자가 그 칸에 학습자 상태를 넣는 것이 정상 행동이 되고, 다음 재계산이 조용히 지운다 |
| 7 | **`done`의 뜻을 "사이클 완주" → "이 단계 완주"로 재해석한다** (§3.3) | 유지하면 접힌 중간 단계의 상태를 표현할 값이 없어 사다리 행이 전부 `pending`으로 남는다 |
| 8 | **기존 7행은 삭제하고 재계산으로 복원한다** (§5.4) | SQL 백필을 택하면 `greatest(...)` 재발 로직이 마이그레이션에 복제된다 — 두 곳이 갈라진다 |
| 9 | **`scenario_context`는 `pending` 행에서만 갱신하고 완주·중단 행에서 동결한다** (약점 3) | 동결하지 않으면 과거 사다리 행의 연습 문구가 나중 오류의 원문으로 덮여 히스토리가 사실과 어긋난다 |

---

_작성: 2026-09-08 · `TASK-12`. 인용한 `파일:줄`은 전부 이 세션에서 직접 열어 확인했다._
_dev DB 수치(과제 7행 · `created_at` 2종 · 패턴 8행 · `users.timezone` 기본값)는 읽기 전용 psql 조회 출력이다._
