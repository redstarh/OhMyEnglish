# 회차 2026-11-14-b18 — 화면 탭 결과 (`TASK-330`)

## 0. 먼저 알릴 것

- 이 탭은 화면 판정에서 결함을 찾지 못했음. 10장면 · 30단계 · 두 폭 모두 통과함. 1건은 데이터가 없어 관측하지 못했음(S6b · 불확실).
- b16 보고서의 결함 5건과 흐름 문제 15건을 하나씩 대조했음. 이 탭이 잰 범위에서는 모두 고쳐졌음. B-D1(창이 맨 위로 튐)은 이 탭이 재지 않았음(§5).
- 새 흐름·논리 관찰은 10건임(§6). 호출자가 지시한 「Best streak 이 Last week 꼬리표 아래에 놓임」도 여기 포함함(N1).
- 공유 인스턴스임. 버튼 탭(:9462)이 같은 앱·백엔드·격리 DB 를 함께 씀. 그래서 내 세션은 개수가 아니라 ID 로 가렸음(§1).
- 지시서 4항에 따라 작업 원장에 아무것도 등록하지 않았고 커밋하지 않았음. §6 의 관찰은 호출자가 사용자에게 진행 여부를 물어야 함.
- Nova 세션은 2개(1400·390 각 1개)로 상한 안임. 두 세션 모두 `completed` · 발화 0건임.

## 1. 환경

| 항목 | 값 |
|---|---|
| 앱 | `http://localhost:3000`(`next dev`) · 200 응답 확인 |
| 백엔드 | `:8002` · `/health` 200 · 격리 DB `ohmyenglish_course_paid` 에 쓰는 것을 확인함(내 세션 2개가 그 DB 에 생김) |
| 브라우저 | 호출자의 헤드리스 Chrome 157.0.8103.52 · CDP `127.0.0.1:9461` · `connectOverCDP` · 페이지만 열고 닫음 |
| 도구 | Playwright 1.58.2(`tests/agent/tools/node_modules`) |
| HEAD | 시작 `0428af4` · 끝 `0428af4`(회차 중 움직이지 않음) |
| 측정 시각 | 2026-11-14 12:24Z~12:31Z |
| dev DB | 시작 기준선(`../db-dev-start.json`)과 끝 값(`evidence/db-end.json`)의 7개 값이 같음 |
| 격리 DB 변화 | 세션 108→110 · 시도 14→16 · 분석 job 518→522 · LLM 호출 429→433 · 발화 643 그대로 |
| 진도 저장 | 홈 문장 연습을 열고 Start 를 눌러 격리 DB 의 진도·시도가 바뀌었음(지시서 6항). 판정 요청은 가로채지 않고 실제 백엔드로 보냈음 |

## 2. 장면 — b16 보드와 설계서 §3 을 대조해 다시 정함

- b16 보드의 「코스 목록 /course」·「Day 화면 /course/1」은 리다이렉트 한 장면으로 합쳤음.
- 「세션 실패(마이크 거부)」는 뺐음. b16 에서 시험 Chrome 의 가짜 권한 UI 가 거부를 우회해 차단됐던 장면임. 지시서 최소 장면에도 없음.
- 「코치 세션」 뒤에 발화 없는 결과와 「Start again →」 단계를 붙였음.
- 「홈 문장 연습」에 KO 켬 · 실시간 표시 · 「← Previous」 단계를 넣었음.
- 「기록」에 날짜 줄 → 결과 단계를 넣었음.

보드: `screens/storyboard/index.html` — 10장면 · 30단계 · 썸네일 60장. 60장 모두 열리고 외부 참조는 0개임(`check-board.mjs` → `evidence/board-check.json`).

## 3. 판정 표

판정 수단은 `evidence/measures.json`(장면·단계별 측정 정본)임. 스크린샷은 보조 증거임.

