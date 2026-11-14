# 회차 2026-11-14-b16 — 화면 탭 결과 (`TASK-316.1`)

## 0. 먼저 알릴 것

- 지시서 상한 위반 1건: 이 탭이 연 Nova 세션은 상한 2개를 넘은 4개임. 코치 Free talk 2개(1400·390)는 계획대로 열었음. 마이크 거부 재실행 2개는 계획에 없었음. 거부가 브라우저에 먹히지 않아 세션이 그대로 열렸음(§3 S6). 네 세션 모두 `completed` 로 닫혔음. 발화는 0건임(`db.py paid` 조회 · id `3e460593…` `90ef37bc…` `55e134d0…` `d327d1e5…`).
- 회차 중 HEAD 가 `3c54359` 에서 `a5ac4bf` 로 움직였음(커밋 3개). 바뀐 것은 `docs/`·`handoff`·`tests/agent/runs/2026-11-14-g2/` 뿐이고 `app/` 은 바뀌지 않았음. 그래서 모든 측정은 같은 앱 코드에 대한 것임. `e26e89d` 는 HEAD 의 조상임(지시서 전제와 맞음).
- 06:15Z 에 측정 페이지가 외부에서 닫혔음(`Target page, context or browser has been closed`). 같은 무렵 `f0732d1`(「회차 b16 일시 정지와 재개」 · 06:25Z)이 들어왔음. Chrome 9401 은 같은 브라우저 ID 로 살아 있었음. 남은 장면은 06:25Z 에 같은 절차로 다시 돌렸음.
- 가로 넘침 판정 수단을 바꿨음. 지시서의 `scrollWidth <= clientWidth`(문서 수준)는 이 앱에서 넘침을 볼 수 없음. `html`·`body` 가 `overflow-x: hidden` 이기 때문임. 양성 대조에서 600 px 요소를 넣어도 문서 `scrollWidth` 는 390 그대로였음. `body.scrollWidth` 와 글자 상자 오른쪽 끝 검사는 그 넘침을 잡았음(`evidence/probe-overflow.json`). 그래서 판정은 `body.scrollWidth`·글자 상자 검사로 함. 코치·마이크 거부 장면은 세션 상한 때문에 다시 돌리지 않았음. 두 장면은 글자 상자 검사로만 판정했음.
- 원장: 지시서 4항(리포 원장 수정 금지 · 커밋 금지)에 따라 결함을 작업 원장에 등록하지 않았음. §5 의 결함 2건은 호출자가 등록해야 함.

## 1. 환경

| 항목 | 값 |
|---|---|
| 앱 | `http://localhost:3000`(`next dev`) · 백엔드 `:8002` 격리 DB `ohmyenglish_course_paid` · `VOICE_ADAPTER=nova` |
| 브라우저 | 호출자가 띄운 헤드리스 Chrome 157.0.8103.52 · CDP `127.0.0.1:9401` · `connectOverCDP` · 시간대 Asia/Seoul |
| 도구 | Playwright 1.58.2(`tests/agent/tools/node_modules`) |
| HEAD | 시작 `3c54359` · 끝 `a5ac4bf`(앱 코드 변경 없음) |
| 측정 시각 | 06:00Z~06:30Z(2026-11-14) |
| 진도 저장 | 홈 문장 연습과 `/course/1` 을 열어 격리 DB 의 진도·시도가 바뀌었음(지시서 6항) |

## 2. 장면 목록 — 옛 보드와 설계서 §3 을 대조해 다시 정함

옛 보드(`docs/ux/2026-11-01-user-scenarios/index.html` · 10장면)에서 바뀐 점은 다음과 같음.
- 「오늘의 문장 연습」을 대기·연습 두 장면으로 나눴음.
- 「문법 코스」는 Day 2 선택·View all 로 홈 안으로 옮겼음.
- `/course`·`/course/1` 은 주소로만 닿는 남은 화면으로 따로 뒀음.
- Listen·Slow 단계는 없앴음.

