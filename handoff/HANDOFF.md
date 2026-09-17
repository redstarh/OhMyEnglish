# HANDOFF — OhMyEnglish

> 최종 갱신 **2026-09-17 09:47 KST** · 세션 `ohmyenglish-44` · 브랜치 `design/first-vertical-slice`
> ⛔ **이전 판은 `handoff/backup/2026-09-17/HANDOFF-0947.md` 에 있음**(그 앞 판은 같은 폴더의
> `HANDOFF-0801.md` 이고 더 앞은 날짜별 하위에 있음). 인계 원칙의 정본은
> `~/.claude/rules/session-handoff.md` 임.
> 상태 정본은 원장(`backlog/`), 근거 정본은 **태스크 노트 · `tests/harness/runs/**` ·
> `docs/ops/captain-instruction-register.md` · `docs/ops/pitfalls.md`** 임.

## ⛔ 먼저 챙길 것 — 첫 코드블록보다 앞에 둠

1. ⛔ **역할이 바뀌었음 — 이 세션은 개발 세션임.** 사용자 지시 2026-09-17:
   *"148,149 와 남은 테스크를 계속 진행해 꼭 필요한 사항이외에 너의 권고대로 진행해, 여기는 계속
   개발하는 세션이야"* · *"개발이 마무리되면 테스트는 필수로 진행해"*. **이전 판의 「역할은
   기본값(통합 테스트)에서 출발함」은 이 지시가 대체했음.** 등재는 지시 대장의 2026-09-17 절임.
2. ⚠️ **살아 있는 사용자 지시 셋**: ⑴ 꼭 필요한 것 외에는 묻지 않고 권고대로 감 ⑵ 개발이 끝나면
   테스트를 필수로 돌림(게이트 수치로 대체하지 않음) ⑶ *"짧게 핵심만 보고해"*.
   ⛔ **En-Coach 는 고치지 않음** — 관련 수정이 생기면 OhMyEnglish 가 흡수함(2026-09-17 결정).
3. ⛔ **DB 배치가 바뀌었음 (마이그레이션 026)**: 우리 표는 `public` 이 아니라 스키마
   **`ohmyenglish`** 에 있음. 역할 `ohmy` 의 `search_path` 가 `ohmyenglish, public` 임.
   `pg_dump` 는 **`-n ohmyenglish`** 를 씀 — `-n public` 은 호환 뷰 셋만 떠서 **데이터 0줄**임.
4. ⛔ **`information_schema` 조회에 스키마를 반드시 건다**(`current_schema()`) — `public` 에 동명
   호환 뷰가 있어 안 걸면 두 스키마의 행이 섞이고 **뷰는 모든 컬럼을 nullable 로 보고함**(`H-BX`).
5. ⛔ **긴 문서는 절 단위로 나눠 쓰고 합침** · **커밋 메시지에 백틱 식별자를 넣을 때 `-m` 을 쓰지
   않음**(인용된 heredoc 을 씀).
6. ⚠️ **백엔드가 떠 있음**(pid 90955 · `:8002` · `WORKER_ENABLED=false VOICE_ADAPTER=stub
   --log-level warning` = 문서가 지정한 baseline 형태). 소스를 고쳤으면 **재기동해야 함**(`--reload`
   없음). 로그는 `/tmp/omy-backend.log` 임.

## 인계 지표 4개 (이 턴에 직접 돌린 출력)

| # | 지표 | 값 |
|--:|---|---|
| 1 | 기준 커밋 | **`5420225`** · `origin` 과 **0/0**(push 완료) · 워킹트리 clean |
| 2 | 다음 한 걸음 | **`TASK-153`** — `public` 에 남은 `redstar` 소유 하네스 기준선 표 둘. ⛔ 그 표를 함부로 지우지 않음(`browser_leg.md` §8-0) |
| 3 | 게이트 | **일곱 다 초록** — 수집 **1283** · `pytest` **1283 passed** · `ruff` 0 · `ruff format` 0 · `ty` 0 · `tsc` 0 · `eslint` 0. ⚠️ `ruff` 범위에 `../../tests ../../scripts` 가 **들어왔음**(`TASK-151`) |
| 4 | 착수 전 필수 | 잔여 **3건**(전부 `To Do` · In Progress **0** · 전체 **214** · 완료 **211**). 아래 ③ |

```bash
cd ~/MyProject/OhMyEnglish
git rev-parse --short HEAD && git rev-list --left-right --count HEAD...origin/design/first-vertical-slice
backlog task list --plain
cd app/backend && ./.venv/bin/pytest -q --collect-only && ./.venv/bin/pytest -q
cd app/backend && ./.venv/bin/ruff check . ../../tests ../../scripts \
  && ./.venv/bin/ruff format --check . ../../tests ../../scripts && ~/.local/bin/ty check
cd app/frontend && npx tsc --noEmit && npx eslint .
```

## ① 이 세션이 한 것 — 태스크 7건을 닫고 통합 회차 1건을 돌렸음

