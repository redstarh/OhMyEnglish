# 발음 패턴에 복습 주기를 부여한다 — R10-6 · R11-9 · AC11-6

> **이 문서가 소유하는 것**: 발음의 재발 판정 기준 · 발음용 복습 주기 규칙 · 초점 허용 집합에
> 발음이 들어오는 경로 · 세 요구사항 판정의 변화.
> **소유하지 않는 것**: 문법 경로의 주기 규칙(`2026-08-25-learning-coach-agent-design.md` §4.1) ·
> 발음 시도 기록의 생명주기(`2026-08-27-pronunciation-echo-design.md` §3.2·§4.3) ·
> 태스크 상태(Backlog.md `TASK-9`).
>
> **범위**: 설계만이다. 이 문서를 쓰면서 코드를 한 줄도 고치지 않았다 — 고칠 자리는 §5·§11이
> `파일:줄`로 지목한다.

---

## 1. 무엇을 닫는가

| 요구사항 | 문구 | 지금 판정 |
|---|---|---|
| **R10-6** (`docs/PRD.md:146`) | 발음 오류도 재사용 가능한 패턴으로 저장해 **이후 학습에 재등장한다** | 저장은 된다(`error_patterns` 1행 실재). **재등장이 안 된다** |
| **R11-9** (`docs/PRD.md:195`) | 발음 시도 이력도 계획 입력에 포함되고, **발음 패턴도 초점 패턴이 될 수 있다** | 앞은 됨, 뒤는 구조적으로 막힘 |
| **AC11-6** (`docs/PRD.md:205`) | 발음 재발화에 반복 실패한 패턴이 **다음 계획의 초점에 포함될 수 있다** | 미충족 |

셋이 같은 뿌리라는 판단은 캡틴 답변이 소유한다 —
`docs/design/2026-09-06-captain-response-to-status-report.md:51`·`:84`.

---

## 2. 지금 막혀 있는 것 — 직접 관측

`error_patterns` 8행 중 발음은 1행이고 `next_review_at`이 **비어 있다**
(2026-09-08 dev DB 읽기 전용 조회, 이 턴에 직접 돌렸다):

```
category                 | pattern_key            | target_form | frequency | next_review_at
pronunciation_intonation | pronunciation_an_as_a  | an_as_a     |         2 | (null)
```

문법 7행은 전부 `next_review_at`이 있고 `review_tasks` 7행이 대응한다. 발음은 0행이다.

**막는 겹은 넷이고, 셋은 이미 문서화된 축소, 하나는 이 문서가 처음 적는다.**

| # | 무엇 | 근거 |
|--:|---|---|
| ① | `recompute`의 호출자가 분석 워커 하나뿐이다 | `app/backend/app/services/analysis.py:467` |
| ② | 그 워커가 넘기는 집합에 발음 패턴이 못 들어온다 — 카테고리 필터(G-8) | `app/backend/app/services/analysis.py:262-268` |
| ③ | 상태 계산 SQL이 `pronunciation_attempts`를 읽지 않는다 | `app/backend/app/services/review.py:83-122` |
| ④ | **`correct` 판정이 패턴에 연결되지 않는다** | `app/backend/app/services/pronunciation.py:380` (`and a.outcome = 'incorrect'`) |

①~③은 `2026-08-25-learning-coach-agent-design.md:168-177`(「구현 공백 4」)가 소유한다.

**④가 이 태스크의 숨은 벽이고, 데이터로 확인했다.** 같은 조회에서:

```
attempt_seq | target_sound | outcome   | linked(pattern_id is not null)
          8 | am_as_i_m    | correct   | f
          9 | w_as_vw      | correct   | f
         10 | an_as_a      | incorrect | t
         11 | an_as_a      | incorrect | t
```

`link_pattern`(`pronunciation.py:434`)은 `incorrect`에만 발화하므로 **정답 시도는 어느 패턴에도
붙지 않는다.** 그래서 `next_review_at`만 채워도 단계가 오르지 않는다 — 문법의 단계 전이 신호는
`pattern_attempts`의 `correct` **행**이고(`review.py:110-118`), 발음에는 그에 대응하는 연결된
행이 영원히 생기지 않는다. **`next_review_at`을 주는 것만으로는 R10-6이 닫히지 않는다.**

**다섯 번째 겹도 있다 — 만성 경로는 이 태스크가 열지 않는다.** `chronic.py:73-74`가
`error_occurrences`를 **inner join**하므로 occurrence가 0인 발음 패턴은 만성 목록에 원리적으로
못 들어온다. 그것을 여는 것은 §4.4 주의 2(발음의 빈도 축과 문법의 빈도 축을 한 정렬에 섞지
않는다)를 정면으로 깨는 일이다 → **발음은 복습 경로 하나로만 들어온다**(§5.1).

---

## 3. 발음의 재발 판정 기준 (인수기준 1)

### 3.1 왜 같은 규칙을 쓸 수 없는가 — 표가 하나다

| | 문법 | 발음 |
|---|---|---|
| 오류가 일어났다 | `error_occurrences` 1행 | — |
| 재시도를 판정했다 | `pattern_attempts` 1행 | — |
| **둘 다** | — | `pronunciation_attempts` 1행 |

문법은 **두 표**가 각각을 담고 재발 앵커가 그 둘의 최대값이다(`review.py:83-95`). 발음은
**한 표**가 둘을 겸한다: Nova가 시범하고(`pending`) 학습자가 따라 말하면 같은 행이 판정으로
닫힌다(`pronunciation.py:176-198`). 즉 **`incorrect` 행 하나가 「그 소리를 틀렸다」와 「재시도에
실패했다」를 동시에 뜻한다.** 이것이 "발생 수 기준 대 시도 수 기준"의 실제 정체다 — 계산식이
다른 것이 아니라 **세는 대상의 개수가 다르다**(문법은 2종, 발음은 1종).

### 3.2 판정 기준 — 확정안

그 패턴의 소리에 대한 `pronunciation_attempts` 행만 본다. **`pattern_id`로 찾지 않고
`target_sound`로 찾는다**(이유는 §5.3).

