# 학습 시나리오 생성기 — 대화 5회로 사용자 전용 무대를 만든다 (`TASK-5`)

> **결정의 정본은 `docs/ops/captain-instruction-register.md` 의 결정 79·80 이다.** 이 설계서는 그
> 둘을 코드로 옮기는 방법만 갖는다 — 왜 그렇게 정했는지는 그 대장이 소유한다.
>
> **캡틴 원문**(노트 항목 8): *"학습자에게 질문을 통해 사용자 전용 주제를 만드는 기능 신규 기능
> 추가 : 학습 시나리오 생성기, 5회 정도의 질문을 통해 학습하고자 하는 시나리오 생성"*
> (`docs/design/2026-09-06-captain-response-to-status-report.md` §1)
> **캡틴 결정 3**: *"대화에 전달하고, **대화를 기반으로 시나리오를 생성한다**"*
> (`docs/design/2026-09-06-captain-decisions.md` §1) — 이 설계가 그 후반부를 이행한다.
>
> 트랙 A(풀) — §6 이 4 Lenses 넷을 모두 담는다. 작성 2026-09-12 · 세션 `ohmyenglish-f4`

---

## §1. 지금 무엇이 없나 — 팀리드가 직접 확인한 것

**⛔ 사용자에게 질문할 수단이 음성뿐이다.**

- `app/frontend/app` 전체(`page.tsx` · `history/page.tsx` · `results/[sessionId]/page.tsx`)에
  `<form>`·`<input>`·`<textarea>` 가 **0건**이다. 화면은 마이크 세션과 버튼 메뉴로만 이뤄진다.
- `app/backend/app/api/**` 의 라우트는 전부 `GET` 이고 쓰기 경로는 웹소켓 하나
  (`ws.py` 의 `WS_SESSION_PATH`)뿐이다. 텍스트 질의응답용 엔드포인트가 없다.
- 대화형 CLI 도 없다 — `scripts/*.py` 는 마이그레이션·백필·보고용이다.
- 음성 세션의 tool 은 **발음 판정 하나뿐**이다(`PRONUNCIATION_TOOL_NAME`).

⚠️ **진입점의 이름은 이미 있다** — `page.tsx` 의 `ADDITIONAL_LEARNING` 에 「질문 답변 5개」 항목이
있으나 **로직이 없다**(지금은 `learning_source='additional'` 태깅뿐). 그 자리가 이 기능의 문이다.

**⛔ 시나리오 표에 소유자·출처 축이 없다.** `learning_scenarios` 의 컬럼은 `id`·`category`·`level`·
`title`·`prompt_template`·`created_at` 뿐이다. 시드 행과 사용자 생성 행을 가릴 수단이 **0곳**이다.
선례는 다른 표에 있다 — `learning_sessions.learning_source`(`recommended`·`additional`·
`user_requested`) · `session_plans.source`(`agent`·`fallback`).

## §2. 정한 것 — 둘 (대장이 정본)

| 결정 | 내용 | 대응 절 |
|---|---|---|
| 79 | 5회 질문은 **음성 대화**로 하고, 생성은 **세션 뒤 job** 이 전사문을 읽어 한다 | §3 · §5 |
| 80 | 사용자가 만든 상황은 **신규 후보의 맨 앞**에 온다. 비율은 그대로 | §4 |

## §3. 질문 5개의 흐름 — 각 질문이 «다른 것»을 좁힌다 (AC#1)

⛔ **다섯이 같은 축을 되묻지 않는다.** 되물으면 다섯 번을 써도 한 가지만 알게 된다.

| # | 무엇을 좁히는가 | 상대가 하는 말(A2 기준 · 단문) | 어느 컬럼으로 접히는가 |
|--:|---|---|---|
| 1 | **무대** — 어디서 영어를 써야 하는가 | "Where do you need English soon? Tell me the place." | `category` 후보 |
| 2 | **상대** — 그 자리에 누가 있는가 | "Who will you talk to there? A colleague? A stranger?" | `prompt_template` 의 역할 |
| 3 | **목표** — 무엇을 이루려 하는가 | "What do you want to get done in that talk?" | `title` |
| 4 | **초점** — 무엇이 가장 어려운가 | "What part feels hardest for you there?" | `prompt_template` 의 강조 |
| 5 | **어조** — 얼마나 격식 있는가 | "Is it a formal talk or a relaxed one?" | `prompt_template` 의 어조 |

