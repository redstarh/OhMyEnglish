# Handoff — 계획 프롬프트·배치·시나리오 생성 갈래 · 세션 `ohmyenglish-f4` (마감)

> 인계 원칙의 정본은 `~/.claude/rules/session-handoff.md` 임. 짧게 씀 — 판정 근거를 옮기지 않고
> 태스크 조회와 회차를 가리킴(`backlog task view <ID> --plain`).
>
> 이전 판은 `handoff/archive/HANDOFF-plan-prompt-2026-09-13-0007.md` 임.
> ⛔ 다른 갈래의 handoff 를 건드리지 않았음 — `HANDOFF-pronunciation.md` 는 발음 축 소유임.

최종 갱신 2026-09-13 · 브랜치 `design/first-vertical-slice`

---

## ① 이 세션이 한 것

**닫은 태스크 셋**: `TASK-130`(설계 결함 판정) · `TASK-130.1`(그 결정의 구현) · `TASK-5`(계획 여섯 완료).
**받은 사용자 결정 하나**: **81** — 노출 순서를 `created_at` 에서 떼어내 `display_order` 로 옮김.
정본은 `docs/ops/captain-instruction-register.md` 임.

**제품에 들어간 것**: 마이그레이션 **019**(`display_order`) · 시드가 배열 자리를 1부터 매기고 upsert 가
그것을 갱신함 · 읽는 자리 넷을 옮김(후보 SQL · `Candidate`→`_staleness` ⑶ · `scenario_progress` 정렬) ·
`nova._SCENARIO_INTAKE_INSTRUCTION`(질문 다섯) · `build_system_prompt` 의 필수 인자 `scenario_intake` ·
`ws.py` 의 무대 정하기 진입과 세션 행 `mode` 기록 · 프런트 「질문 답변 5개」에 `mode` 추가.

**회차**: `tests/harness/runs/2026-09-12-task4-rotation-app-path.md` **§3-3·§3-4**(새로 씀).
**등록한 함정**: `H-BR`(같은 파일을 두 세션이 고칠 때 나는 조용한 혼입 — 아래 ⑤).

## ② 다음 한 걸음 — `TASK-102.1` AC#1

`TASK-102` 는 AC#2(대화형 생성) 하나만 남았고 배선은 끝났음. 남은 것은 **실측**이고 그것을
`TASK-102.1` 이 갖음. **AC#1 은 사람 없이 돌 수 있어 먼저 함** — 스텁 어댑터로 앱 경로를 열어
`?mode=scenario_intake` 세션을 끝내고, `analysis_jobs` 에 `generate_scenario` 가 걸리는지와 워커가
그것을 처리해 `source='generated'` 행이 생기는지를 봄.

⛔ **착수 전에 `tests/harness/p5_worker_leg.py` 머리말을 끝까지 읽음.** `H-AT` 경로 둘이 보존 세션을
파괴하고 그 파괴가 `learning_sessions.status` 에 드러나지 않음 — 이 회차가 그 함정의 사정권임.

**AC#2 는 실물 Nova 세션이라 사용자 승인이 필요함**(결정 38·39 의 선례 · 마이크가 있어야 함).
그것 없이 「다섯을 하나씩 묻는다」를 참으로 적지 않음.

**나란히 가능**: `TASK-132` AC#1(`Awaiting Decision` · 파서 두 판을 합칠지) · `TASK-122`(빈 이름 키 · `low`).

## ③ 착수 전 필수 — 7개

1. ⛔ 태스크를 새로 열기 전에 **결정 대장과 원장을 함께** `grep` 함(같은 요구가 두 태스크에 있었음).
2. ⛔ **부분 실행에 `-c pyproject.toml`** 을 붙임(`H-AJ`). 빼면 `asyncio` 모드가 안 걸려 거짓 빨강임.
3. ⛔ **게이트는 cwd `app/backend`**(`H-A`·`H-BN`). 리포 루트에서 부르면 `line-length` 를 88 로 잼.
4. ⛔ **`ty` 는 절대경로 `/Users/redstar/.local/bin/ty`** — 이름만으로는 **exit 127** 임.
5. ⛔ `git add <디렉터리>` 금지(`H-BE`) · 커밋 **전** `git diff --cached --name-only` · push **전**
   `git log --oneline origin/<브랜치>..HEAD`(`H-BO`). **그리고 공유 파일은 고친 턴에 커밋함**(`H-BR`).
