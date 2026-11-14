# v0 홈 대시보드 리디자인 — 설계서

- 작성 2026-11-01 · 태스크 `TASK-292`(결정) · 구현 태스크는 §7
- 디자인 원본: v0 채팅 `mWIhFuLAh5s` → `~/Downloads/oh-my-english-ui-redesign.zip`.
  컴포넌트 사본은 `docs/design/2026-11-01-v0-home-redesign/oh-my-english-dashboard.tsx.txt` 임.
- 설계 초안은 Plan 에이전트가 코드를 읽고 만들었고, 내가 결정·범위에 맞춰 옮겼음.

## 1. 사용자 결정 (2026-11-01)

1. 스타일은 Tailwind v4 + shadcn(+ lucide 아이콘)을 프런트에 도입함.
2. 화면 문구는 홈만이 아니라 모든 화면을 영어로 바꿈. 문구는 학습자의 현재 수준(단문·일상 어휘)에 맞춤(`h-doc`).
3. 데이터가 없는 칸은 가짜 수치를 두지 않고 있는 데이터로 채움. 백엔드는 바꾸지 않음.
4. 범위는 홈 + 공통 틀임. 사이드바와 밝은 테마를 모든 화면에 두고, 다른 화면의 내부 배치는 그대로 둠.
5. 위 넷 뒤에 사용자는 「추천대로 계속 진행」을 지시했음. 그래서 아래 권장안은 묻지 않고 확정으로 봄.

## 2. 먼저 처리할 함정 셋

1. `app/globals.css` 의 `* { padding: 0; margin: 0 }` 은 CSS 층 밖에 있어 Tailwind 간격 클래스를 이김. `@layer base` 로 옮김.
2. `--accent` 의 뜻이 충돌함. 이 앱에서는 브랜드 색(인라인 15곳)이고 shadcn 에서는 옅은 hover 배경임. shadcn 의 `--color-accent` 는 `--surface` 를 가리키게 하고, 이름 `--accent` 는 브랜드 색으로 남김.
3. 하네스(`tests/harness/`)와 회차 드라이버가 한국어 문구와 토큰 이름 둘(`--foreground` · `--foreground-muted`)을 읽음. 문구를 바꾸는 태스크에서 그 시험 코드도 함께 바꿈.

## 3. 구조 결정

| 주제 | 결정 | 근거 |
|---|---|---|
| 테마 | 밝은 테마만 둠. 어두운 테마 블록을 지움 | 결정 4 · 대비 검사를 한 벌만 함 |
| 기존 토큰 | 이름을 모두 남기고 값만 밝은 테마로 바꿈 | 각 화면의 인라인 스타일을 고치지 않아도 됨 |
| v0 색 | 되풀이되는 색을 토큰으로 둠(`--brand` · `--brand-soft` · `--hero` · `--page` · 카드 옅은 색 셋) | 인라인 `[#…]` 값 수십 개를 피함 |
| 옛 요소 모양 | Tailwind 기본 재설정이 버튼·제목·목록·입력 모양을 지우므로 `@layer base` 에 최소 모양을 되살림 | 옛 화면이 깨지지 않음 · 유틸리티가 이김 |
| shadcn | `button.tsx` · `lib/utils.ts` · `components.json` 만 손으로 옮김. CLI 패키지 `shadcn` · `tw-animate-css` · `@vercel/analytics` 는 넣지 않음 | 의존성을 줄임 |
| 공통 틀 | `components/app-shell.tsx`(클라이언트) — 넓은 화면은 사이드바, 좁은 화면은 위쪽 아이콘 막대. 데이터를 부르지 않음 | 이동마다 요청이 생기지 않음 |
| 학습 세션 | ~~세션이 도는 동안(`state !== "idle"`) 화면 전체를 덮는 층으로 그림~~ → 2026-11-01 뒤집음(아래 「세션 화면의 번복」). 지금은 오늘의 연습 카드 안에 그리고 이동 링크를 잠금 | 세션 중 사이드바를 누르면 화면이 내려가 연결이 끊김 |

### 세션 화면의 번복 (2026-11-01 · `TASK-301`)

- 사용자 지시: 「Practice Session 화면을 별도로 띄우지 말고, home 화면의 start speaking 버튼을 누르면, 그 영역에 바로 영어를 연습할 수 있도록 화면의 섹션을 사용해. 다른 디자인을 재배치 하지 않아도 돼」.
- 옛 결정: 세션 동안 화면 전체를 덮는 층(`session-overlay`)을 그림. 근거는 세션 중 이동이 소켓을 닫는다는 것이었음.
- 새 결정: 덮는 층을 없앰. 대시보드는 모든 상태에서 그대로 그려짐.
- 세션 화면은 오늘의 연습 카드 자리(`home-hero` 안의 `session-panel`)에 그림. 카드의 격자 자리와 너비는 그대로이고 높이만 늘어남.
- 세션 동안 그 카드는 남색에서 밝은 카드로 바뀜. 대화·쉐도잉·리포트 패널이 `--foreground` 글자색을 쓰므로 남색 위에서는 읽히지 않음.
- 옛 근거(이동이 소켓을 닫음)는 덮개 대신 잠금이 막음. `components/app-shell.tsx` 의 `useSessionLock` 이 대기가 아닌 동안 사이드바·좁은 화면 막대·로고 링크를 잠금(`aria-disabled` · 흐림 · `data-locked="true"` · 「End the lesson first」).
- 대시보드 안의 이동 링크와 다른 세션을 여는 버튼도 같은 동안 잠김(빠른 카드 · More practice · Continue your path · View all · Practice a pattern).
  - 정정(2026-11-14 · `TASK-320` · 회차 b16): `TASK-314` 뒤 View all 은 화면 이동이 아니라 제자리 펼침이라 세션 중에도 눌림. 펼친 Day 줄은 잠김(disabled). 이 동작을 정본으로 둠.
