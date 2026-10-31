# 회차 2026-11-01-b3 — 문법 코스 통합 테스트 (`TASK-287`, HEAD `f574612`)

## 판정표

| # | 시나리오 | 판정 | 근거 요약 |
|---|---|---|---|
| R1 | b2 S1 목록 · 시작 화면에서 이동 | PASS | Day 6개 · 단원 범위 일치 · 「1회차」 · 칸 112개 · 「이어서 학습 ▶」 1개 · 「문법 코스」 → `/course` 52ms (`S1.json`) |
| R2 | b2 S2 첫 화면 · 모드 유지 | PASS | 문장이 API `units[0].sentences[0].text` 와 같음 · 「수동」 뒤 새로 고침에도 `aria-pressed=true` (`S2.json`) |
| R3 | b2 S3 수동 모드 단계 | PASS (Chrome 가짜 장치) | `listen 102 → repeat 3699 → judge 8294 → done 8298` · done 에서 3.5초 더 머묾 · 503 안내 (`S3.json`) |
| R4 | b2 S4 자동 모드 진행·시간 | PASS (Chrome 가짜 장치) | 문장 1→2→3 스스로 넘어감 · repeat = listen + 995~1001ms · done → 다음 listen 1502~1507ms (`S4.json`) |
| R5 | b2 S5 이전·다음 | PASS | 첫 문장 「← 이전」 disabled · 다음 5번 → Unit 23 문장 1 · 이전 1번 → Unit 22 문장 5 (`S5.json`) |
| R6 | b2 S6 진도 저장 후 새로 고침 | PASS | API `unit 22 · sentence_index 4` · 새로 고침 뒤 「문장 5 / 5」 (`S6.json`) |
| R7 | b2 S9 콘솔 오류 · 플레이어 준비 전 | PASS | 로드 77ms 뒤 「시작」, 12초 동안 예외 0건 (`S9.json`) |
| R8 | b2 S10 떠난 뒤 마이크 정리 | PASS (Chrome 가짜 장치) | 획득 뒤 떠남 · 직후 떠남 2변형 모두 떠난 뒤 `live` 트랙 0개 (`S10-wait.json` · `S10-now.json`) |
| N1 | 「느리게」 | PASS | 같은 문장(11낱말) listen: 보통 3573·3577ms, 느리게 4282·4284ms(1.20배). repeat 창도 4578 → 5286ms (`SLOW-2.json`) |
| N2 | 「다시」 수동 | PASS | done 뒤 「다시」 → 같은 「문장 5 / 5」 에서 listen → repeat → judge → done, 번호 그대로 (`RETRY_MANUAL.json`) |
| N3 | 자동 모드 「다시」·「이전」 | PASS | repeat 중 「다시」 → 14ms 뒤 같은 문장 listen, 흐름이 다음 문장까지 이어짐. 다음 문장 repeat 중 「이전」 → 앞 문장 listen 부터 다시, 다시 다음 문장으로 넘어감 (`AUTO_RETRY.json`) |
| N4a | 「내가 말한 문장」 — 실제 경로(stub) | PASS (판별 범위 좁음) | stub 은 503(`transcriber_available` 이 `nova` 만 참). 표시 없음 · 안내 「지금은 따라 하기 판정을 쓸 수 없어요…」 · 「따라 함 0회」 (`SPOKEN_REAL.json`) |
| N4b | 「내가 말한 문장」 — 밑줄·취소선 렌더링 | PASS (합성 응답) | 판정 응답만 CDP Fetch 로 바꿔 끼움. 본문은 백엔드 `compare_readback` 이 만든 값. `missing`→`line-through` · `different`→`underline` · 「따라 함 1회」. 실제 DB 쓰기 0건 (`SPOKEN_SYNTH.json` · `SPOKEN_SYNTH-body.json`) |
| N5a | 영상 배치 | PASS | 플레이어가 카드 위(top 58 vs 275) · 300×169 (`LAYOUT-3.json`) |
| N5b | 영상 위치 저장 — 재생 중 5초 저장 | PASS | 재생 1.4→23.5초 동안 저장값 1.69 · 6.69 · 11.69 · 16.69 · 21.69 (`VIDEO-day3.json`) |
| N5c | 영상 위치 — 떠난 뒤 다시 열면 그 자리부터 | **FAIL — D3** | 「← 학습 목록」으로 떠나면 저장값이 0으로 덮어써짐(2/2). 새로 고침 경로는 통과 |
| N5d | 연습 ↔ 영상 상호 정지 | PASS | 영상 재생 중 「시작」 → 영상 `paused` · 연습 중 영상 재생 → 단계 `idle` (`VIDEO-day3.json`) |
| N6a | 다른 Day 를 처음부터 열기(순서 잠금 없음) | PASS | 진행 중이 Day 4 일 때 Day 1 「시작하기」 → Unit 1 「문장 1 / 5」 |
| N6b | 진행 중 Day 의 멈춘 자리 · 「이어서 학습」 | PASS | 「Unit 27 · 문장 2 · 13:20」 · 강조 테두리 · 막대 21.3% → Unit 27 「문장 2 / 5」 (`LIST-day2-unit27s2.json`) |
| N6c | 단원 첫 문장에 멈춘 Day 의 상태 문구 | **FAIL — D6** | Unit 2 · 문장 1 에 멈춘 Day 가 「아직 안 함」 으로 보이고, 「이어서 학습 ▶」은 Unit 2 문장 1 을 엶(2/2) |
| N7a | 이력 — 실제 데이터와 대조 | PASS (빈 상태만) | API·DOM 칸 112개 모두 0 · 마지막 칸 `2026-11-01`(KST) · 「아직 따라 한 문장이 없어요.」 · DB attempts 0 (`HEAT_REAL.json`) |
| N7b | 이력 — 칸 색 4단계 · 표 | PASS (합성 응답) | 1·9 → 1단계, 10·29 → 2단계, 30·100 → 3단계, 범례 4색과 일치. 표 「10/31 · 2 · 22–27 · 12문장 · 18회」 등 3행 (`HEAT_SYNTH.json`) |
| N7c | 이력 — 실제 시도 집계가 DB 와 맞는가 | **차단** | stub 은 시도를 기록하지 않음(503). 직접 DB 삽입은 지시로 금지됨 |
| N8 | D1 판별 — 완료 날짜가 KST 인가 | PASS — D1 고쳐짐 확인 | 자동 모드 UI 로 Day 6 마지막 문장을 마침. `last_completed_at 2026-10-31T15:28:17Z`(UTC 날짜 10/31) → `last_completed_date 2026-11-01` · 목록 「완료 · 11/1」 · 막대 100% (`DAY_END-6.json` · `D1-list.json`) |
| N9 | 수동 모드에서 Day 마지막 문장을 마침 | **FAIL — D4** | `completed_count` 0 그대로 · 「다음 문장 →」 disabled · 목록 「Unit 100 · 문장 5」 (2/2) |
| N10 | 6개 Day 완료 → 2회차 · Day 1 부터 | **FAIL — D5** | 「2회차」 표시는 맞음. 「이어서 학습 ▶」이 Day 1 이 아니라 마지막으로 완료한 Day 에 붙음(Day 5 · 재현 순서 1→6 에서는 Day 6) |
| N11 | 콘솔 오류 0건 | PASS | 예외 0 · 앱 `console.error` 0. 오류 수준 로그 18건은 모두 stub 503 판정 요청의 브라우저 리소스 로그. 경고 1건은 YouTube `www-widgetapi` (`console-summary.txt`) |

