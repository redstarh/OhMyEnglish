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

닫은 태스크 여섯: `TASK-117` · `TASK-108` · `TASK-119` · `TASK-121` · `TASK-112` · `TASK-60`.
판정과 근거는 각 태스크 노트가 정본임.

회차 기록 셋이 이 세션의 관측 정본임.

1. `runs/2026-09-12-task108-deepest-marker.md` — 표식 대상 초점 포함 3/3 · `parse_plan` 통과 2/3.
2. `runs/2026-09-12-task119-extra-keys.md` — 여분 키 2/5 · 전역 금지 문장이 이미 있었음.
3. `runs/2026-09-12-task121-level-bullet.md` — 이름 있는 형태 0/8 · 이름 없는 빈 키 1/8.

제품에 들어간 것: 만성 줄의 `[deepest recurrence]` 표식 + 조건부 `_DEEPEST_FOCUS_RULE` ·
`- level:` 불릿의 국소 금지 문장 · `set_session_mode` 로 `mode=pronunciation` 기록 ·
`llm_calls` 표와 호출 단위 사용량 기록(`models/usage.py` · `services/usage.py`).

마이그레이션 둘을 발급·적용했음 — `013_llm_calls.sql` · `014_pronunciation_session_mode.sql`.
⛔ `scripts/migrate.py` 를 돌리지 않고 `psql` 로 파일 둘만 적용했음(그 스크립트의 시드 upsert 가
공유 DB 의 가변 컬럼을 덮음). `schema_migrations` 행은 같은 트랜잭션에서 직접 넣었음.

받은 결정 둘: `66`(사용량은 새 표 `llm_calls`) · `67`(`mode` 값역에 `pronunciation`).
정본은 `docs/ops/captain-instruction-register.md` 임.

## ② 다음 한 걸음 — `TASK-39` 를 먼저, `TASK-124` 는 나란히

- `TASK-39`(botocore 재시도 정책 · `To Do`) — 이 세션이 그 노트에 실측과 새 사실을 넣었음:
  기본값은 connect/read 60초 · `retries None` 이고, ⛔ 재시도가 SDK 안에서 나므로 방금 만든
  `llm_calls` 가 재시도분을 못 봄. 그래서 그 태스크의 AC#2(중복 과금이 사라지는지)는 이 표로
  잴 수 없음 — 재는 방법을 회차 설계에서 먼저 정해야 함.
- `TASK-124`(Nova 호출도 적기 · `To Do`) — 지금 `llm_calls` 는 「비용을 볼 수 있다」를 절반만
  이룸. ⚠️ `nova.py` 를 건드리므로 세션 `ohmyenglish-19` 와 겹침 — 착수 전에 그쪽에 알림.
- 나란히 가능: `TASK-41`(전용 스키마 이관 검토 · 공유 DB 라 검토만) · `TASK-122`(빈 이름 키 ·
  `low` 로 내렸고 되살릴 조건을 그 노트에 적었음).

## ③ 착수 전 필수 — 5개

1. ⛔ 태스크를 새로 열기 전에 결정 대장을 `grep` 함. 이 세션이 `결정 65` 를 못 보고 같은 부류를
   다시 열어 Claude 13회를 썼음(경위는 그 대장의 「결정 65 의 사후 기록」 절).
2. ⛔ 회차 상한과 해석 규칙을 돌리기 전에 회차 기록에 적음. 위 회차 셋 전부 그렇게 했음.
3. ⛔ 부분 실행에는 `-c pyproject.toml` 을 붙임(`H-AJ`) · 게이트는 `app/backend` cwd(`H-A`) ·
   `tests`·`scripts` 는 경로 지정(`H-L`) · 파이프 뒤 `$?` 금지(`H-AZ`).
4. ⛔ `git add <디렉터리>` 금지(`H-BE`) · 커밋 뒤 `git show --stat` 확인(`H-BA`). 이 세션은 커밋
   9건 전부 그렇게 확인했고 남의 파일이 섞인 건 0건임.
5. ⚠️ 공유 dev DB 는 SELECT 만 함. 스키마를 바꿀 것이면 마이그레이션 번호를 그 순간의
   `schema_migrations` 조회로 발급함(`H-AL`) — 지금 최대는 `014` 임.

## ④ 인계 지표 — 이 마감 시점에 직접 돌려 얻음

| # | 지표 | 값 |
|--:|---|---|
| 1 | 기준 커밋 | `e17c7a4` 이상 · `origin` 에 푸시 완료(`dbc09f5..e17c7a4` · 직후 `0 0` 확인) · 내 미커밋 0건. ⚠️ 이 표를 고친 커밋 1건이 뒤에 붙으므로 등호를 요구하지 않음 |
| 2 | 다음 걸음 | `TASK-39`(`To Do`) · 나란히 `TASK-124`(`To Do`). 내 갈래의 `In Progress` 는 0건임 |
| 3 | 게이트 | `pytest` 984 passed(12.80s) · `ruff check` 0 · `format --check` 38 files · 게이트 밖 `ruff` 0 · `ty` 0 — 전부 파이프 없이 종료 코드로 확인 |
| 4 | 착수 전 필수 | 5개(위 ③) |

⚠️ 게이트를 돌린 워킹트리에 동료 세션의 미커밋 3건이 있었음(`services/pronunciation.py` ·
`test_pronunciation_service.py` · `task-103` 노트). 그 상태로도 초록이었음 — 즉 위 수치는
「내 변경만」의 값이 아님. ⛔ 그 셋을 건드리지 않았음.

⚠️ 오늘 쓴 Claude: 이 세션 계획 생성 20회(스파이크 16 + 실물 확인 1 + 팔 A 1 + 배선 확인 2).
`llm_calls` 에는 그중 1건만 있음 — 기록 배선이 그 뒤에 붙었기 때문임. ⛔ 그 1건을 「오늘 쓴 전부」로
읽지 않음.

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