- 대기로 돌아오거나 화면이 언마운트되면 잠금이 풀림. 실패 화면은 「Try again」과 대기로 돌아가는 「← Home」을 그대로 가짐.

### 오늘의 연습 카드가 문장 연습을 엶 (2026-11-01 · `TASK-304`)

- 사용자 지시: 「home에서 "start speaking" 을 누르면 pactice 의 아래 하단 영역이 "start speaking" 이 위치한 그 자리에 표시되도록 해 · youtube 화면이 따로 표시되지 않아도 돼 · youbebe 에서 참조할 내용은 학습하는 문자의 패턴만 필요해」.
- 사용자 결정: 「코치 대화 빼기」. 홈의 추천 코치 대화 시작점을 없앰.
- 옛 동작: 「Start speaking」이 추천 코치 대화(`source: recommended`)를 열고 카드 안에 대화 화면을 그렸음(`TASK-301`).
- 새 동작: 「Start speaking」(`start-session`)은 문법 코스 Day 화면의 영상 아래 부분을 카드 안에 그림. 단원 줄 · Auto/Manual · 문장 카드 · 안내가 그 범위임.
- 카드는 `fetchCourse()` 의 `current_day` 로 Day 를 고르고 `fetchCourseDay()` 로 문장을 읽음. 문장은 단원 패턴으로 새로 쓴 백엔드 콘텐츠이고 영상에서 가져오는 것이 없음.
- 홈은 영상을 그리지 않음. 연습 중 카드는 밝은 카드(`data-mode="practice"`)이고 「Day N · Units a–b」 줄(`practice-day`)과 「← Close」(`practice-close`)를 가짐.
- 문장 연습의 논리와 화면은 `components/course/SentencePractice.tsx` 로 뽑았음. Day 화면은 영상 핸들을 넘기고 홈은 넘기지 않음.
- 영상이 없으면 진도 저장은 불러온 `position_sec` 을 그대로 보냄. Day 를 마친 때만 0 을 보냄. 그래서 홈의 연습이 Day 화면의 영상 위치를 지우지 않음.
- 문장 연습은 소켓이 없으므로 이동을 잠그지 않음. More practice 등에서 코치 세션을 열면 문장 연습을 먼저 닫음.
- 대기 카드의 문구는 코스 쪽으로 바꿈. 큰 문장은 `Day N: listen and say it.` 이고 버튼 옆 줄은 `Day N · Units a–b` 임(`home-hero-day`).
- 이 변경으로 §5 표의 「오늘의 연습」(`next-plan.reason`) · 「레벨」(`target_level`) 칸은 홈에서 빠짐. 홈은 `next-plan` 을 더 부르지 않음.
- 빠른 카드 · More practice · Practice a pattern 은 그대로 코치 세션을 열고 카드 안에 그림(`TASK-301` 동작).
- 하네스(`tests/harness/`)는 코치 세션을 `start-session` 대신 `practice-free_talk` 로 엶. 대상은 `c1_session_walkthrough.py` · `c2_render_hierarchy.py` · `c5_pronunciation_badge.py` · `p_app_path.py` 임.
- 그 버튼은 홈 아래쪽에 있으므로 하네스의 좌표 클릭(`Cdp.click`)이 먼저 요소를 화면 안으로 끌어옴.
- 진입 출처가 `recommended` 에서 `additional` 로 바뀜. 출처를 판정하는 회차는 이 차이를 알고 읽어야 함.

### 카드 높이 고정의 번복 (2026-11-01 · `TASK-307`)

- 사용자 지시: Start speaking 을 누르면 연습 화면의 내용이 스크롤바 없이 위쪽 카드 안에 모두 보여야 함. 아래 두 칸의 세로 크기를 줄여 위쪽 카드를 키움.
- 사용자 정정(같은 날): 카드 높이는 대기와 연습·세션에서 같은 고정 높이로 둠. 그 고정 높이를 문장 연습이 다 보일 만큼 키움.
- 옛 결정(`TASK-305`): 세션·연습 카드의 높이를 대기 카드의 잰 높이에 맞춤. 넘치는 내용은 카드 안의 칸(`home-hero-body`)만 스크롤함.
- 옛 결정의 결과: 대기 높이가 문장 연습보다 낮아 연습의 아래 줄이 카드 안 스크롤 뒤로 숨었음.
- 새 결정: 세 상태가 같은 고정 높이(`HomeDashboard.tsx` 의 `HERO_HEIGHT`)를 씀. 넓은 화면(`sm` 이상)은 33rem(528 px)이고 좁은 화면은 42rem(672 px)임.
- 문장 연습은 그 높이 안에서 스크롤 없이 다 보임. 셈한 최악보다 길어지는 경우에만 카드가 늘어나고 스크롤하지 않음(`min-h`).
- 대기 카드는 같은 높이 안에서 제목 묶음을 위에, 시작 줄을 아래에 둠. 좁은 화면은 가운데로 모음.
- 코치 대화는 줄이 계속 늘어나므로 대화 기록 칸이 남은 높이를 채우고 그 안에서만 스크롤함. 카드는 스크롤하지 않음.
- 쉐도잉·리포트 패널이 대화 아래에 더 붙어 기록 칸이 최소 높이(120 px)까지 줄어든 경우에만 `home-hero-body` 가 받침으로 스크롤함.
- 키운 높이는 아래 두 칸이 받음. 「Continue your path」 줄(약 78 px → 58 px)과 빠른 카드 셋(약 156 px → 68 px)을 모든 상태에서 줄였음. 상태마다 바뀌면 화면이 튐.
- 창의 스크롤을 옮기지 않는 `TASK-305` 의 규칙(`scrollIntoView` 제거)은 그대로 둠.

