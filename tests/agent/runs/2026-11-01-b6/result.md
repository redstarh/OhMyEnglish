# 회차 2026-11-01-b6 — 문법 코스 유료 회차 (`TASK-288` 실제 Nova 전사 · `TASK-289` 영상 자동 재생)

HEAD `65df3d6` + 미커밋 작업 트리(`CoursePlayer.tsx` 의 `seekTo` 뒤 `pauseVideo()`). 시작과 끝 모두 같음.
회차 중 `app/backend/app` · `app/frontend/app` · `app/frontend/lib` 의 소스 mtime 변화는 없었음.

## 판정표

| # | 확인 | 판정 | 근거 요약 |
|---|---|---|---|
| 1 | (a)(b)(c) 실제 전사 · 밑줄·취소선 | 차단됨 — Bedrock `AccessDeniedException` (2/2) | 시도 2건 모두 백엔드 로그에 `AccessDeniedException` 이 남았음. 응답은 `200 {"transcript":"","words":[]}` 임. 보낸 PCM 에는 말소리가 있었음(`sent-b-analysis.txt`: 3.04초 중 0.2~2.0초). (c) 는 보내지 않았음 |
| 1' | 인증 실패의 표현 | 실패 — 새 결함 D1 | 인증 거부가 화면에서 「잘 안 들렸어요. 「다시」를 눌러 한 번 더 해 보세요.」로 나옴. `course_attempts` 에도 빈 전사 행으로 기록됨 |
| 2 | 「따라 함 N회」 증가·새로 고침 뒤 유지 | 통과 (2/2) | 0 → 1 → 2. 두 번 다 새로 고침 뒤 같은 값이고 API `attempts` 와 같음 (`ATTEMPT-a.json` · `ATTEMPT-b.json`) |
| 3 | 집계 — DB · 히트맵 · 이력 표 | 통과 | DB 2행. UTC `10-31 17:29·17:30` 이 KST `2026-11-01` 로 묶임. 히트맵 마지막 칸 「2026-11-01 · 2회」, 전날 0. 이력 표 `11/1 · 1 · 1 · 1문장 · 2회` (`OVERVIEW-after-ab.json` · `db-after-ab.json`). 단 두 행 모두 D1 의 실패 시도임 |
| 4 | 자동 모드 실제 전사로 다음 문장 | 차단됨 | 1 과 같은 이유임. 거부될 호출을 더 쓰지 않았음 |
| 5a | 저장 위치 > 0 인 Day 를 열면 스스로 재생되지 않음 | 통과 | 두 정책 모두 15초 동안 `paused` 임 |
| 5b | 그 위치로 옮겨져 멈춤 · ▶ 로 그 위치부터 재생 | 실패 — 새 결함 D2 (5/5) | 영상 칸이 검게 비고 ▶ 버튼이 없음. 플레이어는 `unstarted · buffering`, `<video>` src 는 비어 있고 `readyState 0` 임. 가운데를 클릭해도 재생되지 않음. 자동 재생 제한을 끈 Chrome(Day 3 ×2 · Day 4)과 기본 정책 Chrome(Day 3 · Day 2) 모두 같았음 |
| 5c | 저장 위치 0(행 있음 · 행 없음)인 Day | 통과 (4/4) | Day 1(position 0) · Day 5(행 없음), 두 정책 모두 15초 동안 cued(`state 5`)·0초 정지. 기본 정책에서 ▶ 를 누르면 0초부터 재생됨 |
| 6 | 콘솔 앱 예외 | 통과 (관측 구간 한정) | 예외 0 · 오류 수준 로그 0 (`console-summary.txt`) |
| AC4 | dev DB 쓰기 없음 | 통과 | `devdb-start.json` 과 `devdb-end.json` 이 같음. `course_attempts` 0 · `course_day_progress` 0 · `llm_calls` 109(최신 2026-09-26) · 쓰기 통계 0 |

