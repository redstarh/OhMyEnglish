# Handoff — 계획 프롬프트·비용 관측 갈래 · 세션 `ohmyenglish-f4` (마감)

> 인계 원칙의 정본은 `~/.claude/rules/session-handoff.md` 임. 짧게 씀 — 판정 근거를 옮기지 않고
> 태스크 조회와 회차 기록을 가리킴(`backlog task view <ID> --plain`).
>
> 이전 판 없음 — 이 파일이 첫 판임(2026-09-12 신설). 백업 대상이 없어 archive 로 복사하지 않았음.
> ⛔ 다른 갈래의 handoff 를 건드리지 않았음 — `HANDOFF-pronunciation.md` 는 세션 `ohmyenglish-19`,
> `HANDOFF-test-harness.md` 는 테스트 갈래 소유임. 구현·감사 갈래는 미사용으로 판정해
> `handoff/backup/2026-09-12/` 로 내렸음(`TASK-117` · 그 폴더 `README.md` 가 근거와 되살리는 명령을 가짐).

최종 갱신 2026-09-12 · 브랜치 `design/first-vertical-slice`

---

## ① 이 세션이 한 것 — 검증과 프롬프트의 어긋남을 닫고 비용을 볼 수단을 만듦

닫은 태스크: `TASK-117` · `TASK-108` · `TASK-119` · `TASK-121` · `TASK-112` · `TASK-60` ·
`TASK-124` · `TASK-126`. 부분 진행 하나: `TASK-39`(AC#1 닫음 — 재시도·타임아웃 명시 · AC#2 는
운영 관찰 항목).
판정과 근거는 각 태스크 노트가 정본임.

회차 기록이 이 세션의 관측 정본임(아래 목록 그대로).

1. `runs/2026-09-12-task108-deepest-marker.md` — 표식 대상 초점 포함 3/3 · `parse_plan` 통과 2/3.
2. `runs/2026-09-12-task119-extra-keys.md` — 여분 키 2/5 · 전역 금지 문장이 이미 있었음.
3. `runs/2026-09-12-task121-level-bullet.md` — 이름 있는 형태 0/8 · 이름 없는 빈 키 1/8.
4. `runs/2026-09-12-task39-retry-policy.md` — 전송 5회 → 2회 · `max_attempts` 키가 실제 전송 수와
   1 어긋남(`total_max_attempts` 는 정확히 일치) · 계획 크기 호출의 실제 소요 30.27초·18.25초.
5. `runs/2026-09-12-task124-nova-usage.md` — Nova 1세션에서 `purpose=nova` 행이 **정확히 1건** ·
   `input 216 = speech 150 + text 66`. ⛔ `output_tokens=0` 이 §0 조건과 어긋났고 원인을 적었음
   (무음이 없어 endpointing 이 안 걸려 응답 발화 전에 끝났음 — 기록 경로 결함이 아님).

제품에 들어간 것: 만성 줄의 `[deepest recurrence]` 표식 + 조건부 `_DEEPEST_FOCUS_RULE` ·
`- level:` 불릿의 국소 금지 문장 · `set_session_mode` 로 `mode=pronunciation` 기록 ·
`llm_calls` 와 사용량 기록(Claude 는 호출 단위 · Nova 는 세션 단위) · Bedrock 재시도·타임아웃
명시(`config.bedrock_boto_config`) · 사용량 집계와 보고 CLI(`load_usage_summary` ·
`scripts/usage_report.py`).

마이그레이션을 발급·적용했음 — `013_llm_calls.sql` · `014_pronunciation_session_mode.sql` ·
`015_llm_calls_token_split.sql`.
⛔ `scripts/migrate.py` 를 돌리지 않고 `psql` 로 파일 둘만 적용했음(그 스크립트의 시드 upsert 가
공유 DB 의 가변 컬럼을 덮음). `schema_migrations` 행은 같은 트랜잭션에서 직접 넣었음.

받은 결정: `66`(사용량은 새 표 `llm_calls`) · `67`(`mode` 값역에 `pronunciation`) ·
`68`(Nova 는 토큰 열 넷으로 speech·text 를 나눠 담음).
정본은 `docs/ops/captain-instruction-register.md` 임.

## ② 다음 한 걸음 — `TASK-127` 의 결정을 받는 것

