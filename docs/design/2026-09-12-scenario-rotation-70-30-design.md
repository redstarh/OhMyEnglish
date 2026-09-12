# 대화 상황 배치 — 반복 70 대 신규 30 (`TASK-4`)

> **결정의 정본은 `docs/ops/captain-instruction-register.md` 의 결정 73·74·75 다.** 이 설계서는 그
> 셋을 코드로 옮기는 방법만 갖는다 — 왜 그렇게 정했는지는 그 대장이 소유하고 여기서 재서술하지 않는다.
>
> **캡틴 원문**: *"주제 9종 : 학습 패턴과 대화 패턴을 기반으로 반복 학습과 신규 주제를 70% : 30%
> 비율로 배치."* (`docs/design/2026-09-06-captain-response-to-status-report.md` §1 항목 7)
>
> 작성 2026-09-12 · 세션 `ohmyenglish-f4` · 브랜치 `design/first-vertical-slice`

---

## §1. 지금 무엇이 어긋나 있나 — 팀리드가 직접 읽어 확인한 것

**⛔ 상황이 3행 들어 있는데 사용자는 1행만 받는다.** `app/backend/app/services/sessions.py` 의
`_CREATE_SESSION_SQL` 이 시나리오를 이렇게 고른다.

```
where s.level = (select u.current_level from users u where u.id = $1)
order by s.created_at, s.id limit 1
```

`scripts/migrate.py` 의 `SEED_SCENARIOS` 는 3행이고 **전부 `category="daily_life"` · `level="A2"`** 다.
⇒ `A2` 사용자는 **항상 `…101`(After work with a colleague)** 만 받고 `…102`·`…103` 은 한 번도
선택되지 않는다. 업무 상황은 시드에 **0행**이다.

**그래서 이 태스크의 무게중심은 시드가 아니다.** 주제를 15종으로 늘려도 이 절이 그대로면 화면은
바뀌지 않는다. 비율이 사는 자리는 **선택 절**이다(결정 73).

`learning_scenarios` 의 컬럼은 `id` · `category`(`daily_life`·`business`·`shadowing` CHECK) ·
`level`(CEFR CHECK) · `title` · `prompt_template` · `created_at` 이다(`db/migrations/001_initial_schema.sql`).
⚠️ **「주제」축을 담는 컬럼은 없다** — 주제는 **행 하나**로 표현한다. `category` 는 무대 종류이고
주제와 다른 축이다. **표 구조를 바꾸지 않는 이유가 이것이다.**

**적용된 마이그레이션 최대 번호는 `015`** 다 — 2026-09-12 에 dev DB 의 `schema_migrations` 를 직접
조회해 얻었다(`015_llm_calls_token_split.sql` · `applied_at` `2026-09-12 01:43:59+00`). 파일 목록의
최대도 같다. ⇒ **이 설계가 발급하는 번호는 `016`** 이다. ⛔ `008` 은 주간 리포트(`TASK-26`)용으로
예약된 빈 자리이므로 쓰지 않는다.

## §2. 정한 것 — 셋 (대장이 정본)

| 결정 | 내용 | 이 설계서의 대응 절 |
|---|---|---|
| 73 | 「반복 70 대 신규 30」은 **대화 상황**에 적용한다 | §4 |
| 74 | 「신규」는 **최근 10회 안에 안 나온 상황**이다 | §4 · §5 |
| 75 | 업무 6종을 **처음부터** 후보에 넣고 `level` 은 `A2` 로 둔다 | §3 |

## §3. 데이터 — 상황 15종

**표 구조를 바꾸지 않는다.** `SEED_SCENARIOS` 상수를 3행에서 15행으로 늘린다. `category` CHECK 에
`business` 가 **이미 있으므로** 값역 변경도 없다.

**기존 3행의 고정 UUID 를 유지하고 `title`·`prompt_template` 만 주제에 맞춘다.** `seed()` 의 upsert 가
그 두 열을 덮고 `category`·`level` 은 **의도적으로 덮지 않는다**(그 스크립트 주석이 근거를 갖는다).

### 일상 9종 — 이름은 `docs/PRD.md` §7 Daily Conversation 그대로