옛 보드의 「Day 마치기」·「약점 연습」·「쉐도잉」은 이번 보드에 없음. 앞의 하나는 문장 수십 개를 끝까지 말해야 함. 뒤의 둘은 Nova 세션이 필요하므로 세션 상한에 걸림.

보드: `screens/storyboard/index.html` — 12장면 · 27단계 · 썸네일 54장. 54장 모두 열리고 외부 참조는 0개임(`check-board.mjs` 실측). 이미지는 `storyboard/shots/*.jpg`(전체 페이지)임.

## 3. 판정 표

| # | 장면 | 판정 | 근거 |
|--:|---|---|---|
| S1 | 홈 대기 | 통과 | 카드 1400 433.6 px · 390 489.6 px · Your progress 1400 433.6 px(카드와 같음) · 넘침 0 · 라벨 5종 모두 12px·700·대문자 · 한국어 0 — `evidence/measures.json` `home_idle` |
| S2 | 홈 문장 연습 | 통과 | 연습 카드 1400 433.2 · 390 489.5 px(대기와 0.4 px 이내) · 연습 중 Your progress 433.2 px · `course-listen`·`course-slow` 0개(양성 대조 `course-next` 1개) — `evidence/probe-practice-buttons.json` |
| S3 | Day 2 를 고른 연습 | 통과 | `practice-day` = 「Day 2 · Units 22–41」 · 주소 `/` 그대로 · 390 에서 창이 카드 위치(scrollY 677→89)로 올라감 |
| S4 | View all 펼침 | 통과 | Day 줄 2→6→2 · 버튼 문구 View all→Show less→View all · 주소 `/` |
| S5 | 코치 세션(Free talk) | 통과(버튼·전환만) | 카드 `data-mode=session` · 높이 대기와 같음 · 잠긴 링크 1개 · 390 창 982→89 · `End lesson` 뒤 `/results/<id>` 로 이동. 전사·코치 발화는 판정하지 않음(지시서 7항). End 버튼은 testid 가 없어 `session-panel` 안의 문구 「End」로 골랐음 |
| S6 | 세션 실패(마이크 거부) | 차단됨 | 관측 수단이 거부를 만들지 못함: CDP 거부 뒤 `permissions.query` = `denied` 인데 `getUserMedia` 는 스트림을 줌(가짜 권한 UI 플래그가 우회) — `evidence/probe-mic.json`. 앱은 거부를 받은 적이 없으므로 실패 화면 0건은 결함이 아님 |
| S7 | 기록 `/history` | 통과(배치) | 넘침 0 · 잘림 0 · 한국어 0. 흐름 문제 §6 |
| S8 | 주간 `/history/weekly` | 통과(배치) | 넘침 0 · 잘림 0 · 한국어 0 |
| S9 | 결과 `/results/7a18a111…` | 통과(배치) | 넘침 0 · 잘림 0. 한국어 6건은 백엔드 분석 콘텐츠(교정 설명·Today's lesson)이고 결함으로 보지 않음. 1단계(`/history` 에서 결과 링크 찾기)는 링크가 없어 실패했고, 세션 ID 는 격리 DB 조회(발화 26건 · completed)로 골랐음 |
| S10 | 코스 목록 `/course` | 통과(배치) · 논리 결함 D2 | 넘침 0 · 잘림 0. 홈과 Day 상태 표시가 갈림(§5 D2) |
| S11 | Day 화면 `/course/1` | 통과(배치) | 넘침 0 · 잘림 0. 한국어는 단원 이름(`grammar_basic.json`)과 YouTube 영상 제목(iframe `title`)이고 결함으로 보지 않음 |
| S12a | 영상 목록 `/videos` | 통과 | 넘침 0. 한국어는 영상 제목(백엔드 영상 메타데이터) |
| S12b | 영상 화면 `/videos/<id>` | 1400 통과 · 390 실패(D1) | 390 `body.scrollWidth` 692 > 390 · iframe 640 px · 2회 모두 재현 — `evidence/probe-video-overflow.json` |

- UI 상수에서 온 한국어: 모든 장면에서 0건임.
- 섹션 라벨: 사이드바 「Workspace」만 10px 임. 사이드바는 설계서 §3 「섹션 라벨과 이동 버튼의 기준은 홈」의 범위 밖(메뉴)이므로 결함으로 보지 않음.
- 잘림: 모든 홈 장면에서 1건이 잡혔음. 그것은 1×1 px 의 화면 낭독기 전용 제목(`H1 Home`)이고 결함이 아님.
- 콘솔 오류: 수집 결과 0건임. 다만 수집 수단의 양성 대조는 하지 않았음.

## 4. 관측 수단의 양성 대조

| 수단 | 대조 | 결과 |
|---|---|---|
| 가로 넘침 · 문서 `scrollWidth` | 390 홈에 600 px 요소 주입 | 잡지 못함(390/390) → 판정 수단에서 뺐음 |
| 가로 넘침 · `body.scrollWidth` · 글자 상자 오른쪽 끝 | 같은 주입 | 잡음(620 > 390) · 실제로 영상 화면 iframe 을 잡음 |
| 잘림 검출 | — | 화면 낭독기 전용 H1(scrollWidth 90 > 1)을 잡음 |
| 한국어 검출 | — | 단원 이름·결과 분석 문구를 잡음 |
| 마이크 거부 | `permissions.query` 와 `getUserMedia` 를 함께 잼 | 거부가 스트림을 막지 못함 → S6 차단됨 |
| Listen·Slow 부재 | 같은 측정으로 `course-next`·`course-prev` 를 셈 | 각 1개 잡음 |

## 5. 결함 — 호출자가 작업 원장에 등록할 것

### D1 · 390 폭 영상 화면에서 영상의 오른쪽 302 px 가 잘려 보이지 않음

- 재현: ① 390×844 로 `/videos` 를 엶 ② 첫 영상을 엶 ③ 영상 칸의 오른쪽이 화면 밖으로 나감. 가로 스크롤도 되지 않음(`body` `overflow-x: hidden`).
- 기대: 영상 칸이 화면 너비 안에 들어감(`body.scrollWidth <= 390`).
- 실제: iframe `width="640"` 고정 · 오른쪽 끝 692 px · 재생 버튼이 반쯤 잘림. 2회 중 2회 재현됨.
- 증거: `evidence/probe-video-overflow.json` · `evidence/video-390-viewport.jpg` · `storyboard/shots/videos-390-02.jpg`.
- HEAD: `a5ac4bf`(앱 코드는 `3c54359` 와 같음) · 시나리오: 화면 탭 S12b.
- 고쳐진 것으로 볼 조건: 390 폭 영상 화면의 `body.scrollWidth` 가 390 이하이고 iframe 오른쪽 끝이 390 이하임.
- 제안: iframe 에 `width: 100%` 와 `aspect-ratio: 16 / 9` 를 줌. Day 화면(`/course/1`)의 영상 칸은 390 에서 넘치지 않으므로 그 방식을 따르면 됨.

### D2 · 홈 Continue your path 가 이번 round 에 시작하지 않은 Day 를 「In progress」로 보임

- 재현: ① 격리 DB 상태(cycle 3 · Day 2~6 은 `completed_count 2` · 시작 위치)에서 홈을 엶 ② View all 을 누름 ③ `/course` 를 엶.
- 기대: 두 화면이 같은 Day 를 같은 상태로 보임.
- 실제: 홈은 Day 1~6 을 모두 「In progress」로 보임. `/course` 는 Day 1 만 진행 중이고 Day 2~6 은 「Not started」임. 홈 Your progress 는 같은 화면에서 「0 / 6 days」를 보임.
- 갈리는 곳: 홈 `components/home/dashboardData.ts` 의 `dayStatus` 는 진도 행이 있으면 `started` 로 봄. `/course` 의 `app/course/page.tsx` `DayRow` 는 시작 위치를 벗어나야 진행 중으로 봄.
- 증거: `storyboard/shots/view_all-1400-02.jpg` · `storyboard/shots/course-1400-01.jpg` · `evidence/api-course.json`.
- 고쳐진 것으로 볼 조건: 같은 응답에서 홈의 Day 상태와 `/course` 의 상태가 Day 마다 같음.
- 제안: 홈 `dayStatus` 가 `/course` 와 같은 기준(이번 cycle 완료 · 시작 위치 이탈)을 쓰게 함. 판정 함수를 하나로 모으면 더 좋음.

## 6. 흐름·논리 점검 — 사람 사용자 입장

기준 ① 다음 할 일이 화면만으로 보이는가 · ② 이름과 하는 일이 맞는가 · ③ 막다른 곳·되돌아갈 길 없음·같은 일을 하는 두 입구가 있는가. 근거 경로는 `storyboard/shots/` 기준임.

| 장면 | 기준 | 문제 | 근거 | 보완안 |
|---|---|---|---|---|
| 홈 대기 | ③ | 빠른 카드 셋이 More practice 버튼과 같은 일을 함: Shadow a sentence = Shadowing · Repair your mistakes = Weak spots · Listen & notice = Learn with videos(코드 `HomeDashboard.tsx` `QuickCards` 가 `additionalLearning.ts` 의 같은 key 를 씀). 사용자는 둘이 다른 학습이라고 기대함 | `home_idle-1400-01.jpg` | 빠른 카드를 More practice 의 추천 표시로 바꾸거나 한쪽을 뺌 |
| 홈 대기 | ③ | More practice 의 Grammar course 와 Start speaking 이 같은 일(현재 Day 문장 연습)을 함(설계서 §3 결정) | `home_idle-1400-01.jpg` | 둘을 남기려면 Grammar course 에 「Today's practice opens above」 같은 안내를 붙임 |
| 홈 대기 | ② | Day 줄이 모두 「In progress」인데 Your progress 는 「0 / 6 days」임(D2) | `view_all-1400-02.jpg` | D2 를 고침 |
| 홈 대기 | ② | Your progress 의 Sessions·Patterns 는 지난 주 리포트(week of Nov 2)의 값임. 그런데 「This week: 0 / 7 days」 바로 아래에 있어 이번 주 값으로 읽힘 | `home_idle-1400-01.jpg` · `../evidence/probe-weekly.json` | 줄 이름을 「Last week」처럼 기간이 보이게 바꿈 |
| 홈 문장 연습 | ② | 카드 머리의 「← Close」(카드 닫기)와 아래의 「← Back」(이전 문장)이 같은 왼쪽 화살표 모양임. 그래서 Back 이 홈으로 돌아가는 버튼으로 읽힘 | `home_practice-1400-02.jpg` · `../evidence/probe-practice-buttons.json` | 아래 버튼을 「← Previous」로 바꿈 |
| 코치 세션 | ① | 시작 후 15초 동안 「Waiting for the coach…」만 보임. 「Just speak.」 안내가 있어 다음 행동은 알 수 있음. 코치가 먼저 말하지 않은 것은 가짜 마이크 조건이라 판정하지 않음 | `coach-1400-03.jpg` | 판정 없음(실제 음성 회차에서 확인) |
| 코치 세션 결과 | ② | 말을 한마디도 안 한 15초 세션 뒤에 「Nothing to check · You finished today」를 보임. 끝낸 것으로 칭찬받는 셈임 | `coach-1400-04.jpg` | 발화 0건이면 「We didn't hear you this time」처럼 사실을 말하고 다시 시작 버튼을 줌 |
| 결과 | ② | 11-01 세션 결과를 11-14 에 열어도 「You finished today — 4 scenes」라고 함 | `results-1400-02.jpg` | 세션 날짜로 문구를 만듦(「You finished on Nov 1」) |
| 기록 | ③ | 공부한 날 줄(예: 2026-11-01 · Mistakes 190)이 눌리지 않음(`SPAN` · 주소 그대로). 지난 결과로 돌아갈 길이 없고, 결과 화면은 세션 직후에만 닿음 | `history-1400-02.jpg` · `measures.json` `history` 2단계 `moved:false` | 날짜 줄을 그날의 결과 목록이나 결과 화면으로 연결함 |
| 기록 | ② | 「Not checked」(11-14)가 무엇을 확인하지 않았다는 뜻인지 화면에 설명이 없음 | `history-1400-01.jpg` | 「Not analyzed yet」처럼 바꾸고 언제 분석되는지 한 줄을 붙임 |
| 주간 | ③ | 홈에서 들어와도 돌아가는 버튼은 「← History」뿐임. 390 에서는 로고만 홈으로 감 | `weekly-390-01.jpg` | 「← Home」을 같이 둠(결과 화면처럼) |
| 주간 | ② | 11-14 에 열면 11/2~11/8(지난 주)을 보임. 그런데 제목은 「Weekly report」이고 본문은 「this week」라고 함 | `weekly-1400-01.jpg` | 제목에 「Last week」를 붙이거나 본문의 「this week」를 고침 |
| 코스 목록 | ③ | 메뉴에서 빠졌는데 Start·Continue 로 옛 Day 화면(영상 + 문장 연습)으로 들어감. 학습은 홈에서만 한다는 결정(설계서 §3)과 다른 두 번째 입구임. 상태 표시도 홈과 갈림(D2) | `course-1400-01.jpg` | 결과 화면에서 닿는 버튼을 홈 Day 줄로 바꾸거나 `/course` 를 홈으로 넘김 |
| Day 화면 | ③ | 홈 문장 연습과 같은 연습을 영상과 함께 다시 제공함 | `course_day-390-01.jpg` | 위와 같음 |
| Day 화면 | — | 390 에서 단원 이름이 낱말 가운데서 줄바꿈됨(「비 / 교」). 백엔드 문구이지만 줄바꿈은 화면 몫임 | `course_day-390-01.jpg` | 단원 줄에 `word-break: keep-all` 을 줌 |
| 영상 화면 | ① | 「Mark start」만 보고는 무엇을 하는지 알기 어려움. 아래 문장(「Mark a part you can't hear」)을 읽어야 앎 | `videos-1400-02.jpg` | 버튼을 「Mark a hard part」로 바꾸거나 설명을 버튼 옆으로 올림 |
| 영상 화면 | — | 390 에서 영상 오른쪽이 잘림(D1) | `videos-390-02.jpg` | D1 |

## 7. 판정 밖 관측

- 06:00~06:02Z 의 홈은 「Weekly report · week of Oct 19」를 보였음. 06:11Z 재현에서는 홈과 주간 화면이 모두 `week_start 2026-11-02` 응답을 받았음. 그래서 「Nov 2」·「11/2 ~ 11/8」로 같았음(`evidence/probe-weekly.json`). 두 입구가 어긋난다는 가설은 반증됐음. 응답이 그 사이에 바뀐 원인은 특정하지 못했음. 그 사이에 이 탭의 코치 세션 종료가 있었음.
- 모든 화면 왼쪽 아래에 Next.js 개발 표시기(N)가 보임. `next dev` 의 도구이고 운영 화면에는 없음.
- `results` 장면의 `/history` 단계가 장면마다 30초씩 걸렸음. 원인은 내 드라이버임(없는 결과 링크에 대한 `getAttribute` 기본 대기 30초). 앱의 지연이 아님.

## 8. 파일

- `screens/storyboard/index.html` · `screens/storyboard/shots/*.jpg`
- `screens/evidence/measures.json`(장면·단계별 측정 정본) · `run.log`
- `screens/evidence/probe-*.json` · `video-390-viewport.jpg` · `board-check.jpg` · `api-course.json` · `api-weekly-report.json`
- 스크립트: `shoot.mjs`(스크린샷·측정) · `summarize.mjs` · `build-board.mjs` · `check-board.mjs` · `probe-*.mjs` · `patch1.mjs`·`patch2.mjs`(내 스크립트만 고침)