- 회귀(b2 대비): 여전히 통과 8건(R1~R8) · 새로 실패 0건 · 고쳐짐 1건(D1, 이번에 판별 성립).
- 새 시나리오에서 실패 4건: D3 · D4 · D5 · D6. 차단 1건: N7c.

## 먼저 알릴 것

1. **호출자의 환경 전제가 이 회차에서 성립하지 않았음.**
   - 전제는 「헤드리스 Chrome 의 오디오 getUserMedia 가 끝나지 않음」이었음.
   - Chrome 156.0.8078.74 `--headless=new --use-fake-device-for-media-stream` 에서는 `live:Fake Default Audio Input` 으로 즉시 끝남 (`audio-env-probe.json`).
   - 그래서 b2 의 `fakeMic()` 대체를 쓰지 않았음. 판정의 「Chrome 가짜 장치」 표시는 Chrome 내장 가짜 입력 장치를 뜻함. 물리 마이크 경로는 여전히 확인하지 않았음.
   - 이 장치는 프레임을 보냈음. 매 시도마다 판정 POST 가 실제로 나갔고 503 을 받았음.
2. **회차 중 다른 주체가 소스를 고쳤음 — 측정 대상은 바뀌지 않았음.**
   - 바뀐 파일 3개(미커밋 `M`): `app/backend/app/models/course.py`(00:26:36 KST) · `app/backend/app/services/course.py`(00:26:48) · `tests/integration/test_course_api.py`(00:26:04). 착수 시점 `git status` 에는 없었음. 내 쓰기가 아님.
   - 실행 중인 백엔드(pid 28110)는 2026-10-26 08:47:43 에 `--reload` 없이 떴음. `9c67008..f574612` 사이 `app/` 변경은 0건임.
   - 그래서 회차 전체(00:22~00:37 KST)의 측정은 HEAD 코드에 대한 것임.
   - 그 미커밋 변경은 D5(회차 시작 Day)를 겨냥한 것으로 보임(`_touched_since_completion`). 실행 중인 서버에 올라가 있지 않아 이 회차는 그것을 시험하지 않았음.