높이 셈(인라인 스타일과 Tailwind 값 · 글자 높이는 줄 높이 1.5 기준):

| 줄 | 넓은 화면(1400 폭) | 좁은 화면(390 폭) |
|---|---|---|
| 카드 위아래 여백·테두리(`p-6`) | 50 | 50 |
| 머리 줄(배지 · Close `h-8`) | 32 | 32 |
| `practice-day` 줄(`mt-4` + 16) | 32 | 32 |
| 단원 줄(14 + Auto/Manual 29 · 좁으면 주제 2줄 41) | 43 | 55 |
| 문장 카드 틀(위 8 · 테두리 2 · 안쪽 32) | 42 | 42 |
| 문장 번호 줄 | 19 | 19 |
| 단계 줄(`course-phase`) | 26 | 26 |
| 문장(8 + 줄당 30 · 넓으면 1~2줄 · 좁으면 3줄) | 38~68 | 98 |
| Listen·Slow 줄(10 + 36) | 46 | 46 |
| 결과 칸(`course-spoken` · 좁으면 전사·단어·안내가 2줄) | 115 | 177 |
| Back·Start·Next 줄(14 + 36) | 50 | 50 |
| 합계 | 약 494~524 | 약 668 |

- 결과 칸과 「I'm listening」 안내·막대는 같이 뜨지 않음. 그래서 결과 칸(115)이 더 큰 쪽으로 셈함.
- 문장 길이는 `app/backend/app/content/grammar_basic.json` 의 565문장에서 셈함. 가장 긴 문장이 61자이고 95 % 가 44자 이하임.

사이드바 대응(가장 긴 경로가 이김): Home `/` · Practice `/course`(`/course*`·`/videos*` 에서 활성) · Review `/history`(`/results*` 포함) · Progress `/history/weekly`.

### 아래쪽 입구의 스크롤 예외 (2026-11-01 · `TASK-308`)

- 관찰(회차 b13 r2 O1): 390 폭에서 More practice 의 Free talk 를 누르면 세션은 맨 위 카드에서 돎. 그때 창은 scrollY 1379 라 카드가 화면 밖에 있음.
- 원인은 `TASK-305` 의 규칙임. 그 규칙은 Start speaking 때 창이 움직이지 않게 하려고 모든 시작에서 창 스크롤을 막았음.
- 사용자 결정: 아래쪽 입구로 시작할 때만 카드로 스크롤함. 카드가 이미 화면 안에 있으면 움직이지 않음.
- 홈 Start speaking 은 그대로 창을 움직이지 않음. `TASK-305` 의 규칙은 이 예외를 뺀 나머지에 남음.
- 버린 대안: 그대로 둠(사용자가 직접 올려야 함) · 모든 폭에서 스크롤(Start speaking 까지 움직일 위험).

### 문장 칸 고정 · 카드는 내용 높이 (2026-11-01 · `TASK-310` · `TASK-307` 의 번복)

- 사용자 지시: 오늘의 연습 카드(A)는 아래쪽 빈 공간이 너무 많음. 내용을 모두 표시할 정도만 높이를 유지함.
- 사용자 지시: 문장 칸(B)은 내용에 따라 크기가 조금씩 바뀜. 고정 크기로 표시하고 긴 문장은 두 줄로 표시함.
- 맞물림: B 가 고정이면 「You said」 결과 칸 자리를 B 안에 늘 비워 둬야 함. 사용자는 그 위에서 「고정 + 압축 배치」를 골랐음.
- 옛 결정(`TASK-307`): 카드가 최악의 연습 상태를 담는 고정 높이(1400 528 px · 390 672 px)를 씀. 결과 칸이 없을 때 그 자리가 카드 아래쪽 빈 공간으로 남았음.
- 새 결정: 단계 표시를 `Sentence N / M` 줄에 붙임. 녹음 막대 자리(4 px)와 문장 두 줄 자리를 늘 잡음.
- 결과·듣기 안내·알림은 한 고정 자리(`course-result-slot`)를 나눠 씀. 넓은 화면은 5rem, 좁은 화면은 8.5rem 임.
- 좁은 화면은 문장 글자를 `text-base` 로 줄이고 단원 줄에 두 줄 자리를 잡음.
- 연습 상태의 카드는 높이를 주지 않음. 대기·세션은 그 잰 높이(`HERO_HEIGHT` · 1400 30rem · 390 33.5rem)를 씀.
- 회차 b15 측정(`tests/agent/runs/2026-11-01-b15/evidence/measure-*.json`): B 는 1400 에서 310 px, 390 에서 355 px 임. 565문장 · 단계 표시 · 가장 긴 결과에서 모두 같았음. 두 줄을 넘는 문장은 0개임.
- 넓은 화면의 Your progress 카드는 격자 줄을 따라 A 와 같은 높이임(1400 479.5 px).