회귀(b5 대비): 새로 실패 1건(D2 — b5 의 「열면 그 위치에서 스스로 재생」 관찰이 「옮겨지지도 재생되지도 않음」으로 바뀜. 원인 후보는 미커밋 `pauseVideo()`). 첫 유료 회차이므로 Nova 쪽 기준선은 없음.

## Nova 호출 수

- 시도 POST: **2회**(상한 12). 둘 다 `u001-s4` 이고 Bedrock 이 거부했음. `llm_calls` 에 사용량 행은 0 임.
- 사전 실행(`PROBE-*` · `ATTEMPT-a-probe1`)은 녹음 창이 끝나기 전에 문서를 떠나 POST 0 임. 첫 시도 `ATTEMPT-a-try1-nopost` 도 POST 0 임(수집기 재연결 문제 · 아래 4).
- 계수 근거: `attempts.jsonl` 의 POST 2건 = 백엔드 로그의 attempts POST 2건 = `course_attempts` 2행.

## 새 결함

### D1 · Nova 가 인증 거부로 실패해도 따라 하기가 「잘 안 들렸어요」로 나오고 시도 1회로 기록됨
- 재현: 1) Bedrock 이 `AccessDeniedException` 을 내는 자격 증명으로 `VOICE_ADAPTER=nova` 백엔드를 띄움 2) `/course/1` 에서 수동 「시작」 3) 판정까지 기다림.
- 기대: 전사기를 쓸 수 없으면 503 이고 화면은 「지금은 따라 하기 판정을 쓸 수 없어요」 임. 시도는 기록되지 않음. 근거는 라우터 docstring 의 「전사기가 없으면 503」 과 같은 판단임.
- 실제: `200 {"transcript":"","words":[],"attempts":N}` · 화면 「잘 안 들렸어요. 「다시」를 눌러…」 · `course_attempts` 에 빈 전사 행 추가 · 히트맵·이력 횟수 증가.
- 경로: `nova.py` `_pump_output` 이 예외를 로그로 남기고 세션을 닫음 → `transcribe_readback` 은 final 없음을 빈 문자열로 돌려줌 → `record_attempt` 가 빈 전사도 기록함.
- 진단 정보도 부족함. 로그에는 예외 클래스 이름만 있고 메시지가 없어서, 거부 원인(IAM 정책 · 모델 접근 · 자격 증명 경로)을 특정하지 못했음.
- 증거: `ATTEMPT-a.json` · `ATTEMPT-b.json` · `attempts.jsonl` · `/private/tmp/omy-stack/backend-paid.log`(회차 폴더 밖, 이 회차가 쓰지 않음).
- 제안: 전사기 예외를 빈 전사와 구별해 503 으로 올림. 그리고 거부 메시지를 로그에 남김.

### D2 · 저장 위치가 있는 Day 를 열면 영상 칸이 검게 비고 ▶ 을 눌러도 재생되지 않음
- 재현: 1) Day 3 에 `position_sec 120` 을 저장함(앱 API) 2) `/course` 에서 Day 3 을 엶 3) 영상 칸을 클릭함.
- 기대: 썸네일과 ▶ 이 보이고, 누르면 120초부터 재생됨(TASK-289 결정).
- 실제: 검은 칸이고 큰 재생 버튼 요소가 없음. 플레이어 `getPlayerState() -1`, `<video>.currentTime 0`, src 빈 값임. 클릭 두 번 뒤에도 같음.
  iframe 에 키 `k` 를 직접 보내면 122.86초에서 재생됨. 그래서 플레이어는 위치를 들고 있고 시작 화면만 막힌 상태임(`VIDEO-np-day3-r2-stuck-tries.json`).
