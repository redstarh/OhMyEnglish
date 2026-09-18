# HANDOFF — OhMyEnglish

> 최종 갱신 **2026-09-18 18:12 KST** · 세션 `omy-0918-1400` · 브랜치 `design/first-vertical-slice`
> ⛔ **이전 판은 `handoff/backup/2026-09-18/HANDOFF-1812.md` 에 있음**(그 앞은 `-1354`·`-1113`·`-0818`).
> 인계 원칙의 정본은 `~/.claude/rules/session-handoff.md` 임.
> 근거 정본은 **태스크 노트 · `docs/ops/pitfalls.md`(`H-CA`~`H-CG`) · 지시 대장 결정 128~131** 임.

## ⛔ 먼저 챙길 것 — 첫 코드블록보다 앞에 둠

1. ⛔ **이 세션은 개발 세션임.** 살아 있는 지시: 묻지 않고 권고대로 감 · 개발 뒤 테스트 필수 ·
   짧게 핵심만 보고 · **기능은 심플하게** · 주요 개발 뒤 `/simplify`. ⛔ **En-Coach 는 고치지 않음.**
2. ⛔ **마감 트리거는 둘뿐임**(사용자 지시 2026-09-18) — **쓴 컨텍스트 70% 초과**와 **compact 경고**.
   「태스크 N개 연속 완료」는 폐기됐고 원장이 닫힌 것은 마감 조건이 **아님**. 정본은
   `~/.claude/rules/session-handoff.md` §5·8항임.
3. ⛔ **`skill`·`rules/**` 의 본문은 영어로 씀**(사용자 지시 2026-09-18). 경계는
   `rules/korean-writing-standard.md` 머리말이 소유함 — 모델만 읽는 지시문은 영어, **사람이 읽거나
   리포에 남는 것은 한글**(대화·커밋 메시지·handoff·원장 노트·설계서·이 리포 코드 주석).
4. ⛔ **Bedrock 자격증명은 `bedrock-credentials` skill 로 확인함.** 이 리포는 **SigV4 가 필요함** —
   Nova 양방향 스트림이 bearer 를 `403 This operation does not support API Keys` 로 거부함. 셸에는
   bearer 만 있고 SigV4 두 키는 `app/backend/.env` 에만 있음 ⇒ **`nova` 로 띄울 때는
   `env -u AWS_BEARER_TOKEN_BEDROCK` 을 앞에 붙임**(2026-09-18 그렇게 띄워 실물 회차가 성립했음).
5. ⛔ **브라우저 검증은 `localhost:3000`**(`H-CA`) · **세션 화면을 `?mode=…` 로 열지 않음**(`H-CC`) ·
   ⛔ **낭독 판정 화면은 스텁 둘로 관측 불가**(`H-CG` — 신설. `stub` 은 세션 즉시 종료 ·
   `stub_unresponsive` 는 10초 연결 상한에 걸려 녹음이 저장되지 않음. 실물 `nova` 회차에서
   `audio_url` 을 지워 404 를 만드는 것이 관측 방법임).
6. ⛔ **워커를 「관측용으로 잠깐」 켜지 않음**(`H-CD`) — 기동이 미등록 발화를 새로 등록해 Bedrock
   호출이 남. ⛔ **회차 뒤 `teardown_session.py --session-id` 를 돌림**(`app/backend` 에서 돌려야
   `.env` 가 읽힘 — 리포 뿌리에서 돌리면 `database_url` 누락으로 죽음).
7. ⛔ **결정 124 는 반증됐음**(따옴표 인용을 프롬프트에 다시 넣지 말 것) · ⛔ **자막을 얻으려 하지
   말 것**(결정 126).
8. ⛔ **DB 배치**: 우리 표는 스키마 **`ohmyenglish`** 에 있음. `pg_dump` 는 **`-n ohmyenglish`**(`H-BX`).
   `psql` 은 `/opt/homebrew/opt/postgresql@17/bin/psql` 임.
