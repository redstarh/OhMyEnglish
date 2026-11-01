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
