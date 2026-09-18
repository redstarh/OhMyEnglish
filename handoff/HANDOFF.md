# HANDOFF — OhMyEnglish

> 최종 갱신 **2026-09-19 05시대 KST** · 세션 `ohmyenglish-46` · 브랜치 `design/first-vertical-slice`
> ⛔ **이전 판은 `handoff/backup/2026-09-19/HANDOFF-prev-0918-1812.md` 에 있음**(그 앞은
> `backup/2026-09-18/` 의 `-1812`·`-1354`·`-1113`·`-0818`).
> 인계 원칙의 정본은 `~/.claude/rules/session-handoff.md` 임.
> 근거 정본은 **태스크 노트 · `docs/ops/pitfalls.md`(`H-CA`~`H-CH`) · 설계서 §6-1** 임.

## ⛔ 먼저 챙길 것 — 첫 코드블록보다 앞에 둠

1. ⛔ **이 세션은 개발 세션임.** 살아 있는 지시: 묻지 않고 권고대로 감 · 개발 뒤 테스트 필수 ·
   짧게 핵심만 보고 · **기능은 심플하게** · 주요 개발 뒤 `/simplify`. ⛔ **En-Coach 는 고치지 않음.**
   ⚠️ **사용자가 2026-09-19 에 「승인이 필요한 작업은 사전 승인」을 줬음** — 실물 Bedrock 회차를
   그 승인으로 돌렸음. 새 세션에서 그 승인이 이어지는지는 확인이 필요함.
2. ⛔ **마감 트리거는 둘뿐임** — **쓴 컨텍스트 70% 초과**와 **compact 경고**. 「태스크 N개 연속
   완료」는 폐기됐고 원장이 닫힌 것은 마감 조건이 **아님**. 정본은 `rules/session-handoff.md` §5·8항.
3. ⛔ **`skill`·`rules/**` 의 본문은 영어로 씀.** 경계는 `rules/korean-writing-standard.md` 머리말이
   소유함 — 모델만 읽는 지시문은 영어, **사람이 읽거나 리포에 남는 것은 한글**(대화·커밋 메시지·
   handoff·원장 노트·설계서·이 리포 코드 주석).
4. ⛔ **Bedrock: 이 리포는 SigV4 가 필요함.** 셸에는 bearer 만 있고 SigV4 두 키는
   `app/backend/.env` 에만 있음(2026-09-19 재확인). `config.prepare_bedrock_credentials` 가 그 쌍을
   환경에 올리고 bearer 를 닫으므로 앱 경로는 그대로 돌지만, **직접 스크립트를 돌릴 때는
   `env -u AWS_BEARER_TOKEN_BEDROCK` 을 앞에 붙임**(그렇게 실물 A/B 두 회차가 성립했음).
5. ⛔ **브라우저 검증은 `localhost:3000`**(`H-CA`) · **세션 화면을 `?mode=…` 로 열지 않음**(`H-CC`) ·
   ⛔ **낭독 판정 화면은 스텁 둘로 관측 불가**(`H-CG`).
6. ⛔ **워커를 「관측용으로 잠깐」 켜지 않음**(`H-CD`). ⛔ **세션을 만든 회차 뒤에는
   `teardown_session.py --session-id` 를 돌림**(`app/backend` 에서 돌려야 `.env` 가 읽힘).
   ⚠️ **전사만 하는 회차는 세션을 만들지 않음** — 2026-09-19 A/B 뒤 pending job 0 · active 세션 0 ·
   발화 증가 0 을 실측했고 걷을 것이 없었음.
7. ⛔ **결정 124 는 반증됐음**(따옴표 인용을 프롬프트에 다시 넣지 말 것) · ⛔ **자막을 얻으려 하지
   말 것**(결정 126).
8. ⛔ **DB 배치**: 우리 표는 스키마 **`ohmyenglish`** 에 있음. `pg_dump` 는 **`-n ohmyenglish`**(`H-BX`).
   `psql` 은 `/opt/homebrew/opt/postgresql@17/bin/psql` 임.
   ⚠️ **`public` 에 En-Coach 호환 뷰 셋이 있음** — introspection 에는 `current_schema()` 를 **반드시
   걸어야 함**(`H-BX`. 2026-09-19 에 그 규율이 한 자리에서 빠져 있던 것을 고쳤음 · `TASK-218`).
