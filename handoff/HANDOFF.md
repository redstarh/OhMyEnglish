# HANDOFF — OhMyEnglish

> 최종 갱신 **2026-09-18 13:54 KST** · 세션 `ohmyenglish-29` · 브랜치 `design/first-vertical-slice`
> ⛔ **이전 판은 `handoff/backup/2026-09-18/HANDOFF-1354.md` 에 있음**(그 앞은 `-1113`·`-0818`·`-0328`).
> 인계 원칙의 정본은 `~/.claude/rules/session-handoff.md` 임.
> 근거 정본은 **태스크 노트 · `docs/ops/pitfalls.md`(`H-CA`~`H-CD`) · 지시 대장 결정 128~130** 임.

## ⛔ 먼저 챙길 것 — 첫 코드블록보다 앞에 둠

1. ⛔ **이 세션은 개발 세션임.** 살아 있는 지시: 묻지 않고 권고대로 감 · 개발 뒤 테스트 필수 ·
   짧게 핵심만 보고 · **기능은 심플하게** · 주요 개발 뒤 `/simplify`. ⛔ **En-Coach 는 고치지 않음.**
2. ⛔ **마감 트리거가 바뀌었음**(사용자 지시 2026-09-18) — **쓴 컨텍스트 70% 초과**와 **compact 경고**
   둘뿐임. 「태스크 N개 연속 완료」는 **폐기**됐고 원장이 닫힌 것은 마감 조건이 **아님**. 정본은
   `~/.claude/rules/session-handoff.md` §5·8항이고 `session-wrap` 의 description 도 함께 고쳤음.
3. ⛔ **`skill`·`rules/**` 의 본문은 영어로 씀**(사용자 지시 2026-09-18). 경계는
   `rules/korean-writing-standard.md` 머리말이 소유함 — 모델만 읽는 지시문은 영어, **사람이 읽거나
   리포에 남는 것은 한글**(대화·커밋 메시지·handoff·원장 노트·설계서·이 리포 코드 주석).
4. ⛔ **Bedrock 자격증명은 `bedrock-credentials` skill 로 확인함**(2026-09-18 신설). 이 리포는
   **SigV4 가 필요함** — Nova 양방향 스트림이 bearer 를 `HTTP 403 This operation does not support
   API Keys` 로 거부함. 셸에는 bearer 만 있고 **SigV4 두 키는 `app/backend/.env` 에만** 있음.
5. ⛔ **브라우저 검증은 `localhost:3000`**(`H-CA`) · **세션 화면을 `?mode=…` 로 열지 않음**(`H-CC` —
   로드 즉시 `getUserMedia` 가 불려 마이크 대체를 심을 틈이 없음. 쿼리 없이 `/` 로 열고 화면의
   「쉐도잉」 버튼을 누름).
6. ⛔ **워커를 「관측용으로 잠깐」 켜지 않음**(`H-CD`) — 큐가 비어 있어도 기동이 미등록 발화를 새로
   등록해 Bedrock 호출이 남. 실측 입력 9,227 · 출력 1,024 토큰.
7. ⛔ **결정 124 는 반증됐음**(따옴표 인용을 프롬프트에 다시 넣지 말 것) · ⛔ **자막을 얻으려 하지
   말 것**(결정 126).
8. ⛔ **DB 배치**: 우리 표는 스키마 **`ohmyenglish`** 에 있음. `pg_dump` 는 **`-n ohmyenglish`**(`H-BX`).
9. ⚠️ **앱이 떠 있음** — 백엔드 **2696**(`:8002` · `WORKER_ENABLED=false VOICE_ADAPTER=stub` ·
   `/health` 200) · 프런트 **15136**(`:3000`). ⛔ 백엔드는 `--reload` 가 없어 **소스를 고쳤으면 재기동**함.
   `app/frontend/.env.local` 은 `:8002` 로 되돌려 뒀음.
10. ⚠️ **`analysis_jobs` pending 0건** — 62건을 `failed` 로 표시했음(TASK-191). 되살리려면 그 행들의
    `status` 를 `pending` 으로 되돌림. ⛔ 워커를 켜기 전에 6번을 읽음.

## 인계 지표 4개 (이 턴에 직접 돌린 출력)

