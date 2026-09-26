# HANDOFF — OhMyEnglish

> 최종 갱신 **2026-09-26 11시대 KST** · 브랜치 `design/first-vertical-slice`
> ⛔ **이전 판은 `handoff/backup/2026-09-26/HANDOFF-1119.md`** (그 앞 판들은 같은 폴더의 날짜별).
> 인계 원칙의 정본은 `~/.claude/rules/session-handoff.md` · 근거 정본은 **태스크 노트 ·
> `docs/ops/pitfalls.md` · 회차 노트**임.

## ⛔ 먼저 챙길 것 — 첫 코드블록보다 앞에 둠

1. ⛔ **원장 잔여 0건임**(`To Do`·`In Progress`·`Awaiting Decision` 전부 0 · `Done` 332).
   사용자 지시(2026-09-19)에 따라 방향 후보를 고르지도, 묻지도 않고 멈춤. 상태만 짧게 적음.
2. ⛔ **음성 어댑터 기본값이 `nova` 로 바뀌었음**(`TASK-267` · 2026-09-26). 플래그 없이 띄운 백엔드가
   `stub` 으로 돌아 학습 시작마다 픽스처 세 턴이 재생되고 dev DB 에 가짜 오류가 쌓였기 때문임.
   ⇒ **하네스·회차에서 스텁이 필요하면 `VOICE_ADAPTER=stub` 을 반드시 명시함.** 빼면 실물 Nova 가 붙음.
3. ⚠️ **스택이 떠 있음** — `:8002`(nova · 워커 켜짐 · `nohup` 로그 `/tmp/omy-backend.log`) ·
   `:3000`. 사용자가 실제로 학습하는 스택이므로 **dev DB 에 회차를 돌리지 않음**(아래 5번).
   ⛔ 리스너 확인은 `lsof -nP -iTCP:8002 -sTCP:LISTEN -t` 로 함(`H-CJ`).
4. ⛔ **이 세션은 개발 세션임.** 살아 있는 지시: 묻지 않고 권고대로 감 · 개발 뒤 테스트 필수 ·
   짧게 핵심만 보고 · 기능은 심플하게. ⛔ **En-Coach 는 고치지 않음.**
5. ⛔ **유료 회차는 격리 DB `ohmyenglish_worker` 에서 돌림 — dev DB 가 아님**(`TASK-191` 의 결정).
6. ⛔ **dev DB 를 한 번 정리했음**(2026-09-26 사용자 결정 · 픽스처 세션 22건 삭제). 백업은
   `~/Backups/OhMyEnglish/ohmyenglish-before-TASK-267-20260926-1036.dump`. 수치는 `TASK-267` 노트가 가짐.
   ⚠️ `weekly_reports`·`learner_notes` 의 생성 문면에는 가짜 데이터 기반 문장이 남아 있을 수 있음.
7. ⛔ **Bedrock 은 SigV4 가 필요함.** 직접 스크립트에는 `env -u AWS_BEARER_TOKEN_BEDROCK` 을 붙임.
8. ⛔ **회차 출력을 `head` 로 자르지 않음**(SIGPIPE). `> 파일` 로 받고 뒤에서 `grep` 함.
9. ⛔ **DB 배치**: 스키마 **`ohmyenglish`** · `pg_dump -n ohmyenglish`(`H-BX`) ·
   `psql` 은 `/opt/homebrew/opt/postgresql@17/bin/psql` · introspection 에는 `current_schema()` 를 걸음.
10. ⚠️ **PRD 가 v1.6 임** — §16·§17 을 읽지 않고 발음·드릴 영역을 손대지 않음.
11. ⚠️ **미결 관측 하나**: 이 세션의 셸에 `HANGUL_SANITY=0` 이 있었고 출처를 못 찾았음(셸 rc ·
    설정 파일 모두 0건). 훅 등록 자체는 `~/.claude/settings.json` 에 그대로 있음. 사용자에게 알렸음.

## 인계 지표 4개 (이 턴에 직접 돌린 출력)

| # | 지표 | 값 |
|--:|---|---|
| 1 | 기준 커밋 | 이 판을 담은 커밋 — 아래 `git log -1` 로 읽음. 그 직전 HEAD 는 **`3c853e6`** · push 전 `origin` 과 **3/0** |
| 2 | 다음 한 걸음 | **없음 — 원장 잔여 0건**(`Done` **332** · 마지막 둘은 `TASK-267`·`268`) |
| 3 | 게이트 | 백엔드 넷 **exit 0** — `pytest` **1432 passed** · `ruff` 0 · `ruff format` 331 files · `ty` 0. ⚠️ 프런트 셋은 프런트 파일을 고치지 않아 돌리지 않았음 |
| 4 | 착수 전 필수 | 미결 승인 0 · 스택 떠 있음(위 3번) |

```bash
cd ~/MyProject/OhMyEnglish
git log --oneline -1 && git rev-list --left-right --count HEAD...origin/design/first-vertical-slice
backlog task list -s "To Do" --plain
cd app/backend && ./.venv/bin/pytest -q
cd app/backend && ./.venv/bin/uvicorn app.api.main:app --port 8002   # 기본 nova · 스텁은 VOICE_ADAPTER=stub
cd app/frontend && npx next dev
```

## ① 이 세션이 한 것

1. **`TASK-267`** — 사용자 신고(「학습 시작이 이미 완료로 나옴 · 오류 수만 오름」)의 원인을 잡았음.
   10:16 에 플래그 없이 뜬 `:8002` 가 `stub` 으로 돌아 학습 시작 즉시 픽스처 세 턴을 재생하고
   세션을 닫았음. 하루 학습량 제한은 코드에 없었고, 「오늘 학습을 마쳤어요」는 결과 화면 표시였음.
   수정: `config.voice_adapter` 기본값 `nova` · `test_ws` 픽스처가 `stub` 을 명시 · 기본값 단정 테스트.
   브라우저에서 학습 시작이 마이크 권한 요청으로 열리는 것을 확인했음(결과 화면으로 튀지 않음).
2. **`TASK-268`** — 스픽 커리큘럼·시나리오 조사를 `docs/research/2026-09-26-speak-curriculum.{md,html}`
   로 정리했음. 공개 페이지만 근거이고 미확인 항목은 그 문서 8장이 가짐.

## ② 이 세션이 배운 것

1. ⛔ **「테스트용 기본값」은 실사용 스택의 기본값이 됨.** 사용자가 문서 명령 그대로 띄우면
   그 값이 붙음 — 테스트가 필요한 값은 테스트가 명시하고, 선언 기본값은 실물 쪽에 둠.
2. ⛔ **가짜 데이터는 대소문자가 달라도 가짜임.** 픽스처 답을 글자 그대로만 찾으면 음성으로 읽힌
   하네스 회차(소문자 전사)가 빠졌음 — 삭제 범위는 되돌림 모드로 수치를 먼저 보고 확정했음.

## ③ 남은 것 — 원장 밖에 적어 두는 자리

1. **계획 부재 시의 퇴화 동작** — 테스트는 `TASK-266` 이 세웠음. 실물 화면 관측은 계획 생성을 끄는
   스위치가 생기면 볼 자리임.
2. **출처를 잃은 문장 1건**(`408d6cc5-da54-4f82-b3a7-69b32404ecd4`) — 사용자가 처리하지 않기로 정했음.
3. **실물 대화 한 턴 이상의 관측**은 자동 브라우저로 못 했음(마이크 권한을 거부함). 사용자가 한 번
   대화하면 확인됨 — 그때 결함이 나오면 새 태스크로 등록함.