| # | 장면 | 판정 | 근거 |
|--:|---|---|---|
| S1 | 홈 대기 | 통과 | 카드 KO 끔 513.6 px · KO 켬 558.4 px(두 폭 같음) · 1400 Your progress 도 같은 높이 · 넘침 0 · 라벨 5종 12px/700/1.68px · 한국어 0 — `measures.json` `home_idle` |
| S2 | 홈 문장 연습 | 통과 | 연습 카드 KO 끔 513.6 · KO 켬 558.4 px(대기와 같음, 두 폭) · 번역 줄 「저희는 세 시에 회의가 있어요.」 · Listen/Slow 없음 · 아래 버튼 「← Previous」 · Previous 로 Sentence 4→3 복귀 · Close 뒤 KO 켬 유지(558.4 px idle) |
| S2-live | 실시간 표시 | 통과 | 가짜 인식기로 말하는 동안 `course-live` 「You're saying: We have a」 · 글자 1400 20px/600 · 390 15.96px/600(문장과 같음) · 판정 뒤 `course-transcript` 도 문장과 같은 글자 · 카드 높이 그대로 |
| S3 | Day 2 를 고른 연습 | 통과 | `practice-day` 「Day 2 · Units 22–41」 · 주소 `/` · 390 창 697→89 로 카드까지 올라감 |
| S4 | View all 펼침 | 통과 | Day 줄 2→6→2 · 버튼 View all→Show less→View all · 주소 `/` · 상태 Day 1 In progress · Day 2~5 Up next · Day 6 Done(Your progress 「1 / 6 days」와 맞음) |
| S5 | 코치 세션(Free talk) | 통과(버튼·전환만) | 카드 `data-mode=session` 513.6 px · 잠긴 링크 1개 · 390 창 744→89 · `session-end` 「End lesson」 → `/results/<id>` · 결과 「We didn't hear you this time.」 · `results-start-again` → `/`. 전사·코치 발화는 판정하지 않음(지시서 7항) |
| S6a | 기록 `/history` 펼친 날짜 줄 → 결과 | 통과 | 2026-11-14 줄(6 lessons) 펼침 → `history-session-link` 6개 → 첫 링크 `/results/3e460593…` · 「Not analyzed yet」 설명 줄 있음 |
| S6b | 기록 세션 하나인 날짜 줄 → 바로 결과 | 불확실 | 격리 DB 에 세션이 하나뿐인 날이 없음(`history-day-link` 0개 · `history-day-group` 2개). 세션 상한 때문에 그런 날을 만들지 않았음. 코드에는 그 갈래가 있음(`app/history/page.tsx` `history-day-link`) |
| S7 | 주간 `/history/weekly` | 통과 | `weekly-heading` 「Weekly report · Nov 2 – Nov 8」 · `weekly-period` 「Last week」 · 「← Home」 → `/` |
| S8a | 결과 · 지난 완료 세션 | 통과 | `/results/7a18a111…` · 「You finished on Nov 1」 · 총평 제목 「Lesson on Nov 1」(`results-1400-01.jpg`) · 한국어 6건은 백엔드 분석 콘텐츠 |
| S8b | 결과 · 발화 없는 세션 | 통과 | `/results/13869294…`(발화 0건) · `results-status` 「We didn't hear you this time.」 · 「Check your microphone…」 · 「Start again →」 |
| S9 | `/course` · `/course/1` 리다이렉트 | 통과 | 두 주소 모두 끝 주소 `/` · 홈 대기 카드가 그려짐 |
| S10a | 영상 목록 `/videos` | 통과 | 홈 Learn with videos 로 닿음 · 넘침 0 · 한국어는 영상 제목(YouTube 메타데이터) |
| S10b | 영상 화면 `/videos/<id>` | 통과 | 390 `body.scrollWidth` 390 · 화면 밖 미디어 0 · 버튼 「Mark a hard part」 |

- UI 상수에서 온 한국어: 모든 장면에서 0건임. 잡힌 한국어의 출처는 넷임 — 번역 줄(`grammar_basic_ko.json`) · 단원 이름(`grammar_basic.json` 의 `topic`, 예 「Unit 22 · 현재 · 과거 시제 정리」) · 결과 분석 콘텐츠(백엔드) · 영상 제목.
- 섹션 라벨: 홈 라벨 5종이 모든 장면에서 12px/700/1.68px 임. 사이드바 「Workspace」(10px)는 설계서 §3 의 범위 밖(메뉴)이라 결함으로 보지 않음.
- 잘림: 홈 장면마다 1건이 잡혔음. 1×1 px 의 화면 낭독기 전용 제목(`H1 Home`)이고 결함이 아님.
- 콘솔 오류: 모든 장면에서 0건임. 수집 수단은 §4 에서 양성 대조했음.

## 4. 관측 수단의 양성 대조

| 수단 | 대조 | 결과 |
|---|---|---|
| 가로 넘침 · `body.scrollWidth` · 글자 상자 | 390 홈에 600 px 글자 상자 주입 | 잡음(`body.scrollWidth` 600 · 상자 오른쪽 600). 문서 `scrollWidth` 는 390 그대로임(b16 실측 재현) — `evidence/probe-controls.json` |
| 콘솔 오류 수집 | 페이지에서 `console.error` 1건 | 1건 잡음 |
| 리다이렉트 판정(끝 주소) | 넘기지 않는 `/history` 를 엶 | `/history` 그대로 남음 → `/course` 의 `/` 는 실제 리다이렉트임 |
| 실시간 표시 | 가짜 인식기 없이 Start | `course-live-interim` 0개 · 「I couldn't hear you…」 → 실시간 글자는 가짜 인식기가 만든 것임. 진짜 인식기는 있으나 가짜 오디오를 전사하지 않음(설계서 §2-2와 같음) |
| 잘림 검출 | — | 화면 낭독기 전용 H1(scrollWidth 90 > 1)을 잡음 |
| 한국어 검출 | — | 번역 줄 · 단원 이름 · 분석 문구 · 영상 제목을 잡음 |
| 카드 높이 | KO 끔/켬 두 상태 | 513.6 과 558.4 로 갈려 잡힘(같은 값만 내는 수단이 아님) |

