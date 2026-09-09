# Phase 1 완료 선언 6항목 대조 (TASK-47 · G-6)

> **판정: 전건 충족이 아님. 6항목 중 4항목 충족 · 2항목은 「충족 판정 불가 — 증거 부재」임.**
> 그래서 이 문서는 **완료를 선언하지 않음.** 대조 기준은
> `docs/design/2026-08-25-first-slice-acceptance-criteria.md` 「완료 선언 규칙」임.
>
> ⛔ **원장에 상태를 두 벌 쓰지 않음** — 각 항목의 후속 작업은 태스크가 소유하고 이 문서는
> **판정과 근거**만 담음. 이 문서를 상태판으로 쓰지 않음.
>
> **모든 수치는 2026-09-09 에 내가 직접 돌려 얻은 것임.** 남이 적어 둔 수치를 그대로 옮긴 자리는
> 그 사실을 표시했음.

---

## 0. 먼저 — 캡틴이 지목했던 미충족 셋은 전부 닫혔음

`docs/design/2026-08-30-captain-decisions-phase1.md` 의 **결정 B-7** 이 *"미완료 항목은 수정하거나,
추가 테스트 수행"* 으로 남기면서 미충족을 **셋**으로 지목했음 — W-live 1회 · E2E-S 1회 · 실물 마이크.

| B-7 이 지목한 것 | 지금 상태 | 증거 |
|---|---|---|
| W-live 1회 | ✅ | 2026-09-09 에 **내가 직접** 돌려 `PASS: 12/12` (§2) |
| E2E-S 1회 | ✅ | `tests/harness/runs/2026-08-26-run-1.md` 6스텝 기록 (§3) |
| 실물 마이크 | ✅ **2회** | `runs/2026-09-01-mic-1.md:16` — 세션 `bbfc3908` `completed` · **3분 28초** · 발화 **51건** · `pronunciation_attempts` **3행** 최초 기록. `runs/2026-09-03-mic-2.md:9` — I-1 오탐 해소 **판정 3/3** |

⚠️ **파일 이름만 인용하지 않고 열어서 읽었고, 한 값은 DB 로 교차 대조했음.** mic-1 이 적은 세션
시각(`22:17:46`)이 내가 방금 `learning_sessions` 에서 읽은 `bbfc3908|completed|2026-08-31 22:17:46`
과 일치함. **발화 51건은 스텁이 낼 수 없는 수임** — 실물 오디오가 흘렀다는 것의 직접 증거임.

⚠️ **그런데 B-7 은 6항목 전체를 훑은 것이 아님** — 아래 항목 4·6 은 그 목록에 없었고, 이 대조에서
처음 증거 부재로 드러났음. **B-7 이 닫혔다는 것과 6항목이 전건 충족이라는 것은 다름.**

---

## 1. 항목 1 — F·W·R·G·U 전 항목 pass → ✅ 충족

### F — 기반

| | 판정 | 직접 돌려 얻은 증거 |
|---|---|---|
| F1 스키마·시드 | ✅ | `schema_migrations` **9행** · `users` **1행**(고정 사용자) · `learning_scenarios` **3행**이고 셋 다 `category='daily_life'`(일상) — `After work with a colleague` · `Weekend plans with a friend` · `Tonight's plans at home` |
| F2 툴체인·품질 게이트 | ✅ | `.venv/bin/python -V` → **3.13.12** · `pyproject.toml:5` `requires-python = ">=3.12,<3.14"` · `aws-sdk-bedrock-runtime` **0.10.0** 설치되고 `import aws_sdk_bedrock_runtime` 성공 · `ruff check` exit 0 · `ruff format --check` unformatted 0 · `ty check` exit 0 |
| F3 테스트 건전성 | ✅ | `pytest -q -rsxX` → **884 passed** 이고 **skip·xfail 보고 줄이 0건**. 소스에서도 `@pytest.mark.skip`·`skipif`·`xfail`·`.only` 가 0건 |
| F4 스키마 문서 정합화 | ✅ **(001 기준)** | 기계 대조로 001 의 **8표 전부 컬럼 단위 일치**(문서가 언급하지 않는 컬럼 0건 — `analysis_jobs` 의 `or` 히트는 다중 행 CHECK 안의 조각이라 파서 잡음이고 직접 열어 확인했음). 「도입 단계」도 문서의 **12표 전부**에 표기돼 있음 |
| F5 자격증명 격리·비노출 | ✅ **(문면)** | `app/backend/.env` 가 git 추적 밖이고 이력에도 0건 · `.gitignore:26-27` 이 `.env`·`.env.*` 를 무시 · `test_config.py:424` 가 「자격증명 문자열이 `config.py` 밖의 `app/` 코드에 없다」를 단정 · 프론트 `app`·`lib` 에서 `aws_`·`secret`·`bearer`·`password`·`access_key` **0건** |