⚠️ **다섯을 프롬프트가 «순서대로 하나씩» 묻게 한다** — 한 번에 다 물으면 학습자가 한 문장으로
답하고 축이 섞인다. `h-doc` 프로필의 현재 수준(단문 위주)이 그 이유다.
⛔ **답을 못 받아도 계속 진행한다** — 학습자가 모르겠다고 하면 그 축은 비운다. 비면 §5 의 파서가
기본값을 쓰지 않고 **그 축을 뺀 채** 만든다(모델이 지어내게 하지 않는다).

## §4. 저장 위치 — 같은 표에 행을 얹는다 (AC#2)

**새 표를 만들지 않는다.** `TASK-4` 가 이미 착지 지점을 정했다 — 생성된 시나리오는
`learning_scenarios` 의 행 하나가 되고 배치 규칙(결정 73·74)이 그것을 신규 후보로 집는다.
⛔ 별도 표로 가르면 배치 규칙이 **두 표를 합쳐 읽어야** 하고 그 조인이 규칙의 단순함을 깬다.

### 마이그레이션 `018` — 셋을 한 번에 고친다

⚠️ **번호는 적용 시점의 `schema_migrations` 조회로 다시 발급한다**(`H-AL`). 이 설계 작성 시점의
최대는 `017` 이다.

1. **`learning_scenarios.source`** — `text not null default 'seed'` ·
   `check (source in ('seed', 'generated'))`. `default` 를 두는 이유: 기존 30행이 전부 시드이므로
   소급 UPDATE 없이 참이 된다.
   ⛔ **`user_id` 를 두지 않는다** — 단일 사용자 로컬 도구이고(`api/ws.py` 의 `FIXED_USER_ID` 가
   그 사실을 이미 갖는다) 지금 두면 항상 같은 값이 들어가는 컬럼이 된다. 다중 사용자가 생기는
   턴에 그때 더한다.
2. **`analysis_jobs_job_type_check`** 에 `'generate_scenario'` 를 더한다.
3. **`analysis_jobs_target_matches_job_type`** 에 그 분기를 더한다 —
   `(job_type = 'generate_scenario' and session_id is not null and utterance_id is null)`.
   ⛔ **2번만 하고 3번을 빼면 job 을 넣을 수 없다** — 007 의 주석이 *"값만 늘리면 안 된다"* 로 그
   함정을 이미 적었다.

### 노출 순서 — 정렬 키 맨 앞자리 (결정 80)

`services/scenario_rotation` 의 `Candidate` 에 `is_generated: bool` 을 더하고 `_staleness` 의
튜플 **맨 앞**에 둔다.

```
(0 if is_generated else 1, 0 if last_used_at is None else 1, 시각, scenario_id)
```

⇒ 신규 차례가 오면 사용자 생성 상황이 먼저 집힌다. ⛔ **비율은 건드리지 않는다**(결정 78).
⚠️ 기존 계약(「수준 일치 0행이면 가장 이른 행」)은 셋째 자리의 `created_at` 이 계속 지킨다.

## §5. 생성 주체와 거부 경계 (AC#3)

**주체는 Claude 다.** 규칙으로는 자유 발화에서 무대를 뽑을 수 없다.

### 흐름

1. 세션이 `learning_source='additional'` + 「질문 답변 5개」 진입으로 열린다.
2. 세션 프롬프트에 **질문 5개 지시**가 실린다(§3). 상대가 하나씩 묻는다.
3. 세션이 끝나면 `end_session` 경로가 `generate_scenario` job 을 넣는다
   (`enqueue_plan_next_session` 이 그 선례다).
4. 워커가 그 세션의 `utterances` 전사문을 읽어 프롬프트를 만들고 Claude 를 부른다.
5. 파서가 검증해 통과하면 `learning_scenarios` 에 `source='generated'` 행 하나를 넣는다.

### ⛔ 모델이 만들 수 없는 값을 요구하지 않는다

`parse_plan` 이 이미 그 원칙의 선례다 — 출력만으로 판정할 수 없는 것은 **호출자가 인자로 준다**.