### 섹션 라벨과 이동 버튼의 기준은 홈 (2026-11-01 · `TASK-310` · `TASK-311`)

- 사용자 지시: Today's practice 라벨을 Your progress 와 같은 디자인·색으로 함. 다른 섹션도 같은 글꼴로 통일함.
- 결정: 홈의 섹션 라벨은 `SectionLabel`(12 px · 굵게 · 대문자 · 자간 0.14em · `--foreground-muted`)을 씀. Continue your path · Focus patterns · More practice 의 큰 제목도 이 라벨로 바꿨음.
- 예외: 남색 대기 카드의 라벨만 흰색 75 % 임. `--foreground-muted` 는 `--hero` 위에서 읽히지 않음.
- 사용자 지시: 모든 화면의 글자 링크 이동(← · → · Back · Home 등)을 홈 버튼과 같은 모양으로 바꿈.
- 결정: 공용 클래스 `omy-button`(`globals.css`)을 홈 문장 칸의 Back·Start·Next 와 공유함. 앞으로 가는 이동만 `omy-button-primary` 를 더함.
- 범위 밖: 사이드바 메뉴 · 영상 목록의 제목 링크 · 홈의 Day 경로 카드. 이동 버튼이 아니라 메뉴·목록 항목임.

### 학습은 홈에서만 · 메뉴는 Home 하나 (2026-11-01 · `TASK-314`)

- 사용자 지시: Home 에서 실제 학습이 이루어짐. Continue your path 에서 학습을 고르면 Today's practice 에서 그 학습을 함.
- 옛 동작: Day 줄이 Day 화면(`/course/<day>`)으로 가서 영상과 옛 연습 화면이 나왔음.
- 결정: Day 줄은 버튼임. 고르면 페이지 이동 없이 오늘의 연습 카드에서 그 Day 의 문장 연습이 열림(영상 없음).
- 고른 Day 의 줄은 테두리로 표시함. 카드가 화면 밖이면 카드로 스크롤함(`TASK-308` 규칙).
- 사용자 결정: View all 은 다른 화면으로 가지 않고 홈 목록을 모든 Day 로 펼침(Show less 로 접음).
- 사용자 결정: 사이드바의 Practice · Review · Progress 를 뺐음. 좁은 화면은 메뉴 줄을 두지 않고 로고가 Home 으로 감.
- 기록(`/history`)·주간 리포트(`/history/weekly`)는 Your progress 카드의 두 버튼으로 들어감.
- 사용자 결정: More practice 의 Grammar course 는 오늘의 연습 카드에서 현재 Day 를 엶.
- Learn with videos · 빠른 카드 Listen & notice 는 영상 학습이라 `/videos` 링크로 남김.
- 남은 화면: `/course` · `/course/<day>` 는 지우지 않았음. 주소와 결과 화면의 이동 버튼으로 닿음.
- 확인(회차 b15 `path-*.json` · `grammar-*.json`): 1400·390 에서 주소가 `/` 그대로이고 고른 Day 가 열림.

### Listen · Slow 제거 (2026-11-14 · `TASK-318`)

- 사용자: Listen · Slow 의 용도를 모르겠고 필요 없어 보임.
- 코드 확인: Listen 은 Start · Try again 과 같은 동작이었음. Slow 는 같은 동작을 0.7배 속도로 했음.
- 사용자 결정: 둘 다 제거함. 다시 듣기는 Try again 이 맡음.
- 높이: 문장 칸이 46 px 줄었음. 대기·세션 높이(`HERO_HEIGHT`)를 다시 잼(1400 433.2 px → 27.1rem · 390 489.5 px → 30.6rem).

### 회차 b16 보고서의 사용자 결정 (2026-11-14 · `TASK-323`)

- 근거: `docs/ux/2026-11-14-ux-flow-review/index.html` §2 의 「사용자 결정」 넷(AskUserQuestion).
- 빠른 카드 셋(Shadow a sentence · Repair your mistakes · Listen & notice)을 제거함. More practice 의 Shadowing · Weak spots · Learn with videos 와 같은 입구였음.
- More practice 의 Grammar course 를 제거함. `TASK-314` 에서 홈 카드를 여는 버튼으로 바꿨으나 Start speaking 과 같은 일이었음(번복).
- `/course` · `/course/<day>` 는 홈으로 넘김. 영상과 함께 하는 옛 Day 연습은 없어짐. 그리로 가던 버튼은 홈으로 감.
- 이동·실행 버튼은 모두 `omy-button` 기준을 씀(More practice · View all · Practice a pattern · End lesson · 영상 화면 버튼). `TASK-311` 의 「범위 밖」 목록에서 Day 경로 카드 · 사이드바 · 영상 제목 링크만 남김.

### 회차 b16 보고서 보완안 9건 (2026-11-14 · `TASK-329`)