- 대조: 같은 Day 2 영상이 저장 위치 없음일 때는 정상이었음(cued · ▶ · 0초부터 재생). 6.49초가 저장된 뒤에는 같은 증상이 났음. 저장 위치 0 인 Day 도 정상임. b5(`pauseVideo()` 없음)에서는 같은 경로가 그 위치에서 재생됐음.
- 증거: `VIDEO-np-day3*.json/png` · `VIDEO-np-day4.json` · `VIDEO-def-day3.json` · `VIDEO-def-day2.json` · 비교 그림 `VIDEO-np-day2-open.png` 대 `VIDEO-np-day3-played.png` · 번들 확인 `codecheck.json`.
- 한계: 헤드리스 Chrome 156 에서만 봤음. 사람이 쓰는 창 있는 브라우저에서는 확인하지 않았음.
- 제안: 시작 전 영상에 `seekTo` 와 `pauseVideo` 를 연달아 부르지 않음. 시작 위치는 `cueVideoById({ videoId, startSeconds })` 나 `playerVars.start` 로 줌.

## 먼저 알릴 것

1. 이 회차는 전용 런처 없이 서브에이전트로 돌았음. 쓰기는 이 폴더와 `/private/tmp/_b6-chrome-*`(삭제함)뿐임. 원장(테스트·작업) 갱신과 결함 등록은 하지 않았음 — 회차 폴더 밖 쓰기 금지 지시 때문임. 결함 D1·D2 는 이 파일에만 있음.
2. 공유 판정: :3000(pid 98345) · :8002(pid 49282, 01:58:54 KST 기동, `VOICE_ADAPTER=nova`, DSN DB 이름 `ohmyenglish_course_paid` 를 프로세스 환경으로 확인)는 남의 것이라 재기동·종료하지 않았음.
3. 지시의 전제와 다른 점이 둘 있음. ⑴ `--use-file-for-fake-audio-capture` 만으로는 파일이 읽히지 않음. Chrome 이 `Failed to read … Try disabling the sandbox` 를 냈고 입력은 무음이었음. `--disable-features=AudioServiceSandbox` 를 더해 해결했음(`chrome-stderr-probe4.log` 대 `ACPROBE-beep4b-*.json`). ⑵ `TASK-288` 본문은 격리 DB 를 `ohmyenglish_worker` 로 적었으나 실제는 `ohmyenglish_course_paid` 임.
4. 첫 실제 시도는 POST 없이 끝났음. 화면에는 「판정을 쓸 수 없어요」가 나왔고, 원인은 확정하지 못했음. 그 직전 사전 실행의 about:blank 이동 뒤 수집기가 다시 붙으면서 관측 스크립트가 빠진 상태였음. Chrome 을 새로 띄운 뒤에는 같은 절차가 정상이었음. 이 1건은 앱 결함으로 올리지 않았음.
5. 입력 파일은 장치를 열 때마다 처음부터 재생됨(표지음 두 번 모두 열린 뒤 87ms). 녹음 창은 열린 뒤 약 2.5초에 시작해 3.0초 동안 열렸음. 그래서 문장을 2.65초에 놓았음. 두 실제 시도에서 말소리는 창 시작 뒤 231~1958ms 에 들어갔음.

## 관찰 (결함으로 올리지 않음)

- 5초 저장 POST 마다 5ms 뒤 `net::ERR_ABORTED`(Fetch) 가 한 건씩 찍힘. 같은 시각 백엔드는 204 를 냈고 DB `updated_at` 도 올랐음. 저장은 도착하므로 원인을 특정하지 않고 남김.
- D2 상태에서도 5초 저장은 120(또는 직전 저장값)을 유지했음. 위치가 0 으로 덮이지는 않았음.

## 만든 데이터 (격리 DB · 지우지 않음)

- `course_attempts` 2행(`u001-s4`, 빈 전사).
- `course_day_progress` 5행: Day 1·2·5 는 열고 재생한 결과로 생김. Day 3·4 는 앱 API 로 놓음(`api-writes.log`) 뒤 재생으로 갱신됨. 끝 값은 `db-end.json`.
- 입력 음성: `audio/in-a.wav` · `in-b.wav` · `in-c.wav`(c 는 미사용) · 표지음 `probe-beep*.wav`. 앱이 보낸 PCM 사본은 `evidence/sent-b-*.wav`.
- Chrome·수집기는 `TaskStop` 으로 종료함. :9334 는 비어 있음.
