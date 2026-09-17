# HANDOFF — OhMyEnglish

> 최종 갱신 **2026-09-18 03:30 KST** · 세션 `ohmyenglish-42` · 브랜치 `design/first-vertical-slice`
> ⛔ **이전 판은 `handoff/backup/2026-09-18/HANDOFF-0328.md` 에 있음**(그 앞 판들은
> `handoff/backup/2026-09-17/`). 인계 원칙의 정본은 `~/.claude/rules/session-handoff.md` 임.
> 상태 정본은 원장(`backlog/`), 근거 정본은 **태스크 노트 · `docs/design/2026-09-18-video-learning-*.md`
> · `tests/agent/runs/2026-09-18-0303/` · `docs/ops/captain-instruction-register.md`** 임.

## ⛔ 먼저 챙길 것 — 첫 코드블록보다 앞에 둠

1. ⛔ **이 세션은 개발 세션임**(사용자 지시 2026-09-17·18). 살아 있는 지시 다섯: ⑴ 묻지 않고 권고대로
   감 ⑵ 개발이 끝나면 테스트를 필수로 돌림 ⑶ 짧게 핵심만 보고함 ⑷ **기능은 심플하게** ⑸ 주요 개발
   뒤 `/simplify`. ⛔ **En-Coach 는 고치지 않음.**
2. ⛔⛔ **결정 124 는 반증됐음 — 「소리를 따옴표로 «따로» 인용하라」를 프롬프트에 다시 넣지 말 것.**
   정본은 `runs/2026-09-17-task154-dedicated-quote/README.md` 이고 `nova.py` 규칙 9 위 주석과
   `test_neither_prompt_asks_the_coach_to_quote_the_sound_on_its_own` 이 그 금지를 지킴.
3. ⛔ **자막을 얻으려 하지 말 것** (결정 126). `captions.download` 는 영상 편집 권한을 요구하고
   스크래핑은 Developer Policies **III.E.6** 이 금지함(「남이 스크래핑한 데이터를 받는 것」까지).
   IFrame API 로도 자막 **텍스트**는 못 읽음. ⇒ 그 자리를 **사용자가 받아 적는 것**이 대신함.
4. ⛔ **DB 배치**: 우리 표는 스키마 **`ohmyenglish`** 에 있고 비수식 이름이 정상 경로임. `pg_dump` 는
   **`-n ohmyenglish`**. `information_schema` 조회에 **`current_schema()` 를 반드시 걺**(`H-BX`).
5. ⚠️ **앱이 떠 있음** — 백엔드 **47873**(`:8002` · `WORKER_ENABLED=false VOICE_ADAPTER=stub
   --log-level info` · 로그 `/tmp/omy-backend.log`) · 프론트 **81310**(`:3000` · `next dev` ·
   로그 `/tmp/omy-frontend.log`). ⛔ 백엔드는 `--reload` 가 없어 **소스를 고쳤으면 재기동**함.
6. ⛔ **원격보다 12 커밋 앞섬**(`ahead 12`). push 는 이 브랜치 한정 사전 승인이 있음.

## 인계 지표 4개 (이 턴에 직접 돌린 출력)

| # | 지표 | 값 |
|--:|---|---|
| 1 | 기준 커밋 | 게이트를 돌린 시점은 **`5f88afc`** 이고 작업트리는 clean 이었음. ⛔ **자기 커밋 해시를 여기 적지 않는 이유는 반드시 낡기 때문임** — 이 handoff 와 그 마감 커밋이 그 뒤에 있으므로 새 세션 `HEAD` 는 그보다 앞임. 그 차이가 **이 파일뿐**이면 정상임. `origin` 과는 **0/0**(push 했음) |
| 2 | 다음 한 걸음 | ⛔ **원장이 완전히 닫혔음 — 열린 태스크 0건**(`To Do` 0 · `In Progress` 0 · `Awaiting Decision` 0 · 전체 **232**). ⇒ 다음 걸음은 **사용자의 방향 지시**임. ⚠️ 열린 축 둘을 아래 ④ 에 적어 뒀음 |
| 3 | 게이트 | **여덟 다 exit 0** — 수집 **1343** · `pytest` **1343 passed** · `ruff` 0 · `ruff format` **291 files** · `ty` 0 · `tsc` 0 · `eslint` 0 · **`next build` 0** |
| 4 | 착수 전 필수 | 전체 **232** · 완료 **232** · **미충족 AC 0건**. ⇒ 착수 전 조건 없음 |