## 5. b16 보고서 항목 대조

| b16 항목 | 지금 | 근거 |
|---|---|---|
| B-D1 Start speaking 때 창이 맨 위로 튐 | 이 탭은 재지 않음 | 이 탭은 맨 위(scrollY 0)에서만 눌렀음. 버튼 탭의 몫임 |
| S-D2 홈 In progress ↔ /course Not started | 고쳐짐 | `/course` 는 홈으로 넘어감 · 홈 Day 상태와 「1 / 6 days」가 맞음(S4) |
| S-D1 390 영상 오른쪽 잘림 | 고쳐짐 | S10b `body.scrollWidth` 390 |
| B-D2 홈 History·Weekly 가 파란 바탕 아님 | 고쳐짐 | `home_idle-1400-01.jpg` 두 버튼 파란 바탕 |
| B-D4 End lesson 등 testid 없음 | 고쳐짐 | `session-end` 로 골랐음 · `session-failed-retry` 가 소스에 있음 |
| A 빠른 카드 셋 = More practice | 고쳐짐 | 홈 버튼 목록에 빠른 카드 없음 |
| A Grammar course = Start speaking | 고쳐짐 | More practice 에 Grammar course 없음 |
| A `/course`·`/course/<day>` 두 번째 학습 길 | 고쳐짐 | S9 |
| B Your progress 의 기간 | 고쳐짐 · 남은 것 N1 | 「Last week · Nov 2 – Nov 8」 |
| B 주간 리포트 제목 기간 | 고쳐짐 · 남은 것 N6 | S7 |
| B 결과 「You finished today」 고정 | 고쳐짐 · 남은 것 N7 | S8a |
| C 「← Close」와 「← Back」 | 고쳐짐 | 「← Previous」 |
| C 「Not checked」 설명 없음 | 고쳐짐 · 남은 것 N5 | 「Not analyzed yet」 + 설명 줄 |
| C 「Mark start」 | 고쳐짐 | 「Mark a hard part」 |
| D 기록 날짜 줄이 눌리지 않음 | 고쳐짐(여럿인 날) | S6a. 하나인 날은 S6b 불확실 |
| D 주간 리포트에 ← Home 없음 | 고쳐짐 | S7 |
| E 발화 0건에 「You finished today」 | 고쳐짐 · 남은 것 N4 | S5 · S8b |
| E 말한 내용이 판정까지 안 보임 | 고쳐짐(가짜 인식기 조건) | S2-live |
| F 버튼 모양 기준 범위 | 고쳐짐 | More practice · View all · Practice a pattern · End lesson · Mark a hard part · Check · Delete 가 모두 `omy-button` |

## 6. 흐름·논리 점검 — 사람 사용자 입장 (새 관찰)

기준: ① 다음 할 일이 화면만으로 보이는가 · ② 이름과 하는 일이 맞는가 · ③ 막다른 곳·되돌아갈 길 없음·같은 일을 하는 두 입구. 근거 경로는 `screens/storyboard/shots/` 기준임. 모두 결함이 아니라 판단이 필요한 관찰임.

