# 회차 2026-10-26-b2 — 문법 코스 화면 (`TASK-286`, 커밋 `9c67008`)

## 판정표

| # | 시나리오 | 판정 | 근거 요약 |
|---|---|---|---|
| S1 | /course 목록 · 시작 화면에서 이동 | PASS | Day 6개 · 단원 범위 6개 일치 · 「1회차」 1개 · `[data-attempts]` 112칸 · 「이어서 학습 ▶」 1개(`/course/1`) · 「문법 코스」 클릭 → `/course` |
| S2 | /course/2 첫 화면 · 모드 유지 | PASS | `Unit 22 · 현재 · 과거 시제 정리` · 「문장 1 / 5」 · 문장이 API `units[0].sentences[0].text` 와 같음 · 「수동」 뒤 새로 고침에도 `aria-pressed=true`, `omy.course.mode=manual` |
| S3 | 수동 모드 단계 | PASS (합성 마이크) | `listen → repeat → judge → done` 관측 · done 에서 3.5초 더 기다려도 문장 번호 그대로 · 안내 문구 일치 |
| S4 | 자동 모드 진행·시간 | PASS (합성 마이크) | 스스로 「문장 2 / 5」→「문장 3 / 5」, 단원 경계(U22 s5 → U23 s1)도 넘음 · repeat = 읽은 시간 + 1.00초 · done 뒤 1.51초 |
| S5 | 이전·다음 이동 | PASS | 첫 문장에서 「← 이전」 disabled · 「다음 문장 →」 5번 → `Unit 23` 「문장 1 / 5」 · 「← 이전」 1번 → `Unit 22` 「문장 5 / 5」 |
| S6 | 진도 저장 후 새로 고침 | PASS | 6.5초 뒤 API `progress` = `unit 22 · sentence_index 4` · 새로 고침 뒤 `Unit 22` 「문장 5 / 5」 |
| S8 | Day 6 완료 표시 | PASS (D1 판별력 없음) | 「완료 · 10/26」 · 막대 `100%`. 단, POST 시각이 00:01 UTC 라 UTC·KST 날짜가 둘 다 10/26 이었음 — 아래 「D1」 |
| S9 | 콘솔 오류 · D2 재현 | PASS | 앱 예외 0건 · `getCurrentTime` 오류 0건. 임베드를 막아 플레이어를 준비 전 상태로 묶은 판별 절차에서도 0건 |
| S10 | 떠난 뒤 마이크 정리 | PASS (합성 마이크) | 3변형(획득 뒤 떠남 · 직후 떠남 · 획득 1.5초 지연 중 떠남) 모두 떠난 뒤 `live` 트랙 0개 |

새로 실패: 없음. 고쳐짐: D2(판별 절차로 확인). D1 은 고쳐짐 미확인(판별 불가 시각). 차단: 없음.
단, 「합성 마이크」 표시 3건은 실제 장치 경로가 아님 — 「먼저 알릴 것」 1.

## 먼저 알릴 것

1. 이 실행 환경의 헤드리스 Chrome 은 오디오 `getUserMedia` 가 끝나지 않음 — 앱 결함 아님.
   - 시도 4가지 모두 실패함. `evidence/audio-env-blocked.txt` 가 원문임.
     지시 플래그의 Chrome 155 · Playwright `chrome-headless-shell` 151 · 오디오 파일 지정 · 오디오 서비스 프로세스 내 구동.
   - 같은 탭에서 `{video:true}` 는 즉시 `live` 임. 권한은 `granted` 임. 가짜 입력 장치 3개가 보임.
   - AudioContext 는 `running` 인데 `currentTime` 이 1.5초 동안 0 에 머문 적이 있음.
     콘솔에 「The AudioContext encountered an error from the audio device」 가 6건 남음.
   - 그래서 S3·S4·S10 은 **브라우저의 `getUserMedia` 만** Web Audio 합성 스트림으로 바꿔 끼우고 돌렸음.
     앱 코드는 그대로임. 대체 코드는 `drive.mjs` 의 `fakeMic()` 임.
     실제 마이크 장치 경로(권한 대화·장치 오류)는 이 회차가 확인하지 않았음.
   - 합성 스트림의 프레임 도착이 불안정했음. 프레임이 0인 회차(S3 1~3차)에서는 앱이 판정 요청 없이
     `judge` 를 DOM 에 커밋하지 않은 채 `done` 으로 감(같은 틱). 프레임이 온 회차에서만 `judge` 가 보였음.