3. 전용 런처(`~/.claude/test-agent/run.sh`) 없이 서브에이전트로 돌았음. OS 샌드박스의 쓰기 경계가 없었음.
   - 쓰기는 이 회차 폴더와 `/private/tmp` 뿐이었음. DB 쓰기는 앱 API 와 끝의 정리 삭제뿐이었음.
4. 테스트 원장(`tests/agent/backlog/`)과 작업 원장은 갱신하지 않았음. 호출자가 회차 폴더 밖 쓰기와 커밋을 금지했기 때문임.
   - 결함 4건의 작업 원장 등록과 시나리오 원장 반영은 남은 일임.

## 환경

- HEAD: 시작·끝 모두 `f574612`. 브랜치 `design/first-vertical-slice`
- 측정 시각: 2026-10-31 15:24:12 ~ 15:36:41 UTC (KST 2026-11-01 00:24 ~ 00:36). KST 00시대라 D1 판별이 성립함
- 스택: 프런트 `:3000`(pid 98345, `next-server v16.3.2`) · 백엔드 `:8002`(pid 28110, `VOICE_ADAPTER=stub`). 둘 다 재기동·종료하지 않았음
- `users.timezone` = `Asia/Seoul`. 읽기만 했음
- 브라우저: Chrome 156.0.8078.74 `--headless=new` · CDP `:9333` · 프로필 `/private/tmp/_b3-chrome`(종료 뒤 삭제) · 창 1280×1000
- 음성 합성: `speechSynthesis` 끝 신호가 왔음. 실측이 어림값(낱말 × 0.4초 ÷ rate)보다 짧았음. 예: 11낱말 느리게 어림 6286ms → 실측 4282ms
- YouTube 임베드: 재생됨. 광고 없음(`ad-showing` false)
- 드라이버: b2 의 `cdp.mjs` · `collector.mjs` · `drive.mjs` 를 복사함. `drive.mjs` 에 시나리오를 더했음
  - 더한 시나리오: SLOW · RETRY_MANUAL · AUTO_RETRY · SPOKEN_* · LAYOUT · RESUME_LIST · STEP_NEXT · DAY_END · HEAT_*
  - 영상 전용 드라이버: `video.mjs` · `video2.mjs`. YouTube iframe 대상에 CDP 로 붙어 `video.currentTime` 을 읽음
  - 재생 조작: 플레이어 중앙에 `Input.dispatchMouseEvent` 클릭을 보냄

## 결함

### D3 — 학습 화면에서 「← 학습 목록」으로 떠나면 영상 위치가 0으로 저장됨 · HIGH

- 재현(최소):
  1) `/course/3` 를 엶 2) 영상을 눌러 25초쯤 재생함 3) 「← 학습 목록」을 누름 4) `GET /api/course/days/3` 의 `progress.position_sec` 를 봄