| # | 지표 | 값 |
|--:|---|---|
| 1 | 기준 커밋 | **`a3e7d1f`** · 작업트리 clean · `origin` 과 **0/0**. ⛔ 이 handoff 의 갱신 커밋이 더 뒤에 오므로 **차이가 handoff 뿐이면 정상**임 |
| 2 | 다음 한 걸음 | **`TASK-213`** — ⛔ **stub 서버에서 낭독 판정을 누르면 스텁 문장이 전사로 «영구» 저장됨**(`judge_readback` 이 값이 있으면 다시 계산하지 않음). 개발용 `:8002` 가 평소 stub 이라 밟기 쉬움. 그 뒤 `TASK-214`~`216`(동작 보존 정리) · `TASK-217`(실물 회차 필요) |
| 3 | 게이트 | **여덟 다 exit 0** — `pytest` **1387 passed** · `ruff` 0 · `ruff format` **302 files** · `ty` 0 · `tsc` 0 · `eslint` 0 · `next build` 0(`/` 가 `○` Static 유지). 전부 2026-09-18 에 직접 돌린 값임 |
| 4 | 착수 전 필수 | 전체 **278** · 완료 **273** · 열린 것 **다섯**(`TASK-213`~`217`) · `In Progress` **0건** · `--ready` 는 넷(`217` 은 `214` 를 기다림) |

```bash
cd ~/MyProject/OhMyEnglish
git rev-parse --short HEAD && git rev-list --left-right --count HEAD...origin/design/first-vertical-slice
backlog task list --plain
cd app/backend && ./.venv/bin/pytest -q
cd app/backend && ./.venv/bin/ruff check . ../../tests ../../scripts \
  && ./.venv/bin/ruff format --check . ../../tests ../../scripts && ~/.local/bin/ty check
cd app/frontend && npx tsc --noEmit && npx eslint . && npx next build
```

## ① 이 세션이 한 것 — 축 넷을 열고 셋을 닫았음

닫은 태스크 **열넷**(`TASK-185`~`TASK-198`). 커밋 아홉. 사용자가 열린 축 넷 중 「1번 진행하고 나머지도」로
전부 열었고, 그 가운데 셋을 끝냈음.

| 축 | 결과 |
|---|---|
| 낭독 회차·진행도 | 결정 129. 서버가 발화 수로 셈 · 화면이 목표 2 이상일 때만 보임. 실물 Nova 로 0→1→2→「3번 다 읽었어요」 관측 |
| `analysis_jobs` | 결정 없음(조사가 방침을 뒤집음). pending 62건이 **전부 하네스 산출물**이라 처리하지 않고 `failed` 표시 |
| 낱말 뜻 조회 | 결정 130. §6 이 뺀 열 중 하나만 되살림 — 그 근거(「외부 의존이 늘어난다」)가 **이미 있는 Claude 경로 앞에서 성립하지 않았음** |
| 낭독 판정 | **설계 미착수**(`TASK-189`) — 아래 ④ |

## ② 이 세션이 배운 것 — 다음 세션이 반복하지 않을 것

1. ⛔ **`/simplify` 가 회귀를 잡았음.** 낱말 조회를 붙이며 Bedrock 클라이언트 생성을 `worker_enabled`
   분기 밖으로 옮긴 것이 `config.py` 가 **스스로 안내하는** 「자격증명 없이 띄우는 길」을 깼음.
   ⚠️ 재현에 **두 번 실패**했음 — `env -u` 만으로는 `.env` 가 살아 있고 `.env` 만 치우면 셸 bearer 가
   살아 있음. **두 자리를 다 치운 뒤에야** 재현됐음(그 교훈이 `bedrock-credentials` skill §1 에 있음).
2. ⛔ **위임 리뷰 둘이 findings 없이 돌아왔음** — 원장 게이트(Stop hook) 메시지가 그들 컨텍스트에
   들어가 원래 과제를 밀어냈음. `SendMessage` 로 이어서 요청해 둘 다 회수했음(`H-AO` ④).
3. ⛔ **내 첫 테스트 단정이 대역을 재고 있었음**(판별력 0) — `app_settings` 가 실물 클래스를 갈아
   끼우므로 `records_usage` 단정이 무의미했음. 기존 게이트와 같은 형태로 **생성 인자를 직접 잡음**.
4. ⚠️ **내가 쓴 주석·docstring 이 두 번 거짓이었음** — `config.py` 의 「코치 지시문이 이 값을 싣는다」
   (그런 지시문 없음) · `api/vocab.py` 의 「다른 라우터와 같은 규약」(`response_model=` 이 유일 사용).
   ⇒ **관행을 주장하기 전에 `grep` 으로 센다.**