**`TASK-127`(`Awaiting Decision`)** — LLM 단가를 어디에 둘지. 지금 집계는 **토큰까지만** 내고
금액을 내지 않음(`TASK-126` AC#4 가 그것을 금지했음). ⛔ 단가는 공개 문서 값이라 이 리포가
**관측할 수 없음** — 사람이 줘야 하므로 결정 항목임. 후보 셋과 대가는 그 태스크가 가짐.

⚠️ **비용을 보는 수단은 이제 있음** — `cd app/backend && .venv/bin/python ../../scripts/usage_report.py`.
화면·API 를 붙일지는 아직 정하지 않았음(그 자리를 CLI 가 임시로 메움).

- 나란히 가능(둘 다 조건이 붙음): `TASK-122`(빈 이름 키 · `low` · 되살릴 조건은 그 노트) ·
  `TASK-41`(전용 스키마 이관 — ⛔ **캡틴 결정 31 이 「모든 구현 뒤」로 미뤄 뒀음.** 지금 조사하면
  표가 늘 때마다 낡음).
- ⛔ **`TASK-39` AC#2 는 「닫을 수 있는 작업」이 아님** — 스로틀을 재현하지 않기로 정했고(회차 §0)
  운영에서 관측될 때 세는 항목임. 세는 방법은 그 회차 실행체가 보여 줌(`before-send` 계수기).
  ⛔ `llm_calls` 로는 못 봄 — SDK 안의 재전송이 1건으로 보임.
- ⚠️ **`TASK-124` 가 남긴 관측 하나**: 실사용 세션에서도 `output_tokens` 가 계속 0 이면 새 태스크가
  필요함. 이 회차의 0 은 픽스처 때문이라고 판정했으므로 **그 판정이 틀렸는지 실사용이 가름**.

## ③ 착수 전 필수 — 6개

1. ⛔ 태스크를 새로 열기 전에 결정 대장을 `grep` 함. 이 세션이 `결정 65` 를 못 보고 같은 부류를
   다시 열어 Claude 13회를 썼음(경위는 그 대장의 「결정 65 의 사후 기록」 절).
2. ⛔ 회차 상한과 해석 규칙을 돌리기 전에 회차 기록에 적음. 위 회차 전부 그렇게 했고, ⚠️ **미리
   적은 조건과 어긋난 결과를 끼워 맞추지 않았음**(`TASK-124` 의 `output_tokens=0`).
3. ⛔ 부분 실행에는 `-c pyproject.toml` 을 붙임(`H-AJ`) · 게이트는 `app/backend` cwd(`H-A`) ·
   `tests`·`scripts` 는 경로 지정(`H-L`) · 파이프 뒤 `$?` 금지(`H-AZ`).
4. ⛔ `git add <디렉터리>` 금지(`H-BE`) · 커밋 **전** `git diff --cached --name-only` · **뒤**
   `git show --stat` 확인(`H-BA`). 이 세션은 커밋마다 그렇게 했고 남의 파일이 섞인 건 0건임.
5. ⚠️ 공유 dev DB 는 SELECT 만 함. 스키마를 바꿀 것이면 마이그레이션 번호를 그 순간의
   `schema_migrations` 조회로 발급함(`H-AL`) — 이 마감 시점의 최대는 `015` 임.
6. ⛔ 게이트를 **다섯 개 다** 돌림 — `pytest` · `ruff check .` · `ruff format --check .` ·
   게이트 밖 `ruff check ../../tests ../../scripts` · 게이트 밖 `ruff format --check ../../tests` ·
   `ty check`. ⚠️ 이 세션이 마감 게이트에서 **게이트 밖 `format --check` 를 빠뜨려** 내 파일 둘의
   미포맷을 다음 작업에서야 발견했음. 빠뜨린 항목은 「초록」이 아니라 「보지 않은 것」임.

## ④ 인계 지표 — 이 마감 시점에 직접 돌려 얻음

| # | 지표 | 값 |
|--:|---|---|
| 1 | 기준 커밋 | `9ef4f0c` 이상 · `origin` 에 푸시 완료(`e6bf0ac..9ef4f0c` · 직후 `0 0` 확인) · 내 미커밋 0건. ⚠️ 이 표를 고친 커밋 1건이 뒤에 붙으므로 등호를 요구하지 않음 |
| 2 | 다음 걸음 | **`TASK-127`**(`Awaiting Decision` — 단가의 자리) — 위 ②. 내 갈래의 `In Progress` 는 0건임 |
| 3 | 게이트 | **다섯 다 `exit 0`**: `pytest` **1004 passed**(13.57s) · `ruff check` 0 · `format --check` 38 files · 게이트 밖 `ruff` 0 · `ty` 0 — 파이프 없이 종료 코드로 확인. ⚠️ 게이트 밖 `format --check` 에 1건이 남아 있고 **내 파일이 아님**(동료 세션의 `test_pronunciation_service.py`) |
| 4 | 착수 전 필수 | 6개(위 ③) |

⚠️ 이 마감 시점의 작업 트리는 **깨끗함**(미커밋 0건). 단 앞선 게이트 회차 일부는 동료 세션의
미커밋이 트리에 있는 상태에서 돌았음 — 그때의 수치는 「내 변경만」의 값이 아니었음. ⛔ 그 파일들을
건드리지 않았음.

⚠️ 이 세션이 쓴 모델 호출: Claude 계획 생성 **22회** · **Nova 1세션**. ⛔ **`llm_calls` 의 행 수를
「이 세션이 쓴 전부」로 읽지 않음** — 기록 배선이 작업 도중에 붙었으므로 그 앞의 호출은 표에 없음.
마감 시점의 표는 `usage_report.py` 로 직접 읽었음: `nova` 1회(입력 216 · 분해 150/66) ·
`spike` 3회(입력 12,378 · 출력 3,396 · 분해 없음). ⚠️ 그 `spike` 3건은 **배선 확인·측정용**이고
제품이 쓴 비용이 아님.

## ⑤ 이 세션이 얻은 규율

- ⛔ 이름을 인용한 금지는 이름 있는 것만 막음. `- level:` 불릿이 `no blank key` 를 명시했는데도
  빈 이름 키가 1/8 로 남았음. 동료 세션이 같은 부류를 독립으로 관측했음(국소 조건절이 전역 강제를
  이기지 못함 · `TASK-123`).
- ⛔ 스파이크의 거부는 job 행을 만들지 않음. `analysis_jobs.last_error` 소급 집계가 「0건」이었고
  그것을 「과거에 발생하지 않았음」으로 읽으면 틀림 — 관측이 무엇을 배제하는지 먼저 물음.
- ⛔ 전역 금지 문장이 이미 있는데 안 지켜지면 같은 층에 문장을 더하지 않음. 국소로 내려가는 것이
  이 리포에서 실제로 먹힌 형태임(`_PRONUNCIATION_FOCUS_RULE` 다섯째 줄이 선례).
- ⚠️ 「대가」를 적어 둔 설계서 문장은 그 대가가 갚아지면 함께 고침. 이 세션이 넷을 고쳤음
  (`ws.py` 모듈 docstring · `PRONUNCIATION_MODE` 주석 · `create_session` docstring · 설계서 §5).
