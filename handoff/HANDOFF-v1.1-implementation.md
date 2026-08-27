# Handoff — 요구사항 v1.1 구현 (발음 시범·재발화 / 추천 학습 루틴)

> 이 갈래의 연속성만 담당한다. 제품 정본은 `handoff/HANDOFF.md`, 하네스는
> `handoff/HANDOFF-test-harness.md`, 수정 세션은 `handoff/HANDOFF-fix-session.md`다.
> 최종 갱신 **2026-08-28** · 기준 커밋 **HEAD ≥ `1a8c908`** · 브랜치 `design/first-vertical-slice`
>
> **다음 한 걸음: 계획 Task 6(세션 저장 · 한글 신호 · 종료 수렴).**
> Task 4·5는 끝났다. **지금 Nova는 발음을 교정해 주지만 기록이 남지 않는다** — Task 6이
> 그 구멍을 닫는다. 착수 전 §2.1(실제 시그니처)과 §6 "내 작업"을 읽어라.

---

## 0. 다음 세션이 30초 안에 알아야 할 것

1. **요구사항이 v1.1로 올라갔다.** 신규 2건 — `PRD.md` **§10 발음 시범·재발화**, **§11 학습 이력 기반 추천 학습 루틴**.
2. **§10은 구현 중이고 9태스크 중 5개가 끝났다.** 계획: `docs/design/2026-08-27-pronunciation-echo-plan.md`
3. **§11은 설계만 끝났고 코드가 0줄이다.**
4. **지금 `VOICE_ADAPTER=nova`로 돌리면 Nova가 발음을 교정해 준다 — 그런데 화면 배지도 없고 기록도 없다.** 서버는 프레임을 방송하지만 프론트가 그 프레임을 모른다(배지=Task 8). 단계별 실측은 **§3.2**. 다음 걸음 Task 6이 기록(저장·한글 신호·종료 수렴)을 닫는다.
   ⚠️ 단 **실물 Nova 왕복으로 확인한 것이 아니다** — §3.1을 읽어라. 앱이 보내는 스키마는 스파이크가 보낸 것과 다르다.
5. 게이트를 돌릴 때 **cwd가 `app/backend`여야 한다**(§4).
6. ⚠️ **계획 Task 6·7의 인터페이스 서술이 낡았다** — Task 4가 계획에서 2건 벗어났다(§2.1). 계획을 그대로 베끼지 말고 §2.1을 먼저 읽어라. 계획이 추측으로 적은 테스트 헬퍼 이름(`_prompt_start_payload`·`_drain_adapter_events`)도 **실제로 없다** — 진짜는 `_translate_all`·`stream.payloads`다.

---

## 1. 실측값 (2026-08-28, 이 절을 쓴 턴에 직접 실행)

```bash
cd app/backend && .venv/bin/pytest -q              # 304 passed
cd app/backend && .venv/bin/ruff check .            # All checks passed!
cd app/backend && .venv/bin/ruff format --check .   # 27 files already formatted
cd app/backend && ty check                          # All checks passed!
cd app/backend && .venv/bin/ruff check ../../tests ../../scripts   # Found 6 errors (베이스라인)
```

| 항목 | 값 |
|---|---|
| 테스트 | **304 passed** (v1.1 착수 전 기준선 241 → +63), skip/xfail 0 |
| ruff · format · ty | 전부 clean |
| `tests/**` ruff | **6건 잔존** — 하네스 5차수 정리 대상. 늘어나지 않았다 |
| `tests/**` format | **4건 잔존**(`ruff format --check ../../tests`) — 전부 `tests/harness/*`. **선언된 게이트 밖이다**(함정 H-L). 4를 넘으면 내가 만든 것이다 |
| dev DB | 마이그레이션 **3개**(001·003·**004**) · 세션 2 · 발화 6 · 패턴 1 · occurrence 2 · job 3 · `pronunciation_attempts` **0행** |
| 미커밋 | `.claude/settings.json`(untracked) — **지우지 마라**, 하네스의 "워크트리 금지"가 의존한다 |

004는 **dev DB에도 적용했다**(0행이라 무손실). 안 하면 Task 6이 쓰기를 연결한 뒤
`order by attempt_seq`가 `UndefinedColumnError`로 죽는다. 확인 명령:

```bash
app/backend/.venv/bin/python scripts/migrate.py   # 멱등
# → schema_migrations: 001_initial_schema.sql, 003_pronunciation_echo.sql, 004_pronunciation_attempt_seq.sql
```

---

## 2. 이번 갈래가 한 것 — 커밋 표

