# HANDOFF — OhMyEnglish

> 최종 갱신 **2026-09-19 12시대 KST** · 세션 `ohmyenglish-47` · 브랜치 `design/first-vertical-slice`
> ⛔ **이전 판은 `handoff/backup/2026-09-19/HANDOFF-1230.md` 에 있음**(그 앞 판 둘도 같은 폴더).
> 인계 원칙의 정본은 `~/.claude/rules/session-handoff.md` 이고, 근거 정본은 **태스크 노트 ·
> `docs/ops/pitfalls.md`(`H-CA`~`H-CH`) · 설계서 §6-1** 임.

## ⛔ 먼저 챙길 것 — 첫 코드블록보다 앞에 둠

1. ⛔ **이 세션은 개발 세션임.** 살아 있는 지시: 묻지 않고 권고대로 감 · 개발 뒤 테스트 필수 ·
   짧게 핵심만 보고 · **기능은 심플하게** · 주요 개발 뒤 `/simplify`. ⛔ **En-Coach 는 고치지 않음.**
   ⚠️ **2026-09-19 에 사용자가 판단 둘을 승인했음**(보류 둘 — 아래 §③) — 그 결정은 `TASK-226`
   노트가 가짐. 새 세션에서 그 승인이 이어지는지는 확인이 필요함.
2. ⛔ **마감 트리거는 「쓴 컨텍스트 70% 초과」와 「compact 경고」 둘뿐임** — 원장이 닫힌 것은 마감
   조건이 아님(정본 `rules/session-handoff.md` §5·8항). ⚠️ 사용자가 직접 마감을 지시하면 그것이 우선.
3. ⛔ **`skill`·`rules/**` 본문은 영어, 사람이 읽거나 리포에 남는 것은 한글**(대화·커밋 메시지·
   handoff·원장 노트·설계서·코드 주석). 경계는 `rules/korean-writing-standard.md` 머리말이 소유함.
4. ⛔ **Bedrock: 이 리포는 SigV4 가 필요함.** 셸에는 bearer 만 있고 SigV4 두 키는
   `app/backend/.env` 에만 있음. 앱 경로는 `prepare_bedrock_credentials` 가 덮지만 **직접
   스크립트에는 `env -u AWS_BEARER_TOKEN_BEDROCK` 을 앞에 붙임.**
5. ⛔ **브라우저 검증은 `localhost:3000`**(`H-CA`) · **세션 화면을 `?mode=…` 로 열지 않음**(`H-CC`) ·
   ⛔ **낭독 판정 화면은 스텁 둘로 관측 불가**(`H-CG`).
6. ⛔ **워커를 「관측용으로 잠깐」 켜지 않음**(`H-CD`) · **세션을 만든 회차 뒤에는
   `teardown_session.py --session-id` 를 돌림**(`app/backend` 에서 돌려야 `.env` 가 읽힘).
7. ⛔ **결정 124 는 반증됐음**(따옴표 인용을 프롬프트에 다시 넣지 말 것) · ⛔ **자막을 얻으려 하지
   말 것**(결정 126).
8. ⛔ **DB 배치**: 우리 표는 스키마 **`ohmyenglish`** 에 있음. `pg_dump` 는 **`-n ohmyenglish`**(`H-BX`).
   `psql` 은 `/opt/homebrew/opt/postgresql@17/bin/psql` 임. ⚠️ **`public` 에 En-Coach 호환 뷰 셋이
   있음** — introspection 에는 `current_schema()` 를 **반드시** 걸어야 함(`H-BX`).
   ⚠️ **마이그레이션 030 이 이 회차에 dev DB 에 적용됐음** — 백업은
   `/tmp/omy-backups/ohmyenglish-20260919-1159.sql` 임(`pg_dump -n ohmyenglish`).
9. ⚠️ **백엔드가 떠 있음** — `:8002` · `WORKER_ENABLED=false VOICE_ADAPTER=stub` ·
   로그는 `/tmp/omy-backend.log`. ⛔ **`--reload` 가 없어 소스를 고쳤으면 재기동함** —
   ⛔ **이 회차가 서비스 소스를 여럿 고쳤으므로 그 프로세스는 낡았음.** 화면을 볼 일이 있으면
   **재기동**하고, 프런트는 떠 있지 않으므로 `:3000` 에 직접 띄움.
10. ⛔ **변이(mutation)는 스크립트로 넣고 스크립트로 되돌림.** 이 회차에
    `git checkout <파일>` 로 되돌리다 **그 파일의 미커밋 변경을 지웠음**(다시 적용해 복구함).
11. ⚠️ **낭독 전사는 「전사 전용 모드」가 기본임**(`TASK-217`) — 실측 정본은 설계서 §6-1 임.

## 인계 지표 4개 (이 턴에 직접 돌린 출력)