2. S1 1차 실패는 드라이버 결함이었음. 하이드레이션 전에 눌렀고, 핸들러가 붙은 뒤에는 54ms 만에 이동함.
   이후 클릭 도우미는 `__reactProps` 부착을 기다림.
3. 단계 관측을 20ms 폴링에서 MutationObserver 로 바꿨음. 503 이 수 ms 만에 와서 `judge` 가 2~6ms 만
   존재했고, 폴링(S4 1차)은 그것을 3번 다 놓쳤음 — 관측 수단의 한계였음, 앱 결함 아님.
4. 테스트 원장(`tests/agent/backlog/`)은 갱신하지 않았음. 호출자가 회차 폴더 밖 쓰기와 커밋을 금지함.
   시나리오 태스크(안: `TS-37`)와 이 판정의 원장 반영은 남은 일임.

## 환경

- HEAD: 회차 시작·끝 모두 `9c67008`. 회차 중 움직이지 않음
- 공유: `:3000`·`:8002` 는 호출자가 띄운 것이고 재기동·종료하지 않았음.
  회차 중 다른 주체가 작업 원장 `backlog/tasks/task-286 - ...md` 를 고쳤음(`git status` ` M`). 내 쓰기 아님
- 측정 시각: 2026-10-25 23:49 ~ 2026-10-26 00:08 UTC (KST 10-26 08:49~09:08)
- 브라우저: Google Chrome 155.0.8059.86 `--headless=new` · CDP `:9333` · 프로필은 회차 폴더 아래(종료 뒤 삭제)
- 드라이버: node 24.19.0 내장 WebSocket. `collector.mjs`(상시 콘솔·네트워크 수집) · `drive.mjs`(시나리오) ·
  일회성 진단 `probe.mjs` · `ev.mjs` · `gum-probe.mjs` · `reload-probe.mjs` · `yt-probe.mjs` · `d2-probe.mjs`
- 읽기 전용 DB 조회: `dbcount.py`(b1 판 복사, `default_transaction_read_only = on`)
- YouTube 임베드: 떴음. iframe 생성 약 160ms · `getCurrentTime` 보유 약 370ms(3회, `evidence/yt-ready-probe.json`)
- `speechSynthesis`: 음성 199개. 끝 신호가 왔음 — 어림(낱말 × 0.4초)·상한(× 3) 경로는 쓰이지 않았음.
  근거: 듣기 시간이 매번 어림값보다 짧고(예: u022-s5 11낱말 어림 4.4초 → 실측 3.60초), repeat 표시가 실측 + 1초였음

## 결함

없음 — 이 회차가 새로 등록할 결함은 없음.

### D1 (b1) — 고쳐짐 미확인

- 이 회차의 Day 6 완료 POST 는 2026-10-26 00:01:06 UTC(09:01 KST)였음. UTC 날짜도 10/26 이라
  옛 동작(UTC 날짜)과 고친 동작(KST 날짜)이 같은 값을 냄. 「완료 · 10/26」 은 D1 을 가려내지 못함.
- API 는 `last_completed_date: "2026-10-26"` 을 돌려주고, 화면 코드(`app/course/page.tsx` `DayRow`)는 그 필드를 씀.
  이것은 코드 읽기이지 판별 측정이 아님.
- 판별 재현 절차(다음 회차): KST 00:00~09:00 사이에 같은 POST → `/course` Day 6 이 KST 날짜인지 봄.
  또는 승인을 받고 `users.timezone` 을 바꿔 시험함(공유 상태라 이 회차는 바꾸지 않았음).

### D2 (b1) — 고쳐짐 (판별 절차로 확인)

- 일반 조건에서는 플레이어가 370ms 에 준비돼 첫 5초 저장보다 이름 — 옛 코드도 오류를 안 냈을 조건임.
- 판별 절차(`d2-probe.mjs`, `evidence/S9-d2-blocked-embed.json`):
  1) 브라우저 수준 `Fetch` 로 `*youtube.com/embed/*` 를 실패시킴(1건) — IFrame API 는 있고 플레이어는 준비 안 됨
  2) `/course/2` 로드 83ms 뒤 「시작」 3) 12초 대기(저장 타이머 2회 이상, `00:07:04`·`00:07:09` 저장 요청 확인)
  - 12초 끝에도 플레이어에 `getCurrentTime` 없음 · 콘솔 오류·예외 0건
- 관측 수단 검증: 같은 수집기로 의도한 `TypeError: o.getCurrentTime is not a function` 1건을 잡아 보였음
- 참고: 페이지 세션의 `Network.setBlockedURLs` 는 교차 출처 iframe 문서를 막지 못했음(1차 시도, 플레이어 준비됨)