9. ⚠️ **앱이 떠 있음** — 백엔드 **7414**(`:8002` · `WORKER_ENABLED=false VOICE_ADAPTER=stub` ·
   `/health` 200) · 프런트 **15136**(`:3000`). ⛔ 백엔드는 `--reload` 가 없어 **소스를 고쳤으면 재기동**함.
   로그는 `/tmp/omy-backend.log` 로 이어 붙임.
10. ⚠️ **`analysis_jobs` pending 0건 · `readback_transcript` 있는 행 0건**(이 턴 실측). 62건은
    `failed` 로 표시돼 있음(TASK-191) — 되살리려면 그 행들의 `status` 를 `pending` 으로 되돌림.

## 인계 지표 4개 (이 턴에 직접 돌린 출력)

| # | 지표 | 값 |
|--:|---|---|
| 1 | 기준 커밋 | **`ca6475d`** · 작업트리 clean · `origin` 과 **0/0**. ⛔ 이 handoff 의 마감 커밋이 더 뒤에 오므로 **차이가 handoff 뿐이면 정상**임 |
| 2 | 다음 한 걸음 | **`TASK-214`** — 좁은 `Transcriber` 포트를 도입해 결정 131 의 경계 약속을 실제로 만듦. 그 뒤 `TASK-215`·`216`(동작 보존 정리) · `TASK-217`(`214` 를 기다림 · **실물 회차 필요**) |
| 3 | 게이트 | **여덟 다 exit 0** — `pytest` **1389 passed** · `ruff` 0 · `ruff format` **302 files** · `ty` 0 · `tsc` 0 · `eslint` 0(경고 1건은 기준선) · `next build` 0(`/` 가 `○` Static 유지) |
| 4 | 착수 전 필수 | 전체 **278** · 완료 **274** · 열린 것 **넷**(`TASK-214`~`217`) · `In Progress` **0건** · 미충족 AC 는 네 태스크 **각 3건**(전부 착수 전) · 의존은 하나(`217` 이 `214` 를 기다림) |

```bash
cd ~/MyProject/OhMyEnglish
git rev-parse --short HEAD && git rev-list --left-right --count HEAD...origin/design/first-vertical-slice
backlog task list --plain
cd app/backend && ./.venv/bin/pytest -q
cd app/backend && ./.venv/bin/ruff check . ../../tests ../../scripts \
  && ./.venv/bin/ruff format --check . ../../tests ../../scripts && ~/.local/bin/ty check
cd app/frontend && npx tsc --noEmit && npx eslint . && npx next build
```

## ① 이 세션이 한 것 — `TASK-213` 하나를 닫았음

커밋 하나(`ca6475d` · 9파일). 전사기가 없는 서버에서 낭독 판정이 **스텁 문장을 전사로 영구 저장**하던
결함을 닫았음.

| 무엇 | 결과 |
|---|---|
| 가드 | `factory.transcriber_available` 신설(어댑터 값을 아는 자리를 팩토리 하나로 둠 · G3) · 라우터가 **전사 앞에서** 503 |
| 화면 | `ok: false` 를 빈 낱말로 접지 않고 「지금은 낭독 판정을 쓸 수 없어요.」 를 보임 |
| 오염 행 | dev DB **0건**(사전·사후 동일) — 지울 것이 없었음 |
| 회차 잔재 | 세션 여섯을 `teardown_session.py` 로 걷음 → pending job **0건** |

⛔ **되돌린 판단**: `TASK-212` 의 「요청 실패와 전사 못 얻음을 같게 말한다」를 뒤집었음. 그 근거가
*"둘 다 다시 눌러 볼 일이다"* 였고 **503·500 은 몇 번 눌러도 달라지지 않아** 전제가 틀렸음.
상태는 필드 대신 갈래 한 값(`kind`)으로 들어 닿을 수 없는 조합을 없앰.

## ② 이 세션이 배운 것 — 다음 세션이 반복하지 않을 것

1. ⛔ **화면 갈래를 관측할 길이 막혀 있을 수 있음**(`H-CG`). 스텁 둘을 차례로 시도해 둘 다 실패한
   뒤에야 실물 회차 + 포인터 삭제라는 길을 찾았음 ⇒ **관측 수단을 먼저 정하고 시작함.**
