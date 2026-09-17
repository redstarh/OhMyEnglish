# HANDOFF — OhMyEnglish

> 최종 갱신 **2026-09-18 08:18 KST** · 세션 `ohmyenglish-42` · 브랜치 `design/first-vertical-slice`
> ⛔ **이전 판은 `handoff/backup/2026-09-18/HANDOFF-0818.md` 에 있음**(그 앞 판은 같은 폴더 `-0328`).
> 인계 원칙의 정본은 `~/.claude/rules/session-handoff.md` 임.
> 근거 정본은 **태스크 노트 · `docs/ops/pitfalls.md`(`H-CA`·`H-CB`) · 지시 대장 결정 127** 임.

## ⛔ 먼저 챙길 것 — 첫 코드블록보다 앞에 둠

1. ⛔ **이 세션은 개발 세션임.** 살아 있는 지시 다섯: 묻지 않고 권고대로 감 · 개발 뒤 테스트 필수 ·
   짧게 핵심만 보고 · **기능은 심플하게** · 주요 개발 뒤 `/simplify`. ⛔ **En-Coach 는 고치지 않음.**
2. ⛔ **브라우저 검증은 `localhost:3000` 으로 엶** — `127.0.0.1` 로 열면 Next dev 가 dev 리소스를
   차단해 **hydration 이 아예 안 되고 브라우저 콘솔에 오류도 없음**(함정 `H-CA`). 증상은 「버튼이
   잠긴 채 반응이 없음」이라 앱 결함으로 오독하기 쉬움. 백엔드는 `127.0.0.1:8002` 로 불러도 됨.
3. ⛔ **결정 124 는 반증됐음** — 「소리를 따옴표로 «따로» 인용하라」를 프롬프트에 다시 넣지 말 것.
   정본은 `runs/2026-09-17-task154-dedicated-quote/README.md` 임.
4. ⛔ **자막을 얻으려 하지 말 것**(결정 126). 그 자리를 **사용자가 받아 적는 것**이 대신함.
5. ⛔ **DB 배치**: 우리 표는 스키마 **`ohmyenglish`** 에 있음. `pg_dump` 는 **`-n ohmyenglish`** ·
   `information_schema` 조회에 **`current_schema()` 를 반드시 걺**(`H-BX`).
6. ⚠️ **앱이 떠 있음** — 백엔드 **47873**(`:8002` · `WORKER_ENABLED=false VOICE_ADAPTER=stub`) ·
   프런트 **21770**(`:3000` · `next dev` · 로그 `/tmp/omy-frontend.log`). ⛔ 백엔드는 `--reload` 가
   없어 **소스를 고쳤으면 재기동**함. `app/frontend/.env.local` 은 `:8002` 로 되돌려 뒀음.
7. ⚠️ **`analysis_jobs` 에 pending 56 건이 쌓여 있음** — 워커를 켜면 그만큼 Bedrock 비용이 나감.
   켜기 전에 판단이 필요함.

## 인계 지표 4개 (이 턴에 직접 돌린 출력)

| # | 지표 | 값 |
|--:|---|---|
| 1 | 기준 커밋 | 게이트를 돌린 시점은 **`8af0d90`** 이고 작업트리 clean · `origin` 과 **0/0**(push 했음). ⛔ 이 handoff 의 마감 커밋이 그 뒤에 오므로 새 세션 `HEAD` 는 그보다 앞임 — **차이가 이 파일뿐이면 정상**임 |
| 2 | 다음 한 걸음 | ⛔ **원장이 완전히 닫혔음 — 열린 태스크 0건**(`To Do` 0 · `In Progress` 0 · `Awaiting Decision` 0 · 전체 **240**). ⇒ 다음 걸음은 **사용자의 방향 지시**임. 열린 축은 아래 ④ |
| 3 | 게이트 | **여덟 다 exit 0** — `pytest` **1343 passed** · `ruff` 0 · `ruff format` **291 files** · `ty` 0 · `tsc` 0 · `eslint` 0 · **`next build` 0**(`/` 가 `○` Static 유지) |
| 4 | 착수 전 필수 | 전체 **240** · 완료 **240** · **미충족 AC 0건** ⇒ 착수 전 조건 없음 |