```bash
cd ~/MyProject/OhMyEnglish
git rev-parse --short HEAD && git rev-list --left-right --count HEAD...origin/design/first-vertical-slice
backlog task list --plain
cd app/backend && ./.venv/bin/pytest -q --collect-only && ./.venv/bin/pytest -q
cd app/backend && ./.venv/bin/ruff check . ../../tests ../../scripts \
  && ./.venv/bin/ruff format --check . ../../tests ../../scripts && ~/.local/bin/ty check
cd app/frontend && npx tsc --noEmit && npx eslint . && npx next build
```

## ① 이 세션이 한 것 — 「영상으로 배우기」 갈래를 처음부터 끝까지 만들었음

사용자 지시(2026-09-18)를 받아 조사 → 스토리보드 → 설계 → 구현 여덟 → `/simplify` → 통합 테스트를
순서대로 돌렸음. 닫은 태스크: `TASK-157`~`TASK-171` (**15건**) + 시나리오 `TS-8`~`TS-18`.

**사용자가 쓸 수 있는 상태임** — 링크를 담고, 구간을 잡아 들은 대로 적고, 그 문장으로 쉐도잉을 여는
한 바퀴가 실물 HTTP·WebSocket·DB·**브라우저 화면**에서 이어지는 것을 관측했음.

⛔ **이 세션의 값은 「만든 것」보다 «찾은 것 셋» 에 있음**:

1. **테스트가 초록인데 브라우저에서만 막히는 구멍** — CORS `allow_methods=["GET"]`. `api_client` 가
   ASGI 로 붙어 preflight 를 거치지 않아 단정 열 개가 다 통과했음. ⇒ preflight 를 직접 보내는 단정을
   두고 **`["GET"]` 으로 되돌려 red 가 되는 것까지 확인**했음.
2. **게이트가 못 잡는 Next.js 함정** — 문서가 *"In development … things may appear to work without
   `Suspense`"* 라 경고함. ⇒ `useSearchParams` 를 피하고 `next build` 로 `/` 가 Static 인 것을 확인.
3. **통합 테스트가 찾은 `500`**(`TASK-170`) — 검증이 **원본 값**으로 순서를 보고 접기는 그 뒤였음.
   ⇒ 접기를 값역 층으로 올렸고 백엔드 로그의 `CheckViolationError` 가 **0건**임.

## ② 지금 상태 — 새로 생긴 계약

- **`youtube_videos`**(027) — 제목·채널만 담고 **썸네일 URL 을 저장하지 않음**(`youtube_id` 로 조립).
  `metadata_fetched_at` 이 30일 보관 제한을 지키는 자리이고 `POST /api/videos` 가 담기와 갱신을 겸함
  (`created` 불린이 화면 문구를 가름).
- **문장은 새 표가 아니라 `shadowing_items`** 에 들어감 — `youtube_video_id` 가 `on delete set null`.
  ⛔ **영상을 지워도 문장이 남는 것이 이 갈래의 가장 값비싼 계약임**(테스트 셋이 그것을 못 박음).
- **오디오 저장 금지를 기존 CHECK 가 지킴** — `youtube_video_id` 가 있으면 `source_url` 이 필수이고,
  그러면 `shadowing_items_audio_only_for_synthetic` 이 자동으로 막음. 새 방어를 만들지 않았음.
- **`?item=<문장 id>`** 가 연습할 문장을 지정함(`coalesce` 맨 앞 항). 없는 id 는 조용히 자동 선택으로
  떨어짐. `/videos/[id]` 의 [연습하기] → `/?mode=…&item=…` → 대시보드가 `entryFromQuery` 로 받음.
- **상한·정밀도를 응답이 실어 줌**(`clip_max_span_sec`·`clip_precision_sec`) — 화면에 사본을 두지 않음.
- **MVP 는 YouTube Data API 를 쓰지 않음** — oEmbed 가 키 없이 되고 CORS 를 허용함. 새 비밀값 0개.

## ③ 착수 전 필수 — 이 세션 실측