9. ⚠️ **백엔드가 떠 있음** — `:8002` · `WORKER_ENABLED=false VOICE_ADAPTER=stub` · `/health` 200 ·
   로그는 `/tmp/omy-backend.log`. ⛔ **`--reload` 가 없어 소스를 고쳤으면 재기동함.**
   ⛔ **프런트는 떠 있지 않음** — 화면을 볼 일이 있으면 `:3000` 에 직접 띄움.
10. ⛔ **`git` 이 exit 69 로 죽으면 Xcode 라이선스임**(`H-CH` 신설). 2026-09-19 세션 시작에 실제로
    막혔고 **사용자가 그 자리에서 해결했음** — 지금은 우회 없이 돌아감. 다시 나면 셸에서
    `DEVELOPER_DIR=/Library/Developer/CommandLineTools` 를 앞에 붙이고, 항구적 해결은 sudo 라서
    사람 몫임.
11. ⚠️ **낭독 전사는 이제 「전사 전용 모드」가 기본임**(`TASK-217`) — 코치 지시문·tool 스펙을 싣지
    않음. 입력 토큰이 2,143 → 897 이고 **전사문은 글자까지 같았음.** 실측 정본은 설계서 §6-1 임.

## 인계 지표 4개 (이 턴에 직접 돌린 출력)

| # | 지표 | 값 |
|--:|---|---|
| 1 | 기준 커밋 | **`26d0788`** · 작업트리 clean · `origin` 과 **0/0** |
| 2 | 다음 한 걸음 | **`TASK-220`** — codex 품질 리뷰 결과를 수신해 심각도로 분류하고 CRITICAL·HIGH 를 닫음. ⛔ **1차 시도가 미수신으로 끝났음**(아래 ②) |
| 3 | 게이트 | **여덟 다 통과** — `pytest` **1397 passed** · `ruff` 0 · `ruff format` **304 files** · `ty` 0 · `tsc` 0 · `eslint` 0(경고 1건은 기준선) · `next build` 0(`/` 가 `○` Static 유지) |
| 4 | 착수 전 필수 | 전체 **280** · 완료 **279** · 열린 것 **하나**(`TASK-220`) · `In Progress` **1건**(그것) · 미충족 AC **3건** · 의존 **0건** |

```bash
cd ~/MyProject/OhMyEnglish
git rev-parse --short HEAD && git rev-list --left-right --count HEAD...origin/design/first-vertical-slice
backlog task list --plain
cd app/backend && ./.venv/bin/pytest -q
cd app/backend && ./.venv/bin/ruff check . ../../tests ../../scripts \
  && ./.venv/bin/ruff format --check . ../../tests ../../scripts && ~/.local/bin/ty check
cd app/frontend && npx tsc --noEmit && npx eslint . && npx next build
```

## ① 이 세션이 한 것 — 태스크 여섯을 닫았음 (커밋 다섯)

| 커밋 | 태스크 | 무엇 |
|---|---|---|
| `8c6a87b` | `TASK-218` | 스키마 무필터 단정에 `current_schema()` 를 추가했음. `TASK-41` 이 세 자리를 고치고 주석까지 남겼는데 한 자리가 빠져 있었고, 그 단정이 **카탈로그 물리적 행 순서**에 붙어 고립 실행에서 8/8 실패했음 |
| `58157d4` | `TASK-219` | `git` 이 죽은 것을 「`.gitignore` 에 걸렸다」로 보고하던 것을 고쳤음. `check-ignore` 의 `0`·`1` 밖 코드를 먼저 갈라 git 의 stderr 를 문면에 실음. `H-CH` 신설 |
| `633ae25` | `TASK-214` | 좁은 `Transcriber` 포트. `audio_gateway/transcribe.py` 신설(어댑터 구동부·침묵·조용함·프레임·수명) · `factory.create_transcriber` · `services/readback.py` 274 → 158줄 · 라우터가 대화형 포트를 아예 모름 |
| `1b7bf04` | `TASK-215` | Nova 사용량 기록을 `_pump_output` 의 `finally` 로. `close()` 는 멱등 백스톱 · `_usage_recorded` 가 「많아야 한 번」을 소유 · 종료 예산 셋의 차례와 합을 `_close_and_record` 한 자리에 적고 합을 테스트로 고정했음 |
| `cee0726` | `TASK-216` | 회차 teardown 이 앱의 삭제 규칙을 재사용. 사설 헬퍼 둘을 공개로 올림. ⚠️ **동작이 바뀜 — 삭제 범위가 좁아짐**(이름 규칙 밖 파일이 남고 디렉터리도 남음) |
| `26d0788` | `TASK-217` | 전사 전용 프롬프트 + tool 스펙 제거. 실물 A/B 로 **입력 −58.1% · 출력 −78.0% · 전사문 동일** |