| 커밋 | 내용 |
|---|---|
| `c02dddb` | 문서 정합화 — 폐기 문서 이관, 카테고리 코드값 통일 |
| `c138190` | **요구사항 v1.1** — `PRD.md` §10·§11 신설, v1.0 사본 백업 |
| `d696043` | 설계 — 발음 설계서 신설 + 학습 코치 설계서 **정본 승격**(미결 3건 종결) |
| `167592a` | 구현 계획 9태스크 (TDD) |
| `f7b8ccc` | **003 마이그레이션** `pronunciation_attempts` |
| `a0eff8e` | **tool 페이로드 검증 모델** |
| `e6833c9` | **포트 확장** `PronunciationEvent` + 세션 분기 |
| `a02cae5` | 요구사항 v1.1 공유용 스냅샷 (Slack #clawair 전송) |
| `5c4087c` | 이 handoff 신설 + `HANDOFF.md` 인용 5건 재지정 |
| `aa1fcfe` | **004 마이그레이션** `attempt_seq` (삽입 순서 강제) |
| `ed91363` | **생명주기 서비스** (계획 Task 4) |
| `582eef6` | **코드리뷰 반영** — 판정이 보조 신호 행을 닫던 결함 + 거짓 주석 1건 + 값역 2건 |
| `b35dd07` | handoff 갱신 (Task 4 마감) |
| `b31227a` | **Nova 어댑터에 발음 tool 연결** (계획 Task 5, 리뷰 5건 반영 포함) |
| `1a8c908` | **fix: agent 텍스트 청크 이어붙이기** — 시범 문장이 전사문에 남게 |

### 리뷰 두 태스크 모두 두 패스를 받았다

**Task 4**: `/simplify` 4관점(reuse·simplification·efficiency·altitude) → code-reviewer(opus).
**Approve, CRITICAL 0.** 실측 재현된 결함 1건을 `582eef6`에서 고쳤고, 못 닫는 1건(설계 공백)은
§6 캡틴 결정 3-b로 올렸다.

**Task 5**: 품질 정리 + 코드리뷰 게이트를 한 리뷰어(opus)에 합쳐 위임. **CRITICAL 0, HIGH 2건**.
리뷰어가 게이트를 독립 재측정해 전부 일치했고, red도 `nova.py`만 HEAD로 되돌려 직접 재현했다.
- HIGH F1(프롬프트가 `target_sound`를 요구하지 않아 Task 7 패턴 upsert가 무증상 미실행) → `b31227a`
- HIGH F2(시범 문장이 전사문에 남지 않음) → **`1a8c908`으로 별 커밋** (Task 5 범위 밖이라 분리)
- MEDIUM/LOW 4건(로그 레벨·TOOL role 폴백·과장된 주석·format) → `b31227a`
- 남긴 것: F5(규칙 8이 설계 §3.3보다 넓다) → §6 1-b · 규칙 4 정본 불일치 → §6 1-c

---

## 2.1 Task 4가 계획에서 벗어난 2건 — **계획을 그대로 베끼면 안 된다**

계획 Task 4~7의 인터페이스 서술이 이 두 건 때문에 낡았다. 계획 문서는 고치지 않았다
(승인된 산출물이라 손대지 않는다) — **여기가 정본이다.**

**① 정렬 키가 `created_at`이 아니라 `attempt_seq`다** (004 신설).
계획은 `order by created_at desc`였다. 그런데 `created_at`의 DEFAULT는 `now()` =
**트랜잭션 시각**이라 한 트랜잭션에서 만든 두 행이 동값이고 "최신 pending"을 고를 수 없다.
실측: `created_at desc, id desc`로 **3회 중 1회** 오래된 쪽을 골랐다(`id`가 난수 uuid라
tie-break가 50%로 뒤집힌다). 앱에서 `clock_timestamp()`로 덮는 안을 **버린 이유**는
그러면 불변조건이 함수 하나의 규약이 되고 표를 직접 쓰는 다른 writer(테스트 픽스처·시더·
백필)를 구속하지 못하기 때문이다 — `tests/unit/test_schema.py`의 INSERT들이 이미
`created_at`을 생략한다. `created_at` DEFAULT는 `now()`로 **그대로 뒀다**: 학습 코치의
시간창 조회(003의 `created_at desc` 인덱스)에는 트랜잭션 시각이 오히려 옳다.

⚠️ **한정 — 리뷰가 붙인 정확한 범위.** 그 "3회 중 1회"는 `db_conn` 픽스처(테스트 하나를
트랜잭션 하나로 감싼다)에서 난 값이다. **오늘 프로덕션에서는 도달 불가능하다** — 모든
writer가 이벤트마다 `pool.acquire()` → autocommit → INSERT마다 별 트랜잭션이라 `now()`가
갈린다. 즉 004가 오늘 막는 것은 **테스트 flake**이고, 내일 막는 것은 **Task 7이 여러 문장을
한 트랜잭션에 넣을 때**다. 그래도 컬럼은 값을 한다: "호출자가 마침 autocommit을 쓴다"에
의존하는 것이 설계서가 경계하는 숨은 계약 그 자체다. 003의 `created_at desc` 인덱스는
**오늘 읽는 코드가 0개**다(학습 코치 시간창용 선provision, 그쪽은 0줄).

**② 보조 신호는 `record_signal`이라는 별 함수다.** 계획은
`record_attempt(..., signal_source=...)` 한 함수였다. 그러면 **인자값이 생명주기 동작을
바꾼다** — 호출부에서 무엇이 일어나는지 안 보이고, Task 7이 세 번째 스위치를 같은 함수에
얹으라고 지시한다. 설계서 §6.1(`signal_source`는 서술 컬럼)·§3.1(판단 주체는 Gateway)이
둘 다 "호출자가 결정하고 저장소는 따른다"를 가리켜 결정을 함수 이름으로 올렸다.

**Task 6이 실제로 쓸 시그니처** (계획 :1186·:1214의 서술을 이것으로 대체):

```python
from app.services.pronunciation import record_attempt, record_signal, resolve_dangling

# Nova tool 이벤트 (pending / 판정 둘 다)
await record_attempt(conn, session_id, target_form=..., outcome=...,
                     spoken_form=..., target_sound=..., utterance_id=...)
#   ↑ signal_source 인자가 **없다**. 항상 'nova_tool'이다.

# 한글 전사 보조 신호 — 열린 pending을 닫지 않고 자기 행을 만든다
await record_signal(conn, session_id, target_form="(전사문이 한국어로 인식되었습니다)",
                    outcome="unclear", signal_source="korean_transcript",
                    spoken_form=..., utterance_id=...)
#   signal_source 값역은 AssistSignal = Literal["korean_transcript", "agent_reprompt"]
#   'nova_tool'을 주면 ty가 잡는다 (의도된 것)

# 세션 종료 — 반드시 세션 종료 기록과 **같은 트랜잭션**에서
await resolve_dangling(conn, session_id)
```

---

## 3. 남은 작업 — 계획 Task 6~9

정본: `docs/design/2026-08-27-pronunciation-echo-plan.md` (각 태스크에 실제 코드가 있다).
⚠️ 계획의 **예상 passed 수는 전부 낡았다** — 실제 기준선이 **304**다(계획은 241 기준).

| # | 태스크 | 현재 상태 |
|--:|---|---|
| ~~4~~ | ~~시도 생명주기 서비스~~ | ✅ **완료** `ed91363` — `record_attempt`·`record_signal`·`resolve_dangling`, 테스트 13건 |
| ~~5~~ | ~~Nova 어댑터 연결~~ | ✅ **완료** — `promptStart.toolConfiguration` 전송 · `toolUse` → `PronunciationEvent` 변환 · `SYSTEM_PROMPT` 규칙 7~10. 테스트 13건. ⚠️ **실물 Nova 왕복은 아직 안 했다**(§3.1) |
| **6** | 세션 저장·한글 신호·종료 수렴 | `record_attempt` 앱 호출처 **0곳** · 한글 감지(`가-힣`) 0곳. 현재는 **방송만** 한다 |
| **7** | 패턴 연결 (`error_patterns` upsert) | 0곳. **착수 전에 §6 "내 작업"의 트랜잭션 항목을 먼저 처리해라** |
| **8** | 결과 화면 발음 카드 | 백엔드 0곳 · 프론트 **0파일** |
| **9** | 하네스 5차수 P9~P12 | 미작성 |

### 3.1 ⚠️ Task 5의 미검증 구멍 — 앱이 보내는 스키마는 스파이크가 보낸 것과 다르다

Task 5는 **단위 테스트만** 통과했다(가짜 스트림). 실물 Nova 왕복으로 확인한 것이 아니다.
그리고 앱이 보내는 tool 스키마는 스파이크가 보낸 것과 **같지 않다**:

| | 스파이크 (`spike_nova_protocol.py:87`) | 앱 (`models/pronunciation.py:44`) |
|---|---|---|
| 필드 | 3개 — `spoken_form`·`target_form`·`outcome` | **4개** — +`target_sound` |
| required | 3개 전부 | **2개** (`target_form`·`outcome`) |
| `outcome` enum | `correct`·`incorrect`·`unclear` | **+`pending`** (F4로 승격) |
| 시스템 프롬프트 | 5문장 전용 프롬프트 | 규칙 **10개** 전문 |

즉 "스파이크가 실증한 형태"는 **봉투 모양**(`toolConfiguration` → `toolSpec` →
`inputSchema.json`이 문자열)까지만 참이고, **내용은 실증되지 않았다.** Nova가 4필드
스키마나 `pending` enum을 거부할 근거는 없지만 확인도 없다.

**닫는 방법**: Task 8 Step 4의 종단 확인(백엔드 :8002 + `VOICE_ADAPTER=nova` + 발음
픽스처 주입)이 첫 실물 검증이 된다. 그 전에 값싸게 보고 싶으면 `spike_nova_protocol.py`의
`_PRONUNCIATION_TOOL_SCHEMA`를 앱 상수로 바꿔 1회 왕복한다. **5차수 P9가 이 확인을 포함해야
한다** — 아니면 "발음 루틴이 동작한다"는 주장의 근거가 단위 테스트뿐이다.

### 3.2 Task 5가 끝난 지금 실제로 무엇이 되고 무엇이 안 되나 (실측)

| 단계 | 상태 |
|---|---|
| Nova가 발음을 지적하고 문장을 다시 읽어준다 | ✅ 지시문 규칙 7~10이 들어갔다 (실물 미검증 — §3.1) |
| `toolUse`가 온다 | ✅ `toolConfiguration` 전송 |
| `PronunciationEvent`로 번역된다 | ✅ `NovaEventTranslator._on_tool_use` |
| 서버가 `{"type":"pronunciation"}` 프레임을 방송한다 | ✅ **이미 된다** — `session.py:215`의 분기가 Task 3에서 들어갔다 |
| **프론트가 그 프레임으로 배지를 띄운다** | ❌ **아니다.** `app/frontend/lib/ws.ts`의 `ServerEvent` 유니온에 `pronunciation`이 **없고** `app/frontend/app/page.tsx`의 switch에 `case "pronunciation"`도 **없다**(실측 0곳). `isServerEvent`는 통과시키므로 프레임이 switch까지 가서 **조용히 무시**된다 — 크래시는 없다. 배지는 **Task 8** |
| **DB에 저장된다** | ❌ **Task 6** — `_broadcast_pronunciation`이 저장하지 않는다(`session.py:225` 주석이 그렇게 적어 뒀다) |
| 한글 전사 보조 신호 | ❌ Task 6 |
| 세션 종료 시 pending 수렴 | ❌ Task 6 (`resolve_dangling` 호출처 0곳) |
| 패턴 연결 | ❌ Task 7 |
| 결과 화면 발음 카드 | ❌ Task 8 |

즉 **지금 `VOICE_ADAPTER=nova`로 돌리면 Nova가 발음을 교정해 주지만, 화면에 배지도 안 뜨고
기록도 남지 않는다.** 학습자가 얻는 것은 **그 순간 들리는 음성 교정뿐**이다.
Task 6이 기록을, Task 8이 화면을 닫는다.

⚠️ **한 줄로 요약하면**: "배지가 뜬다"고 적힌 낡은 서술을 믿고 nova로 띄운 뒤 배지가 없는 것을
보고 **정상인** 어댑터·세션을 디버깅하지 마라. 프론트는 아직 그 프레임을 모른다.

### §11 (추천 학습 루틴) — 별도 계획이 아직 없다

설계서 `docs/design/2026-08-25-learning-coach-agent-design.md`(정본) §12.1의 **2슬라이스**로 가기로 결정됐다. 계획 문서를 쓰는 것이 첫 걸음이다.

| 확인 항목 | 실측 |
|---|---|
| 테이블 `session_plans`·`learner_notes`·`pattern_attempts` | **전부 없음** (003의 `pattern_attempts` 언급은 "왜 합치지 않는가" **주석**이다) |
| 컬럼 `next_review_at`·`mastery_score`·`review_tasks`·`current_level`·`self_difficulty`·`impact_score`·`suggested_contexts` | **각 앱 참조 0곳** |
| `sessions.py:29` | 여전히 `order by created_at, id limit 1` — 고정 시나리오 1개 |
| `port.py` `start()` | 인자 없음 — 지시문을 넘길 자리가 없다 |

**권고 순서**: §10 Task 4~6 → §11 슬라이스 1(데이터 유실 정지) → §10 Task 7~8 → §11 슬라이스 2.
슬라이스 1을 먼저 하는 이유: `suggested_contexts`는 모델이 산출해도 지금 **버려지고 소급이 불가능하다**.

---

## 4. 반복하지 말 것 (이번 세션에 실제로 걸린 함정)

| # | 함정 | 대응 |
|---|---|---|
| **H-A** | **게이트의 cwd가 판정의 일부다.** 리포루트에는 ruff 설정이 없어 거기서 돌리면 기본 규칙으로 `check .` **56 errors** · `format --check .` **21 files**가 난다. 회귀가 아니다 | 반드시 `cd app/backend` 후 판정. 이 handoff를 쓰다가 나도 한 번 걸렸다 |
| **H-B** | `python3 scripts/migrate.py`는 **돌지 않는다** — 시스템 python에 asyncpg가 없다 | `app/backend/.venv/bin/python scripts/migrate.py` |
| **H-C** | `git add -A`가 `.claude/settings.json`을 끌어들인다 | 경로를 명시해 add한다 |
| **H-D** | **유니온 타입을 넓히는 변경은 모든 소비처와 함께 착지해야 한다.** `AdapterEvent`에 5번째 타입을 넣자 `ty`가 `session.py`의 `event.kind`를 잡았다 — 분기가 없으면 런타임 `AttributeError`로 세션이 죽는다 | 포트 확장과 `isinstance` 분기를 한 커밋에 |
| **H-E** | `db_conn` 픽스처는 테스트 하나를 **트랜잭션 하나**로 감싼다. CHECK 위반이 트랜잭션을 abort시켜 **한 테스트에 `pytest.raises`를 두 번 넣을 수 없다** | 음성 케이스마다 테스트를 쪼갠다 |
| **H-F** | `ty`는 `tests/`까지 본다. 억제 주석은 **오류가 보고되는 그 줄**에 붙여야 한다(호출 첫 줄에 붙이면 `unused-ignore` 경고) | `bogus=1,  # ty: ignore[unknown-argument]` |
| **H-G** | macOS에 `tac`이 없다 | `tail -r` 또는 `git log --reverse` |
| **H-H** | `PRD.md`는 `:29`~`:117`, `requirements-summary.md`는 `:15`~`:60`이 **줄 단위로 인용**된다(실측 13곳·5곳) | 새 내용은 **문서 끝에만** 추가. 기존 절은 **한 줄 → 한 줄** 교체만. 규약은 각 문서 맨 아래 |
| **H-I** | **`db_conn` 픽스처는 마이그레이션만 적용하고 시드는 하지 않는다.** 계획 Task 4가 쓴 `select id from users limit 1` 헬퍼는 `None`을 돌려주고 not-null 위반으로 죽는다. 시드는 `scripts/migrate.py`의 `seed()`가 하고 `test_schema.py`만 그걸 명시 호출한다 | `db_conn` 테스트는 사용자·세션을 **직접 insert**한다. 리포 관례이기도 하다(`test_schema.py`·`test_utterances.py`·`test_jobs.py` 전부 자기 헬퍼를 쓴다). 커밋된 행이 필요하면 `db_pool`+`committed_session` |
| **H-J** | **트랜잭션 시각 함정은 1회 실행으로 안 드러난다.** `created_at default now()`로 정렬하는 테스트가 **3회 중 1회만** 실패했다 — 한 번 돌려 통과하면 정상으로 보인다 | 순서·시각에 의존하는 테스트는 **최소 3~5회 반복 실행**으로 판정한다. 근본 대응은 정렬 키를 단조값으로 두는 것(004 `attempt_seq`) |
| **H-L** | **선언된 게이트에 구멍이 있다 — `ruff format`이 `tests/`를 보지 않는다.** 게이트는 `ruff format --check .`(cwd `app/backend`)인데 그 범위에 `tests/`가 없다. `ruff check`는 `../../tests`를 따로 돌리도록 문서화됐지만 **format은 그 짝이 없다.** 그래서 테스트 파일의 포맷 위반이 **무증상으로 커밋된다** — Task 4·5가 각각 1건씩 남겼고 리뷰가 잡았다 | 테스트를 건드린 커밋 전에 **`.venv/bin/ruff format --check ../../tests`를 함께 돌린다**. 현재 잔존 **4건**은 전부 `tests/harness/*`(기존) — 5차수 정리 대상. 이 수치가 4를 넘으면 내가 만든 것이다 |
| **H-M** | **"실패하는 테스트를 먼저 썼다"가 증거로 약할 수 있다.** Task 5는 13건을 먼저 썼지만 실제 red는 **5건**이었다 — 나머지 8건(모르는 tool 무시·깨진 페이로드 6종·발음 이벤트 0건)은 구현이 없으면 **자동으로 통과하는 부재 가드**다. `_on_tool_use`를 통째로 지워도 계속 초록이다 | 부재를 단정하는 테스트는 T0 증거로 쓰지 않는다. red 개수를 세어 **"N건 중 M건이 red였다"**로 적는다. 긍정 단정(이벤트가 실제로 만들어진다)이 짝을 이루는지 확인한다 |
| **H-K** | **`ty`의 검사 범위는 리포루트 `ty.toml`의 `[src] include = ["app/backend/app", "tests"]`다.** `app/backend/` 직하에 둔 파일은 **조용히 검사되지 않는다** — `x: int = "문자열"`도 통과한다. 타입 방어가 실제로 작동하는지 확인하려다 "ty가 못 잡는다"는 잘못된 결론을 낼 수 있다(내가 한 번 냈다) | 타입 가드 검증용 임시 파일은 **`tests/` 안에** 두고 확인 후 지운다. `ty.toml:8`이 `[tool.ty]`를 pyproject에 추가하지 말라고 경고하는 것도 같은 이유다 |

---

## 5. 결정과 근거 (뒤집지 말 것 — 뒤집으려면 근거를 반박해야 한다)

**① 발음 판정 주체 = Nova (전사문 경로 아님).**
4차수 P2가 실측했다 — 음소를 치환해 발음해도 ASR이 원문으로 복원해 전사문에 흔적이 **0**이다. 전사문만 받는 분석 워커는 **원리적으로** 발음을 판정할 수 없다. `services/analysis.py:48`의 금지 카테고리 설정은 옳다.

**② Nova tool use가 동작한다 — 그리고 지시하면 Nova가 실제로 교정한다.**
2026-08-27 스파이크(`tests/harness/runs/2026-08-27-P-tooluse-spike/`, git 추적). `promptStart.toolConfiguration`이 받아들여지고 `contentStart(type=TOOL,role=TOOL)` → `toolUse` → `contentEnd(stopReason=TOOL_USE)` 순서로 온다. `inputSchema.json`은 **JSON 문자열**이어야 한다.

Nova가 실제로 낸 응답: *"Say this after me: I think I found three very useful videos."* → *"Now you repeat that sentence for me."*

→ **4차수의 "Nova도 발음을 지적하지 않았다"는 능력 부재가 아니라 지시 부재였다.** 이 결론이 캡틴의 "수정 보류" 결정을 뒤집은 근거다.

재현: `cd app/backend && .venv/bin/python ../../tests/harness/spike_nova_protocol.py --wav p1m.wav --tools`

**③ Nova는 재발화 *전에* tool을 부른다** (`outcome: "pending"`, `spoken_form: "[awaiting user repetition]"`).
그래서 시도를 **2단계 생명주기**로 모델링한다: `pending` INSERT → 판정 UPDATE → **세션 종료 시 남은 `pending`을 `unclear`로 수렴**. 마지막 규칙이 핵심 방어다 — `pending`을 영구히 남기면 미판정 시도가 숙련도를 왜곡한다.

**④ Nova가 스키마 enum을 어겼다** (`pending`은 내가 준 enum에 없던 값).
그래서 ⓐ `pending`을 정식 값으로 승격했고 ⓑ 페이로드를 **신뢰하지 않고 강등·폐기**한다. 엄격 검증으로 거부하지 않는 이유는 전례다 — 1차수 I-5에서 모델 출력에 엄격 검증을 걸었을 때 발화가 5회 재시도 끝에 `failed`가 됐다.

**⑤ 교정 예산 = B안.** 일반 세션은 문법 우선, 발음은 보조 신호가 뜬 경우만 개입. 발음 집중은 추가 학습 메뉴의 독립 항목. 근거: 안 들리는 일은 드문데 매 턴 예산을 뺏기면 핵심 루프가 흔들린다.

**⑥ 학습 코치 설계서 미결 3건 종결.** 최근 창 14일 **유지** / 정답 판정은 **두 경로 병존**(문법=분석 워커, 발음=Nova tool) / `impact_score` **영구 제외**.

**⑧ 시도의 순서는 DB가 강제한다 — 앱 규약이 아니다** (004 `attempt_seq`). 상세와 버린 대안은 §2.1 ①. 요지: 벽시계는 순서의 대리일 뿐이고, 함수 하나의 규약은 표를 직접 쓰는 다른 writer를 구속하지 못한다.

**⑨ 보조 신호와 Nova 생명주기는 다른 함수다** (`record_signal` vs `record_attempt`). 상세는 §2.1 ②. 요지: 인자값이 생명주기 동작을 바꾸면 호출부에서 안 보인다. 설계서 §6.1이 `signal_source`를 서술 컬럼으로 정의한 것과 맞춘다.

**⑦ `pronunciation_attempts`를 `pattern_attempts`와 합치지 않는다.** 그 표는 `unique(pattern_id, utterance_id)`로 "패턴이 있는 발화의 재발화"를 센다. 발음 시도는 패턴이 아직 없을 수 있고, tool 호출이 발화가 아니며, `target_form`·`signal_source`처럼 자리가 없는 필드를 갖는다.

---

## 6. 미결 — 소유자별

### 캡틴 결정 대기

1. ~~**`toolResult`를 Nova에 돌려보내야 하는가.**~~ → ✅ **결정됨(2026-08-28): 보내지 않는다.**
   기본안 유지 — 관측된 거동을 따른다(스파이크에서 안 보냈는데 `END_TURN`으로 정상 종료).
   계획 Task 5가 이미 이 전제로 쓰여 있어 추가 작업이 0이다.
   ⚠️ **그 관측은 1회뿐이다** — 다중 턴에서 Nova가 응답을 기다리며 멈추는지는 여전히 미검증이다.
   멈춤이 재현되면 그때 추가한다. 확인 방법은 `spike_nova_protocol.py --tools`에 2턴 주입을
   더하는 것이고, **5차수 관측 대상으로 넘긴다**(계획 Task 9의 P9~P12와 함께).
1-b. ⭐ **교정 예산이 프롬프트에서 설계보다 넓다 — 기록되지 않은 요구사항 갭.** (Task 5 리뷰 MEDIUM)
설계서 §3.3은 일반 Speaking 세션에서 **"보조 신호가 떴을 때만"** 발음 개입이라고 정했는데,
`SYSTEM_PROMPT` 규칙 8은 **무조건**이다("When a sound is clearly off"). 좁혀 줄 장치가
§4.1이 말한 **지시문 가변부**인데 **계획 Task 1~9에 그 구현이 없다**(grep "가변부"·"개입 모드"
0건 — 학습 코치 설계서 §5.2가 만드는 자리다).
**failure**: 문법 오류 + 살짝 흐린 발음이 같은 턴에 있으면 규칙 8이 발음 개입을 발동하고
규칙 10이 문법 동시 교정을 금지해 **문법 교정이 밀려난다.** 매 턴 반복되면 §3.3이 막으려던
"핵심 루프가 흔들린다"가 그대로 일어난다.
선택지: (a) 지금은 수용하고 **5차수에 대조군**(발음 오류 없는 픽스처로 일반 대화 1턴,
`partial`/`final` 프레임 수와 agent 행 수가 3차수 N5와 같은지)으로 관측한다
(b) §11 학습 코치의 지시문 가변부가 붙을 때 함께 좁힌다. **계획 위반은 아니다** — 계획대로
구현했고 계획 Self-Review가 R10-4 갭만 적고 이 갭은 적지 않았다.

1-c. **규칙 4의 교정 상한이 요구사항 정본과 어긋난다** (Task 5 리뷰 ①, **기존 불일치**).
`docs/agent-system-prompt.md:19`는 "at most one **or two** high-impact recurring errors"이고
설계서 §3.3이 그 줄을 인용한다. 그런데 `nova.py`의 규칙 4는 **"At most one** correction per
turn"이다 — 이 diff 이전부터 있던 불일치인데, Task 5의 규칙 10이 "one-per-turn"을 다시
못박아 **두 곳으로 굳혔다**. (계획 :1069는 "one-or-two"라고 썼지만 그대로 넣으면 같은
프롬프트 안의 규칙 4와 정면 모순이라 규칙 4에 맞췄다 — 그 판단은 리뷰도 옳다고 봤다.)
선택지: (a) 정본을 코드에 맞춘다("at most one") (b) 규칙 4를 정본에 맞춘다("one or two").
**Surgical Changes상 지금 규칙 4를 손대지 않았다** — 캡틴 결정 사항이다.

2. **`agent_reprompt` 보조 신호를 유지할 가치가 있는가.** 문구 매칭이라 취약하다. **첫 구현에서 제외했고 그래서 R10-4의 절반이 미충족이다.** 5차수 관측 후 판정.
3. **발음 `pattern_key`의 값역.** `target_sound`를 Nova가 만들면 키가 흩어질 수 있다(`th_as_s` vs `theta_to_s`). **기본안: §5.6 규약 재사용**(기존 키 주입 + 재사용 우선).

3-b. ⭐ **판정↔시범 짝짓기에 상관키가 없다 — Task 8 착수 전 결정 필요.** (Task 4 코드리뷰
HIGH, 실측 재현). 판정 UPDATE는 `session_id` + 최신 pending만 보고 **판정의 `target_form`을
버린다**. 그래서 Nova가 A를 시범한 뒤 B에 대한 판정을 보내면 한 행에
`target_form='Sentence A.'` + `spoken_form=B의 발화`가 **어긋난 채** 저장되고, ① 학습자에게
보일 쌍이 틀리고 ② A의 pending이 소비돼 §3.2 수렴이 "A는 대답 없이 끝났다"를 기록하지 못하고
③ Task 7이 B의 `target_sound`로 만든 패턴을 A의 행에 연결한다.
**계획 위반이 아니다** — 설계서 §3.2·계획 :594가 "최신순 매칭"만 규정한 **설계 공백**이다.
선택지: (a) 서브쿼리에 `and target_form = $N` 술어를 더한다 (b) 다르면 warning 로그만 남기고
최신순을 의식적으로 수용하고 설계서 §8 D5에 5번째 약점으로 적는다.
**Task 8이 이 쌍을 화면에 렌더하므로 그 전에 정해야 한다.**
4. 이월 중인 기존 게이트 3건 — 실물 마이크 1회 / 발음 픽스처 보정 / M계층 반영 단위(A·B 함께 쓰기)

### 내 작업

- ⭐ **Task 7 착수 전 필수 — `record_attempt`가 자기 트랜잭션을 열어야 한다.** 지금은
  호출자의 것을 쓴다. 설계서 §7 Failure가 "시도 INSERT와 패턴 upsert를 **한 트랜잭션**에
  둔다"를 요구하는데, 계획 Task 6의 호출자가 `pool.acquire()`(**autocommit**, 계획 :1185)라
  호출자에게 맡기면 부분 실행이 생긴다 — 패턴 `frequency`만 +1 되거나 시도의 `pattern_id`가
  null로 남는다. 대응은 `async with conn.transaction():`(호출자 트랜잭션이 있으면 savepoint로
  합성된다 — `services/utterances.py:13-17`이 같은 결론을 문서화). **Task 4에서 넣지 않은
  이유**는 실패하는 테스트를 붙일 수 없어서다(묶일 두 번째 문장이 아직 없다). 모듈
  docstring에도 미결로 남겼다.
- ⚠️ **Task 6 (d) "세션 종료 기록과 같은 트랜잭션"은 지금 구조로 불가능하다.**
  `services/sessions.py:49-54`의 `mark_session_ended(pool, session_id, status)`가 `pool`을
  받아 **자기 연결을 acquire**한다(`session.py:148`에서 호출). 합류할 트랜잭션이 없다.
  문자 그대로 하려면 그 시그니처를 `conn`으로 바꾸고 `_close_and_record`가 `db.tx()`를
  열어야 한다 — **`pronunciation.py`가 아니라 거기서 고칠 일이다.** 실측으로 확인했다.
- ⚠️ **Task 6에서 `_record_pronunciation`을 `create_task`로 띄우면 동시성 결함이 열린다.**
  `record_attempt`의 판정 서브쿼리 `for update`는 "같은 행을 닫는 것"은 막지만, 잠금이 풀리면
  EPQ 재검사가 이미 닫힌 행을 떨어뜨리고 서브쿼리가 **다음 pending으로 전진**해 무관한 시도를
  닫는다(리뷰가 연결 2개로 실측). 지금은 `_pump_adapter_events`가 순차 await라 도달 불가지만
  `session.py:249`의 `_store_final`이 이미 `create_task`+`shield` 패턴이라 그대로 베끼면 즉시
  도달한다. **띄울 거면 동시성 테스트를 함께 붙여라.** 코드 주석에도 남겼다.
- **계획 Task 7의 버그를 미리 잡아 두었다**: `error_patterns.target_form`이 **not null**이라 계획에 쓴 upsert가 그대로면 실패한다. 값을 채워야 한다.
- 계획 Task 6·8의 테스트 본문에 `...`가 남아 있다 — 기존 `test_gateway.py`·`test_results.py`의 가짜 어댑터 헬퍼 이름을 확인하지 않았다. **파일을 열어 재사용**하고 새로 만들지 않는다.
- `tests/**` ruff 6건 — 하네스 5차수에서 정리
- **추적 체크리스트 HTML** (캡틴 요청) — 요구사항 상세 기능이 설계·구현에 실제로 반영됐는지 대조표. 구현이 끝난 뒤 만든다

---

## 7. 다음 세션 진입 절차

1. 이 파일과 `handoff/HANDOFF.md`를 읽는다 (CLAUDE.md `<handoff>` 규약).
2. `git log --oneline --reverse c02dddb~1..HEAD`로 위 커밋 표와 대조 (**HEAD ≥ `ed91363`**).
3. 게이트 4개를 **`app/backend` cwd에서** 돌려 §1의 수치(**285 passed**)와 일치하는지 확인한다. 다르면 그 차이를 먼저 설명한다.
4. Nova를 건드리면 `spike_nova_protocol.py --wav p1a.wav`로 자격증명 생존을 먼저 확인한다.
5. **§2.1을 읽는다** — 계획 Task 6·7의 인터페이스 서술이 낡았다. 계획을 그대로 베끼면 없는 인자(`signal_source=`)를 넘겨 `TypeError`가 난다.
6. 계획 `docs/design/2026-08-27-pronunciation-echo-plan.md`의 **Task 6**부터 TDD로 진행한다.
   - 계획 Task 6의 테스트 본문에 `...`가 있다 — `tests/integration/test_gateway.py`의 **기존 가짜 어댑터·세션 구동 헬퍼를 파일을 열어 확인**하고 재사용한다. Task 5에서 같은 일을 했고, 계획이 추측한 이름은 실제로 없었다.
   - Task 6 (d)의 "세션 종료 기록과 같은 트랜잭션"은 **지금 구조로 불가능하다** — §6 "내 작업" 두 번째 항목을 먼저 읽어라.
7. **테스트를 건드렸으면 `ruff format --check ../../tests`를 함께 돌린다** — 선언된 게이트 밖이라 무증상으로 커밋된다(함정 H-L). 잔존 4건이 기준이다.
8. **각 태스크 완료 직후 이 파일을 갱신한다** — 별도 지시를 기다리지 않는다.

## 8. 관련 문서

| 문서 | 역할 |
|---|---|
| `docs/PRD.md` (v1.1) | **요구사항 정본.** §10·§11이 이 작업의 근거 |
| `docs/requirements-summary.md` (v1.1) | 학습자 관점 요약, PRD와 같은 버전 |
| `docs/share/2026-08-27-requirements-v1.1.md` | Slack 공유용 스냅샷 (파생본 — 손으로 고치지 말 것) |
| `docs/design/2026-08-27-pronunciation-echo-design.md` | §10 설계 (4 Lenses · PS1~PS10) |
| `docs/design/2026-08-27-pronunciation-echo-plan.md` | §10 **구현 계획 9태스크** |
| `docs/design/2026-08-25-learning-coach-agent-design.md` | §11 설계 (**정본 승격**, 2슬라이스) |
| `docs/storyboard.html` | 03b 발음 시범 · 03c 추천 루틴 화면 |
| `tests/harness/runs/2026-08-27-P-tooluse-spike/` | tool use 실증 원자료 |
| `docs/backup/superseded/README.md` | 폐기 문서 규약 (수정 금지) |