| # | 지표 | 값 |
|--:|---|---|
| 1 | 기준 커밋 | **`b33d029`** · 작업트리 clean · `origin` 과 **0/0**(푸시 완료) |
| 2 | 다음 한 걸음 | **없음 — 원장이 비었음**(전체 289 · 잔여 0 · `In Progress` 0). 방향은 사용자가 정할 자리임. 후보는 §④ 에 적어 둠 |
| 3 | 게이트 | **여덟 다 통과** — `pytest` **수집 1419 · 통과 1419**(skip 0) · `ruff` 0 · `ruff format` **306 files** · `ty` 0 · `tsc` 0 · `eslint` 0 errors(경고 1은 기준선) · `next build` 0(`/` 가 `○` Static 유지) |
| 4 | 착수 전 필수 | 열린 태스크 **0건** · 의존 **0건** · 미결 승인 **0건** |

```bash
cd ~/MyProject/OhMyEnglish
git rev-parse --short HEAD && git rev-list --left-right --count HEAD...origin/design/first-vertical-slice
backlog task list --plain
cd app/backend && ./.venv/bin/pytest -q
cd app/backend && ./.venv/bin/ruff check . ../../tests ../../scripts \
  && ./.venv/bin/ruff format --check . ../../tests ../../scripts && ~/.local/bin/ty check
cd app/frontend && npx tsc --noEmit && npx eslint . && npx next build
```

## ① 이 세션이 한 것 — 태스크 여섯을 닫았음 (정리 회차의 후속 전부)

`TASK-223`(결함: 고아 스윕이 정지 중 세션의 `.part` 를 지움 · **동작 바뀜**) ·
`224`(lease 를 잃은 뒤 결과를 커밋하던 호출부 셋 · `jobs.LeaseLost` 신설 · **동작 바뀜**) ·
`225`(워커 라우팅을 `_HANDLERS` 표로 + 누락 분기 단정 넷) ·
`226`(정리 지적 16건 중 **14건 적용 · 2건 보류** · 묶음 일곱) ·
`227`(마이그레이션 030 인덱스 둘 + 스윕 왕복 20→2 · 연결 3→1) ·
`228`(거짓 신호 여섯 강화 · 각각 거짓 통과를 먼저 재현).
⛔ **커밋별 상세는 `git log --oneline ad420ba..HEAD` 와 각 태스크 노트가 가짐** — 여기 복제하지 않음.

## ② 이 세션이 배운 것 — 다음 세션이 반복하지 않을 것

1. ⛔ **변이가 반증 불가일 수 있음.** `wav_from_pcm` 의 규격 인자를 무시하는 변이가 1414건을
   통과했는데 원인은 테스트 공백이 아니라 **두 규격의 값이 같아서**였음(16kHz·16bit·mono).
   값이 실제로 다른 변이(8kHz)를 넣으니 2건이 실패했음. ⇒ **변이가 결과를 바꿀 수 있는지 먼저 봄.**
2. ⛔ **내가 쓴 단정이 약해서 두 번 고쳤음** — 전사문 순서(행 2개로는 `created_at` 오름·내림 중
   하나가 반드시 겹침) · 라우팅 누락 사유(분석의 종류 가드가 같은 문면을 남겨 통과함).
   ⇒ **새 단정에도 변이를 걸어 봄.**
3. ⛔ **성능 가드는 「개수」로 재지지 않음** — 스윕의 바깔 상한은 결과 수가 같아서 호출 수로 재야
   드러났고, 「걷은 묶음을 곧바로 처리한다」는 주기를 5초로 줘야 보였음.
4. ⚠️ **리뷰의 계측 주장 둘이 크기 탓이었음**(`TASK-227`): 「리퍼가 매초 전체 순차 스캔」과
   「인덱스 하나가 회복 스윕도 덮는다」 — 20만 행에서 재니 각각 Index Scan 이고 계획 불변이었음.
   ⇒ **dev DB(111행)의 계획을 성능 근거로 쓰지 않음.**

## ③ 보류 둘 — 사용자 승인(2026-09-19)

- **고도 4**: `daily_summary` 네 함수의 `timezone` 을 필수 키워드로 바꾸지 **않음**(테스트 여섯
  자리와 `LookupError` 경로가 사라지는 대가가 조건 네 줄보다 큼).
- **단순화 8**: `audio_gateway/session.py` 의 `_send` 한 홉을 없애지 **않음**(리뷰가 값이 가장
  낮다고 적었고 회귀 위험 셋이 모인 파일임).
⇒ 되살릴 근거가 생기면 `TASK-226` 노트의 그 표를 먼저 읽음.

## ④ 다음 방향 후보 — 원장이 비었으므로 사용자 결정 자리임

1. **실물 회차로 회귀 확인**: 이 회차가 lease·라우팅·스윕을 건드렸으므로 Bedrock 실물 1회와
   화면 관측이 아직 없음(단위·통합 테스트만 있음).
2. **유휴 스윕 간격**(정리 회차 효율 7 · **동작변경=예**): 1Hz 인데 고유 해상도는 60초·1일임.
   회복 지연이 화면에 보이므로 별 태스크로 재야 함.
3. **기능 축**: PRD 잔여 요구 가운데 다음 수직 슬라이스를 고르는 일.
