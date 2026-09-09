# Handoff — OhMyEnglish

> **다음 세션이 첫 30초에 쓸 것만 담는다.** 최종 갱신 **2026-09-10** · 브랜치
> `design/first-vertical-slice`
> ⛔ **누적하지 않는다** (2026-09-10 사용자 지시). 끝난 일·결정 이력·상세 근거는 여기 두지 않고
> 정본을 가리킨다: 결정은 `docs/ops/captain-instruction-register.md` · 태스크 상태는 원장
> (`backlog task view <ID>`) · 관측은 `tests/harness/runs/**` · 함정은 `docs/ops/pitfalls.md`.
> ⛔ **줄 수·개수를 적지 않는다** — 적는 순간 낡는다(`H-O`).

## 다음 한 걸음

**`TASK-79` → `TASK-80` → 좁힌 재리뷰 → `TASK-73`.** 그 넷이 닫히면 **Phase 1 완료 선언**이 된다.

| | 무엇을 알고 착수하는가 |
|---|---|
| `TASK-79` | ⛔ **상수를 키워서 닫지 않는다.** 스윕이 언제 도는지 보장하는 **계약이 없어** 어떤 상수도 맞을 수 없다. 지금 계측도 지연 시나리오를 못 잡는다 |
| `TASK-80` | 결정 41(자격증명 회전 면제)에 **걸리지 않는다** — 회전이 아니라 선택 로직의 결함이다 |
| 재리뷰 | ⚠️ **범위를 좁혀 돌린다** (2026-09-10 사용자 지시: *"리뷰가 너무 길어지는 것 같아"*). 전체 Phase 1 모듈이 아니라 **`TASK-79`·`TASK-80` 이 건드린 자리와 이웃만.** 1·2차 판정이 나머지를 덮었다 |
| `TASK-73` | ⛔ **codex 리뷰가 도는 동안 뮤테이션을 걸지 않는다** — 리뷰어가 변이된 코드를 읽어 판정이 무효가 된다. 항목별 대상 단정은 그 노트가 줄 번호로 갖고 **W1 은 완료**다 |

**Phase 1 선언 자리는 AC 문서**(`docs/design/2026-08-25-first-slice-acceptance-criteria.md`
「선언 자리」 절)이고 6항목 대조의 근거는 `docs/design/2026-09-09-phase1-completion-audit.md` 다.
⛔ **원장에 상태를 두 벌 쓰지 않는다.**

## 착수 전 필수

1. ⛔ **받은 캡틴 결정을 다시 묻지 않는다.** 정본은 register 하나다. **지금 판단을 바꾸는 것 넷**:
   **43**(태스크 경계에서 멈추지 않는다 — 보고로 턴을 끝내지 않는다) · **40**(크리티컬 아닌 것은
   사전 승인 — 실물 호출·워커·재기동 포함) · **48**(red→green 의 등가 증거는 뮤테이션 KILL) ·
   **50**(발음 판정은 계획 수정 → 재측정 → 그때 우회로 제거. **그 순서를 건너뛰지 않는다**).
2. ⛔ **발음 tool 의 현재 사실**: 배선은 문제가 **아니고**(문장 되말하기 ⟺ tool) **지금 앱 설정에서
   코칭 자체가 안 일어난다** — 원인은 **계획 블록**(`Focus on:`·무대·힌트가 전부 문법을 가리킨다).
   지금 우회로를 걷어내면 **둘 다 0** 이 된다. 소유자 `TASK-78`(**다른 세션**).
   ⚠️ **`--app-prompt` 는 앱 프롬프트가 아니라 기반 프롬프트다**(2,339자). 앱은
   `build_system_prompt`(인자 6개)로 계획·무대를 붙여 보낸다 — **이 구별을 놓치면 통제 대조가
   무효다.** 재결정 전에는 `toolChoice` 강제를 제품 경로에 넣지 않는다(강제하면 발화가 사라진다).
3. ⚠️ **다른 세션이 같은 리포에서 일한다.** 매번 `ListAgents` 로 확인하고, **`pytest` 를 돌리기 전에
   알린다**(`H-X` 동시 실행 금지 — codex 도 스스로 돌린다). 커밋은 **경로를 열거해** 스테이징한다
   (`H-AM`). 남의 태스크 md·handoff 를 건드리지 않는다.
4. ⚠️ **백엔드 기준선**: pid **58241** · `VOICE_ADAPTER=stub_unresponsive` · `WORKER_ENABLED=false`.
   ⛔ **워커를 켜기 전에 `H-AT` 를 읽는다** — `flush_ended_sessions` 가 job 을 새로 만들어 보존
   세션을 파괴한다(실제로 두 번 일어났다). DB 는 **공유 인스턴스**다(`:5432`) — 재시작·
   `ALTER SYSTEM` 금지(`docs/ops/shared-database-guide.md`).
5. ⚠️ **`backlog task list --ready` 는 상태를 걸러내지 않는다** — SessionStart 브리핑의 분류를 믿는다.
6. **최근에 실제로 물린 함정 넷** (전체는 `docs/ops/pitfalls.md`): `H-AV`(`tests/` 아래 새 `.py` 는
   `ty` 대상인데 `pytest` 가 수집하지 않는다 — 하네스를 건드렸으면 게이트 넷을 모두 다시 잰다) ·
   `H-AJ`(`pytest` 에 **경로만** 주면 async 가 죽는다 → `-k` 만 쓴다) · `H-AU`(맨 `grep -r` 는
   셰임이라 전수에는 `command grep -r`) · `H-AR`(format 의 「N files」는 `.md` 를 세므로 지표로
   적지 않는다).