- 근거: `docs/ux/2026-11-14-ux-flow-review/index.html` §2 B~E. 사용자는 9건 모두 고치기로 결정함.
- 날짜 기준: 「오늘」·「이번 주」는 서버가 학습자 타임존(`users.timezone`)으로 준 값만 씀. 화면은 브라우저 시각으로 구하지 않음.
- 서버가 더 싣는 값은 셋임. 주간 리포트의 `this_week_start` · 결과의 `session_date`·`finished` · 기록 줄의 `sessions` 임.
- ① 홈 Your progress: Sessions·Patterns 위에 기간 줄을 둠(`Last week · Nov 2 – Nov 8`). `This week` 는 리포트가 정말 이번 주일 때만 씀. 그 밖의 주는 날짜만 보임.
- ① 옛 아래 줄 `Weekly report · week of …` 는 기간 줄과 겹쳐 뺐음. 리포트가 없을 때의 `No weekly report yet.` 는 남김.
- ② 주간 리포트 제목: `Weekly report · Nov 2 – Nov 8`. 그 아래 `Last week`·`This week` 를 흐린 글자로 보임.
- ② 본문은 리포트의 주로 부름: `Common mistakes last week` · `Nothing to show for last week.` 임. 그 밖의 주는 `that week` 임.
- ② 다음 제안 제목: 이번 주 리포트는 `Try next week`, 지난주 리포트는 `Try this week`, 그 밖은 `Try next` 임.
- ③ 결과 화면: 오늘 세션은 옛 문구(`You finished today` · 개수)를 그대로 씀. 지난 세션은 `You finished on Nov 1` 임.
- ③ 지난 세션은 그날 몇 개를 마쳤는지 화면이 모르므로 개수를 붙이지 않음. 총평 제목도 `Lesson on Nov 1` 로 바꿈.
- ③ 범위 밖: `Today's mistakes` 는 정말 오늘의 요약이라 그대로 둠. 드릴 미달 문구는 C3 하네스의 기대값이라 이번에 바꾸지 않음.
- ④ 문장 연습 아래 버튼: `← Back` → `← Previous`. 카드 머리 `← Close` 와 갈라 읽히게 함. testid `course-prev` 는 그대로임.
- ⑤ 기록: `Not checked` → `Not analyzed yet`. 그런 날이 있을 때만 목록 아래에 한 줄 설명을 붙임.
- ⑤ 설명 문구: `What you say in a lesson is checked for mistakes after each of your turns.` 와 그 뜻 한 문장임.
- ⑤ 규칙의 근거: 차례가 닫힐 때마다 분석 job 이 걸리고, 분석이 저장될 때 그날 요약 행이 생김. 그 행이 없는 날이 `Not analyzed yet` 임.
- ⑥ 영상 화면: `Mark start` → `Mark a hard part` · `Mark end` → `End the hard part here` 임.
- ⑥ 시작을 찍은 뒤 안내는 `The hard part starts at 0:12. Press the button when it ends.` 임. `Mark again` 은 표시를 지우는 일이라 `Cancel` 로 맞춤.
- ⑦ 기록 날짜 줄: 세션이 하나면 줄이 그 결과(`/results/<id>`)로 감. 여럿이면 줄을 펼쳐 시나리오 제목 목록에서 고름.
- ⑦ 날짜 줄은 목록 항목이라 `omy-button` 모양을 쓰지 않음(`TASK-311` 의 범위 밖과 같은 판단).
- ⑧ 주간 리포트: `← History` 옆에 `← Home`(`omy-button` · testid `weekly-home`)을 둠.
- ⑨ 발화 0건 세션 결과: 상태 줄을 `We didn't hear you this time.` 로 바꾸고 완료 문구를 숨김.
- ⑨ 그 아래 `Check your microphone, then start a new lesson from Home.` 과 `Start again →`(`omy-button-primary` · 홈) 을 둠.
- ⑨ 회복 대상(`awaiting_analysis` 참)은 들은 말이 있으므로 옛 `Nothing to check` 를 그대로 씀. C3 하네스도 이 갈래를 따로 셈.

### 문장 아래 한국어 번역 · KO 켜기/끄기 (2026-11-14 · `TASK-328`)

- 사용자 지시: 문장 아래 번역 표시 여부는 설정에서 하도록 함.
- 사용자 결정: 565문장 번역을 미리 만들어 넣고 검수함(열 때마다 요청하지 않음). 켜기/끄기는 카드의 Auto 옆에 둠.
- 데이터: `app/backend/app/content/grammar_basic_ko.json`(문장 키 → 번역). 콘텐츠 파일과 나눠 둠. 모든 문장에 번역이 있는지는 단위 시험이 봄.
- 생성: `scripts/translate_grammar_course.py` · 분석 워커와 같은 Claude 경로. 대부분 Claude Opus 5 · 남은 단원은 Opus 5.5 · Sonnet 5.5.
- 실측: Day 단위로 보내면 평범한 문장도 `refusal(cyber)` 로 거절됐음. 단원 단위로 나눠 만들었음. 원인은 추정임.
- 번역 규칙: 뜻이 낱말과 대응되는 짧은 한국어 · 해요체 통일(내가 정한 값) · 지명·인명은 한국어 · 제품명은 영어.
- 검수: 표본 18문장을 직접 봄. 영어로 남은 지명·인명을 바꾸고 조사 둘(한강은 · 미국을)을 고쳤음.
- 화면: KO 는 Auto/Manual 과 같은 모양으로 그 왼쪽에 둠. 처음 값은 끔(내가 정한 값) · `localStorage` 에 기억함.
- 번역 줄은 KO 를 켰을 때만 두 줄 자리를 잡음. 565개 모두 두 줄에 듦(320 · 390 · 1400).
- 높이: KO 켬이면 대기·세션 높이와 연습 최저 높이가 34.9rem, 끔이면 32.1rem 임. 1400·390 에서 대기와 연습이 같음.