| ID | 장면 | 기준 | 문제 | 근거 | 보완안 |
|---|---|---|---|---|---|
| N1 | 홈 Your progress | ② | 「Last week · Nov 2 – Nov 8」 꼬리표 아래에 Sessions · Best streak · Patterns 가 한 줄로 놓임. Best streak 은 전체 기간 값(`streak.longest`)인데 지난주 값으로 읽힘 | `home_idle-1400-01.jpg` · `home_idle-390-01.jpg` | Best streak 을 꼬리표 위(진도 줄)로 옮기거나 꼬리표가 Sessions·Patterns 만 덮게 묶음 |
| N2 | 홈 문장 연습 결과 | ② | 「You said: We have a meeting at three」 바로 아래에 원문 줄이 이름표 없이 거의 같은 문장으로 다시 나옴. 다 맞았을 때 같은 말이 두 번 보임 | `home_practice-1400-04.jpg` · `home_practice-390-04.jpg` | 둘째 줄에 「Sentence:」 같은 이름표를 붙이거나, 다 맞으면 둘째 줄 대신 「All words matched」 한 줄을 보임 |
| N3 | 코치 세션 | ② | More practice 의 버튼은 「Free talk」인데 열린 세션 제목은 「English talk」임 | `coach-1400-01.jpg` · `coach-1400-03.jpg` | 세션 제목을 누른 버튼 이름과 맞춤 |
| N4 | 발화 없는 결과 | ②·③ | 「Start again →」와 「← Home」이 둘 다 홈으로 감(S5 실측). 「Start again」은 그 학습을 다시 여는 것으로 읽힘. 설계서 §3 ⑨ 의 결정대로이지만 이름과 하는 일이 갈림 | `coach-1400-04.jpg` · `coach-1400-05.jpg` · `results-390-02.jpg` | 같은 학습(Free talk)을 바로 다시 열거나, 이름을 「Back to Home」으로 바꾸고 아래 「← Home」을 뺌 |
| N5 | 기록 | ② | 11-14 의 6 lessons 는 모두 발화 0건인데 「Not analyzed yet」으로 보임. 설명 줄이 「아직 확인 안 됨」으로 읽혀 나중에 분석될 것처럼 보임. 같은 화면의 「1-day streak!」도 말하지 않은 세션으로 셈 | `history-1400-03.jpg` · 회차 시작 때의 `db.py paid` 조회(11-14 06:01~06:26Z 세션 6개 모두 발화 0건) | 발화 0건뿐인 날은 「Nothing said」처럼 따로 적음. 연속 학습일 셈에서 발화 0건 세션을 뺄지 정함 |
| N6 | 주간 리포트 | ② | 「Try this week」 제목 아래 본문이 「Nothing to show for last week.」임. 제목은 이번 주, 본문은 지난주를 말함 | `weekly-1400-01.jpg` | 그 절의 빈 문구를 「No suggestions yet.」처럼 기간 없는 말로 바꿈 |
| N7 | 결과 · 지난 세션 | ② | 11-01 세션 결과에 「Today's drill was shorter than planned.」가 남음. 설계서 §3 ③ 이 C3 하네스 기대값이라 범위 밖으로 둔 문구임 | `results-1400-01.jpg` | 하네스 기대값과 함께 「This drill was shorter than planned.」로 바꿀지 정함 |
| N8 | 기록 | ① | 공부하지 않은 날짜(11-02~11-13 · 10-16~10-31)가 눌리지 않는 줄로 모두 나와 공부한 두 날이 묻힘 | `history-1400-03.jpg` | 공부한 날만 보이거나 빈 날을 「No study · Nov 2 – Nov 13」 한 줄로 접음 |
| N9 | 영상 목록 | ② | 링크 저장 버튼 이름이 「Check」라 무엇을 확인하는지, 저장까지 하는지 이름만으로 모름 | `videos-1400-01.jpg` | 「Save video」로 바꿈 |
| N10 | 홈 대기 | ① | KO 켬이면 대기 카드가 558.4 px 이고 내용은 제목 한 줄과 설명 한 줄이라 남색 빈 자리가 큼. 대기 = 연습 높이 결정의 결과임 | `home_idle-1400-02.jpg` | 판단 없음 — 높이 결정(`TASK-310`·`TASK-328`)을 유지할지 사용자가 정함 |

판정 밖 관찰:

- 연습 카드의 KO 버튼은 글자가 「KO」뿐이라 처음 보는 사용자는 무엇을 켜는지 모를 수 있음. `aria-label` 은 「Show Korean translation」임.
- 모든 화면 왼쪽 아래에 Next.js 개발 표시기(N)가 보이고, 390 에서는 Your progress 의 「Grammar course」 글자를 가림(`home_practice-390-04.jpg`). `next dev` 의 도구이고 운영 화면에는 없음.
- Start speaking 은 Day 1 의 Sentence 3 / 5 에서 열림. 저장된 진도에서 이어 여는 것이고 결함이 아님.

## 7. 결함

없음. 화면 판정(넘침 · 잘림 · 카드 높이 · 라벨 · UI 한국어 · 전환)에서 기대와 다른 동작을 관측하지 못했음.

## 8. 파일

- `screens/storyboard/index.html` · `screens/storyboard/shots/*.jpg`(60장 · 전체 페이지)
- `screens/evidence/measures.json`(장면·단계별 측정 정본) · `run.log` · `summary-*.txt`
- `screens/evidence/probe-controls.json`(양성 대조) · `board-check.json` · `board-check.jpg` · `db-end.json`
- 스크립트: `shoot.mjs`(스크린샷·측정 · 가짜 인식기는 b17 `live.mjs` 의 `installFakes` 와 같음) · `summarize.mjs` · `build-board.mjs` · `check-board.mjs` · `probe-controls.mjs`