| UUID 끝 | 주제 | `title` | `prompt_template` |
|---|---|---|---|
| `…101` | 하루 일과 | After work with a colleague | You are a friendly colleague chatting with the learner after work. |
| `…102` | 약속 | Weekend plans with a friend | You are a friend catching up with the learner about the weekend. |
| `…103` | 식사 | Deciding what to eat tonight | You are a housemate deciding with the learner what to eat tonight. |
| `…104` | 인사 | Meeting someone for the first time | You are someone the learner has just met. Keep the small talk short and friendly. |
| `…105` | 취미 | Talking about a hobby | You are a friend asking the learner about a hobby they enjoy. |
| `…106` | 감정 | How the day felt | You are a close friend asking the learner how their day felt. |
| `…107` | 길 묻기 | Asking the way to a station | You are a passer-by the learner stops to ask for directions. |
| `…108` | 작은 부탁 | Asking a small favour | You are a neighbour the learner asks for a small favour. |
| `…109` | 의견 말하기 | Giving an opinion about a film | You are a friend asking the learner what they thought about a film. |

⚠️ `…101`·`…102` 는 기존 문구를 그대로 두고 주제만 배정했다. `…103` 은 *"Tonight's plans at home"* 에서
「식사」로 옮겼다 — 집·오늘 밤이라는 무대를 유지하면서 9종의 한 자리를 채우는 가장 가까운 이동이다.

### 업무 6종 — 이름은 `docs/PRD.md` §7 Business English 그대로 · `level` 은 `A2`

| UUID 끝 | 주제 | `title` | `prompt_template` |
|---|---|---|---|
| `…110` | daily update | Daily update in a short stand-up | You are a teammate listening to the learner's short daily update. |
| `…111` | blocker 공유 | Sharing a blocker | You are a teammate the learner tells about something blocking their work. |
| `…112` | 일정 변경 | Moving a deadline | You are a teammate the learner asks to move a deadline. |
| `…113` | 우선순위 조율 | Agreeing what comes first | You are a teammate deciding with the learner which task comes first. |
| `…114` | incident update | Reporting a small service problem | You are a teammate the learner reports a small service problem to. |
| `…115` | stakeholder 보고 | Short report to a manager | You are a manager listening to the learner's short project report. |

⛔ **업무 6종의 `level` 을 `A2` 로 둔다 — 올리지 않는다.** 근거는 결정 75 의 완화 조항이고, 그것이
`h-doc` 학습자 프로필의 경고(*"AWS 보고 수준 문형으로 예문을 만들면 첫 세션에서 얼어붙는다"*)를 피하는
장치다. ⚠️ **무대는 업무이고 문형 난이도는 일상과 같다** — 이 구분이 이 설계의 안전장치 전부다.

⛔ 문구에 **질문을 넣지 않는다.** 결정 14 가 시나리오를 「무대」로, 계획을 「목표」로 갈랐다 — 질문은
계획이 만든다.

## §4. 선택 규칙 — 새 모듈 `app/backend/app/services/scenario_rotation.py`

**`sessions.py` 에 넣지 않는 이유**: 그 모듈이 이미 563줄 · 공개 함수 9개다. 선택 규칙은 「무엇을
근거로 어느 상황을 고르는가」라는 독립된 하나의 일이고 **순수 함수로 뺄 수 있다** ⇒ 독립으로 테스트
가능하다. ⚠️ 새 모듈을 만드는 것이 여기서 **더 단순한** 쪽이다(단순 대안 검토는 §7).

### 순수 함수 — 이력과 후보를 받아 하나를 고른다

```
pick_scenario(
    *,
    recent: Sequence[RecentPick],   # 직전 10회 · 최신 먼저 · (scenario_id, pick)
    candidates: Sequence[Candidate], # 후보 · (scenario_id, last_used_at | None)
) -> Pick | None                     # (scenario_id, pick) · 후보가 0이면 None
```

**규칙**:

1. `new_count` = `recent` 안에서 `pick == "new"` 인 행 수.
2. `recent_ids` = `recent` 의 `scenario_id` 집합.
3. `new_candidates` = `candidates` 중 `recent_ids` 에 **없는** 것 · `repeat_candidates` = 있는 것.
4. **`new_count < 3` 이고 `new_candidates` 가 비지 않으면 신규**, 아니면 반복을 고른다.
5. 고르려는 쪽이 비면 **다른 쪽으로 넘어간다**(멈추지 않는다).
6. 고른 묶음 안에서는 **`last_used_at` 이 가장 이른 것** — `None`(한 번도 안 쓴 것)이 가장 이르다.
   동률은 `scenario_id` 로 가른다(결정론을 위해).