### 회차 b18 보고서 관찰 13건 (2026-11-14 · `TASK-333` · `TASK-332`)

- 근거: `docs/ux/2026-11-14-b18-ux-flow-review/index.html` §2·§3. 사용자는 13건 모두 권장안대로 결정함.
- `TASK-332`: 영상 두 화면의 실행 버튼·링크에 testid 를 붙임. 목록은 `videos-url` · `videos-check` · `videos-save` · `videos-cancel` · `videos-title` · `videos-delete` 임.
- `TASK-332`: 영상 화면은 `video-mark-start` · `video-mark-end` · `video-mark-cancel` · `video-span-transcript` · `video-span-save` · `video-span-cancel` 임.
- `TASK-332`: 문장 줄은 `video-listen` · `video-practise` · `video-delete` · `video-word` 임. `video-open-youtube` 도 붙임. 옛 `videos-home` · `video-back` 은 그대로임.
- N1 홈 Your progress: `Best streak: N days` 를 진도 줄(`Grammar course` · `This week`)로 옮김. 전체 기간 값이기 때문임.
- N1: `Last week · …` 꼬리표는 Sessions · Patterns 두 칸만 덮음. testid `stat-best-streak` 는 그대로임.
- N2 문장 연습 결과: 다 맞으면 낱말 판정 줄 대신 `All words matched` 한 줄을 보임(testid `course-all-matched`).
- N2: 하나라도 다르면 판정 줄 앞에 `Sentence:` 이름표를 붙임. 낱말 판정(`data-verdict`)은 다 맞을 때도 숨긴 채 DOM 에 남김.
- N2: 결과 자리 높이(`course-result-slot`)는 바꾸지 않음. 카드 크기는 그대로임.
- N3 코치 세션 제목: 고정 문구 `English talk` 를 없애고 누른 버튼의 이름을 씀(`Free talk` · `Weak spots` · `Practice a pattern` 등).
- N3: 버튼 이름이 없는 진입(주소 질의 · 음성 명령)은 진입으로 More practice 목록에서 고름. 모드 없는 말하기는 `Free talk` 임.
- N3: 목록에 없는 진입만 옛 `English talk` 를 씀. 판정은 `sessionTitleFor`(`app/additionalLearning.ts`) 하나가 가짐.
- N4 발화 없는 결과: `Start again →` 은 같은 학습을 다시 엶. 결과 API 가 그 세션의 진입(`entry`: 모드 · 출처 · 클립 · 패턴)을 실음.
- N4: 화면은 그 진입으로 홈 질의(`/?mode=…&source=…`)를 만들고 홈이 세션을 엶. 말하기는 `mode=speaking` 을 명시함.
- N4: `via` 는 옮기지 않음(화면 버튼임). 진입이 없는 옛 서버에서는 홈으로 감. 안내 문구는 `Check your microphone, then start again.` 임.
- N4: 아래 `← Home` 은 남김. 홈으로만 가는 다른 일이라 중복이 아님.
- N4 한계: Free talk 와 Weak spots 는 세션 행이 같아 Weak spots 의 다시 시작은 `Free talk` 제목으로 열림.
- N5 기록: 그날 마친 세션이 모두 발화 0건이면 `Not analyzed yet` 대신 `Nothing said` 를 씀. 서버가 날짜 줄에 `spoken` 을 실음.
- N5: 「말했다」의 술어는 분석 대상 발화(학습자 · 학습 발화)와 같음. 정본은 `services/utterances.py` 임.
- N5: 연속 학습일(현재 · 최장)은 발화 0건 세션을 세지 않음. 완료 판정(`completed_today` · `learned`)은 그대로 둠.
- N5: 그래서 연속일과 완료 술어가 이 한 가지에서 갈림. 「마쳤다」는 사실과 「말하며 공부한 날」을 가르는 의도임.
- N5: 설명 줄(`history-not-analyzed-hint`)은 `Not analyzed yet` 인 날이 있을 때만 보임.
- N6 주간 리포트: 다음 제안 절(`Try this week` 등)의 빈 문구를 `No suggestions yet.` 로 바꿈. 다른 두 절은 그대로임.
- N7 결과: 드릴 미달 문구를 `This drill was shorter than planned.` 로 바꿈. C3 하네스 기대값도 함께 바꿈.
- N8 기록: 공부하지 않은 날이 이어지면 `No study · Nov 2 – Nov 13` 한 줄로 접음(testid `history-gap`). 하루면 `No study · Nov 5` 임.
- N8: 공부한 날 줄의 날짜 표기(`2026-11-14 · Studied`)는 바꾸지 않음.
- N9 영상 목록: `Check` 는 저장하지 않고 제목 · 채널을 받아 미리 보임. 저장은 그 아래 `Save` 가 함.
- N9: 그래서 권장안 `Save video` 대신 하는 일과 맞는 `Preview video` 로 씀.
- N10 홈 대기(KO 켬): 대기 = 연습 높이를 유지함(`TASK-310` · `TASK-328` 결정 그대로). 남색 빈 자리는 알고 둠.
- X1 예외: 남색 대기 카드의 `Start speaking` 은 `omy-button` 이 아닌 흰 버튼임. 남색 위에서 첫 동작을 가장 눈에 띄게 하려는 의도된 예외임.
- X2 규칙: More practice 묶음의 버튼은 다른 화면으로 가더라도(`Learn with videos`) 회색 `omy-button` 임.
- X2: 「앞으로 가는 이동만 `omy-button-primary`」 규칙은 More practice 에 적용하지 않음. 고르는 목록이라 모두 같은 무게로 둠.
- X3 KO 켜기/끄기: `title="Show Korean translation"` 을 붙임. `aria-label` 과 같은 문구임.