1. ⛔ **`pytest`·`ruff` 는 `app/backend` 에서 돌림**(`H-BN`). **부분 실행은 `-o asyncio_mode=auto`** —
   `test_ws.py` 는 마커 없이 auto 에 의존하므로 빼면 기존 테스트가 「async 미지원」으로 죽음.
2. ⛔ **한글 주석을 쓴 직후 `ruff check`** — `E501` 은 표시 폭이라 한글이 2열임(`H-BW`). 이 세션에서
   **다섯 번** 걸렸음.
3. ⛔ **종료 코드 판정에 파이프를 걸지 않음**(`H-AZ`). 이 세션에서 `eslint | tail` 로 `exit=0` 을 읽었는데
   실제는 **`exit=1`** 이었고 오류가 하나 있었음.
4. ⛔ **`db_conn` 에서 CHECK 위반을 여러 번 내려면 중첩 `transaction()`(savepoint)로 감쌈** — 안 감싸면
   뒤따르는 문장이 `InFailedSQLTransactionError` 로 죽음.
5. ⚠️ **`api_client` 는 커밋된 행만 봄** — `db_pool` 을 쓰고 **정리 책임이 테스트에 있음**. 그리고
   `FIXED_USER_ID` 를 **내가 만든 경우에만** 지움(무조건 지우면 cascade 로 남의 데이터를 걷음).
6. ⚠️ **불변 지표(이 세션 마지막 실측)**: `learning_sessions` **23** · `utterances` **164** ·
   `error_patterns` **9** · `review_tasks` **15** · `analysis_jobs` **93** ·
   `pronunciation_attempts` **7** · `schema_migrations` **25** · `shadowing_items` **1**(시드 합성 클립
   하나) · `youtube_videos` **0** · `harness_runs` **28** · `harness_sessions` **100**.
   ⚠️ 세션·발화·job 이 늘어난 것은 통합 테스트가 실물 소켓을 여섯 번 연 결과임.
7. ⛔ **`git add <디렉터리>` 금지** · 커밋 뒤 `git show --stat` 으로 담긴 것 전체를 봄.

⚠️ **나머지 일반 함정의 정본은 `docs/ops/pitfalls.md` 임.**

## ④ 열린 태스크 0건 — 다만 열린 «축» 둘

⛔ **다음 세션의 첫 행동은 태스크를 고르는 것이 아니라 사용자의 방향을 받는 것임.**

1. **영상 학습의 다음 조각** — 검색·추천(PRD §5 가 「무제한 자동 수집」을 비범위로 둠) · 낱말 사전 ·
   재생목록 담기 · 임베드 차단 안내의 실물 확인. 스토리보드 §6 이 **뺀 것 열 가지와 근거**를 가짐.
2. **코치 발화·오디오 어긋남 판정** — 이전 세션이 남긴 축. 남은 후보가 「오디오를 듣는 판정」이고
   설계서 §6 이 범위 밖에 뒀으므로 **사용자 결정이 필요**함.

⚠️ **이 세션이 확인하지 못한 것 셋**(태스크로 등록하지 않았음 — 관측값이고 끝낼 사람이 정해지지
않았음): 임베드가 막힌 영상의 `101`·`150` 안내(그런 영상 id 를 갖고 있지 않음) · 실물 음성 연습 왕복
(`VOICE_ADAPTER=stub` 임) · 30일 stale 갱신의 **화면** 거동(서버 쪽은 확인했음).

## ⑤ 착수 전 반드시 읽을 것

- **`docs/design/2026-09-18-video-learning-design.md` §1** — 갈림길 다섯의 답과 **되돌리는 비용**.
  ⚠️ 질문 4 의 답이 한 번 뒤집혔고 그 경위가 그 자리에 있음(`TASK-170`).
- **스토리보드 §6** — 뺀 기능 열과 근거. 그것을 읽지 않고 기능을 더하면 「심플하게」가 무너짐.
- **결정 125·126** (지시 대장) — PRD 범위를 넓히지 않았다는 판정과 자막을 포기한 근거.
- ⚠️ **가장 값 있는 관찰**: 게이트 여덟이 초록이어도 **브라우저에서만 막히는 것**과 **정책이 금지하는
  것**은 잡히지 않음. 이 세션은 그 둘을 각각 preflight 단정과 스키마 CHECK 로 옮겼음.
