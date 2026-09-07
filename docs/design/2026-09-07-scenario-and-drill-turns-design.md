# 설계 — 시나리오를 대화에 싣고, 드릴 턴을 관측한다 (`TASK-6` + `TASK-25`)

> **한 문서에 두 태스크를 쓴다.** 근거: `2026-09-06-captain-decisions.md` §2 *"결정 2·3은 같은
> 자리를 건드린다 — 함께 설계한다"*. 둘 다 **지시문 조립 경로 하나**를 바꾼다.
>
> **캡틴 결정 1·2·3·9·10·11의 정본은 `2026-09-06-captain-decisions.md`다** — 여기서 재서술하지
> 않고 필요한 곳에서 가리킨다. 태스크 상태의 정본은 **Backlog.md**다.
>
> **상태**: 설계 완료. **결정 12로 구현 착수에 일반 승인은 필요 없다** — 올리는 것은 「중요한
> 설계 결정」뿐이다. 이 설계는 그 기준에 **5건** 걸렸고 **2026-09-07 캡틴이 5건 전부 승인했다.**
>
> | # | 올린 것 | 판정 | 어디 |
> |--:|---|---|---|
> | 1 | `build_system_prompt(known_sounds, plan)` → **인자 3개** | ✅ 승인 | §2.1 · §6-6 |
> | 2 | `create_voice_adapter(...)`에 `scenario` 인자 | ✅ 승인 | §2.1 · §6-5 |
> | 3 | `PreparedPlan`에 `questions` 필드 | ✅ 승인 | §2.1 · §6-3 |
> | 4 | 결과 API 응답에 `drill` 키(생략 규약) | ✅ 승인 | §2.3 · §6-7 |
> | 5 | 결과 화면에 한 줄이 는다 — **톤 계약에 닿는다** | ✅ 승인 | §2.3 · §6-8 |
>
> **마이그레이션은 0건이라 스키마 항목은 걸리지 않는다**(§2.3의 판정 — 그 판정 자체는 §7 유도 2다).
> ⚠️ **승인은 이 5건의 계약 변경에 대한 것이고, 설계 내용 전체에 대한 백지 위임이 아니다** —
> §7의 유도 8건은 여전히 한 줄씩 뒤집을 수 있는 상태로 둔다.
>
> ## 2판 — critic `CHALLENGE`를 반영했다 (2026-09-07)
>
> 첫 판을 반증 위임(opus)에 걸어 **`CHALLENGE`**를 받았고, 지적 4건을 **내가 직접 그 줄을 열어
> 사실로 확정한 뒤** 반영했다. 무엇이 틀렸는지 지우지 않고 남긴다 — 지우면 같은 실수가 돌아온다.
>
> | 첫 판의 오류 | 어디서 고쳤나 |
> |---|---|
> | ⛔ **`learning_scenarios`를 길이만 재고 내용을 안 봤다** — 3행은 무대가 아니라 **질문**이고 `title`과 바이트 동일이었다 | §1 · §2.1(**결정 14**) · §2.2 |
> | ⛔ `.env.example`이 *"없다"* — **실재한다**. `captain-decisions.md:35`에서 검증 없이 물려받았다 | §3 · §6-13 |
> | ⛔ 영향 범위 **과소** — `services/results.py`·`scripts/migrate.py`·테스트 2개·`.env.example`이 빠졌다 | §6 (8곳 → **13곳**) |
> | ⚠️ barge-in에서 턴이 합쳐질 수 있는 경로를 **검토한 흔적이 없었다** | §2.3 · §5 약점 2 |
>
> ⏸ **판정문이 D2 중간에서 잘려 D3·D4·D5·결정 준수 4건·공격 3건을 아직 못 받았다** — 재요청했다.
> **미수신 부분을 「없음」으로 읽지 않는다.**

---

## §1. 판정된 데이터 — 착수 전에 직접 확인한 것

설계가 이 값들에 걸려 있다. **전부 그 줄을 열어 확인했다**(2026-09-07).

