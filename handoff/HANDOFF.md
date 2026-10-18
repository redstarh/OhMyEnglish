# HANDOFF — OhMyEnglish

> 최종 갱신 **2026-10-18 11시대 KST** · 브랜치 `design/first-vertical-slice`
> ⛔ **이전 판은 `handoff/backup/2026-10-18/HANDOFF-1147.md`** (그 앞 판들은 같은 폴더의 날짜별).
> 인계 원칙의 정본은 `~/.claude/rules/session-handoff.md` · 근거 정본은 **태스크 노트 ·
> `docs/ops/pitfalls.md` · 회차 노트**임.

## ⛔ 먼저 챙길 것 — 첫 코드블록보다 앞에 둠

1. ⛔ **원장 잔여 0건임**(`To Do`·`In Progress`·`Awaiting Decision` 전부 0 · `Done` **344**).
   사용자 지시(2026-09-19)에 따라 방향 후보를 고르지도, 묻지도 않고 멈춤. 상태만 짧게 적음.
2. ⛔ **스택이 내려가 있음** — `:8002`·`:3000` 둘 다 리스너 없음(2026-10-18 실측).
   ⚠️ **이전 판의 「스택이 떠 있음」은 폐기됨.** 학습이나 회차가 필요하면 먼저 띄워야 함.
   리스너 확인은 `lsof -nP -iTCP:8002 -sTCP:LISTEN -t` 로 함(`H-CJ`).
3. ⛔ **음성 어댑터 기본값이 `nova` 임**(`app/backend/app/config.py:89` 에서 확인 · `TASK-267`).
   ⇒ **하네스·회차에서 스텁이 필요하면 `VOICE_ADAPTER=stub` 을 반드시 명시함.** 빼면 실물 Nova 가
   붙어 과금되고 dev DB 에 가짜 발화가 쌓임.
4. ⛔ **이 세션은 개발 세션임.** 살아 있는 지시: 묻지 않고 권고대로 감 · 개발 뒤 테스트 필수 ·
   짧게 핵심만 보고 · 기능은 심플하게. ⛔ **En-Coach 는 고치지 않음.**
5. ⛔ **유료 회차는 격리 DB `ohmyenglish_worker` 에서 돌림 — dev DB 가 아님**(`TASK-191` 의 결정).
6. ⛔ **Bedrock 은 SigV4 가 필요함.** 직접 스크립트에는 `env -u AWS_BEARER_TOKEN_BEDROCK` 을 붙임.
7. ⛔ **회차 출력을 `head` 로 자르지 않음**(SIGPIPE). `> 파일` 로 받고 뒤에서 `grep` 함.
8. ⛔ **DB 배치**: 스키마 **`ohmyenglish`** · `pg_dump -n ohmyenglish`(`H-BX`) ·
   `psql` 은 `/opt/homebrew/opt/postgresql@17/bin/psql` · introspection 에는 `current_schema()` 를 걸음.
9. ⚠️ **PRD 가 v1.6 임** — §16·§17 을 읽지 않고 발음·드릴 영역을 손대지 않음.
10. ⛔ **superpowers 가 7.0.0 으로 올라갔음**(chrome 은 3.3.0 · 2026-10-17). 이름이 사라진 스킬은
    없고 **절차가 바뀐 것이 넷**임 — `brainstorming`(「무엇을 원하는지 먼저 알아냄」으로 변경) ·
    `writing-plans`(한 단계 기준이 「확인할 수 있는 결과」로 변경) · `requesting-code-review` ·
    `systematic-debugging`(예시 명령만). ⚠️ **6 버전 기억으로 절차를 쓰지 않음.**
    버전 정본은 `claude plugin list` 임(`~/.claude/CLAUDE.md` 의 버전 고정은 삭제했음).
11. ⛔ **`~/.claude` 리포에 다른 작업에서 온 미커밋 변경이 여러 건 있음**(`CLAUDE.md` 전체를 영어로
    옮기는 작업 포함). **그 변경을 커밋하거나 되돌리지 않음** — 남의 작업을 삼키게 됨.
12. ⚠️ **이전 판의 미결 관측 하나가 해소됐음** — 셸의 `HANGUL_SANITY=0` 은 이번 세션에서 재현되지
    않음(`<unset>`). 훅 등록은 `~/.claude/settings.json` 에 그대로 있음.

## 인계 지표 4개

| # | 지표 | 값 |
|--:|---|---|
| 1 | 기준 커밋 | **`93a3b7d`** · 작업 트리 깨끗함 · `origin` 과 **0/0** (이 판을 담은 커밋은 아래 `git log -1` 로 읽음) |
| 2 | 다음 한 걸음 | **없음 — 원장 잔여 0건**(`Done` **344** · 마지막은 `TASK-280`) |
| 3 | 게이트 | 백엔드 넷 통과 — `pytest` **1452 passed** · `ruff` 0 · `ruff format` 328 files · `ty` 0. ⚠️ **측정 주체는 후속 세션**(`superpowers 7.0.0 첫 세션`)이고, 그 측정 뒤 `app`·`tests` 변경이 0건이므로 `rules/session-handoff.md` §6-1 에 따라 **승계값**임 — 재측정값이 아님. 프런트 셋은 돌리지 않았음 |
| 4 | 착수 전 필수 | 미결 승인 0 · 스택 내려가 있음(위 2번) |

⚠️ **이 판에는 셸 코드블록을 두지 않았음.** `tests/test_docs_commands.py` 가 `docs/`·`handoff/` 의
bash 코드블록마다 케이스를 만들어 **블록 하나가 pytest 개수를 1 늘리기** 때문임(2026-09-25 실측).
위 3번의 `1452` 를 그대로 유효하게 두려면 블록을 넣지 않는 쪽이 맞음.

## 이번 세션 요약 (2026-10-17 ~ 10-18)

코드 변경 0건임. 도구·설정·세션 운영만 했음.

- **Claude Code** `2.1.296` → **`2.1.302`**(네이티브 판 · 심링크 `~/.local/bin/claude` 정상)
- **superpowers** `6.4.1` → **`7.0.0`** · **superpowers-chrome** `3.0.5` → **`3.3.0`**
- `~/.claude/CLAUDE.md` 에서 superpowers 버전 고정을 삭제하고 정본을 `claude plugin list` 로 바꿈.
  ⛔ **커밋하지 않았음**(위 11번의 이유)
- Paseo 원격 접속 경로를 조사했음 — 데몬이 `127.0.0.1:6767` 루프백만 듣고 릴레이는 켜져 있음.
  경로 넷(릴레이 페어링 · LAN 직접 · Tailscale · SSH)의 상세는 이 문서가 담지 않음
- 중복 세션 `plugin-7.0.0 적용 확인`(`52264fa`)을 중단·보관했음. 토큰 사용량 0 이라 버린 작업 없음
- 후속 세션이 인계 지표를 대조해 **이전 판의 지표 3개가 낡았음**을 찾았음. 원인은 하나로,
  인계서를 마지막으로 고친 뒤 커밋 14건(`TASK-269`~`280`)이 들어갔는데 갱신되지 않았음.
  이 판이 그 교차 확인 결과임

## 다음 세션이 먼저 볼 것

원장 잔여가 0건이므로 **새 지시를 받기 전까지 할 일이 없음**. 지시가 오면 태스크 등록부터 함
(`rules/task-management.md` §3). 작업을 시작하면 위 2번에 따라 스택을 먼저 띄워야 함.