| 값 | 누가 정하는가 | 근거 |
|---|---|---|
| `level` | ⛔ **호출자** — `users.current_level` | 모델은 학습자의 CEFR 등급을 모른다. 지어내면 난이도가 튄다 |
| `category` | 모델이 고른다 | 값역 6개를 **프롬프트에 열거해** 주고, 파서가 그 밖을 거부한다 |
| `title` · `prompt_template` | 모델이 만든다 | 이것이 이 기능의 산출물이다 |
| `source` | ⛔ **호출자** — 항상 `'generated'` | 모델에게 물으면 `'seed'` 를 낼 수 있다 |
| `created_at` | DB | |

### 거부 경계 — 통과하지 못하면 «저장하지 않는다»

`PlanValidationError` 와 같은 형태로 `ScenarioValidationError` 하나에 수렴시킨다. 거부 조건:

1. `category` 가 값역 밖이다.
2. `title` 이 비었거나 지나치게 길다(화면 라벨이므로 한 줄이어야 한다).
3. `prompt_template` 이 **질문이다**(`?` 로 끝난다) — 시나리오는 **무대**이고 질문은 계획이
   소유한다(캡틴 결정 14). `test_seeded_scenarios_are_stages_not_questions` 가 시드에 대해 재는
   것과 같은 규칙이다.
4. `title` 과 `prompt_template` 이 같다 — 규칙 6 방어가 공허해진다.
5. 이미 같은 `title` 의 `generated` 행이 있다(같은 무대를 두 번 만들지 않는다).
   ⚠️ 비교는 **`btrim` + 소문자**로 한다 — 공백과 대소문자만 다른 제목을 다른 무대로 세면 중복
   방어가 공허해진다. ⛔ 시드 행(`source='seed'`)과는 비교하지 않는다: 학습자가 시드와 비슷한
   무대를 자기 말로 다시 정의하는 것은 막을 일이 아니다.

**⛔ 축 1(무대)이 비면 거부한다 — 다른 넷은 비어도 통과한다.** §3 이 「답을 못 받으면 그 축을
비운다」로 정했지만 무대가 없으면 `category` 를 고를 근거가 **아예 없고**, 그 상태에서 모델이
값역 중 하나를 내면 그것은 **지어낸 값**이다. ⇒ 무대만 필수이고 상대·목표·초점·어조는 없으면
`prompt_template` 이 그만큼 짧아진다.
⚠️ 이 비대칭이 의도임을 적어 둔다 — 다섯을 모두 필수로 하면 학습자가 한 축만 모른다고 답해도
생성이 실패하고, 그것은 5회 대화를 버리는 일이다.

⛔ **반쯤 검증된 시나리오를 쓰지 않는다.** 거부는 `analysis_jobs.last_error` 에 남고
`fail_or_retry` 가 최대 5회까지 재시도한 뒤 `failed` 로 닫는다(기존 관행).
⚠️ **거부돼도 세션은 이미 끝났고 학습은 일어났다** — 생성 실패가 학습을 되돌리지 않는다.

## §6. 4 Lenses 검증

### Contract

- **전제조건**: 대상 세션이 존재하고 그 세션에 `utterances` 가 1행 이상 있다. 세션의
  `learning_source` 가 `'additional'` 이다.
- **사후조건**: 성공하면 `learning_scenarios` 에 `source='generated'` 행이 **정확히 하나** 늘고
  job 이 `done` 이 된다. 실패하면 **행이 0개 늘고** `last_error` 가 채워진다.
- **불변조건**: `source='seed'` 행은 이 경로로 **절대 바뀌지 않는다** — 생성은 `insert` 만 하고
  `update` 를 하지 않는다. ⇒ 시드의 배열 순서(결정 76)가 생성으로 흔들리지 않는다.

### Boundary

- **모델 경계**: Claude 출력이 자유 텍스트로 들어오고 `parse_scenario` 가 그 경계에서 값역을
  검증한다. ⛔ 검증 전 값이 DB 로 넘어가는 경로를 만들지 않는다.
- **세션 → job 경계**: 세션이 끝나는 순간과 생성이 도는 순간이 **다른 시각**이다. 그 사이
  전사문이 더 늘지 않는다(세션이 닫혔으므로) — 그래서 job 이 나중에 돌아도 입력이 같다.
- **타입 경계**: `category` 는 DB CHECK 가 정본이고 앱은 값역을 **복제하지 않는다**. 프롬프트에
  열거하는 목록은 예외이고, 그 복제의 대가는 파서 테스트가 갚는다.