### This week 기준 · 320 폭 결과 자리 (2026-11-15 · `TASK-335` · `TASK-337`)

- `TASK-335` 사용자 지시: 홈 `This week: N / 7 days` 는 학습 발화가 있는 날만 셈. 연속 학습일 · 기록 `Nothing said` 와 같은 기준임.
- `TASK-335`: 셈의 술어는 `learned && spoken !== false` 임(`learnedInLastWeek`). `spoken` 이 없는 옛 서버에서는 마친 날을 그대로 셈.
- `TASK-337` 실측: 320 폭에서 문장 칸 너비는 196 px 이고 글자는 최저 12 px 에 멈춤. 61자 문장이 틀리면 판정 줄도 세 줄이 됨.
- `TASK-337`: 칸 너비 12.5rem 미만에만 결과 자리를 `8.4em + 3.25rem` 으로 늘림. 320 폭에서 132 px → 153 px 이고 내용이 다 듦.
- `TASK-337`: 12.5rem 이상은 글자가 칸 너비를 따르므로 줄 수가 폭과 무관함. 390 · 1400 의 결과 자리(160 px)와 카드(513.6 px)는 그대로임.
- `TASK-337` 한계: 320 폭의 연습 카드는 전부터 대기보다 컸음(534.3 px 대 513.6 px). 이번에 555.1 px 가 됨. 대기 높이는 390 · 1400 기준이라 그대로 둠.

### 홈은 매일 연습만 — More practice · Practice a pattern 숨김 (2026-11-15 · `TASK-338`)

- 사용자 지시: Weak spots · Free talk 메뉴가 없어도 될 것 같음. 일단 매일 연습하는 것만 있으면 됨. 필요하면 나중에 넣음.
- 사용자 결정(범위): More practice 전체와 Focus patterns 의 Practice a pattern 을 숨김. 화면과 코드는 지우지 않음.
- 구현: `HomeDashboard.tsx` 의 `HOME_EXTRAS`(`morePractice` · `focusPractice` 모두 `false`). 다시 넣을 때는 값만 바꿈.
- 홈에 남는 것: Today's practice · Continue your path · Focus patterns(목록) · Your progress.
- 앞 결정의 번복: `TASK-336`(Weak spots 를 약점 패턴 연습으로)은 이 결정으로 폐기했음(보관).
- ⚠️ 남는 길: 음성 명령의 추가 학습 시작은 이 값과 무관하게 남음 · `/videos` 와 결과 화면의 연습 링크도 남음.
- ⚠️ 수동 하네스 드라이버 다섯(`tests/harness/c1_session_walkthrough.py` · `c2_render_hierarchy.py` · `c5_pronunciation_badge.py` · `p_app_path.py` · `p_readback_leg.py`)은 숨긴 버튼(`practice-*`)을 눌러 세션에 들어감. 다음 실물 회차 전에 진입 방법을 바꿔야 함(게이트 시험은 영향 없음).

### 320 폭 아래 버튼 · 숨긴 입구의 주소 스위치 (2026-11-15 · `TASK-340` · `TASK-341`)

- `TASK-340`: 320 폭(칸 약 196 px)에서 ← Previous · Try again · Next → 너비 합이 칸보다 커 Next → 가 37~63 px 잘렸음.
- 고침: 칸이 200 px 미만일 때만 세 버튼의 여백·글자를 줄임(`globals.css` 의 `@container` · `omy-course-nav`). 줄바꿈은 상태마다 카드 높이를 바꾸므로 쓰지 않음.
- 확인(회차 b24 `nav.mjs`): 320 은 Start · Try again 두 상태 모두 칸 안 · 카드 325.1 px 로 같음. 390 · 1400 은 버튼과 카드 높이가 고치기 전과 같음.
- `TASK-341`: 홈 주소 `?extras=1` 이면 숨긴 More practice · Practice a pattern 이 보임(`components/home/homeExtras.ts`). 기본은 숨김(`TASK-338`).
- 이유: 수동 하네스 드라이버 다섯은 마이크 대체를 심을 틈 때문에 질의 진입 대신 버튼을 눌러 세션에 들어감(`H-CC`). 그래서 드라이버의 기본 주소를 `/?extras=1` 로 바꿨음.

## 4. 파일 계획

- 새 파일: `postcss.config.mjs` · `components.json` · `lib/utils.ts` · `components/ui/button.tsx` · `components/app-shell.tsx` · `app/additionalLearning.ts`(추가 학습 목록과 `entryForTarget` 을 옮기고 고정 `key` 를 줌) · `components/home/HomeDashboard.tsx`.
- 바뀌는 파일: `package.json` · `app/globals.css` · `app/layout.tsx` · `app/page.tsx`(세션 논리는 그대로, 대기 상태만 대시보드로) · 각 화면의 문구.
- 문구에 기대지 않도록 `data-testid` 를 더함: `start-session` · `practice-<key>` · `session-failed` · `course-mode-manual` · `course-mode-auto` · `course-start` · `course-prev` · `course-next` · `course-retry` · `course-slow` · `course-listen` · `course-finish` · `course-back`.
- 기존 문법 코스 `data-testid` 13개와 `data-phase` · `data-attempts` · `data-verdict` 는 그대로 둠.