**닫은 것 일곱**: `TASK-149`(죽은 podman 폴백 제거 · 결정 123) · `TASK-148`(`api/ws.py` 의 도메인
정책 넷을 경계 밖으로) · `TASK-152`(절차 문서 둘의 podman 경로 + 재실측으로 뒤집힌 사실 둘) ·
`TASK-151`(tests 트리 E501 17건 + 기준선 0 을 게이트로) · `TASK-147`(왕복 8→6 · 4→2) ·
`TASK-39`(스로틀 분기 재현 — 최대 청구 25→10) · `TASK-41`(전용 스키마 이관 · 026).

**새로 등록한 것 둘**: `TASK-152`(닫음) · `TASK-153`(열림 — 다음 걸음).

⛔ **이 세션의 값은 코드보다 단정에 있었음.** 셋을 새로 세웠고 셋 다 **뒤집어서 FAIL 을 확인**했음:
- 발음 모드가 드릴 턴을 기록하지 않는다(결정 37의 절반이 **무보호**였음 — 변이가 1279건을 통과했음)
- 사라진 패턴 키를 이름으로 경고한다(`grep` 으로 그 경로 테스트 0건이었음)
- 파이썬 값역 `SESSION_MODES` 가 DB CHECK 와 일치한다(하드코딩 목록을 **대체하지 않았음** — 대체하면
  양쪽에서 같은 값을 지울 때 통과함)

## ② 지금 상태 — 새로 생긴 계약 넷

- **DB**: 표 19개가 `ohmyenglish` 스키마 · `public` 에는 En-Coach 호환 뷰 셋 + `redstar` 소유 하네스
  기준선 둘. En-Coach 는 뷰로 그대로 읽음(`set role en_coach` 로 9·24·7행 확인).
- **모드 정책**: `services/session_modes.py` 의 표가 정본. `api/ws.py` 에 모드 비교가 0곳이고
  513줄 → 418줄. 값역의 파이썬 이름은 `models/session`, 고정 사용자는 `models/user`.
- **게이트 범위**: `ruff`·`ruff format` 이 `tests`·`scripts` 를 포함함. 두 트리 기준선은 **0**.
- **재시도**: Bedrock 은 `standard` · `total_max_attempts=2`. 스로틀 분기도 2회로 실측됨.

## ③ 착수 전 필수 — 이 세션 실측

1. ⛔ **`pytest` 는 `app/backend` 에서 인자 없이 돌림.** 부분 실행은 `-o asyncio_mode=auto`.
   툴 호출 사이에 cwd 가 남으므로 **절대 경로**를 씀.
2. ⛔ **`ruff` 를 리포 루트에서 돌리지 않음**(`H-BN`) — 기본 규칙셋으로 떨어져 「0건」이 나옴.
   그리고 **`E501` 은 문자 수가 아니라 표시 폭임**(한글 2열 · `H-BW`) — `len()` 으로 재면 못 찾음.
3. ⛔ **zsh 는 변수에 담은 명령을 단어로 쪼개지 않음** — `PSQL='psql -h …'; $PSQL …` 은
   `command not found` 임. **셸 함수**로 묶음(이 세션에서 두 번 밟았음).
4. ⛔ **`psql -tAc` 는 `insert … returning` 에 명령 태그를 붙임**(`H-BY`) — `psql_cli` 에 `-q` 를
   넣어 고쳤음. ⚠️ **`select` 로 확인하면 그 결함이 안 드러남**(태그가 없음).
5. ⚠️ **하네스 회차는 워커를 끄고 돌림** — 켜면 복습 시계가 움직여 teardown 이 되돌리지 못함.
   불변 지표(이 세션 실측): dev `learning_sessions` **17** · `utterances` **128** ·
   `error_patterns` **9** · `analysis_jobs` **57** · `schema_migrations` **24**.
6. ⛔ **`git add <디렉터리>` 금지** · 커밋 뒤 `git show --stat` 으로 담긴 것 전체를 봄.

## ④ 열린 태스크 3건

| 태스크 | 상태 |
|---|---|
| **`TASK-153`** | **다음 걸음.** `public` 의 `redstar` 소유 하네스 기준선 둘. 소유자 변경은 superuser 가 필요함. ⛔ 내용이 유효한 기준선인지 먼저 판정함 |
| `TASK-116.5` | 결함 후보 — 문장 전체 인용 구멍(2/59 파킹) |
| `TASK-122` | LOW · 이름 없는 빈 키(네 세션이 보류) |

## ⑤ 착수 전 반드시 읽을 것

- **결정 123** (지시 대장 2026-09-17 절) — podman 폴백 제거의 근거와 그 절의 「역할이 개발로 바뀜」.
- **`db/migrations/026_dedicated_schema.sql` 머리주석** — 되돌리는 방법이 그 안에 있음.
- **함정 `H-BW`·`H-BX`·`H-BY`** — 이 세션이 새로 세운 셋. 전부 **「직접 돌렸는데도 못 잡은」** 부류임.
- ⚠️ **가장 값 있는 관찰**: 낮에 `select` 로 확인해 통과시킨 자리가 저녁 통합 회차에서 결함으로
  드러났음. **직접 돌렸다는 사실이 판별력을 보장하지 않음** — 고치는 대상과 같은 모양의 입력으로 잼.