| 신호 | 조건 | 시각 |
|---|---|---|
| **재발** | `outcome = 'incorrect'` | `resolved_at` |
| **단계 전진** | `outcome = 'correct'` | `resolved_at` |
| **무시** | `outcome in ('pending','unclear')` | — |

세 규칙 모두 **문법과 같은 의미**를 다른 표에서 읽는 것이다:

- `incorrect`가 재발인 것 — `review.py:93`이 문법에서도 `pattern_attempts.outcome='incorrect'`를
  재발에 넣는다.
- `correct`만 전진시키는 것 — `review.py:113`.
- `unclear`를 양쪽에서 빼는 것 — `docs/database-schema.md:339`("판정할 수 없는 발화를
  `incorrect`로 강제하면 숙련도가 부당하게 깎인다"). `pending`은 계획 입력에서도 이미
  제외된다(`plan_input.py:72`).

**`target_sound is null` 행은 자동으로 빠진다** — 소리를 못 짚은 행이라 어느 패턴의 것인지
정의되지 않는다. 한글 전사 보조 신호(`pronunciation.py:89`, `outcome='unclear'`)가 그 경우이고
`unclear` 규칙과 이중으로 걸린다.

⛔ **네 번째 규칙 — 보조 신호는 복습 단계를 전진시키지 않는다** (사용자 판정 2026-09-11 ·
`TASK-74` · 캡틴 지시 대장 결정 59). 이력 쿼리가 `signal_source = 'nova_tool'` 로 **허용 목록**을
걸어 집행한다. **복습 시계는 tool 경로에만 걸린다.**

- **왜 필요한가.** 위 세 규칙과 `target_sound` 규칙만으로도 지금은 보조 신호가 걸러지지만, 그
  근거가 **전부 호출자 쪽 관례**다 — 유일한 생산자 `note_transcript` 가 `unclear` +
  `target_sound=None` 만 낸다는 사실 하나다. `AssistOutcome` 의 타입 잠금은 절반만 막는다:
  `incorrect` 는 값역에 없지만 **`correct` 는 허용된다.** 새 생산자가 `outcome='correct'` +
  `target_sound` 를 주는 순간 학습자가 다시 말하지 않았는데 단계가 접힌다.
- **왜 자격이 없는가.** 한글 전사는 「학습자가 어느 소리를 틀렸다」가 아니라 「ASR 이 언어 판별을
  뒤집었다」는 관측이라 소리를 지목하지 못한다. 같은 축의 원칙을 결정 54 ①이 먼저 정했다 —
  틀린 기록으로 시계를 돌리면 엉뚱한 소리에 걸린다.
- **기록은 그대로 남는다.** R10-4 의 관측·기록은 영향을 받지 않고, 계획 입력
  (`plan_input.py`)과 빈도 재계산도 이미 `target_sound`·`pattern_id` 로 같은 행을 거른다.
  즉 이 규칙이 바꾸는 것은 **단계 전진 자격** 하나다.
- **허용 목록으로 쓴 이유.** `signal_source` 값역에 값이 늘면 새 값이 기본으로 배제된다.
  배제 목록으로 쓰면 값을 더할 때마다 이 줄을 같이 고쳐야 하고, 그것을 빠뜨리는 것이 원래
  결함의 모양이다.

### 3.3 시각 축은 `resolved_at`이다 — `utterances.created_at`이 아니다

문법 경로는 **발화 시각**을 쓴다. 그 이유는 `analyze_utterance` job이 재시도되고 결과가 발화 단위
replace라서 벽시계를 쓰면 재실행마다 예정일이 밀리는 것이다(`review.py:17-19`). **발음 경로에는
그 이유가 없다** — 시도 행은 웹소켓 이벤트에서 **한 번 쓰이고 다시 계산되지 않는다.**
`resolved_at`은 그 한 번에 확정되므로 앵커로서 안정적이다.

그리고 이것은 새 경계가 아니다. `docs/database-schema.md:139-140`이 **이미**
"문법 경로의 `last_seen_at`은 발화 시각, 발음 경로는 시도의 판정 시각(`resolved_at`)"이라고
정해 두었다 — 같은 결정을 재사용한다.

`utterance_id`를 쓰지 않는 두 번째 이유: 그 컬럼은 nullable이고 `on delete set null`이다
(`docs/database-schema.md:281`) → join하면 발화가 지워진 판정 기록이 **조용히 사라진다.**

---

## 4. 발음용 복습 주기 규칙 (인수기준 2)

### 4.1 결론 — **1·3·7일을 그대로 쓴다**

`STAGE_DAYS = (1, 3, 7)`(`review.py:43`)과 `FINAL_STAGE = 3`을 발음에도 적용한다.
`fold_stages`(`review.py:165-209`)를 **그대로 재사용한다** — 순수 함수라 표가 무엇이든 상관없다.

### 4.2 근거 — 다른 값을 쓰면 그것이 발명값이다

- 1·3·7일은 **문서로 확정된 값이다**: `docs/database-schema.md:377`("최소 1일, 3일, 7일 간격
  3단계") · `review.py:41-42`가 그 근거를 명시한다. 이 리포에서 근거가 있는 유일한 주기 숫자다.
- §3의 차이는 **무엇을 세는가**의 차이이고 **간격의 차이가 아니다.** 재발 판정이 다르다는 사실은
  "며칠 뒤에 다시 물어야 하는가"에 대해 아무 것도 말해 주지 않는다.
- 발음에 다른 곡선(예: 0.5·2·5일)이 낫다는 근거가 이 리포에 **0건**이다. 정하면 그것은
  `<work_continuity>` ③이 금지하는 발명값이다 → **캡틴 질문 Q2로 올린다**(§10).

### 4.3 그래서 완주 조건이 같다

- 3단계를 재발 없이 완주 → `mastery_score = 100`, 재발 → `0`. 중간값 없음
  (`docs/database-schema.md:147-150`, 캡틴 결정 2026-09-03). **발음도 같은 상태 마커를 쓴다** —
  발음용 점수 체계를 만들지 않는다(`requirements-summary.md`가 발음 점수·등급을 "하지 않는 것"에
  두었고, 2026-09-04 캡틴 결정이 발음 성과를 난이도 판단에 넣는 것을 MVP 이후로 미뤘다).
- 예정일 **전**의 정답은 단계를 올리지 않는다 → 한 세션에서 세 번 맞혀 11일을 건너뛰는 경로가
  발음에서도 막힌다. `fold_stages`를 재사용하는 것이 이 방어를 복제 없이 얻는 방법이다.
- 예정일을 한참 지나 맞힌 것은 통과시킨다(상한을 발명하지 않는다).

### 4.4 실측 데이터에 적용하면 — 예측값 (아직 돌리지 않았다)

`an_as_a`의 `incorrect` 두 건은 `2026-08-31 22:21:14+00`과 `2026-09-03 13:51:26+00`이고
그 뒤 `correct`가 0건이다(§2의 조회). 따라서:

- 재발 앵커 = `2026-09-03 13:51:26+00` (두 값의 최대)
- `stage = 1`, `next_review_at = 2026-09-04 13:51:26+00` → **이미 예정일이 지났다**
- `review_tasks` 1행 (`review_stage=1`, `status='pending'`,
  `scenario_context = "I had a project meeting yesterday."` — §5.4)

⚠️ **이 셋은 규칙을 손으로 적용한 예측이고 실행 출력이 아니다.** 구현 후 백필
(`recompute_all`, `review.py:373`)로 확인할 값이다 — 확인 전에 "닫혔다"고 적지 않는다.

---

## 5. 초점 허용 집합에 발음이 들어오는 경로 (인수기준 3)

### 5.1 경로는 하나다 — 복습 목록

허용 집합은 `plan.py:391-393`에서 만들어진다:
`{복습 예정}` ∪ `{만성 지표}`. **만성 쪽은 열지 않는다**(§2의 다섯 번째 겹).

좋은 소식: **`_DUE_REVIEWS_SQL`에는 카테고리 필터가 없다**(`review.py:131-139`) — `next_review_at`이
채워지는 순간 발음 패턴은 **쿼리 수정 없이** 복습 목록에 들어오고, 허용 집합에도
`_format_due_reviews`(`plan.py:180-193`)의 `pattern_id`와 함께 실린다. 그래서 §2의 ④와
`next_review_at`을 채우는 배선(§5.2·§5.3)만 하면 초점 경로가 열린다.

`models/plan.py:271-277`이 만성 최상위를 초점에 강제하므로(AC11-2), 만성 목록이 비지 않은 지금
데이터에서는 발음이 **초점 2개 중 두 번째 자리**로 들어온다. `focus`는 1~2개이므로 그 자리가
있다. 만성이 0건이면 발음 단독 초점도 성립한다.

### 5.2 배선 — 상태 계산을 카테고리로 분기한다

**`next_review_at`·`mastery_score`의 유일한 writer는 `review.py`다**
(`docs/database-schema.md:145`) — 그 불변조건을 지킨다. `pronunciation.py`가 그 컬럼을 쓰지 않는다
(자매 설계도 `2026-08-27-pronunciation-echo-design.md:196`에서 "이 설계는 값을 쓰지 않는다"고
스스로 정했다).

`recompute(conn, pattern_id)`가 **먼저 그 패턴의 `category`를 읽고** 이력 쿼리를 고른다:

| category | 이력 쿼리 |
|---|---|
| `pronunciation_intonation` | **신설** `_PRONUNCIATION_HISTORY_SQL` (§5.3) |
| 그 외 6종 | 기존 `_HISTORY_SQL` (`review.py:83-122`) |

그 뒤는 **완전히 공유한다** — `fold_stages` → `_APPLY_PATTERN_SQL` → `review_tasks`.
호출자 시그니처가 바뀌지 않으므로 `analysis.py`도 `recompute_all`(백필)도 손대지 않는다.

⚠️ ~~`review_tasks` **0~1행 replace**~~ → ⛔ **뒤집혔다** (2026-09-08 · `TASK-43` · 마이그레이션
010). 이 문장은 원래 *"`review_tasks` 0~1행 replace"*였다 — 아래 §7 L1 과 같은 사유로 함께 고쳤다.
**지금은 자연키 `(pattern_id, cycle_started_at, review_stage)` upsert 이고 사이클마다 사다리 행이
남는다.** 발음 경로가 이 공유 구간을 그대로 쓰므로 **발음 복습 과제도 히스토리에 쌓인다** — 그것이
§9 약점 5 가 요구사항으로 올린 바로 그것이고, `tests/unit/test_pronunciation_review.py` 가 발음
패턴의 사다리 `[(1,"done"),(2,"pending")]`를 단정해 이미 잠갔다.
**정본**: `docs/design/2026-09-08-review-task-history-design.md` · `docs/database-schema.md` 의
`review_tasks` 절 · `db/migrations/010_review_task_history.sql`.

**분기를 호출자에 두지 않는 이유**: 두 곳에 두면 한쪽이 조용히 낡고, 발음 패턴에 문법 모양의
상태가 계산되는 조합이 생긴다.

### 5.3 신설 이력 쿼리 — `target_sound`로 잇는다

```sql
-- 발음 패턴 하나의 이력. `pattern_id`로 잇지 않는 이유는 아래 ⚠️.
with sound as (
      select target_form as key from error_patterns where id = $1
)
select (select max(a.resolved_at)
          from pronunciation_attempts a
          join learning_sessions s on s.id = a.session_id
          join error_patterns p on p.id = $1
         where s.user_id = p.user_id
           and btrim(a.target_sound) = (select key from sound)
           and a.outcome = 'incorrect')                       as relapse_at,
       …  -- correct_times: 같은 조건 + outcome='correct' + resolved_at > relapse_at,
          --                array_agg(order by resolved_at)
       …  -- scenario_context: 가장 최근 incorrect 행의 target_form (§5.4)
```

⚠️ **`pattern_id`로 잇지 않는다.** §2의 ④ — `correct` 행은 `pattern_id`가 영원히 null이다.
그것을 고치는 대안(정답 시도도 연결한다)은 §9-2에서 기각했다.

⚠️ **`btrim(a.target_sound) = error_patterns.target_form`이 이 쿼리의 전제조건이다.** 근거는
발명이 아니라 두 곳의 확정 서술이다: `docs/database-schema.md:162-166`("발음 패턴의 일반형은
`target_sound`다") · `pronunciation.py:371-385`의 upsert가 `target_form`에 `btrim(target_sound)`를
넣고 conflict에서도 같은 값을 다시 쓴다. **`'pronunciation_' || …` 접두사 리터럴을 두 번째
장소에 복사하지 않기 위해** `pattern_key`가 아니라 `target_form`으로 잇는다.

### 5.4 `review_tasks` 행의 내용

| 컬럼 | 값 | 근거 |
|---|---|---|
| `task_type` | `'rephrase'` | CHECK 값역 3개 중 유일하게 지금 쓰는 값(`docs/database-schema.md:240`). "다시 말해보기"는 발음 재발화의 문자 그대로의 뜻이다. **마이그레이션이 필요 없다** |
| `scenario_context` | 가장 최근 `incorrect` 시도의 **`pronunciation_attempts.target_form`** (시범 문장) | 문법이 최신 `original_span`을 쓰는 것과 같은 자리다(`review.py:96-106`). 실측값: `"I had a project meeting yesterday."` |
| `review_stage`·`due_at`·`status` | `fold_stages` 결과 그대로 | 공유 경로 |

⛔ **패턴의 `target_form`(= `an_as_a`)을 `scenario_context`에 넣지 않는다** — 소리 키는 연습할
문장이 아니다. 이것은 1차수 F-2와 같은 종류의 오류다(`docs/database-schema.md:152-166`).

**발음 과제임은 `pattern_id → category`로 유도한다.** `review_tasks`에 새 컬럼을 두지 않는다 —
`user_id`를 두지 않은 것과 같은 규약(`docs/database-schema.md:226-227`).

### 5.5 재계산 트리거 — 여기가 ④를 닫는 자리

지금 `link_pattern`은 `record_attempt`(`pronunciation.py:216`)와
`resolve_dangling`(`pronunciation.py:346`) 두 곳에서 불린다. 그 **바로 뒤**에 재계산 호출을 넣는다.

```
판정이 온다 (correct / incorrect / unclear)
  → link_pattern(attempt_id)          # 기존. incorrect일 때만 실효 (그대로 둔다)
  → refresh_review(attempt_id)        # 신설. 그 소리의 기존 패턴을 찾아 review.recompute 호출
```

`refresh_review`는 **패턴을 만들지 않는다** — `btrim(target_sound)`로 기존 행을 찾고 없으면
no-op이다. 그래서 한 번도 틀린 적 없는 소리를 맞힌 것(실측: `am_as_i_m` `correct`)은 아무 것도
만들지 않는다. **`correct`가 이 경로로 처음 재계산을 발화시키는 것**이 ④의 해소다.

`pronunciation.py → review.py` import는 순환이 아니다 — `review.py`는 `models.analysis`만
import한다(`review.py:37`).

두 진입점 모두 이미 자기 트랜잭션 안이므로(`pronunciation.py:149`·`:327`) 재계산이 시도 기록과
한 단위로 커밋된다.

### 5.6 프롬프트 문구 — 어디를 어떻게 고치는가 (⛔ 이 문서는 고치지 않았다)

**① `app/backend/app/services/plan.py:136-138` — `_PRONUNCIATION_NOTE`.** 지금:

```
Pronunciation attempts (context only, never a focus source — counted per attempt, not per error
occurrence, so do not rank these against the grammar counts above):
```

교체안 (⚠️ **"context only"를 첫 줄에 유지한다** — `tests/unit/test_plan.py:108`이 제목 줄에서
그 문구를 재고, 제목이 `):`로 끝나는 규약도 유지한다):

```
Pronunciation attempts (context only — these tallies carry no pattern_id, so do not pick a focus
from this section; a pronunciation pattern that is ready to revisit appears in "Due for review
today" above with its pattern_id. Counted per attempt, not per error occurrence, so do not rank
these against the grammar counts above):
```

**왜 "never a focus source"를 통째로 지우지 않는가**: 이 절 자체는 여전히 초점 출처가 아니다 —
`PronunciationTally`(`plan_input.py:119-127`)에 `pattern_id`가 없어서 여기서 고르면 모델이 UUID를
지어내고, 그 값은 `focus_pattern_ids`에 FK가 없어 조용히 저장된다(재리뷰 라운드 2의 Critical-1,
`plan.py:24-28`). **바뀌는 것은 "발음은 초점이 될 수 없다"이지 "이 목록에서 고른다"가 아니다.**

**② `app/backend/app/services/plan.py:146-149` — `_OUTPUT_SPEC`의 `- focus:`: 고치지 않는다.**
지금도 "Due for review today"·"Chronic metrics" 두 목록을 이름으로 지목하고 그것이 계속 참이다.
발음은 첫 목록 **안에서** 들어온다. 문구를 건드리면 라운드 2가 닫은 경로가 되살아난다.

**③ `app/backend/app/services/plan.py:49-51` — 모듈 docstring: 두 문장이 거짓이 된다.**
"`PronunciationTally`에는 `target_sound`만 있어 애초에 유효한 `FocusPattern`을 만들 수 없다"는
**그 절에 대해서만** 참이므로 그렇게 좁혀 적고, "복습 스케줄에 들어오지 않는 것은 「구현 공백 4」의
알고 남긴 축소다"는 **이 문서로 해소됐다**고 바꾼다(철회 사실과 근거를 함께 남긴다).

**④ 발음 줄의 표시(권장 · 유도)**: `_format_due_reviews`(`plan.py:188-193`)는
`target form "an_as_a"`로 낸다 — 모델이 문장으로 오독할 여지가 있다. 발음 카테고리일 때
`target sound "an_as_a"`로 낱말만 바꾸는 안을 제시한다. `category`가 이미 줄에 실리므로 분기
재료는 있다. **유도이므로 §9-4에 적었다.**

---

## 6. 마이그레이션 — 필요 없다

컬럼·표·CHECK 값역을 **하나도 늘리지 않는다**: `next_review_at`·`mastery_score`·`review_tasks`는
Phase1부터 있고, `task_type='rephrase'`는 기존 값역, 필요한 시도 데이터는 003~005가 전부 갖고
있다. 그래서 `010`을 발급하지 않는다(008은 `TASK-26` 예약).

**인덱스도 추가하지 않는다.** 신설 쿼리는 `pronunciation_attempts`를 `target_sound`·`outcome`으로
거르는데 그 표는 지금 4행이고 인덱스 2개는 다른 경로용이다(`docs/database-schema.md:297`).
관측 없이 성능을 추측해 인덱스를 만들지 않는다 — 필요해지는 시점은 §9-5에 적었다.

---

## 7. 4 Lenses 검증

### L1. Contract

- **`recompute(conn, pattern_id)`** — 전제: 그 패턴이 실재하고 호출자가 트랜잭션을 갖는다.
  사후: `next_review_at`·`mastery_score`·`review_tasks`가 이력과 정합. 멱등.
  **이 설계가 그 계약을 넓히지 않는다** — 시그니처·멱등성·트랜잭션 요구가 그대로다.
  ⚠️ ~~`review_tasks`**(0~1행)**~~ → ⛔ **이 사후조건은 뒤집혔다** (2026-09-08 · `TASK-43` ·
  마이그레이션 010). **조용히 덮지 않고 뒤집힌 사실과 근거를 함께 남긴다**(코드 리뷰 HIGH-2 —
  이 문서가 `Done` 이고 **살아 있는 정본**이라, 낡은 계약을 읽은 다음 사람이 사다리 행을 버그로
  판정할 경로가 열려 있었다).
  - **원래 판정**: 재계산이 그 패턴의 행을 전부 지운 뒤 현재 상태 1행만 넣었다(패턴당 0행 또는
    1행 · 캡틴 결정 2026-09-03). 무손실 근거는 완주·재발 여부를 이력에서 언제든 다시 계산한다는
    것이었다.
  - **왜 뒤집혔나**: 그 근거는 **파생값에 대해서만** 참이다 — `id`(화면·API 가 과제를 가리키는
    손잡이) · `created_at` · 학습자가 손으로 만든 상태에는 닿지 않는다. 삭제하면 접힌 중간 단계와
    **끊긴 사이클이 흔적 없이 사라져** "어디서 끊겼는가"를 복원할 수 없다.
  - **지금의 판정**: 사후조건은 **「현재 사이클 행이 사다리와 일치하고, 과거 사이클 행은 파생값이
    덮이지 않는다(종료 상태를 못 받은 `pending` 하나만 `abandoned`로 내려간다)」**다. 정체성은
    자연키 `(pattern_id, cycle_started_at, review_stage)`이고 `id` 는 그 위에서 보존된다.
    값역도 넓어졌다: `pending`·`done`·`abandoned`·`superseded` (`skipped` 는 제거됐다).
  - **정본**: `docs/design/2026-09-08-review-task-history-design.md` §2.2·§3.3·§4 ·
    `docs/database-schema.md` 의 `review_tasks` 절 · `db/migrations/010_review_task_history.sql`.
    ⚠️ 되살리려면 그 설계서를 먼저 뒤집어라 — 이 줄만 고치면 코드와 어긋난다.
- **`fold_stages`** — 불변: `correct_times`는 오름차순. 신설 쿼리도 `order by resolved_at`으로
  그 전제를 지킨다. 순서가 흐트러지면 단계가 **예외도 실패도 없이** 틀린다(`review.py:81-82`).
- **`refresh_review(conn, attempt_id)`** — 사후: 패턴이 없으면 아무 것도 바뀌지 않는다(no-op).
  ⛔ **패턴을 만들지 않는다**가 계약이다. 만들면 `correct` 한 번으로 오류 패턴이 태어난다.
- **불변조건 유지**: `next_review_at`·`mastery_score`의 writer는 `review.py` 하나
  (`docs/database-schema.md:145`). `frequency`의 writer 2개 구도도 그대로다 — 이 설계는
  `frequency`를 쓰지 않는다.

### L2. Boundary

| 경계 | 넘는 것 | 변환·검증 |
|---|---|---|
| 표 → 표 | 문법은 2표, 발음은 1표 | 카테고리 분기(§5.2). 한 쿼리에 union하지 않는다 — 시각 축이 다르다 |
| 시각 | 발화 시각 ↔ `resolved_at` | §3.3. 둘 다 `timestamptz`이고 간격 연산은 `timedelta`라 타임존 무관 |
| 정체성 | `pattern_id` ↔ `btrim(target_sound)` | §5.3. `target_form = btrim(target_sound)` 규약에 의존한다(명시) |
| 카테고리 | 발음 축 ↔ 문법 축 | 만성 목록을 열지 않아 `frequency` 정렬이 섞이지 않는다(§4.4 주의 2 유지) |
| null | `target_sound is null`·`utterance_id is null` | 전자는 조건에서 제외, 후자는 join하지 않는다 |
| 계획 프롬프트 | 발음 절 ↔ 복습 목록 | 절에는 id가 없고 목록에는 있다 — §5.6이 그 차이를 문장으로 말한다 |

### L3. Failure

- **판정이 오지 않는다** → 세션 종료가 `pending`을 `incorrect`로 수렴시키고
  (`pronunciation.py:292`) 그 경로에도 `refresh_review`가 붙는다(§5.5) → 재발로 기록된다.
- **재계산이 실패한다** → 두 진입점의 트랜잭션이 롤백되어 시도 기록도 함께 사라진다.
  ⚠️ **이것은 지금보다 나빠지는 유일한 지점이다** — 지금은 재계산이 없으니 실패할 것도 없다.
  판단: 부분 실행(시도는 남고 예정일은 안 남는 상태)보다 낫다. `link_pattern`이 이미 같은
  트랜잭션에 있으므로 새 원자성 경계를 만드는 것도 아니다(`pronunciation.py:454-455`).
- **패턴이 없는데 `correct`가 온다** → no-op(§5.5). 실측 `am_as_i_m`이 그 경우다.
- **소리 키가 갈라진다** (`th_as_s` ↔ `theta_to_s`) → 갈라진 쪽이 별 패턴이 되어 각자 1단계에서
  시작한다. **이 설계가 만든 결함이 아니다** — `pronunciation.py:446-452`가 소유한 기존 함정이고,
  복습이 생김으로써 **눈에 보이게 된다**(같은 소리의 복습이 둘로 뜬다).
- **재발 후 재계산** → `fold_stages`는 마지막 재발 이후만 접으므로 100 → 0이 되고 1단계로
  돌아간다. 완주 이력은 시도 행에 남아 재계산 가능하다.

### L4. Dependency

- **호출 순서**: `link_pattern` → `refresh_review`. 뒤집으면 `incorrect` 첫 발생에서 패턴이
  아직 없어 재계산이 no-op이 되고, **그 시도가 예정일을 못 받는다.** 순서가 계약이다.
- **`recompute`는 `frequency`를 읽지 않는다** → 재계산과 `_RECOUNT_PATTERN_FROM_ATTEMPTS_SQL`의
  순서는 자유다(`analysis.py:462-466`이 문법 쪽에서 같은 사실을 실측으로 확정했다).
- **import 방향**: `pronunciation → review` 단방향, 순환 없음(§5.5).
- **소비자 순서**: 예정일은 시도 시점에 써지고 계획 job은 세션 종료 후 돈다 → 계획이 읽을 때
  이미 값이 있다. 기존 발음 패턴 1행은 **백필**(`recompute_all`)이 필요하다.
- **초점 강제와의 상호작용**: `deepest_recurrence`(`chronic.py:105`)는 만성 목록만 보므로 발음이
  최상위가 될 수 없다 → 발음은 항상 강제된 자리 **밖**의 슬롯을 쓴다(§5.1).

---

## 8. 세 판정이 어떻게 바뀌는가 (인수기준 4)

| 요구사항 | 지금 | 이 설계 적용 후 | **판정의 증거는 무엇인가** |
|---|---|---|---|
| **R10-6** — 이후 학습에 재등장한다 | 부분(저장만) | **충족** — 발음 패턴이 `next_review_at`을 받아 복습 목록에 뜨고 `review_tasks` 행이 생긴다 | `error_patterns`의 발음 행에 `next_review_at is not null`, 대응 `review_tasks` 1행 |
| **R11-9** — 계획 입력 + 초점 가능 | 부분(입력만) | **충족** — 두 갈래 모두. 발음이 "Due for review today"에 `pattern_id`와 함께 실려 허용 집합에 들어간다 | `build_plan_prompt` 출력에 발음 패턴 줄 + `allowed_pattern_ids`에 그 id 포함 |
| **AC11-6** — 초점에 포함될 수 있다 | 미충족 | **충족 가능**(강제가 아니다 — "될 수 있다"가 요구사항 문구다) | 실물 계획 1회에서 발음 id가 `focus`에 들어오거나, 최소한 **거부되지 않는다**는 것 |

⚠️ **셋 다 "설계로 닫았다"가 아니라 "구현 + 백필 + 실물 1회로 닫힌다".** §4.4의 값은 예측이다.

**AS11(확인 시나리오)이 틀리게 된다.** `docs/design/2026-09-04-learning-coach-slice2-plan.md:2727`이
"발음 패턴의 `next_review_at`은 영구히 null이므로 **복습 목록 경로로는 검증할 수 없다**"고 적었고,
이 설계가 그 전제를 뒤집는다. 새 AS11 문안 (⛔ 이 문서는 그 파일을 고치지 않았다):

```markdown
**AS11 — 발음이 초점 패턴에 들어올 수 있다** (요구사항 AC11-6 · R10-6 · R11-9)
Given 발음 재발화에 실패한 소리가 있고 그 예정일이 지났을 때, When 계획이 생성되면,
Then 그 패턴이 「Due for review today」 목록에 `pattern_id`와 함께 실리고 초점 허용 집합에
들어가며, 모델이 그것을 초점으로 고른 계획이 거부되지 않는다.
```

**AC11-2와 충돌하지 않는다** — 만성 최상위 강제는 그대로이고 발음은 두 번째 슬롯을 쓴다(§5.1).

---

## 9. 이 설계의 약점

1. **복습 시계가 Nova의 선택에 걸려 있다.** 문법은 자유 발화에서 자발적으로 재발하지만
   (`error_occurrences`), 발음 행은 **Nova가 그 소리를 다시 시범해야만** 생긴다. 예정일이 와도
   Nova가 그 소리를 안 다루면 단계가 영원히 1에 머물고 예정일만 밀린 채 목록 맨 위에 쌓인다.
   지금 그것을 유도하는 유일한 장치는 `load_known_sounds`(`pronunciation.py:403`)가 세션 시작
   지시문에 **모든** 소리를 싣는 것이고(`api/ws.py:226`), **예정일로 좁히지 않는다.**
   → 그 필터는 이 태스크의 범위 밖이다. §10 Q1으로 올린다.

   > ⚠️ **이 약점의 크기가 2026-09-09에 측정됐다 — 예상보다 크다** (5차수 · `TASK-13`·`TASK-24`).
   > 실물 세션 2건에서 발음 픽스처(`p1m`·`p1k`·`p2m`)를 흘렸는데 **`pronunciation_attempts` 신규
   > 0행**이었다. 그래서 `refresh_review`가 **발동할 입력 자체가 없었다**(`review_tasks` 10→10 ·
   > `next_review_at` 8→8 — 고장이 아니다).
   > ⛔ **원인은 프롬프트이고 통제 대조로 확정했다**: 같은 오디오·같은 tool 스키마에서 스파이크
   > 프롬프트는 `toolUse` 1건, **앱 프롬프트는 0건**이다. 앱 프롬프트 규칙 9가
   > *"never for a mild accent"* 로 **의도해서** 억제한다(B-2 결정 2026-08-30).
   > **즉 이 약점은 「Nova가 안 다룰 수도 있다」가 아니라 「mild 오류에서는 설계상 안 다룬다」다.**
   > 복습 시계가 도는 조건은 **사람이 마이크로 충분히 심한 오류를 말하는 것**이다 — 기존
   > `pronunciation_attempts` 4행이 전부 그렇게(2026-08-31·09-03 실물 마이크) 생겼다.
   > 실측 전문은 `tests/harness/runs/2026-09-09-run-5.md` 가 소유한다.

   > ## ⛔ 2026-09-09 정정 — 위 블록의 마지막 두 문장이 반증됐음 (`TASK-67`)
   >
   > **「mild 오류에서는 설계상 안 다룬다」가 이 약점을 설명하지 못함.** 위 대조는 `p1m`(mild)
   > 표본으로만 쟀는데, **`p1k`(ASR 이 한글로 전사할 만큼 심한 억양)에서 다시 재니 결과가
   > 달랐음**: 규칙 9 가 *"take it up"* 하라고 한 구간이 맞고 **코칭 발화가 실제로 나오는데도
   > `toolUse` 는 여전히 0건**임. 표본 다섯(위임 회차 3 · 팀리드 재현 2)이 전부 같음.
   >
   > ⛔ **따라서 「사람이 마이크로 충분히 심한 오류를 말하면 시계가 돈다」는 보장되지 않음.**
   > 심한 오류에서도 tool 이 오지 않았으므로 그 조건은 **충분조건이 아님.** 기존 4행이 실물
   > 마이크에서 생긴 것은 사실이지만, 그것이 「심하면 온다」를 뜻하지는 않음 — 그 4행이 생긴
   > 조건이 무엇이었는지는 이 관측으로 좁혀지지 않음.
   >
   > ⚠️ **함께 관측된 것 — 미이행이 tool 하나가 아님.** 그 코칭 발화가 규칙 9 의
   > **`name the sound that was off` 도 이행하지 않았음**(어긋난 소리를 지목하지 않고 문장만
   > 되읽어 줌). 즉 규칙 9 도 절반만 이행됨.
   >
   > ⛔ **원인 미확정.** 후보 넷 전부 열려 있음 — 규칙 10 의 강제력 · 규칙 11 one-per-turn ·
   > 규칙 2 와의 경합 · 모델의 tool 우선순위. **어느 것도 배제하지 못했음.**
   >
   > ✅ **약점 1 자체는 오히려 커졌음.** *"복습 시계가 Nova 의 선택에 걸려 있다"* 는 그대로
   > 참이고, 그 선택을 **유도하는 장치가 프롬프트에 있는데도 안 듣는다**는 것이 더해졌음.
   > 정본은 `TASK-67` 이고 실측은 `tests/harness/runs/2026-09-09-task37-p-layer-agent.md` 임.
2. **정답을 연결하는 대안을 기각했고, 그 대가가 있다.** `correct` 시도에도 `pattern_id`를 채우면
   §5.3의 `target_sound` join이 필요 없어진다. 기각 이유: `_RECOUNT_PATTERN_FROM_ATTEMPTS_SQL`
   (`pronunciation.py:421-431`)이 `where pattern_id = $1`로 세므로 **정답이 `frequency`를 올린다.**
   그리고 `frequency`는 `deepest_recurrence`의 깊이 축이다(`chronic.py:100-102`) → **잘 맞힐수록
   재발이 깊어 보인다.** 대가: 정체성이 `target_sound` 문자열 일치에 의존한다(§5.3의 ⚠️).
3. ~~**`review_tasks`의 정체성 문제를 상속한다.**~~ ⛔ **해소됐다** (2026-09-08 · `TASK-43` ·
   마이그레이션 010). 원래 서술: *"재계산이 delete+insert라서 `id`·`created_at`이 매번 새로 생기고
   `status`가 덮인다 — `2026-08-25-learning-coach-agent-design.md`의 이월 항목이고 캡틴 결정
   19(히스토리 기록)가 걸려 있다. 발음 행이 늘어나 그 미결의 대상이 넓어진다. 이 문서는 그 결정을
   선점하지 않는다."*
   **010이 정체성을 자연키로 옮겨 그 셋을 보존한다** — 그래서 이것은 「상속하는 약점」이 아니라
   **이미 고쳐진 것**이고, 발음 행이 늘어난 것은 미결을 넓힌 것이 아니라 **히스토리에 담기게 된
   것**이다(§9 약점 5가 요구사항으로 올린 그것). 캡틴 결정 19는 010으로 이행됐다.
4. **§5.6-④는 유도다** — `target sound`로 낱말을 바꾸는 것이 모델 오독을 줄인다는 관측이 없다.
5. **성능을 관측하지 않았다.** 시도 4행에서 판단했다. 백필은 패턴 수 × 쿼리 1회이므로 지금
   규모에서 무해하지만, 발음 시도가 수천 행이 되면 `(target_sound, outcome)` 인덱스가 필요해질
   수 있다 — 그때 측정해서 만든다.
6. **`unclear`가 정보를 버린다.** "여러 번 시도했으나 계속 안 들렸다"는 학습 신호일 수 있는데
   양쪽에서 제외된다. 문법과 같은 규칙을 쓰는 대가이고, 다르게 하려면 없는 기준을 발명해야 한다.

---

## 10. 캡틴에게 물을 것

| # | 질문 | 왜 사람이 정해야 하는가 | 기본값(답이 없으면) |
|---|---|---|---|
| **Q1** | 세션 시작 시 Nova에게 싣는 소리 목록을 **예정일이 지난 것 우선**으로 좁힐까? | §9-1. 좁히지 않으면 복습 주기를 줘도 실제로 다시 물어보지 않을 수 있다. 별 태스크 감이다 | 지금처럼 전부 싣는다(이 설계 범위 밖) |
| **Q2** | 발음 주기를 **1·3·7일이 아닌 값**으로 하고 싶은가? | §4.2 — 다른 값의 근거가 리포에 0건이다. 정하면 발명값이 된다 | 1·3·7일(문서 확정값) |
| **Q3** | 발음 복습 과제를 `task_type='rephrase'`로 겸용할지, 값역에 새 코드를 더할지 | §5.4. 후자는 마이그레이션 010과 CHECK 변경이고 되돌리기 스크립트가 0건인 리포다 | `rephrase` 겸용(마이그레이션 없음) |
| **Q4** | 발음 패턴을 **만성 목록**에도 넣고 싶은가? | §2의 다섯 번째 겹. 넣으면 발음의 빈도 축과 문법의 빈도 축이 한 정렬에 섞이고 그것은 §4.4 주의 2를 깬다. AC11-2의 최상위 판정도 바뀐다 | 넣지 않는다(복습 경로 하나) |

---

## 11. 내가 유도한 것 — 6건

각 항목의 **「뒤집으면 무엇이 달라지는가」**를 함께 적는다. 캡틴이 한 줄씩 되돌릴 수 있게.

| # | 유도 | 근거의 성격 | **뒤집으면** |
|--:|---|---|---|
| **D1** | 재발 = `incorrect`의 `resolved_at`, 전진 = `correct`의 `resolved_at`, `unclear`·`pending` 제외 | 문법 규칙(`review.py:93`·`:113`)과 `docs/database-schema.md:339`에서 **이전**했다. 발음 고유 근거는 없다 | `unclear`를 재발로 세면 안 들린 시도가 숙련도를 깎고 예정일이 계속 리셋된다. 발음 패턴이 1단계에서 못 벗어날 확률이 크게 오른다 |
| **D2** | 시각 축을 `resolved_at`으로 (발화 시각이 아니라) | `docs/database-schema.md:139-140`의 기존 결정 재사용 + "시도 행은 재계산되지 않는다"는 관측 | `utterance_id` join으로 바꾸면 `utterance_id is null`인 판정 기록이 이력에서 **조용히 사라진다**(`on delete set null`). 예정일이 과거 값으로 되돌아간다 |
| **D3** | 주기를 1·3·7일로 (발음 전용 곡선을 만들지 않는다) | 문서 확정값 인용. **다른 값을 고르지 않은 것 자체가 판단이다** | 예: 0.5·2·5일로 하면 완주가 11일 → 7.5일로 짧아지고, `RECENT_WINDOW_DAYS=14`("최장 간격의 2배", `plan_input.py:20-21`)의 유도 근거도 함께 바뀐다 |
| **D4** | 만성 경로를 열지 않고 **복습 경로 하나**로 들어온다 | §4.4 주의 2(빈도 축을 섞지 않는다)에서 이전. 캡틴 결정으로 확정된 것은 아니다 | 만성에도 넣으면 `deepest_recurrence`가 발음을 최상위로 뽑을 수 있고 AC11-2의 강제 대상이 바뀐다. 발음이 초점을 **차지하게** 되어 "될 수 있다"가 "된다"로 변한다 |
| **D5** | 정체성을 `btrim(target_sound) = target_form`으로 잇는다(정답 시도를 연결하지 않는다) | `docs/database-schema.md:162-166` + upsert 규약. `frequency` 오염을 피하려는 **내 판단** | 정답도 연결하면 join이 단순해지지만 `frequency`가 부풀고 깊이 축이 뒤집힌다(§9-2). 되돌리려면 recount에 `outcome='incorrect'`를 더해야 하고 그것은 `frequency`의 문서상 정의("시도 수")를 고치는 일이다 |
| **D6** | 발음 줄을 `target sound "…"`로 표시한다(§5.6-④) | 관측 0건. 오독 방지 추측 | 그대로 `target form`이면 모델이 소리 키를 연습 문장으로 오독할 수 있다. 반대로 바꾼 뒤 다른 오독이 생길 수도 있다 — 실물 1회에서 관측할 항목이다 |

**유도가 아닌 것**(문서·코드·데이터에서 직접 온 것): §2의 네 겹 · §5.1의 "카테고리 필터가 없다" ·
§5.5의 호출 순서 · §6의 "마이그레이션 불필요" · §8의 판정 표.

---

## 12. 범위 밖 발견 — 고치지 않고 적는다

1. **`docs/database-schema.md:137-138`·`:303-305`의 "발음 `frequency`는 시도 수"가 코드와
   어긋난다.** `_RECOUNT_PATTERN_FROM_ATTEMPTS_SQL`은 `where pattern_id = $1`로 세고 `pattern_id`는
   `incorrect`에만 붙으므로(§2의 ④) 실제로는 **`incorrect` 시도 수**다. 실측이 일치한다:
   `an_as_a` frequency 2 = incorrect 2건, `am_as_i_m`·`w_as_vw`는 correct라 패턴조차 없다.
   문서를 "시도 수" → "**틀린 시도 수**"로 정정할 자리다.
2. **`plan.py:49-51`의 두 문장이 이 설계로 거짓이 된다** — §5.6-③.
3. ✅ **넷 다 정정됐다** (원래 목록: 학습 코치 설계서의 「구현 공백 4」와 §11 이월,
   슬라이스 2 계획서의 AS11 블록과 그 머리말). 넷 다 "발음은 복습에 들어오지 않는다"를
   전제하고 있었다. 구현 공백 4와 §11 이월은 `TASK-44`(`9df2369`)가, 학습 코치 설계서의
   **AS11 신설**은 `TASK-48`(2026-09-11)이 닫았다. 넷 다 철회 사실과 근거를 남겼다.
   ⚠️ **이 항목에서 줄 번호 인용을 없앴다** — 원래 적었던 `:481`은 §11 이월이 아니라 **AS10**을
   가리키고 있었다(2026-09-11 직접 확인). 줄 번호는 편집마다 밀리므로 절 이름으로 가리킨다(`H-H`).
4. **`load_known_sounds`가 예정일을 보지 않는다** — §9-1 / Q1.
5. **소리 키 값역이 여전히 고정되지 않았다**(`pronunciation.py:446-452`). 캡틴 항목 18이 "실측
   데이터를 늘려 값 범위를 검증"으로 답했고 이 설계는 그것을 선점하지 않는다. 다만 복습이
   생기면 키 갈라짐이 **학습자에게 보이는** 결함이 된다(§7 L3).

---

_작성: 2026-09-08. 원장 `TASK-9`. 이 문서는 설계만이고 코드 변경 0건이다._
_실측 출처: dev DB 읽기 전용 조회 3회(2026-09-08, `error_patterns` 8행 · `pronunciation_attempts`_
_4행 · `review_tasks` 7행) · 인용한 `파일:줄`은 전부 이 세션에서 직접 열어 확인했다._