## 게이트 — 이 cwd 에서만 판정한다 (`H-A`)

```bash
cd app/backend
.venv/bin/pytest -q                        # ⛔ 동시 실행 금지 (H-X) · 경로만 주면 async 가 죽는다 (H-AJ)
.venv/bin/ruff check . && .venv/bin/ruff format --check .
/Users/redstar/.local/bin/ty check         # ⚠️ `.venv/bin/ty` 는 없다 — pipx 전역
.venv/bin/ruff check ../../tests ../../scripts    # 게이트 «밖» — 기준선 0
.venv/bin/ruff format --check ../../tests         # 게이트 «밖» — unformatted 0
cd ../frontend && npx tsc --noEmit && npx eslint app lib
```

⚠️ 게이트 전에 `brew services list | grep postgresql@17` — 안 떠 있으면 대량 errors 가 나는데
**회귀가 아니라 연결 거부다**(`H-T`).

## 인계 지표 — **직접 돌려** 얻고 대조한다

| # | 지표 | 2026-09-10 마감 시점에 직접 돌려 얻은 값 |
|--:|---|---|
| 1 | `git rev-parse --short HEAD` · `git status` | **`c572be4` 이상**(등호를 요구하지 않는다 — `H-P`) · `origin` 과 동기. ⚠️ 다른 세션이 동시에 쓰면 미커밋 0건이 아닐 수 있다 |
| 2 | `grep -h "^status:" backlog/tasks/*.md \| sort \| uniq -c` | 전체 **83** · Done **60** · To Do **20** · In Progress **3**(`TASK-70`·`TASK-73` 내 것 · **`TASK-78` 다른 세션**) · Awaiting Decision **0** |
| 3 | 게이트 | **884 passed** · `ruff check` exit 0 · format **unformatted 0** · `ty check` 통과 · 게이트 **밖** `ruff` **0건** · 프론트 `tsc`·`eslint` exit 0 |
| 4 | DB (읽기만) | `schema_migrations` **9** · `learning_sessions` **13** · `utterances` **120** · `error_patterns` **9** · `error_occurrences` **24** · `review_tasks` **15** · `session_plans` **2** · `pronunciation_attempts` **4** · `analysis_jobs` **49** · **보존 세션 6개 전건 생존**. ⚠️ **수치에 표 이름을 붙여 적는다** |
| 5 | 결과 API 상태 6개 | `210233be` `analyzing` · `6225ddaf` `final` · `b2f0d169` `partial_failure` · `76d9ef31` `connection_failed` · `d127dece` `no_utterances` · `e0c5e580` `final`(교정 2 + 드릴 미달 — **A4-2·A3-3 표본 겸용**). ⛔ **여섯을 지우지 않는다** |

⚠️ **3번과 5번이 핵심이다** — 읽기는 전달을 증명하지 못하고 **직접 돌린 출력**만 데이터다.
⚠️ **인용한 남의 수치는 그쪽이 고칠 때 함께 낡는다** — 최소 1건을 직접 검증하고, 정정되면 내 문서도
같은 턴에 고친다(2026-09-10 에 실제로 두 번 일어났다).

## 이 리포의 지배 실패 모드

**"본문을 고치고 그것을 설명하는 문장을 안 고친다."** 판별법: **본문을 고쳤으면 그것을 설명하는
문장·개수·방향·시그니처를 같은 커밋에서 함께 고친다.** 개수를 말하는 문장은 **아예 세지 않는
서술로 바꾸는 것**이 실제로 통한 유일한 구조적 해법이다.

⛔ 파생 규칙 셋 (전부 실측): **설계서·원장의 「~하지 않는다/없다」를 근거로 쓸 때 지금도 참인지
코드로 확인한다**(`H-AL`) · **재는 단위를 앱이 도는 단위와 맞춘다**(단일 발화로 재고 다중 턴을
결론해 결정 하나를 잘못 만들었다) · **한 명령에 여러 단계를 묶지 않는다**(앞 단계 실패를 확인하지
않고 다음을 실행해 보존 세션을 파괴했다 — `H-AT`).

## 진입 절차

1. **원장을 조회해 태스크 ID 를 말한 뒤 착수한다.** 태스크가 없는 일이면 **먼저 등록한다.**
2. 게이트를 `app/backend` cwd 에서 돌려 지표 3 과 대조한다. **다르면 그 차이를 먼저 설명한다.**
3. 태스크 상태는 원장을, 다음 걸음이 바뀌면 이 파일을 갱신한다. 커밋 뒤 **푸시한다.**
4. ⛔ **태스크를 `Done` 으로 올린 같은 턴에 다음 태스크를 조회해 착수한다 — 보고로 턴을 끝내지
   않는다**(결정 43). **멈추는 조건은 셋뿐이다**: 승인 밖 항목 · 인계 트리거(≲35%·compact 경고 —
   이때는 멈추는 것이 아니라 **마감**) · 사용자가 멈추라고 한다.