⚠️ **F4 의 001 밖 공백 하나** — `docs/database-schema.md` 가 `session_plans`·`learner_notes`
(둘 다 `007_learning_coach_slice2.sql`)를 **다루지 않음.** 007 은 **슬라이스 2** 이므로 Phase 1 완료
기준 밖이라 미충족으로 세지 않았음. ⛔ **그래도 문서-SQL 불일치가 F4 의 존재 이유이므로 태스크로
남김.**

⛔ **F5 의 잔여 노출을 숨기지 않고 적음** — 추적되는 `.env.example` 에 **`.env` 와 동일한 실제 DB
비밀번호**가 들어 있고 리포는 PUBLIC 임(길이를 각각 재서 값이 같음을 확인했음). F5 의 문면은
`.env` 만 말하므로 판정은 충족이지만, 이 위험의 소유자는 **결정 41**(회전 면제)과 **결정 42**
(선택지 셋)임 — 여기서 다시 발명하지 않음.
⚠️ **비밀번호가 4자라 `git grep` 으로 「이력에 없다」를 잴 수 없음** — 4자 문자열은 `uv.lock` 같은
무관한 파일에도 걸려 **판별력이 0임.** 그 grep 결과를 증거로 쓰지 않았음.

### W — 분석 워커 + PG 큐 → ✅ 전 항목 테스트 실재

각 항목을 지목하는 테스트를 파일·줄로 인용함. 전부 위 **884 passed** 에 포함됨.

| | 테스트 |
|---|---|
| W1 | `tests/unit/test_utterances.py:1` · `tests/integration/test_worker.py:1`·`:276`(active 세션 job 이 1사이클 후 done — 관측형). ⛔ **아래 정정 참조 — 원자성 부분의 근거가 공허했다** |
| W2 | `tests/unit/test_analysis.py:1` · `tests/integration/test_pipeline.py:163`(같은 key → patterns 1행 / occurrences 2행 / frequency 2) |
| W3 | `tests/unit/test_utterances.py:329` · `tests/unit/test_jobs.py:1` |
| W4 | `tests/unit/test_jobs.py:171`(lease 만료 회수 + 이전 token 의 complete 가 False) |
| W5 | `tests/unit/test_jobs.py:248`(attempts 상한 → failed + last_error, 재claim 불가) |
| W6 | `tests/unit/test_utterances.py:134`·`:211`(voice_command 는 저장되나 job 미등록) |
| W7 | `tests/unit/test_claude_schema.py:1` · `tests/integration/test_pipeline.py:277` |

⛔ **W2 의 실물 계약은 가짜 클라이언트로 잴 수 없음** — AC 의 「W1~W7 검증 방식」이 그것을 명시하고
**W-live 가 담당함.** §2 가 그 증거임.

⛔ **2026-09-09 정정 — W1 의 「원자성」 부분은 이 대조가 충족으로 셀 근거가 없었다.** 항목 6의
코드 리뷰(`TASK-70`)가 지적하고 팀리드가 코드로 확인했다:
`tests/unit/test_utterances.py:117` 이 `async with db_conn.transaction():` 으로 **호출자
트랜잭션**을 열어 두 호출을 감싸는데, **프로덕션은 그 패턴을 금지한다** —
`_flush_analysis` 의 docstring 이 *"호출자의 트랜잭션 안에서 부르지 않는다"* 를 명시한다.
즉 테스트가 증명하는 성질을 프로덕션이 의도적으로 피하고, AC W1 의 *"한 트랜잭션이고"* 는
**프로덕션 경로에서 검증된 적이 없다.**
⚠️ **덮지 않고 정정으로 남긴다** — 이 대조가 「테스트가 실재한다」를 충족의 근거로 쓴 것이
어디까지 통하는지가 다음 사람에게 필요하다. 소유자는 `TASK-76` 이고, I-1 이후 설계(묶음 단위
job)와 AC 문면이 어긋난 것도 그 태스크가 함께 판정한다.
⚠️ **피해 자체는 리퍼+스윕이 덮는다** — `flush_ended_sessions` + `reap_orphan_sessions` 가
「전사문만 남고 job 이 없다」를 영구 상태로 두지 않는다(`services/utterances.py:238~252`).
그래서 항목 1 전체 판정은 유지하고 이 한 칸만 정정한다.