| 사실 | 근거 |
|---|---|
| `session_plans.questions jsonb not null` — CHECK `array` ∧ `3 ≤ len ≤ 5` | `db/migrations/007_learning_coach_slice2.sql:25`·`:42-43` |
| 그런데 `_PREPARED_PLAN_SQL`은 `sp.id`·`sp.reason`·`sp.instruction` **셋만** select한다 | `app/backend/app/services/sessions.py:108-115` |
| `PreparedPlan` docstring이 *"초점 패턴 id·질문 목록은 담지 않는다"*고 **의도적으로** 적어 뒀다 | 같은 파일 `:122` |
| `SessionInstruction`에 `questions` 필드가 **없다** — 조립 지점이 받는 타입이 이것이다 | `app/backend/app/models/plan.py:106-113` |
| `PlanOutput.questions`는 3~5개로 실재한다 · `PlanQuestion` = `prompt`·`context` | `plan.py:130` · `:85-90` |
| `learning_sessions.scenario_id`는 nullable FK이고 INSERT가 채운다 | `001_initial_schema.sql:35` · `sessions.py:51-67` |
| ⛔ `learning_scenarios` 3행은 **무대가 아니라 질문이다** — `title`과 `prompt_template`이 **바이트 동일**(`identical = t`) · 34·35·31자 · 전부 `A2`·`daily_life` | psql 직접 조회 2026-09-07 |
| 같은 문자열이 **스텁 어댑터의 픽스처 질문**이다 | `app/backend/app/audio_gateway/fixtures.py:20-21` |
| 리포 자신이 질문이라 부른다 — *"learning_scenarios 3행(**질문 3개**)"* | `tests/unit/test_schema.py:145` |
| 시드 원본은 `SEED_SCENARIOS`이고 주석이 *"3 daily_life **questions** … verbatim from the task brief"*라 자백한다 | `scripts/migrate.py:33-55` |
| ⚠️ `on conflict (id) do nothing`이라 **상수만 고쳐도 기존 3행은 안 바뀐다**(고정 id) | `scripts/migrate.py:109` |
| `learning_sessions.summary jsonb not null default '{}'` — **앱 참조 0곳** | `001_initial_schema.sql:46` · grep 0건 |
| 턴 경계 감지 = *"agent가 말을 시작했다 = 사용자 턴이 닫혔다"* | `app/backend/app/audio_gateway/session.py:322-326` |
| 마이그레이션 **008은 주간 리포트(`TASK-26`)에 예약**됐다 | `captain-decisions.md` §3 유도 1 |

⛔ **구멍 (a) 「재료 미전달」의 원인은 데이터 부재가 아니라 SELECT 누락이다.** 질문은 이미
저장되고 있고 읽히지 않는다. → **마이그레이션 없이 닿는다.** 이 판정이 설계 전체를 가른다
(`gap-investigation.md` 항목 9가 구멍을 둘로 나눈 것 중 (a)의 실체).

---

## §2. 설계

### §2.1 재료를 조립 지점까지 나른다

**질문** (결정 2 · `TASK-6` 구멍 (a))

- `_PREPARED_PLAN_SQL`에 `sp.questions`를 더한다. `PreparedPlan`에 `questions: list[PlanQuestion]`.
- asyncpg가 `str`를 돌려준다 — 이 리포에 jsonb 코덱이 없다(`set_type_codec` 0건). `instruction`이
  이미 `json.loads` → `model_validate`를 하므로 **같은 처리**를 한다.