- 기대: 떠나기 직전 위치(약 30초)가 저장되고, 다시 열면 그 자리부터 재생됨(설계서 §1 · §4 「화면을 떠날 때 저장함」 · 스토리보드 화면 A)
- 실제:
  - 1차(`VIDEO-day3.json`): 떠나기 직전 영상 30.0초 · 저장값 25.18 → 떠난 뒤 `position_sec 0`. 다시 연 영상은 0초 · 목록 「아직 안 함」 · 막대 0%
  - 2차(`VIDEO2-day4.json`): 저장 위치 10.95 에서 열어 14.4초까지 들음 · 저장값 14.37 → 떠난 뒤 `position_sec 0`
- 경계: 새로 고침(pagehide)은 통과함. 저장값 10.95 가 유지됐고, 다시 연 영상이 그 자리부터 재생됐음(`VIDEO2-day4.json` A).
  - 그래서 앱 안 이동(언마운트 경로)만 실패함. 2차에서 시작 위치가 10.95 인데 0 이 저장됨. 따라서 「시작 위치로 되돌림」도 아님
- 영향: 학습자가 목록으로 돌아올 때마다 그 Day 의 영상 진도가 사라짐. 목록의 진행 막대와 상태 문구도 0 으로 돌아감
- 원인 미특정. 코드 읽기로 세운 가설: 언마운트 때 `[day]/page.tsx` 의 정리 `save()` 가 도는 시점에 `CoursePlayer` 의 플레이어가 이미 `destroy()` 됐거나 0 을 돌려줌. 계측은 하지 않았음
- 제안: 언마운트 저장은 마지막으로 읽은 재생 위치(5초 타이머가 읽은 값)를 쓰게 함. 그리고 `currentTime()` 이 0 을 돌려주는 경우를 「위치 모름」으로 다루는 방안을 검토함

### D4 — 수동 모드에서는 Day 의 마지막 문장을 마쳐도 Day 가 완료되지 않음 · HIGH

- 재현(최소):
  1) `POST /api/course/days/5/progress {"position_sec":0,"unit":100,"sentence_index":4}`
  2) `/course/5` 에서 「수동」을 고르고 「시작」을 누름 3) done 뒤 4초 기다림 4) `GET /api/course/days/5` 를 봄
- 기대: 「Day 완료는 영상이 끝까지 재생됐거나 마지막 문장을 마쳤을 때임」(설계서 §4). `completed_count` 1 · 처음으로 되감김
- 실제: 2/2 모두 `completed_count 0` · `unit 100 · sentence_index 4` 그대로 · 「다음 문장 →」 disabled
  - 목록은 「Unit 100 · 문장 5 · 0:00」 (`DAY_END-5-manual-run1.json` · `DAY_END-5.json` · `DAY_END-5-list.json`)
  - 자동 모드의 같은 절차(Day 6)는 완료됨(`DAY_END-6.json`)
- 영향: 수동 모드만 쓰는 학습자는 영상을 끝까지 틀지 않는 한 어느 Day 도 완료할 수 없음. 따라서 2회차로 넘어갈 수 없음
- 근거(코드 읽기): `run()` 의 완료 처리(`save(true)`)는 `readMode() !== "auto"` 일 때 그 앞에서 돌아감. 마지막 문장에서는 「다음 문장 →」이 `nextPosition` = `null` 로 비활성임
- 제안: 수동 모드 마지막 문장의 done 에서 완료를 기록함. 또는 마지막 문장에서 「다음 문장 →」 자리에 완료 동작을 둠. 어느 쪽인지는 사용자 결정 대상임

### D5 — 6편을 모두 끝내 새 회차가 되면 「이어서 학습」이 Day 1 이 아니라 마지막으로 완료한 Day 에 붙음 · MEDIUM