## ③ 착수 전 필수 — 이 세션 실측

1. ⛔ **`pytest`·`ruff` 는 `app/backend` 에서 돌림**(`H-BN`). 부분 실행은 `-c pyproject.toml`(`H-AJ`).
2. ⛔ **한글 주석을 쓴 직후 `ruff check`** — `E501` 은 표시 폭이라 한글이 2열임(`H-BW`). 이 세션에서
   그 자리에 **여섯 번** 걸렸음.
3. ⛔ **훅 `hangul-sanity.py` 가 정상 낱말을 막음** — 셋을 `~/.claude/hangul-allow.txt` 에 등재했고
   그 파일을 쓰는 것도 막혀 자모 조합으로 만듦. ⚠️ **첫 시도가 틀렸음**(쌍시옷 초성은 9 가 아니라
   **10**) ⇒ **기대하는 유니코드 이름을 먼저 적고 대조**함. 이름만 보고 단정하면 실수를 반복함.
4. ⛔ **종료 코드 판정에 파이프를 걸지 않음**(`H-AZ`) — `ty check | tail` 이 `exit 0` 으로 보였음.
5. ⚠️ **프런트에 테스트 러너가 없음** ⇒ 화면 판정은 브라우저 관측이 유일함.
6. ⛔ **마이그레이션 적용 전 `pg_dump -n ohmyenglish` 로 백업함.** 적용은
   `./app/backend/.venv/bin/python scripts/migrate.py`(`/usr/bin/python3` 은 `asyncpg` 없음).
7. ⛔ **`git add <디렉터리>` 금지** · 커밋 뒤 `git show --stat` 으로 담긴 것 전체를 봄.

⚠️ **나머지 함정의 정본은 `docs/ops/pitfalls.md` 임**(이 세션이 `H-CC`·`H-CD` 를 더했음).

## ④ 열린 태스크 다섯 — 전부 `/simplify` 가 낳았음

| ID | 무엇 | 실물 회차 |
|---|---|---|
| **`TASK-213`** | ⛔ stub 서버에서 판정을 누르면 스텁 문장이 전사로 **영구 저장**됨 + 503 가드 부재 | 불필요 |
| `TASK-214` | 좁은 `Transcriber` 포트 — 결정 131 의 경계 약속을 실제로 만듦 | 불필요 |
| `TASK-215` | 사용량 기록을 `_pump_output` 의 `finally` 로 · 종료 예산 셋을 하나로 | 불필요 |
| `TASK-216` | teardown 이 앱의 고아 파일 스윕을 재사용(삭제 정책 한 자리) | 불필요 |
| `TASK-217` | 전사 전용 프롬프트 + `end_input()` — 입력 약 1,600 토큰 절감 | **필수** |

⛔ **낭독 판정 축(`TASK-205`~`212`)은 닫혔음.** 정본은
`docs/design/2026-09-18-read-aloud-judgment-design.md` 와 결정 131 임. 실측 확정 셋: ⑴ ⛔ **낭독 끝에
침묵 2초가 «필수»**(없으면 실물 Nova 가 전사를 안 줌) ⑵ 학습자 final 을 **모아** 이어 붙임(첫 것만
받으면 여섯 문장 클립이 두 문장에서 끊김) ⑶ 판정에 모델을 부르지 않음.
⚠️ 전사기가 `All right` 을 `alright` 로 합쳐 「다름」이 잡히는 한계가 있음.
⛔ 브라우저 회차는 `tests/harness/p_readback_leg.py` 로 돌리고 뒤에 `teardown_session.py` 로 걷음.

## ⑤ 착수 전 반드시 읽을 것

**결정 128·129·130**(기각한 대안·되돌리는 조건) · **`TASK-197` 노트**(`/simplify` 처분과 유지 근거) · **`bedrock-credentials` skill**(자격증명이 필요할 때 먼저 부름).

## ⑥ 인계 확인 — 후계 `omy-0918-1400` (2026-09-18 14:20 KST)

인계 성립 — 후계가 `TASK-199` 를 받아 그 축과 후속 여덟(`TASK-200`~`211`)까지 진행했음.
⛔ 첫 지시가 `manual mode` 승인 대기에 걸려 멈춘 함정은 `session-wrap` skill 이 가짐.
⚠️ 그때 지표 넷의 개별 값은 스크롤백에서 밀려나 직접 보지 못했음 — 추측을 사실로 적지 않음.