2. ⛔ **파이프가 종료 코드를 가렸음**(`H-AZ` 재발) — `ruff format --check | tail` 이 `exit 0` 으로
   보였고 실제로는 실패였음. ⇒ **`cmd >/tmp/out 2>&1; echo $?`** 로만 판정함.
3. ⛔ **한글 주석 직후 `ruff check`** — `E501` 이 표시 폭이라 한글이 2열임(`H-BW`). 이 세션에서도 걸림.
4. ⚠️ **`ps eww` 로 프로세스 환경을 덤프하면 비밀이 화면에 남음** — 이 세션이 실제로
   `AWS_BEARER_TOKEN_BEDROCK` 값을 전사에 남겼음. ⇒ 환경 확인은 **키 이름만** 뽑음
   (`ps eww -p <pid> | tr ' ' '\n' | grep -o '^[A-Z_]*='`).
5. ⚠️ **`nohup … &` 로 띄운 Chrome 이 턴이 끝나면서 죽었음** — 브라우저·서버는 **`run_in_background`**
   로 띄워야 다음 턴까지 살아 있음.

## ③ 착수 전 필수 — 이 세션 실측

1. ⛔ **`pytest`·`ruff` 는 `app/backend` 에서 돌림**(`H-BN`). 부분 실행은 `-c pyproject.toml`(`H-AJ`).
2. ⛔ **프런트에 테스트 러너가 없음** ⇒ 화면 판정은 브라우저 관측이 유일함(`H-CG` 가 그 방법을 가짐).
3. ⛔ **마이그레이션 적용 전 `pg_dump -n ohmyenglish` 로 백업함.** 적용은
   `./app/backend/.venv/bin/python scripts/migrate.py`.
4. ⛔ **`git add <디렉터리>` 금지** · 커밋 뒤 `git show --stat` 으로 담긴 것 전체를 봄.

⚠️ **나머지 함정의 정본은 `docs/ops/pitfalls.md` 임**(이 세션이 `H-CG` 를 더했음).

## ④ 열린 태스크 넷 — 전부 `/simplify` 가 낳았음

| ID | 무엇 | 실물 회차 |
|---|---|---|
| **`TASK-214`** | 좁은 `Transcriber` 포트 — 결정 131 의 경계 약속을 실제로 만듦 | 불필요 |
| `TASK-215` | 사용량 기록을 `_pump_output` 의 `finally` 로 · 종료 예산 셋을 하나로 | 불필요 |
| `TASK-216` | teardown 이 앱의 고아 파일 스윕을 재사용(삭제 정책 한 자리) | 불필요 |
| `TASK-217` | 전사 전용 프롬프트 + `end_input()` — 입력 약 1,600 토큰 절감 | **필수** |

⛔ **낭독 판정 축의 정본은 `docs/design/2026-09-18-read-aloud-judgment-design.md` 와 결정 131 임.**
실측 확정 넷: ⑴ 낭독 끝에 **침묵 2초가 필수** ⑵ 학습자 final 을 **모아** 이어 붙임 ⑶ 판정에 모델을
부르지 않음 ⑷ **전사기가 없으면 1번에서 503**(이 세션이 더함). ⚠️ 전사기가 `All right` 을 `alright`
로 합쳐 「다름」이 잡히는 한계가 있음.

## ⑤ 착수 전 반드시 읽을 것

**결정 128·129·130·131** · **`TASK-213` 노트**(되돌린 판단과 관측 방법) · **`bedrock-credentials`
skill**(자격증명이 필요할 때 먼저 부름).

## ⑥ 마감 기록 — 세션 `omy-0918-1400` (2026-09-18 18:12 KST · 후계를 띄우지 않았음)

⛔ **사용자 지시로 마감했음**(*"현재까지 내용만 기록하고 다시 연결되면 그때해"* · 연결 끊김 예정).
마감 트리거는 오지 않았음(쓴 컨텍스트 낮음) ⇒ **후계를 띄우지 않고 기록만 남김**(`session-wrap`
6·7단계 미실행). 다시 연결되면 위 지표 4개를 직접 돌려 대조한 뒤 `TASK-214` 로 들어감.