- 재현(최소): Day 1~6 을 순서대로 `POST /api/course/days/{d}/progress {"position_sec":0,"unit":<첫 단원>,"sentence_index":0,"completed":true}` → `/course` 를 봄
- 기대: 「Day 6을 마치면 2회차가 Day 1부터 시작됨」(스토리보드 화면 B 「내가 정한 기준」)
- 실제:
  - 1차(Day 6 은 UI 로, 1~5 는 API 로 완료): `cycle 2 · current_day 5`. Day 5 에 「이어서 학습 ▶」 · 강조
  - 2차(1→6 순서): `cycle 3 · current_day 6`. Day 6 에 「이어서 학습 ▶」
  - 회차 표시(「2회차」·「3회차」)는 맞음
  - 근거 파일: `CYCLE-api.txt` · `CYCLE-list.json` · `CYCLE-repro-api.txt` · `CYCLE-repro-list.json` · `api-writes.log`
- 근거(코드 읽기): `load_overview` 가 「이번 회차 미완료 Day 중 `updated_at` 최댓값」을 고름. 완료 쓰기도 `updated_at` 을 갱신하므로 방금 끝낸 Day 가 뽑힘
- 참고: 회차 중 작업 트리에 이 지점을 고치는 미커밋 변경이 생겼음(「먼저 알릴 것」 2). 실행 중인 서버에 올라가 있지 않아 이 회차는 판정하지 않았음. 서버를 다시 띄운 뒤 이 재현 절차로 확인할 것

### D6 — 단원의 첫 문장에 멈춘 진행 중 Day 가 목록에서 「아직 안 함」으로 보임 · MEDIUM

- 재현(최소):
  1) `/course/1` 수동 모드에서 「다음 문장 →」을 5번 눌러 Unit 2 문장 1로 감. 영상은 틀지 않음
  2) 6초 기다림(저장) 3) `/course` 를 봄
- 기대: 「진행 중인 Day에는 멈춘 단원과 문장 번호를 보여 주고…」(스토리보드 화면 B). 「Unit 2 · 문장 1」
- 실제: 상태 「아직 안 함」. 같은 행이 강조되고 「이어서 학습 ▶」을 보이며, 누르면 Unit 2 「문장 1 / 5」을 엶
  - 2차: API 로 `unit 30 · sentence_index 0 · position 0` → 「아직 안 함」
  - 근거 파일: `STEP_NEXT-1.json` · `RESUME_LIST-1.json` · `LIST-day2-unit30s1.json`
- 근거(코드 읽기): `app/course/page.tsx` `DayRow` 는 `position_sec > 0 || sentence_index > 0` 일 때만 진도 문구를 씀. 단원은 보지 않음
- 영향: D3 와 겹치면 더 자주 남. 목록으로 떠나면 위치가 0 이 되므로, 단원 첫 문장에 멈춘 Day 는 모두 「아직 안 함」이 됨
- 제안: 진도 행이 있고 `unit` 이 그 Day 의 첫 단원이 아니어도 진도 문구를 씀

## 차단

- N7c 실제 시도 집계(히트맵 칸 값 · 표의 단원 범위·문장 수·횟수가 DB 와 맞는가)
  - 이유: `VOICE_ADAPTER=stub` 이면 `POST …/attempts` 가 전사 앞에서 503 을 내 `course_attempts` 에 쓰지 않음(`api/course.py`)
  - 앱 API 로 시도 행을 만들 길이 없음. 직접 삽입은 지시로 금지됨
  - 화면 렌더링(N7b)은 합성 응답으로, 빈 상태 대조(N7a)는 실제로 확인했음. 서버 쪽 SQL 집계는 이 회차가 확인하지 않았음
- N4 의 실제 전사 경로도 같은 이유로 합성 응답(N4b)으로만 확인했음

## 관찰 (결함으로 올리지 않음)

- 「내가 말한 문장」의 표시 방식이 스토리보드 그림과 다름. 판단은 사용자 결정 대상임
  - 스토리보드: 학습자가 말한 문장 한 줄 안에서 학습자의 낱말에 밑줄(`I <u>might</u> … <s>on</s>`)을 침
  - 구현: 전사문을 무표시로 보이고, 그 아래 «원문» 낱말에 판정을 표시함(다르게 말한 원문 낱말 `Tuesday.` 에 밑줄)
  - 조문 「기존 쉐도잉 판정과 같은 방식임」과는 맞음(`app/ShadowingPanel.tsx` `wordStyle` 도 원문 낱말 기준)