```bash
cd ~/MyProject/OhMyEnglish
git rev-parse --short HEAD && git rev-list --left-right --count HEAD...origin/design/first-vertical-slice
backlog task list --plain
cd app/backend && ./.venv/bin/pytest -q
cd app/backend && ./.venv/bin/ruff check . ../../tests ../../scripts \
  && ./.venv/bin/ruff format --check . ../../tests ../../scripts && ~/.local/bin/ty check
cd app/frontend && npx tsc --noEmit && npx eslint . && npx next build
```

## ① 이 세션이 한 것 — 「미확인 셋」을 닫고 낭독 녹음을 열었음

닫은 태스크 **여덟**(`TASK-172`~`TASK-179`). 커밋 셋: `bed062a` · `9e36a45` · `8af0d90`.

⛔ **값은 「만든 것」보다 «전제를 세 번 뒤집은 것» 에 있음**:

1. **「담기 버튼이 안 눌린다」가 앱 결함이 아니었음** — `127.0.0.1` 로 열어 hydration 이 죽었음.
   ⚠️ 청크를 `fetch` 로 받아 전부 200 을 확인한 검사는 **그 차단을 거치지 않아 판별력이 없었음**.
2. **「없는 영상은 `onError` 100 을 낸다」가 틀렸음** — 아무 이벤트도 오지 않음. 대조군(정상 영상이
   `onReady` 를 받는 것)을 넣어서야 갈렸음. ⇒ 감지 불가라 `TASK-177` 을 「그대로 둠」으로 닫았음.
3. **「낭독은 Nova 를 안 타니 stub 으로 충분하다」가 틀렸음** — stub 은 세션을 **33ms** 에 끝내
   낭독 턴이 열릴 틈이 없음. **지난 세션의 「stub 이라 미검증」이 옳았음.**

## ② 지금 상태 — 새로 생긴 계약

- **낭독 녹음이 처음으로 돌았음** — `shadowing_recording` 발화 1건 · 파일 **917,504 바이트**
  (`assets/audio/<세션>/<발화>.pcm`) · 조회 엔드포인트 200. 전사문은 **클립의 것을 그대로** 씀
  (Nova ASR 을 타지 않는 설계임).
- **`ShadowingPanel` 이 「따라 읽기」·「읽기 끝」 토글을 가짐.** ⛔ **언마운트 시 열린 턴을 닫음** —
  닫지 않으면 세션 전체가 녹음됨. 부모가 넘기는 콜백 둘은 **`useCallback` 안정화가 계약**임.
- **녹음 시작이 클립 재생을 끄고 녹음 중에는 「클립 듣기」를 잠금** — 스피커 원본이 마이크로 되돌아오면
  저장된 것이 학습자가 읽은 것이 아니게 됨.
- **`onError` 는 코드를 보지 않음**(`PLAYER_EMBED_BLOCKED` 를 없앴음). 어느 오류든 안내와 YouTube
  링크로 모임. ⛔ 비교·재생은 여전히 범위 밖임(결정 127 이 「녹음」만 해제했음).
- **30일 stale 갱신은 목록 화면 진입만으로 조용히 됨** — 실측했고 알림 문구는 0건임.

## ③ 착수 전 필수 — 이 세션 실측

1. ⛔ **`pytest`·`ruff` 는 `app/backend` 에서 돌림**(`H-BN`). 부분 실행은 `-o asyncio_mode=auto`.
2. ⛔ **한글 주석을 쓴 직후 `ruff check`** — `E501` 은 표시 폭이라 한글이 2열임(`H-BW`).
3. ⛔ **종료 코드 판정에 파이프를 걸지 않음**(`H-AZ`). `grep -c` 는 0건이면 exit 1 임.
4. ⚠️ **프런트에 테스트 러너가 없음**(`devDependencies` 에 jest·vitest 0건) ⇒ 화면 판정은 **브라우저
   관측이 유일**함. 그래서 ①의 함정 둘이 게이트 여덟을 통과했음.
5. ⚠️ **브라우저 자동화에 오디오 장치가 없음** — 마이크가 필요하면 `AudioContext` →
   `MediaStreamDestination` 으로 `getUserMedia` 를 갈아 끼움. ⛔ **프로브 플레이어는 화면 «안» 에
   붙임** — `left:-9999px` 면 초기화되지 않아 **대조군까지 timeout** 이 됨.