### R · G · U → ✅ 전 항목 증거 실재

| | 증거 |
|---|---|
| R1 | `tests/unit/test_results.py:1`·`:114`(3패턴 세션 → 정확히 2개, high 가 medium 보다 먼저) |
| R2 | `tests/unit/test_results.py:197`(analyzing + corrections 키 부재) ·`:267` |
| R3 | `tests/unit/test_results.py:267`(failed 1 + done 2 → partial_failure + 성공분 병존) |
| G1 | `tests/integration/test_gateway.py:1`·`:8`(close 가 종료 기록보다 먼저)·`:194` |
| G2 | `tests/integration/test_gateway.py:733`(무응답 → failed + 실패 이벤트, 무한 대기 없음) |
| G3 | `tests/integration/test_gateway.py:1081`·`:1113`(소켓 계층이 `nova` 를 import 하지 않는 이음매) |
| G4 | `tests/integration/test_gateway.py:608`(픽스처 완주 → final 3행 + job 3건) · `tests/integration/test_ws.py:1` |
| U1 | 브라우저 회차 `runs/2026-09-06-t3-c2-render-hierarchy.md:12` **PASS**(A2-1·A2-2·A2-3 전건 · 라이트·다크 두 모드). 부분=`--foreground-muted`·확정=`--foreground` 가 계산 스타일에서 토큰 probe 와 일치함(`:28`·`:31`). 게이트는 `tests/harness/test_c2_gates.py` · 세션 완주는 `c1_session_walkthrough.py`+`test_c1_gates.py` |
| U2 | 브라우저 회차 C3 — 2026-09-09 에 **내가 직접** 돌려 **단정 94건 전건 통과**(5상태 + 없는 세션 + 드릴 계약). `runs/2026-09-09-task34-drill-number-contract.md` |

---

## 2. 항목 2 — W-live 1회 → ✅ 충족 (직접 돌렸음)

⛔ **기존 기록을 그대로 옮기지 않고 다시 돌린 이유가 있음.** `runs/2026-09-04-slice1-live.md:69` 는
`PASS: 11/11` 을 적었는데 **그 뒤 스크립트의 단정이 12개로 늘었음**(`d0dca09`·`2b90c40` — TASK-43
복습 과제 히스토리). 즉 **첨부된 출력이 현재 코드를 증명하지 못하는 상태**였음. 완료 선언의 증거로
쓰려면 낡은 수치를 쓸 수 없음.

2026-09-09 실행 — `cd app/backend && .venv/bin/python ../../scripts/smoke_analysis.py`:

```
job1: status=done attempts=1        'I usually go to gym after work.'
job2: status=done attempts=1        'I usually go to office by subway.'
PASS: 12/12 단정 통과
```

단정 12건이 전부 ✓ 임 — `error_patterns 1행` · `error_occurrences 2행` · `frequency=2` ·
`category=article` · `target_form에 'the' 포함` · **`두 번째 분석 프롬프트에 첫 pattern_key 포함`** ·
`신규 key 형식 ^article_[a-z0-9_]+$` · `실물 모델이 suggested_contexts를 냈다` ·
`next_review_at이 채워졌다` · `review_tasks 자연키 중복 없음` · `패턴당 열린 단계 최대 하나` ·
`pattern_attempts의 outcome이 값역 안`.

**여섯째 단정이 §5.6 계약의 실물 증거임** — 실제 Claude 가 주입된 목록에서 기존 `pattern_key` 를
재사용했고, 그래서 두 발화가 패턴 1행으로 병합되며 `frequency=2` 가 됐음. 저장된 값도 그것을 보임:
`pattern_key='article_missing_before_noun'` · `frequency=2` · occurrence 2건.

⚠️ **전용 스모크 DB 만 씀** — 스크립트가 `ohmyenglish_smoke` 를 drop/create 하므로 dev·test DB 와
보존 세션에 닿지 않음(스크립트 docstring 이 그것을 명시하고 직접 읽어 확인했음).

---

## 3. 항목 3 — E2E-S 1회 → ✅ 충족. 스텝 1 을 미충족으로 세지 않음 (판정과 근거)