- **검증 실패는 `instruction`과 같게 다룬다**: `warning` + `None`(계획 전체 포기). 근거 —
  `questions`는 DB CHECK가 3~5를 지키므로 정상 경로에서 깨질 수 없고, 깨졌다면 계약이 어긋난
  것이다. **반쯤 유효한 계획을 쓰는 것이 이 리포의 지배 실패 모드**(*"통과했는데 통과한 이유가
  틀렸다"*)에 가장 가깝다.
- ⚠️ **`PreparedPlan` docstring `:122`를 같은 커밋에서 고친다.** 본문을 고치고 그 본문을 설명하는
  문장을 두는 것이 **리뷰 5차 중 4차가 걸린 형태**다.

**시나리오** (`TASK-25` AC#1·#3)

- `load_session_scenario(conn, session_id) -> SessionScenario | None` 신설.
  `learning_sessions`에 **이미 박힌** `scenario_id`를 join해 읽는다.
- ⚠️ **INSERT가 고른 행을 다시 고르지 않는다.** 세션 행에 박힌 것을 읽어야 *"그 세션이 실제로
  받은 무대"*와 일치한다. 수준 조회를 다시 하면 학습자 수준이 올라간 뒤 두 값이 갈라진다
  (INSERT의 폴백 경로는 실제로 발동한다 — `sessions.py:59-63`이 그 근거를 소유한다).
- `scenario_id`가 null이면 join이 **0행** → `None` → 블록만 빠진다. **AC#3이 코드 분기 없이
  충족된다** — "null이면 지금 동작 유지"를 if로 쓰지 않는다.
- 타입 `SessionScenario(title, prompt_template)`는 **`app/models/`**에 둔다.
  `factory`·`nova`는 `models`만 알고 `services`가 그것을 채우는 기존 방향(`SessionInstruction`)과
  같다 — `services`를 import하면 의존 방향이 뒤집힌다.

**시드를 무대로 고친다 — 캡틴 결정 14 (2026-09-07)**

⛔ **이 설계의 전제가 데이터와 어긋나 있었다.** 결정 9는 「시나리오 = 무대(상황·역할)」인데
현재 3행은 **질문**이고 스텁 픽스처와 같은 문자열이다(§1). 그대로 실으면 `Today's setting:`에
**질문**이 박혀 계획의 질문 3~5개와 **종류가 겹친다.** 캡틴 결정 14로 **데이터를 고친다** —
결정 9는 그대로 살고 질문은 계획이 소유한다.

문구는 **h-doc(학습자 프로필)이 소유하는 규약**을 따랐다: 단문·단일 절 · 난이도 상향 경로의
첫 칸(일상) 유지 · **목표 수준 문형을 쓰지 않는다**(AWS 보고 문형으로 만들면 첫 세션에서 얼어붙는다).
**원래 3행의 화제(퇴근 후 · 주말 · 오늘 밤)는 보존하고 「종류」만 질문 → 무대로 바꾼다.**

| id 끝 | `title` (화면 라벨) | `prompt_template` (지시문에 실린다) |
|---|---|---|
| `…101` | `After work with a colleague` | `You are a friendly colleague chatting with the learner after work.` |
| `…102` | `Weekend plans with a friend` | `You are a friend catching up with the learner about the weekend.` |
| `…103` | `Tonight's plans at home` | `You are a housemate talking with the learner about tonight.` |

⚠️ **범위를 넓히지 않는다** — 행을 더하지 않고 `category`(`daily_life`)·`level`(`A2`)를 바꾸지 않는다.
`_CREATE_SESSION_SQL`이 `users.current_level`로 고르므로 `A2`를 유지해야 지금 경로가 산다.
업무 시나리오 추가는 **결정 5의 몫이고 `TASK-4`·`TASK-5`가 소유한다.**

⚠️ **`on conflict (id) do nothing`이라 상수만 고쳐도 기존 3행이 안 바뀐다**(`migrate.py:109`).
→ **`do update set title, prompt_template`으로 바꾼다**(§7 유도 8). 고정 id + upsert라 멱등성은
유지되고, 앞으로 시드를 고치면 실제로 반영된다. `category`·`level`은 갱신 대상에서 뺀다.
⛔ **적용 전에 `pg_dump` 백업을 뜬다** — 결정 14가 부과한 제약이고, 기존 행의 내용을 바꾸는
작업이다.

**배선**

- `ws.py`에 `_load_scenario_or_none(pool, session_id)` — `_load_known_sounds_or_empty`·
  `_load_prepared_plan_or_none`(`ws.py:117-135`)과 **글자 그대로 같은 실패 규약**: 조회 실패를
  세션 시작 실패로 번역하지 않고, 로그를 남기고 없이 진행한다.
- `factory.create_voice_adapter(..., scenario=...)` → `build_system_prompt(known_sounds, plan, scenario)`.
  **G-3는 유지된다** — 팩토리는 여전히 **데이터**를 받아 여기서 조립하고, 소켓 계층은 어떤 구현이
  붙는지 모른다(`factory.py:37-47`이 그 근거를 소유한다).

### §2.2 지시문 블록 — 문구와 축 분석

**블록 순서: `SYSTEM_PROMPT` → 놓친 소리 → `Today's setting:` → `Today's plan:`**

무대가 목표보다 **먼저** 읽혀야 하고, 계획 블록의 마지막 줄이 앞의 setting을 **되짚어**
우선순위를 말할 수 있다(결정 9). 뒤집으면 대체 문장이 아직 나오지 않은 블록을 가리킨다.

```
Today's setting:
{prompt_template}
```

```
- Work through these questions one at a time. Stay on each one for at least {N} turns:
  ask it, let the learner answer, ask one follow-up about their answer, then have them
  say it again a different way. This repeat is practice, not a correction — it does not
  count against the one-correction-per-turn limit in rule 4.
    1. {prompt} ({context})
    …
- If today's setting suggests a different pattern than the focus above, follow the focus.
```

**축 분석** — `build_system_prompt` docstring이 축마다 「대체한다/안 한다」를 근거와 함께 소유하는
규약을 잇는다. **이 표의 정본은 그 docstring이 되고**, 아래는 설계 시점의 판정이다.

| 축 | 판정 | 근거 |
|---|---|---|
| 시나리오 ↔ 규칙 3 (일상→업무 순서) | **대체하지 않는다** | 결정 9가 *"시나리오는 「오늘의 상황」과 같은 축"*이라 정했고, 그 축의 비대체 근거(비용 비대칭 · h-doc이 이름 붙인 실패)는 docstring이 소유한다 |
| 질문 목록 ↔ 규칙 2 (하나씩 묻고 멈춘다) | **대체하지 않는다 — 강화한다** | 같은 방향이다. `one at a time`이 규칙 2를 되짚는다 |
| 질문 목록 ↔ 규칙 3 | **대체하지 않는다** | `contexts`와 **같은 처리**. ⛔ 그래서 문구에서 **`in this order`를 뺀다** — 순서를 지정하면 규칙 3의 순서와 부딪히고, 결정 9가 세운 「계획 = 목표, 무대·순서는 안 덮는다」 틀을 벗어난다 |
| 드릴 반복 ↔ 규칙 4 (교정 1건/턴) | **명시적으로 갈라낸다** | 규칙 11이 *"발음 교정도 교정이다"*로 상한을 못박은 **선례의 반대 방향**이다. 적지 않으면 모델이 드릴 반복을 교정으로 세어 **드릴이 1턴에 끝난다** |
| 우선순위 문장 ↔ 결정 9의 예외 | **계획이 이긴다** | 결정 9: *"시나리오 문구가 패턴을 지정하는 경우만"*. 문구가 31~35자라 실제로 드물지만, 프롬프트에 적어 두는 것이 «드물기를 바라는 것»보다 낫다 |

⚠️ **`title`은 지시문에 싣지 않는다.** 규칙 6이 *"Never read JSON, lists, or metadata out loud"*이고
제목은 화면용 라벨이다. `prompt_template` 하나로 무대가 성립한다.

⛔ **이 방어는 시드 교체 **전에는 공허했다** — 첫 판이 이것을 못 봤다.** `title`과
`prompt_template`이 **바이트 동일**이었으므로(§1) `title`을 빼도 같은 문자열이 들어갔고,
계획한 tripwire 「`title`이 지시문에 없다」는 **실물 데이터에서 반드시 실패**했다.
**결정 14의 시드 교체가 두 값을 갈라놓아 이 방어와 tripwire가 처음으로 실질을 갖는다.**
→ **그래서 시드 교체는 이 설계의 선행 조건이다**(§6이 순서를 정한다).

⚠️ **값이 없는 줄은 아예 넣지 않는다** — 기존 규약(`known_sounds` 0건·`contexts` 빈 목록)을 잇는다.
시나리오도 질문도 없으면 결과는 `SYSTEM_PROMPT` **그 자체**다.

### §2.3 턴 관측과 노출

**두 값을 서로 다른 시점에 얻는다.**

- **기대 턴 수** = `min(len(questions), drill_count) × drill_turns_min`.
  **세션 시작에 `learning_sessions.summary`에 적는다** (결정 10의 *"세션에 남기고"*).
  모양: `{"drill": {"count": K, "turns_expected": M}}`.
  ⚠️ **왜 저장하나** — 실제 턴 수는 사후 도출되지만 **기대값은 복원 불가**다. 계획 조회가
  「사용자 최신 1건」(`_PREPARED_PLAN_SQL`)이므로 다음 세션이 지나면 그 세션이 어느 계획을
  썼는지 알 길이 없다.
  ⚠️ **`summary`에는 CHECK가 없다** → **모양의 정본은 이 UPDATE를 하는 함수 docstring 하나**다.
  두 곳에 적으면 한쪽이 조용히 낡는다.
  실패 규약: 쓰기 실패 → 로그 + 세션 진행(부가 정보 — 기존 규약과 같다).

  ⛔ **덮어쓰지 않고 병합한다 — `summary = summary || $2::jsonb`.** 대입(`summary = $2`)으로 쓰면
  나중에 다른 기능이 같은 컬럼에 넣은 키를 조용히 지운다. `summary`가 **`jsonb NOT NULL` +
  기본값 `'{}'::jsonb`**라서 이 병합이 안전하다(직접 조회 2026-09-07: `is_nullable=NO` ·
  `column_default='{}'::jsonb` · **12행 전부 `{}` · null 0행**). ⚠️ **null이 섞일 수 있는
  컬럼이면 `||`를 쓸 수 없다** — `null || jsonb`는 `null`이라 기존 값이 통째로 사라진다.
  NOT NULL + 기본값이 그 경로를 닫는 것이 이 설계가 대입 대신 병합을 쓸 수 있는 이유다.
  같은 이유로 **INSERT(`_CREATE_SESSION_SQL`)를 고치지 않는다** — 기본값이 이미 `{}`를 넣는다.

- **실제 턴 수** = 결과 조회 시점에
  `count(*) from utterances where session_id = $1 and speaker = 'agent'`.
  ⚠️ **이것이 「agent final = 사용자 턴 닫힘」과 같은 값인 이유**: `session.py:322-326`이 그 판별을
  하는 바로 그 순간 저장되는 행이 agent final 행이다. **새 감지기를 만들지 않는다.**
  ⚠️ **`_flush_analysis` 경로에 카운터를 얹지 않는다.** 그 함수는 예외를 밖으로 던지지 않는
  계약(`session.py:339-355`)이고, 카운터를 얹으면 세는 일이 그 침묵 안으로 들어가 **누락이
  관측되지 않는다.** 읽을 때 세면 두 곳에 세지 않아 갈라질 수 없고, 세션이 예외로 끝나도 값이 남는다.

  ⚠️ **이 값이 세는 것은 정확히 「agent 전사문 행 수」다 — 「agent 턴 수」와 같다는 것은
  조건부다.** 조건: **한 completion = 한 행.** 성립 근거와 성립하지 않는 경로를 둘 다 확인했다:
  `_flush_pending_agent_text`가 한 턴의 청크를 **이어붙여 한 행**으로 만들고(`nova.py:451-472`),
  `completionEnd`가 그 flush를 부른다(`nova.py:346-347`). 그런데 **barge-in에서
  `contentEnd(stopReason=INTERRUPTED)`는 flush하지 않고 즉시 반환한다**(`nova.py:442-443`).
  즉 **그 completion의 `completionEnd`가 오지 않으면** 끊긴 턴의 청크가 남아 다음 턴과
  **한 행으로 합쳐지고**, 그러면 이 지표가 턴을 **적게** 센다.
  ⛔ **지금은 관측 불가다** — 런타임이 `VOICE_ADAPTER=stub`이고 barge-in은 Nova 실물 경로다.
  **그래서 「성립한다」고 단정하지 않고 조건을 적어 둔다**(§5 약점 2). 확정하려면 Nova 실물
  세션에서 barge-in을 일으켜 `completionEnd` 수신 여부를 봐야 한다.

- **계획이 없으면 기대값이 없다 → 관측 대상이 아니다.** 드릴은 계획의 질문에서 나온다.

**노출** (결정 10: 결과 화면·로그에 보이게 · 점수처럼 보이면 안 된다)

- 결과 API는 `corrections`의 **키 생략 규약**(`api/results.py:105-106`)을 그대로 따른다 —
  기대값이 없으면 응답에 `drill` 키를 **넣지 않는다.**
- 모양은 `{"turns_observed": N, "turns_expected": M}` **둘뿐**이다.
  ⛔ **비율·퍼센트·「달성/미달」 낱말을 넣지 않는다.** 결과 화면 톤 계약은
  *"채점하지 않습니다. 시범합니다"*(`docs/storyboard.html`)이고 그 계약이 문구를 소유한다.
- 프론트는 값이 오면 **사실 진술 한 줄**, 없으면 아무것도 그리지 않는다.
- 로그: 미달이면 `warning` 한 줄. `INFO`가 아닌 이유는 **H-Z**(문서가 지정한 실행에서 INFO는
  보이지 않는다)다.

---

## §3. 설정값

§2 *"설정값은 새로 만들지 않는다"*를 따라 **새 체계를 만들지 않고** `app/config.py`의
`Settings`(`BaseSettings`, `:44-73`)에 필드를 더한다.

⛔ **정정 — `.env.example`은 실재한다.** 첫 판은 *"지금도 없으므로 만들지 않는다"*고 적었고
그것은 **거짓**이다: `/.env.example`(**876 B** · 9월 1일 · 직접 확인)이 있고,
`NOVA_ENDPOINTING_SENSITIVITY`·`WORKER_ENABLED`처럼 **운영자가 조정하는 노브를 근거 주석과 함께
문서화하는 관례**를 이미 갖고 있다 — 드릴 값 둘이 정확히 그 종류다. ⚠️ **그래서 만들지는 않지만
기존 파일에 2줄을 더한다**(§6). 이 거짓 문장은 `captain-decisions.md:35`에서 **검증 없이 물려받은
것**이다 — 인용의 출처가 정본이어도 그 사실이 지금도 참인지는 직접 확인해야 한다.

| 필드 | 기본 | 검증 | 근거 |
|---|---|---|---|
| `drill_turns_min` | `4` | `ge=1` | 요구사항이 명시한 값(드릴마다 4턴 이상) |
| `drill_count` | `3` | `ge=1` | 결정 1의 *"드릴 횟수는 설정값"* |

값역 위반은 `Field(ge=1)`이 **기동 시점에** 던진다 — §2가 *"런타임에 조용히 잘리지 않게"*를
요구한다.

⚠️ **상한을 발명하지 않는다.** 캡틴이 범위를 명시한 것은 재생 속도(0.5~2.0)·반복 횟수(1~10)이고
드릴 값 둘은 범위를 말하지 않았다. 하한만 건다.

⚠️ **어긋남 하나를 기록한다 —** 결정 1은 *"드릴 **횟수**는 설정값"*, §2는 *"드릴 **턴 수**"*라고
적었다. **둘 다 설정값으로 두어 어느 쪽 문구도 어기지 않는다**: `drill_count`가 드릴 수의
**상한**이 되고(`min(질문 수, drill_count)`) `drill_turns_min`이 턴 수다. 질문이 5개인데 설정이
3이어도 모순이 없다. ⚠️ **이것은 내 유도다 — §7 유도 1**(뒤집는 방법은 그 표가 소유한다).

---

## §4. 4 Lenses 검증

### Contract

- `build_system_prompt(known_sounds, plan, scenario)` — 셋 다 없으면 결과는 `SYSTEM_PROMPT`
  **그 자체**(기존 계약 보존). `scenario`만 있고 `plan`이 없으면 setting 블록만 붙는다.
- `load_session_scenario` 사후조건: 세션 부재·`scenario_id` null·시나리오 행 부재 → 전부 `None`.
  **DB 오류는 던진다** — 흡수는 `ws.py` 래퍼가 한다(기존 분업 그대로. 예외를 안으로 삼키면
  «조회가 깨졌다»와 «시나리오가 없다»가 서비스 계층에서 구분되지 않는다).
- `PreparedPlan` 불변조건: `questions`는 3~5개. DB CHECK와 pydantic **이중 방어**이고, 중복이
  아닌 이유는 `models/plan.py` 모듈 docstring이 소유한다(읽을 수 있는 오류 대 다른 경로의 쓰기).

### Boundary

- **jsonb → 객체**: `questions`도 `instruction`과 같이 `str`로 온다 → `json.loads` + `model_validate`.
- **DB → 지시문 문자열**: `prompt_template` 31~35자. 블록이 짧은 문구로도 성립한다(§2.2).
  `title`은 넘기지 않는다(규칙 6).
- **모양이 강제되지 않는 경계**: `summary` jsonb에는 CHECK가 없다 → 정본을 docstring 한 곳에.
- **시각 경계**: 이 설계는 **달력 날짜를 판정하지 않는다.** `timestamptz`를 읽지도 쓰지도 않고
  「오늘/어제」 경계가 없다 — 그래서 `current_date` 함정이 걸리지 않는다.

### Failure

| 실패 | 결과 | 근거 |
|---|---|---|
| 시나리오 조회 실패 | 로그 + 블록 없이 진행 | 계획과 같은 규약(`ws.py:117-135`) |
| `questions` 검증 실패 | 계획 **전체** 포기 + warning | §2.1 |
| `summary` 쓰기 실패 | 로그 + 진행 | 부가 정보 |
| 세션이 예외로 끝남 | `turns_observed`는 **그래도 나온다** | 읽을 때 세므로 |

⚠️ **남는 모호함 하나**: `drill` 키 부재가 「계획이 없었다」와 「`summary` 쓰기가 실패했다」를
**구분하지 않는다.** 지금은 둘 다 «관측 없음»으로 수렴하는 것이 맞다(화면이 할 일이 같다).
구분이 필요해지면 **로그가 답한다** — 쓰기 실패에만 로그가 남는다.

부분 실행: `summary` 쓰기는 단독 UPDATE라 반쯤 쓰일 수 없다. 결과 조회는 읽기 전용이다.

### Dependency

- 순서: `create_session`(`ws.py:149`) → `load_session_scenario` · 계획 로드(`ws.py:168`) →
  `summary` 쓰기(질문 수를 알아야 기대값을 계산한다). **둘 다 기존 순서로 이미 만족한다** —
  새 순서 제약을 만들지 않는다.
- 의존 방향: `models` ← `services`·`audio_gateway`. `SessionScenario`를 `models`에 두는 이유(§2.1).
  순환 없음.
- ⚠️ **진행 중 세션의 `turns_observed`는 미완값이다.** 결과 화면은 종료된 세션을 보므로 실무상
  드러나지 않지만 계약으로 적는다 — 이 값은 「지금까지 닫힌 사용자 턴 수」다.

---

## §5. 이 설계의 약점 (D5)

### 약점 1 — 드릴별 귀속이 안 된다

⛔ **집계 턴 수는 드릴별로 귀속되지 않는다.** 한 질문에 12턴·나머지 0턴이어도 집계는 통과한다.
이 관측이 답하는 것은 *"각 드릴이 4턴을 채웠나"*가 아니라 *"세션 전체가 기대 턴 수에 닿았나"*다.

드릴별 귀속은 모델이 드릴 경계를 보고해야만 가능하고, 그것은 ① 결정 10이 *"의지하지 않는다"*고
한 런타임 경로에 가깝고 ② **측정하려는 대상(모델이 지시를 지키는가)을 모델의 협조로 재는
순환**이 된다. 그래서 **범위 밖으로 두고 약점으로 기록한다.**

⚠️ **그래서 이 관측을 「드릴 4턴 요구사항이 지켜졌다」의 증거로 쓰지 않는다.** 쓰임은 결정 10이
정한 것 하나 — **집계된 미달을 「지시문을 고치는 입력」으로 쓴다.**

### 약점 2 — barge-in이 턴을 합칠 수 있다 (조건부 · 지금 관측 불가)

⛔ `turns_observed`는 **agent 전사문 행 수**이고 턴 수와 같다는 것은 **「한 completion = 한 행」이
성립할 때만**이다. `contentEnd(INTERRUPTED)`가 flush하지 않으므로(`nova.py:442-443`) 그 completion의
`completionEnd`가 오지 않으면 두 턴이 한 행이 되어 **적게 센다**(근거는 §2.3).

⚠️ **지금 확정할 수 없다** — `VOICE_ADAPTER=stub`이라 barge-in 경로가 돌지 않는다. **미확정을
「성립한다」로 적지 않는 것이 이 절의 목적이다.** 방향은 셋이고 이 설계는 셋 다 하지 않는다:
Nova 실물에서 barge-in을 일으켜 확인(별도 관측 태스크) · `InterruptionEvent`를 세어 보정
(계측 대상이 계측을 바꾸는 결합이 생긴다) · 지표를 「행 수」로만 부르고 턴이라 부르지 않기.
⚠️ **`stub` 모드에서 이 약점은 발동하지 않는다** — 그래서 지금 구현·테스트는 유효하고,
Nova가 붙는 시점에 이 절을 다시 읽어야 한다.

---

## §6. 변경 대상과 테스트

**마이그레이션 0건.** ⛔ `mode`·`sessions.py:65`의 `'speaking'` 리터럴을 **건드리지 않는다**
(결정 11 — 정본은 `captain-decisions.md` §5).

| # | 파일 | 무엇 |
|--:|---|---|
| 1 | `app/config.py` | `Settings` 필드 2개 |
| 2 | `app/models/scenario.py` | **신설** — `SessionScenario` |
| 3 | `app/services/sessions.py` | `sp.questions` select · `PreparedPlan` + docstring `:122` · `load_session_scenario` · `summary` UPDATE |
| 4 | `app/api/ws.py` | `_load_scenario_or_none` + 배선 |
| 5 | `app/audio_gateway/factory.py` | 인자 1개(`scenario`) |
| 6 | `app/audio_gateway/nova.py` | 블록 조립 + **docstring 축 분석에 시나리오·질문·드릴 축 추가** |
| 7 | `app/api/results.py` | `drill` 키(생략 규약) |
| 8 | 프론트 결과 화면 | 사실 진술 한 줄 (문구는 톤 계약이 소유) |
| 9 | `app/services/results.py` | ⛔ **첫 판이 빠뜨렸다** — `SessionResult`(`:110-119`)에 `drill` 필드 + 조회. `api/results.py:6-7`이 *"라우터는 판정 로직을 갖지 않는다"*를 명시하므로 **조회를 라우터에 넣으면 그 모듈 계약 위반**이다 |
| 10 | `scripts/migrate.py` | `SEED_SCENARIOS` 3행 교체(`:34-55`) + `on conflict … do update set title, prompt_template`(`:109`) · `:33` 주석의 *"questions"* 서술도 함께 고친다 |
| 11 | `tests/unit/test_schema.py` | `:145` 서술(*"질문 3개"*) · `:164-169`의 title 단정 3건 |
| 12 | `tests/integration/test_ws.py` | ⛔ **spy 둘이 시그니처를 하드코딩한다**(`:306-320`·`:379-392`) → `scenario` kwarg가 늘면 **`TypeError`**. `:142-144`의 픽스처가 `values (…, $1, $1)`로 넣어 `title`=`prompt_template`을 만드는 것도 무대 모양으로 고친다 |
| 13 | `/.env.example` | ⛔ **실재한다**(§3 정정) — 드릴 값 2줄을 근거 주석과 함께 더한다 |

⛔ **순서가 있다 — 시드 교체(10·11)가 선행이다.** `title`≠`prompt_template`이 되기 전에는
§2.2의 규칙 6 방어와 그 tripwire가 **성립하지 않는다**(그 절의 ⛔ 상자). 시드를 먼저 바꾸고
`pg_dump` 백업 → 적용 → 3행을 직접 조회해 확인한 뒤 나머지로 간다.

**테스트 (T0 red→green — 구현 전 실패를 실제로 관측한다)**

- 조립 4조합: 시나리오·질문 각 유무 → 특히 **둘 다 없으면 `SYSTEM_PROMPT` 그 자체**
- 드릴 줄에 설정값 `N`이 실린다 · 우선순위 문장이 실린다 · 질문이 번호로 열거된다
- ⛔ **`in this order`가 없다는 tripwire** — 규칙 3 비대체를 지키는 회귀 방어
- ⛔ **`title`이 지시문에 없다는 tripwire** — 규칙 6
- SELECT 왕복(질문 3개·5개) · 검증 실패 → `None` + warning
- 시나리오: `scenario_id` null → `None` · 시나리오 행 부재 → `None`
- 기대값 경계 4건: 질문 3·5 × `drill_count` 1·3 → `min` 이 실제로 먹는지
- `turns_observed` = agent final 개수(사용자 발화만 있는 세션 → 0)
- 계획 없는 세션 → 응답에 `drill` 키 **없음**
- `drill_turns_min=0` → **기동 거부**
- **시드 3행이 무대다** — `title != prompt_template`이고 `prompt_template`이 `?`로 끝나지 않는다
  (⚠️ 이것이 §2.2 tripwire의 **선행 조건**이라 같은 판에서 함께 든다)
- **시드 upsert 멱등성** — `migrate.py`를 두 번 돌려 3행이 유지되고 내용이 새 값이다(`do update` 확인)
- **`SessionResult.drill`** — 계획 있는 세션에 값 · 없는 세션에 `None` → API 키 생략
- 무회귀: **666 passed 유지 또는 증가**. ⚠️ **`test_ws.py` spy 둘과 `test_schema.py` title 단정은
  「고쳐야 통과하는」 기존 테스트다** — red가 아니라 **회귀**이므로 T0 red 증거로 세지 않는다

---

## §7. 내가 유도한 것 8건 — 틀렸으면 이 줄만 뒤집으면 된다

`captain-decisions.md` §3의 선례를 따른다. **캡틴 결정이 답하지 않은 자리에서 내가 정한 것**이고,
근거는 각각 본문이 소유한다. 뒤집을 때 무엇을 지우는지 함께 적었다 — 그것이 이 절의 쓸모다.

| # | 유도 | 뒤집으면 |
|--:|---|---|
| 1 | `drill_count`·`drill_turns_min` **둘 다** 설정값으로 둔다 (결정 1 *"드릴 횟수"* 대 §2 *"드릴 턴 수"*의 어긋남 — §3) | 필드는 하나여야 한다 → **`drill_count`를 지우고** 기대 드릴 수를 질문 수로만 센다 |
| 2 | **마이그레이션 0건** — 기대 턴 수를 기존·미사용 `summary` jsonb에 둔다 (§2.3) | `learning_sessions`에 컬럼을 신설하고 **009**를 쓴다(008은 `TASK-26` 예약) → 스키마 변경이라 승인 항목이 하나 는다 |
| 3 | `questions` 검증 실패 시 **계획 전체를 포기**한다 (§2.1) | 질문만 빈 목록으로 떨어뜨리고 계획은 살린다 → 「드릴 지시 없는 세션」이 정상처럼 보인다 |
| 4 | 실제 턴 수를 **저장하지 않고 읽을 때 센다** (§2.3) | 세션 종료 시 저장한다 → 예외로 끝난 세션의 값을 잃고, 세는 자리가 둘이 된다 |
| 5 | `title`을 지시문에 **싣지 않는다** — 규칙 6 (§2.2). ⚠️ **결정 14의 시드 교체 뒤에만 실질이 있다** — 그전에는 두 값이 바이트 동일이라 공허했다 | 무대 문구에 제목을 앞세운다 → 무대를 더 진하게 하지만 메타데이터 노출 여지가 생긴다 |
| 6 | 질문 문구에서 **`in this order`를 뺀다** — 규칙 3 비대체 (§2.2) | 순서를 지정한다 → 드릴 순서가 예상 가능해지지만 규칙 3과 부딪힌다 |
| 7 | 드릴 반복이 **교정이 아니라고 지시문에 명시**한다 — 규칙 11의 반대 방향 (§2.2) | 그 문장을 뺀다 → 모델이 드릴 반복을 교정으로 세어 드릴이 1턴에 끝날 위험이 돌아온다 |
| 8 | 시드를 `on conflict … **do update**`로 바꾼다 (§2.1 · 결정 14는 「고친다」까지만 정했다) | `do nothing`을 두고 **일회성 UPDATE 스크립트**를 쓴다 → 시드 상수와 DB가 다시 갈라질 수 있지만, upsert가 손으로 고친 행을 덮을 위험은 없어진다 |

## §8. 범위 밖

`mode` 파라미터화(`TASK-27` AC#7이 소유 — 결정 11) · 결과 화면 **문구**(톤 계약이 소유) ·
드릴별 귀속(§5) · 시나리오를 대화에서 **생성**하는 것(결정 3의 후반부 — `TASK-5`).

---

_작성 2026-09-07. 인용한 `파일:줄`과 DB 표 모양은 **이 세션에서 직접 열어 확인했다** — 다른_
_세션의 보고를 근거로 쓴 곳은 없다. 설계 착수는 brainstorming architectural 경로이고 섹션 1~3을_
_각각 승인받아 이 문서로 굳혔다._
_결정 12로 일반 승인 게이트는 해제됐다 — 남은 것은 머리말 표의 **5건**뿐이고, 그 5건은_
_공개 계약·톤 계약에 닿아 결정 12 자신의 기준에 걸린다._

_2026-09-07 **2판**: critic `CHALLENGE` 지적 4건 + **캡틴 결정 14**(시드를 무대로 고친다)를 반영했다._
_⛔ **첫 판이 틀린 자리를 지우지 않고 남겼다** — `.env.example` 부재 주장과 「길이만 재고 내용을_
_안 본」 것 둘 다 본문에 정정으로 남아 있다. 지우면 같은 실수가 돌아온다._
_⚠️ **한 문장을 특히 기억할 것**: 인용의 출처가 정본(`captain-decisions.md`)이어도 **그 사실이_
_지금도 참인지는 직접 확인해야 한다** — 이 판의 오류 2건 중 1건이 그 경로로 들어왔다._