6. ⚠️ 마이그레이션 번호는 적용 직전 `schema_migrations` 조회로 발급함(`H-AL`) — **이 마감 시점의
   최대는 `019`** 임(dev DB 에 적용됨).
7. ⛔ **`db_pool` 픽스처는 아무것도 정리하지 않음** — 손으로 지움. **사용자를 먼저** 지워야
   세션·발화·job 이 cascade 되고 그 뒤에 무대를 지울 수 있음(반대 순서는 FK 위반).

## ④ 인계 지표 — 이 마감 시점에 직접 돌려 얻음

| # | 지표 | 값 |
|--:|---|---|
| 1 | 기준 커밋 | **`765c98e`** · `origin` 과 **동기**(`rev-list --left-right --count` → `0 0`) · **미커밋 0건** |
| 2 | 다음 걸음 | **`TASK-102.1` AC#1** (스텁으로 파이프라인만). `Awaiting Decision` 1건 = `TASK-132` |
| 3 | 게이트 | **전부 초록 · 종료코드까지 확인함** — `pytest` **1088 passed**(exit 0) · `ruff check .` 0 · 게이트 밖 `ruff check` 0 · `ruff format --check` 0(204 files) · `ty` 0 · 프런트 `tsc --noEmit` exit 0 · `eslint` exit 0 |
| 4 | 착수 전 필수 | 7개(③) · 원장 집계 To Do 11 · In Progress 7 · Awaiting Decision 1 · Done 125 |

⚠️ **`In Progress` 7건 가운데 여섯은 발음 축 것임**(`TASK-116`·`78`·`81`·`97`·`128`·`128.4`). 내 것은
`TASK-102` 하나임 — 그 축의 상태를 내가 고치지 않음.

## ⑤ 이 세션이 얻은 규율

- ⛔ **전건 초록이 이행을 뜻하지 않음 — 축을 옮길 때 «옛 축을 재는 단정»을 남기지 않음.** 019 를
  넣고 앱 넷을 옮긴 직후 `pytest` 가 1080 passed 였는데 기존 단정들은 여전히 `created_at` 을 재고
  있었음. 통과해도 아무것도 지키지 않는 단정임.
- ⛔ **필터가 무엇을 배제하는지 먼저 봄.** 무력화 검증을 `-k "scenario"` 로 돌려 **9 passed** 를 보고
  「판별력 없음」으로 판정할 뻔했음 — 새 테스트 이름에 그 낱말이 없어 **안 돌았던 것**임. 통과
  개수가 그대로면 「안 깨졌다」가 아니라 「안 돌았다」일 수 있음.
- ⛔ **같은 파일을 두 세션이 고치면 먼저 커밋하는 쪽이 남의 편집을 담아 감**(`H-BR`). `git add` 에
  경로를 열거해도 그 파일 «안»의 남의 편집은 못 막고, 병합 충돌이 나지 않아 도구가 알려 주지 않음.
  드러난 신호는 **내가 고친 파일이 `git status` 에 없었던 것** 하나였음.
- ⚠️ **과거 감사 기록의 문면은 고치지 않고 «이후 변경»을 덧붙임.** 현재 코드에 맞추려 고치면 그
  회차의 증거가 훼손됨(`scenarios-E-agent-learning.md:169`).
- ⚠️ **설계서가 정하지 않은 자리를 만나면 규약이 가리키는 층에 둠.** 무대 정하기 세션에서 드릴
  질문·무대를 걷는 판단이 그것이고, 조립 규약 ⑵(소켓이 데이터로 정함)에 따라 소켓에 뒀음.