6. ⚠️ **실물 Nova 검증 형태**: `:8014` 에 `WORKER_ENABLED=false VOICE_ADAPTER=nova` 백엔드를 띄우고
   `app/frontend/.env.local` 의 `NEXT_PUBLIC_API_BASE` 만 그쪽으로 돌림(검증 뒤 되돌림).
   ⛔ **프런트를 다른 포트에 띄우는 길은 막혀 있음** — `api/main.py` 의 `FRONTEND_ORIGIN` 이
   `http://localhost:3000` **하드코딩**이라 `:3001` 은 CORS 에 걸림.
7. ⚠️ **불변 지표(이 턴 실측)**: `learning_sessions` **25** · `utterances` **171**(그중
   `shadowing_recording` **1**) · `shadowing_items` **2** · `youtube_videos` **1** ·
   `pronunciation_attempts` **7** · `analysis_jobs` **102**(pending 56 · done 44 · failed 2) ·
   `error_patterns` **9** · `review_tasks` **15** · `schema_migrations` **25**.
8. ⛔ **`git add <디렉터리>` 금지** · 커밋 뒤 `git show --stat` 으로 담긴 것 전체를 봄.

⚠️ **나머지 일반 함정의 정본은 `docs/ops/pitfalls.md` 임.**

## ④ 열린 태스크 0건 — 열린 «축» 셋

⛔ **다음 세션의 첫 행동은 태스크를 고르는 것이 아니라 사용자의 방향을 받는 것임.**

1. **낭독 녹음의 다음 조각** — 녹음을 들려주기 · 원본과 비교 · `drill_turns_expected`(지금 NULL) ·
   발음 판정에 연결. ⛔ 결정 127 이 「녹음」만 해제했으므로 그 앞은 **다시 결정이 필요**함.
2. **영상 학습의 다음 조각** — 낱말 사전 · 재생목록 담기. 스토리보드 §6 이 **뺀 것 열과 근거**를 가짐.
3. **코치 발화·오디오 어긋남 판정** — 남은 후보가 「오디오를 듣는 판정」이고 설계서 §6 이 범위 밖에 둠.

⚠️ **확인하지 못한 것 둘**: 임베드가 막힌 영상의 안내(그런 영상 id 를 얻을 경로가 없음 — oEmbed 가
차단 영상에도 200 을 주고 후보 수집은 `search.list` 가 필요함) · `analysis_jobs` pending 56 의 처리.

## ⑤ 착수 전 반드시 읽을 것

- **결정 127**(지시 대장 끝) — 마감을 사람 입력에서 뗀 것 · 재생 불가 감지를 넣지 않은 것 ·
  결정 90 의 낭독 녹음 유예를 해제한 것. ⛔ 비교·재생이 아직 범위 밖인 근거가 거기 있음.
- **`docs/design/2026-09-08-shadowing-task-design.md` §12** — 진입점 요구 5개. 요구 4 를 이 세션이
  채웠고 나머지 넷은 이전에 채워졌음.
- **함정 `H-CA`·`H-CB`** — 게이트 여덟이 초록이어도 **브라우저에서만 막히는 것**과 **관측 장치 자체가
  틀린 것**은 잡히지 않음. **대조군이 그 둘을 가른 유일한 수단**이었음.

## ⑥ 인계 확인 — 후계 세션이 직접 돌린 결과 (2026-09-18 08:25 KST)

이 세션이 후계 세션 `ohmyenglish-0b`(tmux `omy-0918-0820`)를 띄우고 첫 지시를 전달했음. 그 세션이
지표 표를 내고 **지표 4(미충족 AC 0건)를 「일치」로 판정**했으며 앱 기동을 직접 확인했음(백엔드
**47873** `:8002` 200 · 프런트 **21770** `localhost:3000` 200). 그 뒤 원장이 **240/240** 으로 닫힌
것을 근거로 ④ 의 축을 정리해 사용자에게 방향을 물었음.
⚠️ **지표 1~3 의 개별 판정은 pane 스크롤백에서 밀려나 내가 직접 보지 못했음** — 그 세션이 「차이」를
보고하지 않고 다음으로 넘어간 것이 간접 근거임. 추측을 사실로 적지 않으므로 그 한계를 남김.