## ② 미결 하나 — 위임한 `/simplify` 4각이 돌아오지 않았음

⛔ **`TASK-220` 이 그것을 소유함.** reuse·simplification·efficiency·altitude 네 에이전트를 병렬로
띄웠고 8분 뒤 넷 다 `idle` 이 됐지만 **결과를 하나도 내지 않았음.** 직접 제출 요청까지 보냈고 그래도
응답이 없었음 ⇒ **`idle` 은 완료가 아님**(메모 `delegated-review-may-never-return` 이 다시 맞았음).
2차 시도로 **codex 리뷰어**에 좁은 범위(신설 `transcribe.py` · `factory` 의 두 갈래 · `nova` 의 사용량
기록과 `transcribe_only` · `port` 의 `Transcriber`)만 걸어 두었음. ⛔ **결과가 오기 전까지 그 네 파일을
고치지 않음.**

## ③ 이 세션이 배운 것 — 다음 세션이 반복하지 않을 것

1. ⛔ **게이트 수치가 handoff 와 다르면 그 차이가 먼저 정보임.** 기록은 `1389 passed` 였고 첫 실행이
   `2 failed, 1387 passed` 였음 — **둘 다 실물 결함**이었고 하나는 환경(`H-CH`), 하나는 8일 묵은
   무필터 단정이었음. 「환경 탓」으로 접지 않은 것이 둘을 갈라낸 이유임.
2. ⛔ **「같은 커밋에서 통과와 실패가 갈리면」 단정이 재려는 성질이 아닌 것에 붙어 있음.** 전체
   실행에서는 통과하고 고립 실행에서는 8/8 실패했고, 그 비대칭이 곧 카탈로그 행 순서 의존의 증거였음.
3. ⛔ **판별력은 「고치는 대상과 같은 모양의 입력」으로 재야 함.** `H-CH` 는 라이선스가 풀리기 «전에»
   재서 `exit 69` 문면을 직접 봤음 — 풀린 뒤에는 그 입력을 만들 수 없었음.
4. ⚠️ **한글 훅이 정상 낱말을 막을 수 있음** — 이 세션에서 명사형 어미 둘이 말뭉치에 없어 막혔고,
   허용 목록에 넣는 것보다 다른 표현으로 바꾸는 쪽이 값쌌음. 훅 메시지에 나온 음절을 **그대로
   인용하면 다시 막히므로** 인용하지 않는 것이 요령임.
5. ⚠️ **실물 A/B 에 브라우저를 태울 필요가 없었음** — 재는 것이 「프롬프트가 전사를 바꾸나」이면
   같은 PCM 을 같은 함수에 두 번 흘리는 것이 가장 좁은 관측임. 브라우저는 변수를 늘림.

## ④ 착수 전 필수

1. ⛔ **`pytest`·`ruff` 는 `app/backend` 에서 돌림**(`H-BN`). 부분 실행은 `-c pyproject.toml`(`H-AJ`).
2. ⛔ **뮤테이션마다 `__pycache__` 를 지움**(`H-CF`). 이 세션의 뮤테이션 여섯이 그렇게 돌았음.
3. ⛔ **마이그레이션 적용 전 `pg_dump -n ohmyenglish` 로 백업함.**
4. ⛔ **`git add <디렉터리>` 금지** · 커밋 뒤 `git show --stat` 으로 담긴 것 전체를 봄.
5. ⚠️ **나머지 함정의 정본은 `docs/ops/pitfalls.md` 임**(이 세션이 `H-CH` 를 더했음).
   ⚠️ 그 문서의 「최종 갱신」 줄이 `2026-09-10 · H-AZ` 로 **8일 낡았음** — 내 태스크 범위가 아니라
   고치지 않았음. 손대는 세션이 함께 고치면 됨.

## ⑤ 범위 밖으로 남긴 것

`end_input()` 으로 침묵 2초·조용함 3초를 없애는 축은 **재지 않았음**(`TASK-217` 노트가 근거를 가짐) —
AC 셋 밖이고 별 A/B 가 필요함(`contentEnd` 만으로 VAD 가 발화를 닫는지). `audioOutputConfiguration`
제거도 미검증으로 남김 — 출력이 이미 −78% 라 남은 이득이 작음.