## 5. 대시보드 칸과 데이터

각 칸은 따로 불러 따로 실패함. 한 요청이 실패해도 그 카드만 비고 「Start speaking」은 늘 눌림. 첫 렌더는 모두 「불러오는 중」이라 하이드레이션 어긋남이 없음.

| v0 칸 | 데이터 | 표시 | 없을 때 |
|---|---|---|---|
| 날짜 | 브라우저 날짜(마운트 뒤) | `Sun, Nov 1` | 빈 줄 |
| 인사 「Good morning, Alex」 | 이름 데이터 없음 | `Welcome back.` | — |
| 연속 학습일 | `/api/history` `streak.current` | `3 days in a row` | `Start a streak today` |
| 오늘의 연습 | `next-plan.reason` | 그 문장 | `Let's talk in English.` |
| 레벨 | `next-plan.target_level` | `Speaking · Level A2` | `Speaking` |
| 진도 68% | 문법 코스 완료 Day 수 / 6 | `Course 2 / 6 days` + 막대 | `0 / 6 days` |
| 세션 · 분 · 패턴 | 주간 `session_count` · `streak.longest` · `pattern_count` | `4 Sessions` · `7 Best streak` · `5 Patterns` | `–` · `No weekly report yet.` |
| 주간 목표 4/5 | 최근 7일 중 학습한 날 | `This week: 4 / 7 days` | `0 / 7 days` |
| Continue your path | `/api/course` 의 진행 중 Day 와 다음 Day | `Day 3 · Units 42–62 · 69 min` → `/course/3` | `Can't load the course.` |
| Focus patterns | 오늘 패턴(분석됨) 아니면 주간 상위 패턴 셋 | `target_form` · `3 times today` | `No patterns yet. Start speaking to find them.` |
| 패턴 % 막대 · 「+8% this month」 · 아바타 | 데이터 없음 | 뺌 | — |
| 빠른 카드 셋 | 쉐도잉 · `/videos` · 약점 패턴 집중 | 그 학습을 시작 | — |
| More practice(새로 둠) | 추가 학습 목록 전부 | 버튼 줄 | PRD §7 은 추가 학습을 늘 보이게 함 |

## 6. 백엔드에서 오는 한국어 — 이번 범위 밖(미결)

백엔드를 바꾸지 않는다는 결정 3 에 따라 다음은 한국어로 남음. 영어로 바꾸려면 프롬프트·콘텐츠 변경이 필요하므로 따로 태스크로 둠(`TASK-299`).

1. `next-plan.reason`(홈의 큰 문장) — `services/plan.py` 프롬프트가 한국어 한 문장을 요구함
2. 오류 패턴 `target_form` 의 한국어 자리 표시(`go to the + 장소 명사`)
3. 교정 이유·설명 · 세션 요약 · 주간 인사이트(각 프롬프트가 한국어를 요구함)
4. 문법 코스 단원 `topic`(`content/grammar_basic.json`)
5. 낱말 뜻·번역(설계상 한국어 — 그대로 두는 것이 맞을 것으로 봄)
6. 음성 명령 안내(「헤이, 학습 종료」) — 영어 명령이 실제로 통하는지 실물 음성으로 확인되지 않았음. 확인 전에는 화면 안내를 영어 명령으로 단정하지 않음

## 7. 구현 태스크

| 태스크 | 내용 | 선행 |
|---|---|---|
| `TASK-293` | 도구·토큰: 의존성 · PostCSS · shadcn 버튼 · `globals.css` 밝은 테마 · `layout.tsx` | — |
| `TASK-294` | 공통 틀: 사이드바·좁은 화면 막대 | 293 |
| `TASK-295` | 홈 분리: 추가 학습 목록 분리 · 세션 덮개 층 | 293 |
| `TASK-296` | 대시보드: §5 대응대로 | 294 · 295 |
| `TASK-297` | 모든 화면 영어 문구 · 시험용 `data-testid` | 295 |
| `TASK-298` | 하네스 갱신 · 통합 회차 · codex 리뷰 | 296 · 297 |

## 8. 위험과 확인 방법

- 층 밖 CSS 가 유틸리티를 이김 → `globals.css` 에 층 밖 `*`·`a`·`body`·`html` 규칙이 없는지 grep 함. 8개 경로를 찍어 버튼 테두리·제목 크기를 봄
- Tailwind 가 안 돎 → `npm run build` 통과 · 브라우저에서 shadcn 버튼 높이가 32px 인지 봄
- 대비 → `measure_contrast.py --schemes light` 에서 본문·흐린 글자 둘 다 4.5:1 이상
- 하이드레이션 경고 → 날짜는 effect 에서만 정함 · 개발 서버 콘솔을 봄
- 실시간 세션 깨짐 → 세션 논리는 문구 외 손대지 않음 · 하네스 C1·C5·앱 경로와 회차 하나로 확인
- 번들 크기 → 아이콘은 이름으로만 가져옴 · `/` 의 First Load JS 를 전후 비교함
- 회차 드라이버의 한국어 선택자 → 옛 회차는 증거로 두고 새 회차는 `data-testid` 로 고름
- 회차는 dev DB 가 아니라 격리 DB(`ohmyenglish_course_paid`)와 `VOICE_ADAPTER=stub` 으로 돌림 — 스텁 세션이 학습 데이터를 오염시키지 않게 함