7. `candidates` 가 0이면 `None` 을 낸다.

⛔ **난수를 쓰지 않는다.** 같은 입력에 같은 출력을 내는 것이 §6 의 검증을 가능하게 하는 조건이다.

**왜 문턱이 3인가**: 창이 10회이고 신규가 30% 이므로 한 창에 3회다(결정 74 가 창 10 의 유도를
갖는다). ⇒ 정상 상태에서 신규가 **정확히 10회 중 3회**가 된다.

### DB 를 읽고 쓰는 얇은 겉면 — `sessions.py`

`create_session()` 이 **한 문장 insert 에서 두 단계**가 된다. ⚠️ 같은 트랜잭션 안에서 한다.

1. `load_rotation_inputs(conn, user_id)` — 직전 10회와 후보 목록을 읽는다.
   - 직전 10회: `learning_sessions` 를 `user_id` 로 `order by created_at desc limit 10`.
   - 후보: `learning_scenarios` 에서 `level` 이 사용자 `current_level` 과 일치하는 행.
     **일치가 0행이면 전체 행으로 떨어진다** — 지금 SQL 의 폴백을 그대로 계승한다.
   - `last_used_at`: `learning_sessions` 를 `scenario_id` 로 묶은 최대 `created_at`(사용자 단위).
2. `pick_scenario(...)` 로 하나를 고른다.
3. `insert into learning_sessions (..., scenario_id, scenario_pick)` 에 **고른 값과 고른 쪽**을 넣는다.

⛔ `_CREATE_SESSION_SQL` 안의 시나리오 서브쿼리 둘을 **지운다** — 두 곳에서 고르면 갈라진다.
⚠️ **쉐도잉 클립 선택(`_ATTACH_SHADOWING_CLIP_SQL`)은 건드리지 않는다.** 그 절이 같은 모양인 것은
의도였고(그 주석이 근거를 갖는다) 이 결정의 범위가 아니다 — §9.

## §5. 기록 칸 — 마이그레이션 `016`

```sql
-- 016_session_scenario_pick.sql
alter table learning_sessions
  add column scenario_pick text
  check (scenario_pick in ('new', 'repeat'));
```

**nullable 로 둔다** — 기존 행에는 이 값이 없고 소급해 채우지 않는다. ⛔ **소급 계산으로 채우지
않는 이유**: 과거 세션의 신규 여부는 그 시점의 창에 달렸고, 지금 창으로 다시 접으면 **실제로 일어난
것과 다른 값**이 된다. `pick_scenario` 는 `pick` 이 `None` 인 행을 `new_count` 에서 **세지 않는다**.

⇒ 도입 직후에는 `new_count` 가 0 이라 **신규가 먼저 3회 연달아 나온다.** 이것은 결함이 아니라 창이
채워지는 과정이다. ⚠️ 그 3회가 지나면 비율로 수렴한다 — §6 이 그것을 센다.

**이 칸이 필요한 이유**: 이 칸이 없으면 「신규를 몇 번 골랐는가」를 셀 수 없고, 그러면 `TASK-4` AC#4
(*"문구 단정이 아니라 계산 검증"*)를 만족할 수단이 없다. 대안과 그 기각 근거는 §7.

## §6. 검증 — 숫자로 센다

⛔ **「비율이 지켜진다」를 문장으로 쓰지 않는다.** 아래를 단위 테스트로 돌려 **출력을 근거로 삼는다.**

| # | 무엇을 세는가 | 기대 |
|--:|---|---|
| 1 | 빈 이력에서 30회 연속 선택 | 신규 **9회** · 반복 21회 (도입 직후 3회 연속 신규를 포함) |
| 2 | 빈 이력에서 **40회** — 그 사이 15종이 모두 쓰인다 | 신규 **12회** · ⛔ **신규 후보가 0 이 되는 시점 0회** |
| 3 | 같은 입력을 두 번 | 같은 출력(결정론) |
| 4 | 후보 0행 | `None` · 세션은 `scenario_id` null 로 진행 |
| 5 | `level` 일치 0행 | 전체 행으로 폴백(기존 동작 보존) |
| 6 | `pick` 이 null 인 과거 행이 섞인 이력 | null 을 세지 않고 동작 |
| 7 | **연속 두 세션**이 같은 주제인지 | 같은 `scenario_id` 가 연달아 나오는 횟수 **0회** |