- **시각 경계**: `created_at` 은 DB 가 찍는다. 앱이 만든 naive datetime 이 들어오는 경로를
  만들지 않는다(전역 시각 규약 2항).

### Failure

- **모델이 값역 밖을 낸다** → 저장 0행 · `last_error` 기록 · 최대 5회 재시도 후 `failed`.
  학습 기록은 그대로 남는다.
- **전사문이 비었다**(학습자가 아무 말도 안 했다) → 만들 재료가 없다. ⛔ 지어내지 않고 **job 을
  즉시 `failed`** 로 닫는다. 재시도해도 입력이 같으므로 재시도가 무의미하다.
- **같은 무대가 이미 있다** → 거부 조건 5번. 중복 행을 만들지 않는다.
- **job 이 도는 중 프로세스가 죽는다** → 기존 `analysis_jobs` 관행이 처리한다(`running` 이
  유예를 넘기면 회수). 부분 저장은 없다 — insert 하나가 트랜잭션 전부다.
- **생성은 성공했지만 사용자가 그 무대를 원하지 않는다** → 이 설계는 **삭제 경로를 만들지
  않는다**(§8). 그 상황은 배치 규칙에서 반복 후보로 남는다.

### Dependency

- `services/scenario_generator`(신규) → `services/jobs`(claim·실패 보고) · `claude` 어댑터 ·
  `utterances` 조회 · `learning_scenarios` 쓰기.
- `services/scenario_rotation` 에 `Candidate.is_generated` 가 **더해진다** ⇒ 그것을 채우는
  `sessions._pick_scenario_for_user` 의 SQL 도 함께 바뀐다. ⛔ **두 자리가 같은 커밋에서
  바뀌어야 한다** — 필드만 더하면 항상 `False` 가 들어가 결정 80 이 조용히 죽는다.
- 초기화 순서 제약: **없다.** job 은 세션 종료 뒤에만 들어가므로 워커 기동 순서와 무관하다.
- ⚠️ **`nova.py` 의 프롬프트에 질문 5개 지시를 싣는 자리가 필요하다** — 그 파일은 지금 다른
  갈래(`TASK-128` · 세션 `ohmyenglish-19`)가 고치고 있다. ⛔ **구현 시점에 그 갈래와 순서를
  맞춘다**(이 설계는 tool 을 늘리지 않으므로 충돌 면적이 프롬프트 조립 한 곳뿐이다).

## §7. 단순 대안 검토

**대안 1 — 질문 5개를 화면 폼으로 받는다.** 답이 구조화돼 파싱이 쉽다.
⛔ **기각**: `h-doc` 이 Speaking 우선을 정하고 읽기·쓰기 전용 기능을 정당화하지 않는다. 프런트에
입력 폼이 0건이라 새 화면·검증·상태 관리가 전부 새로 생긴다.

**대안 2 — 대화 중 새 tool 로 답을 모아 즉시 만든다.** 그 세션에서 바로 쓸 수 있다.
⛔ **기각**: 발음 tool 계약을 다른 갈래가 지금 고치는 중이라 충돌한다. 그리고 모델이 tool 을
부르는 시점을 지시문으로 통제하려는 시도가 이 리포에서 **두 방향 다 반증됐다**(결정 70·72).

**대안 3 — 별도 표(`user_scenarios`)를 만든다.** 시드와 완전히 격리된다.
⛔ **기각**: 배치 규칙이 두 표를 합쳐 읽어야 하고 그 조인이 규칙의 단순함을 깬다. `source` 컬럼
하나가 같은 격리를 준다.

## §8. 범위 밖

- **생성된 시나리오를 지우거나 고치는 경로** — 화면·API 가 정해지지 않았다. 지금은
  `scenario_report.py` 로 보고 `psql` 로 지운다.
- **한 세션에서 여러 시나리오를 만드는 것** — 5회 질문이 무대 하나를 좁히므로 산출물도 하나다.
- **생성된 시나리오의 품질 평가** — 학습자가 그 무대를 실제로 쓸 만하다고 느끼는지는 회차로
  관측할 항목이고 이 설계가 재지 않는다.
- **다중 사용자** — `user_id` 를 두지 않은 이유가 §4 에 있다.
- **`TASK-102` AC#1(시나리오 수집)** — 외부에서 가져오는 경로는 이 설계가 다루지 않는다.