증거는 `tests/harness/runs/2026-08-26-run-1.md` 의 6스텝 기록임. 쟁점은 그 문서 `:108` 이 적은
한 줄임 — *"AC `E2E-S` 스텝 1의 「오디오 프레임 전송 확인」은 스텁 모드에서 구조적으로 관측
불가능하다."*

**판정: 미충족으로 세지 않음.** 근거 셋임.

1. **원인이 앱 결함이 아님.** 스텁 세션 전체가 **0.139초**인데 `RECORDER_TIMESLICE_MS = 250` 이라
   첫 `ondataavailable` 이 터지기 전에 `session_ended` → `stopMedia()` 가 끝나 있음. 합성 스트림이
   무음이 아닌 것은 격리 검증으로 확인됐음(`MediaRecorder` 900ms → **4청크·14,683B**).
2. **같은 사실이 다른 자리에서 관측됐음.** 같은 회차 문서가 경로 관통을 적음 —
   `getUserMedia` → `MediaRecorder`(opus) → `blobToBase64` → `WebSocket.send`, 그리고 서버가
   **유효 base64 3프레임을 무경고로 흡수**했음(A2).
3. **실물 마이크 2회에서 실제 오디오가 흘렀음** — mic-1 이 세션 `bbfc3908` 에서 **3분 28초 ·
   발화 51건**을 기록했고 그 시각이 DB 와 일치함(§0). **스텁 세션은 0.139초에 끝나므로 51건을 낼
   수 없음** — 스텁에서 관측 못 한 것이 실물에서는 관측됐다는 뜻임.

⛔ **왜 이렇게 판정하는가가 중요함.** 스텁으로 **원리적으로** 관측할 수 없는 것을 미충족으로 세면
그 AC 는 어떤 스텁 회차로도 만족될 수 없고, **「완료」가 영원히 도달 불가능한 상태**가 됨. 그것은
기준이 아니라 함정임. 대신 **그 한 줄을 지우지 않고 남김** — 다음 사람이 「스텁으로 재보면 되지
않나」를 다시 묻지 않게 하는 것이 그 문장의 값어치임.

---

## 4. 항목 4 — 각 W/R/G AC 테스트의 red→green 증거 → ⛔ 충족 판정 불가 (증거 부재)

**찾은 것**: Phase 1 구현 창(`de61434`~`5c6c92c`)의 커밋 중 본문에 `red` 증거를 담은 것은 **4건**
이고 **전부 `fix:`** 임 — `3d823ae`(pool 경쟁) · `e002f79`(attempts 상한 좀비 job) ·
`fb3754d`(쓰기 원자성·문장 시계·seq 경쟁) · `5c6c92c`(게이트웨이 실패 경로). 그중 `fb3754d` 는
red 출력을 값으로 적었음(*"백오프가 transaction_timestamp가 아닌 문장 시계 기준(red: 정확히
120초)"* · *"실제 2커넥션 경합 → 재시도로 seq 1,2 두 행 모두 저장(red: UniqueViolation)"*).

**못 찾은 것**: **W/R/G AC 테스트를 도입한 `feat:` 커밋 본문에는 red 기록이 없음** — 다섯 개를
직접 열어 확인했음(`1351c0b` W3·W4·W5 · `e6f58a7` W1·W6 · `e96ab01` W2 · `7d453e4` R1~R3 ·
`bac4144` G1~G4). 그리고 `docs/design/2026-08-25-phase1-implementation-plan.md` 의 체크박스가
**36개 전부 미체크**임 — 태스크별 red→green 확인 칸이 그 안에 있음.

⛔ **이것은 사후에 만들 수 없는 증거임.** 2026-08 에 일어난 red 를 지금 다시 관측할 수 없음. 그래서
선택은 둘뿐이고 **둘 다 사람의 결정임** — ⑴ Phase 1 코드에 대해 이 항목을 면제하고 그 사실을
기록함 ⑵ 지금 리포가 널리 쓰는 **뮤테이션 KILL 확인**을 이 항목의 등가 증거로 인정함(테스트가
결함을 실제로 잡는 것을 보이는 것이 red→green 의 목적이었으므로). 태스크로 등록하고
`Awaiting Decision` 으로 둠.

---

## 5. 항목 5 — `/simplify` 실행 후 7단계 재검증 → ✅ 충족