**9 와 12 는 규칙을 손으로 돌려 얻은 값이다** — 창 10 · 문턱 3 이면 주기가 **11회**(신규 3 + 반복 8)로
수렴한다. 첫 주기는 1·2·3 회차가 신규이고, 다음은 12·13·14, 그다음은 23·24·25, 그다음은 34·35·36 이다.
⇒ 30회에 **9**, 40회에 **12**. ⚠️ 이 값이 구현과 다르면 **구현이 아니라 이 수치를 먼저 다시 센다.**

⚠️ **테스트 2 가 이 설계의 핵심 단정이다** — 「신규」를 *한 번도 안 한 것*으로 읽으면 15회 뒤 신규
후보가 0 이 된다. 결정 74 의 창 정의가 그것을 막는 기전은 **창 10 이 15종보다 작다**는 것이다
⇒ 항상 창 밖에 최소 5종이 남는다. 테스트 2 의 두 번째 열이 그 「최소 5종」을 반증 가능하게 만든다.
⛔ **테스트 7 은 「창 안 재등장 0회」가 아니다** — 반복 선택은 창 안의 상황을 **일부러** 다시 고른다.
재는 것은 **연달아** 같은 주제가 나오지 않는다는 것뿐이다.

## §7. 단순 대안 검토 — 기각 근거를 남긴다

**대안 1 — SQL 안에서 `random() < 0.3` 으로 확률 선택.** 새 모듈도 새 컬럼도 필요 없다.
⛔ **기각**: 표본이 작아 편차가 크다(10회에 신규가 1회일 수도 5회일 수도 있다). AC#4 가 요구한
**계산 검증**을 할 수 없고 「비율을 지킨다」가 단정이 아니라 희망이 된다.

**대안 2 — 새 컬럼 없이 이력에서 신규 여부를 매번 재계산.** 마이그레이션이 필요 없다.
⛔ **기각**: 세션 t 의 신규 여부가 t 이전 10개에 달려 **재귀**가 되고, 창 크기를 바꾸면 **과거 판정이
소급해 흔들린다.** 컬럼 하나가 그 흔들림을 없앤다.

**대안 3 — 선택 로직을 `sessions.py` 에 함수로 더한다.** 새 파일이 없다.
⛔ **기각**: 그 모듈이 이미 563줄 · 공개 함수 9개다. 선택 규칙은 DB 없이 테스트 가능한 순수 함수이므로
분리하는 쪽이 **테스트와 이해 둘 다 싸다.**

## §8. 감수한 대가와 관측 항목

- ⛔ **진짜 새 주제는 늘지 않는다**(결정 74). 15종이 상한이고 그것을 늘리는 일은 `TASK-5`
  (시나리오 생성기)가 소유한다. **이 설계는 그것을 대체하지 않는다.**
- ⚠️ **창 10 은 유도값이다**(결정 74). 캡틴 문서에 직접 근거가 없다. ⛔ 복습 사다리 `1·3·7일` 과
  **다른 축이므로 섞지 않는다.**
- ⚠️ **업무 상황을 일찍 열었다**(결정 75). 학습자가 업무 무대에서 얼어붙는지는 **회차로 관측할
  항목**이다. ⛔ 관측 전에 「완화했다」를 근거로 인용하지 않는다.
- ⚠️ **도입 직후 3회는 신규가 연달아 나온다**(§5). 이것을 결함으로 보고하지 않는다.

## §9. 범위 밖 — 이 설계가 하지 않는 것

- **시나리오를 대화에서 생성하는 것** — `TASK-5` 다. 이 설계는 그 생성물이 들어갈 자리(주제 = 행
  하나)를 정해 둘 뿐이다.
- **한 세션 안 질문 배분에 비율을 두는 것** — 결정 73 이 기각한 갈래다.
- **쉐도잉 클립 선택 규칙**(`_ATTACH_SHADOWING_CLIP_SQL`) — 같은 모양이지만 다른 결정이 소유한다.
- **주제별 난이도 상향** — `level` 값역을 쓰는 설계는 이 태스크가 열지 않는다. 결정 75 가 업무 6종을
  `A2` 로 고정했으므로 지금은 단일 등급이다.
- **화면·API 노출** — 사용자가 무슨 주제를 받았는지 보여 주는 것은 정해지지 않았다.