- 완료 날짜 표기가 「11/1」임(0 채움 없음). 스토리보드 예시(10/25)로는 0 채움 여부를 가를 수 없음
- 다시 연 영상이 저장 위치에서 스스로 재생을 시작함(`VIDEO2-day4.json` A_reopenV: state 1). `seekTo` 의 동작으로 보임. 설계서에 자동 재생 여부가 없음
- 새로 고침 직전 영상은 12.1초 이상이었으나 저장값은 직전 5초 저장의 10.95 였음. pagehide 저장이 반영되지 않았을 수 있음. 손실은 5초 안이라 설계서 §4 범위 안임
- 학습 화면을 열고 떠나기만 해도 언마운트 저장이 `updated_at` 을 갱신함. 그래서 그 Day 가 「진행 중」이 됨. 예: Day 4 를 열었다 닫자 「아직 안 함」 행에 「이어서 학습 ▶」이 붙음. 이 조회의 파일은 다음 조회가 덮어써 드라이버 출력으로만 남음(`apiCurrentDay 4`)
- 학습 화면 머리는 「Day N · Unit a–b」 임. 스토리보드 그림은 「Day 2 · 1회차」와 「어제 멈춘 자리 62:34」를 보임. 조문 문장에는 없는 그림 요소임
- 스토리보드 파일의 `<title>` 은 「스토리보드 v2」, 본문 태그는 「스토리보드 v3」 임
- 「느리게」 rate 0.7 의 실측 배율은 1.20배임. 음성 엔진(Samantha 계열 en-US) 특성으로 보임

## 만든 데이터와 정리

- 앱 API 쓰기: `evidence/api-writes.log`(진도 위치 지정 6건 · 완료 11건). 나머지는 화면 조작의 저장임
- `course_attempts` 는 회차 내내 0건이었음. 판정 요청 18건은 모두 503 이었고, 합성 응답 1건은 서버에 닿지 않았음
- 정리(2026-10-31 15:36:41 UTC): 회차 시작 이후의 `course_day_progress` 6행을 삭제함(`cleanup.py`). 회차 이전 행은 0건이었음
  - 삭제 뒤 조회: `attempts 0` · `progress_rows 0` · API `cycle 1 · current_day 1 · progress 전부 null` (`evidence/db-cleanup.txt`)
  - 첫 실행은 인자 형 오류로 트랜잭션이 롤백돼 아무것도 지우지 않았음. 고친 뒤 다시 돌렸음
- `omy.course.mode` 는 회차 Chrome 프로필 안에만 있었고, 프로필을 지웠음
- Chrome(`TaskStop`)과 수집기를 종료함. 종료 뒤 `:9333` 비어 있음 · CDP 연결 불가 · `/private/tmp/_b3-*` 삭제

## 증거 색인 (`evidence/`)

- 시나리오별 DOM·API 값: `S1.json`~`S10-*.json` · `SLOW-2.json` · `RETRY_MANUAL.json` · `AUTO_RETRY.json` · `SPOKEN_*.json` · `LAYOUT-3.json`
  - 영상: `VIDEO-day3.json` · `VIDEO2-day4.json`
  - 목록: `RESUME_LIST-*.json` · `LIST-*.json` · `STEP_NEXT-1.json`
  - Day 끝: `DAY_END-*.json` · `D1-list.json`
  - 이력: `HEAT_*.json`
  - 2회차: `CYCLE-*`
- 콘솔·네트워크 전체: `console-all.jsonl` · 집계 `console-summary.txt`
- DB: `db-start.txt` · `db-end-before-cleanup.txt` · `db-cleanup.txt` · API 쓰기 기록 `api-writes.log`
- 환경: `audio-env-probe.json` · `chrome-stderr.log`
- 스크린샷(보조): `S1-*.png` · `S2-*.png` · `S3-done.png` · `S4-third-listen.png` · `S5-*.png` · `S6-after-reload.png` · `S9-after.png` · `SPOKEN_SYNTH.png` · `LAYOUT-day3.png` · `RESUME_LIST-*.png` · `DAY_END-*.png` · `HEAT_SYNTH.png`