`b915b09`(2026-08-25) — *"Applies the 8 confirmed /simplify (4-lens) fixes"* 이고 본문이 재검증을
함께 적었음: *"No behavior change; full backend suite (199 passed) and lint/type checks stay green."*
⚠️ **199 는 그 시점의 수임** — 지금은 884 이고 그 사이에 게이트 테스트가 늘었음. 이 항목이 요구한
것은 **그때 재검증이 돌았는가**이므로 수의 차이는 미충족이 아님.

---

## 6. 항목 6 — code-reviewer Approve → ⛔ 충족 판정 불가 (증거 부재)

**찾은 것**: 태스크별 리뷰와 고침 라운드가 실재함 — Phase 1 창 커밋 본문에 *"Task 9 fix round 1 —
리뷰 Important 5건 + 컨트롤러 추가 1건. 전건 revert-재현으로…"* · *"리뷰 fix round 1 — Important
5건 + Minor 1건"* · *"리뷰 Important 3건 (fix round 2)"* 가 있음. 즉 리뷰는 돌았고 지적은 반영됐음.

**못 찾은 것**: **Phase 1 전체에 대한 `Approve` 판정 기록**. 계획 문서가 남은 단계를
*"re-review → W-live → E2E-S → /simplify+최종 리뷰"* 로 적었는데 그 **「최종 리뷰」의 판정 기록이
없음.** 리포에 있는 `Approve` 기록은 전부 **다른 범위**임 — 2026-09-04 것은 **학습 코치 슬라이스 1**
(006·`review_tasks`)이고 S2-* 는 슬라이스 2 임. `.superpowers/sdd/` 의 보고서 셋도 슬라이스 2 ·
시나리오·쉐도잉 범위임.

⛔ **이 항목은 지금 실행할 수 있음** — red→green 과 달리 리뷰는 사후에 돌려도 같은 판정을 냄.
그래서 결정 사안이 아니라 **작업**임. 태스크로 등록함(`TASK-70`).

### 2026-09-09 실행 결과 — **Not Approve · HIGH 3건**

`codex exec review` 를 Phase 1 소유 모듈 범위로 돌렸음(과거 diff 가 아니라 **현재 상태** — 그
파일들이 이후 슬라이스로 바뀌었으므로 그때의 diff 를 보면 지금 없는 코드를 본다).

| 지적 | 팀리드 검증 | 처리 |
|---|---|---|
| 실행 중 어댑터 오류를 `completed` 로 기록함 (`session.py`) | ✅ **맞음** — `finally` 가 무조건 `completed` 를 기록해 R2 가 `connection_failed` 에 걸리지 못함 | ✅ **고쳤음.** red 를 먼저 관측하고(`assert 'completed' == 'failed'`) 고친 뒤 885 passed |
| 전사문 저장과 job 등록의 원자성 (`session.py`) | ⚠️ **프레이밍을 정정함** — 「전사문만 남는다」는 리퍼+스윕이 덮음. **실제 내용은 그 테스트가 공허하다는 것**이고 그것은 맞음 | `TASK-76` |
| 종단 이벤트 없는 소켓 종료를 성공으로 처리함 (`page.tsx`) | ✅ **맞음** — `onClose` 가 `session_ended` 수신을 보지 않고, 이른 종단 상태 읽기가 폴링을 영구히 멈춤 | `TASK-77` |

⛔ **Approve 가 아니므로 `TASK-70` 을 닫지 않음.** 그 태스크의 AC 가 *"Approve 전에 Done 으로
올리지 않는다"* 를 요구함. `TASK-76`·`TASK-77` 이 닫힌 뒤 재리뷰해야 함.

---

## 7. 완료 선언을 어디에 쓰는가 (AC#3)

**자리: `docs/design/2026-08-25-first-slice-acceptance-criteria.md` 의 「완료 선언 규칙」 절 바로
아래.** 규칙을 소유한 문서가 그 판정도 소유하는 것이 맞고, 규칙과 판정이 떨어져 있으면 한쪽만 읽고
결론을 내게 됨.

⛔ **원장에는 상태를 두 벌 쓰지 않음** — 원장은 후속 태스크의 상태만 갖고, 판정과 근거는 이 문서와
AC 문서가 가짐. **이 문서를 진행판으로 쓰지 않음.**

**지금 선언하지 않음** — 항목 4·6 이 열려 있음. 그 둘이 닫히면 AC 문서의 그 자리에 선언을 적음.