### 관찰 (결함 아님)

- 진도 저장 fetch 마다 Chrome 이 `net::ERR_ABORTED` 를 붙임(182건). 응답은 매번 204 이고 서버에 반영됨 —
  본문을 읽지 않은 204 에 대한 표시로 봄
- 자동 모드에서 503 안내가 다음 문장의 듣기 동안에도 남음. 설계서 §4 「보인 채 흐름을 이어 감」과 맞음
- Day 2 의 진행 막대는 문장 진도(Unit 22 · 문장 5)와 무관하게 0% 임. 막대는 `position_sec / duration_sec` 이고
  영상을 재생하지 않아 0 임. 설계서에 막대의 기준이 없어 결함으로 올리지 않음
- YouTube `postMessage` 경고 123건은 모두 내가 임베드를 막은 창(00:06:59~00:07:30)의 것임(수신 origin `null`)

## 측정 시간 (MutationObserver 기록, ms)

| 회차 | 문장 | 낱말(어림 ms) | listen | repeat | judge | done → 다음 listen |
|---|---|---|---|---|---|---|
| S4 2차 | u022-s5 | 11 (4400) | 3595 | 4600 | 2 | 1514 |
| S4 2차 | u023-s1 | 6 (2400) | 2262 | 3258 | 2 | 1506 |
| S4 2차 | u023-s2 | 8 (3200) | 1950 | 2946 | 2 | 1511 |
| S4 2차 | u023-s3 | 6 (2400) | 2028 | 3024 | 6 | (수동으로 바꿔 멈춤) |
| S4 1차(폴링) | u022-s1 | 10 (4000) | 3062 | 4061 | 관측 못 함 | 1518 |
| S4 1차(폴링) | u022-s2 | 9 (3600) | 2940 | 3940 | 관측 못 함 | 1520 |
| S4 1차(폴링) | u022-s3 | 12 (4800) | 3140 | 4159 | 관측 못 함 | — |
| S3 4차(수동) | u023-s3 | 6 (2400) | 2002 | 3007 | 5 | done 유지 3.5초+ |

- repeat − listen = 995~1019ms. 기대(읽은 시간 + 1초)와 일치함
- done → 다음 listen = 1506~1520ms. 기대(약 1.5초)와 일치함
- 화면의 대기 표시(`② 따라 말하기 · N초`)는 repeat 실측과 맞음(예: 4.1초 표시 ↔ 4061ms)

## 만든 데이터

- `course_day_progress` 2행(회차 시작 0행):
  - `day 2` — `unit 23 · sentence_index 2 · position_sec 0 · completed_count 0` (화면 조작의 5초 저장이 만듦)
  - `day 6` — `unit 101 · sentence_index 0 · completed_count 1 · last_completed_at 2026-10-26 00:01:06.992839+00`
    (S8 의 `POST /api/course/days/6/progress {"completed":true}`)
- `course_attempts` 0행 그대로 — 판정 요청 11건은 모두 503(stub)
- `omy.course.mode` 는 회차 끝에 `auto` 로 되돌림(그 Chrome 프로필은 삭제함)
- 근거: `evidence/db-start.txt` · `evidence/db-end.txt`

## Chrome 종료 확인

- 회차 Chrome(`:9333`)·진단 Chrome 3개(`:9334`)·수집기를 모두 `TaskStop` 으로 종료함
- 종료 뒤 `lsof -ti:9333`·`:9334` 비어 있음 · `pgrep -fl 'chrome-profile|_b2-chrome|_b2-shell'` 0건 ·
  `curl :9333/json/version` 연결 불가
- 프로필 디렉터리(`chrome-profile/` 172MB · `/tmp/_b2-*`)와 `/tmp` 임시 파일을 지움

## 증거 색인 (`evidence/`)

- 시나리오별 DOM·API 값: `S1.json` ~ `S10-*.json` · `RESET_MODE.json` (덮어쓴 이전 차수는 `*-run*.json`)
- 콘솔·네트워크 전체: `console-all.jsonl` · 집계 `console-summary.txt`
- 환경 차단 원문: `audio-env-blocked.txt` · `chrome-stderr.log`
- 스크린샷(보조): `S1-course.png` · `S1-from-home.png` · `S2-*.png` · `S3-done.png` · `S4-third-listen.png` ·
  `S5-*.png` · `S6-after-reload.png` · `S8-course.png` · `S9-after.png`.
  `S1-error.png`·`S3-error.png` 는 드라이버 오류 차수의 것임
