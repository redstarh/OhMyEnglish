# Brief — OhMyEnglish 모바일 홈 (스크롤 없는 한 화면)

> Written 2026-11-15 in phase P1. Approved by the user: yes, 2026-11-15.
> 기존 앱(`app/frontend`, Next 16 · Tailwind v4)의 **모바일 폭 홈만** 다시 잡는 시안임. 데스크톱(1400) 배치는 바꾸지 않음.
> 현재 디자인 정본: `docs/design/2026-11-01-v0-home-redesign-design.md` §3.

## Raw input

1. 사용자(2026-11-15): 「접속 확인했어. 모바일 창에서 스크롤이 생기는데 디자인 에이전트로 모바일 페이지에 대해 스크롤 생기지 않게 다시 디자인 시안을 잡고 아이폰에서 테스트 하기 전에 미리 시뮬레이터로 시뮬레이션 해봐. 필요하면 xcode 를 사용해도 되고, 다른 시뮬레이터를 사용해도 돼」
2. 사용자: 「내폰은 현재 12 max 야, 아이폰 버전별로 따로 만들어야 하는거야?」 → 답: 따로 만들지 않음. 한 배치가 화면 높이에 맞춰 바뀜.
3. 홈 구성 질문의 답: 「연습만 두고 나머지는 별도 화면」 — 홈에는 오늘의 연습 카드와 진도 한 줄 요약만 둠. 상세 진도 · 경로 · 패턴은 헤더 버튼으로 여는 다른 화면으로 옮김.
4. 대상 크기 질문의 답: 「12 Pro Max + iPhone 16 (권장)」 — 428×745 와 393×659 둘 다 스크롤 없음.
5. 연습 중 화면 질문의 답: 「연습 카드가 화면 전체 (권장)」 — 연습 중에는 진도를 숨기고 문장 · 말한 내용 · 버튼만 크게 보임. Close 로 돌아옴.
6. 사용자(2026-11-15, 시안 작성 전): 「화면 시안이 나오면 로그인 되어 있는 https://v0.app/redstarhs-projects 에 최종 화면 시안에 대해 검토를 받고 변경된 모양으로 다시 보여줘. 기존 web 화면도 검토 받아. 화면이 부족하면 다른 것은 제거해도 돼. 매일매일 문장 연습이 이 앱의 주목적이야」
   → 우선순위: 매일 문장 연습이 화면의 주인공임. 공간이 모자라면 진도 요약 · 부가 문구 같은 다른 요소를 빼도 됨.

## Product

OhMyEnglish 는 한국인 성인 학습자 한 명(사용자 본인)이 매일 짧은 영어 문장을 듣고 소리 내어 따라 말하는 연습 앱임.
홈의 「Today's practice」에서 그날 Day(문장 묶음)의 문장을 하나씩 듣고(Listen) 말하고(Say it) 판정(Check)받음.
말하는 동안 말한 내용이 실시간으로 문장 아래에 보임(Web Speech). KO 를 켜면 문장 아래 한국어 번역이 보임.
사용 맥락: 아이폰 Safari 로 tailnet 주소에 접속해 손에 들고 소리 내어 연습함. 한 손 조작 · 짧은 세션.

## Platform

모바일 웹(iPhone Safari, 세로). 실측한 Safari 가시 영역(상태 막대 아래 · 아래 주소 막대 위):

| 기기 | 가시 영역(CSS px) | 근거 |
|---|---|---|
| iPhone 12 Pro Max(사용자 폰) | 428×745 | iOS 시뮬레이터 스크린샷 2026-11-15 |
| iPhone 16 | 393×659 | iOS 시뮬레이터 스크린샷 2026-11-15 |

시안은 두 크기 모두에서 스크롤 없이 완결되어야 함. 높이는 `100dvh` 기준으로 맞춰짐(기기별 화면을 따로 만들지 않음).

## Screens

| id | purpose | key content | viewport |
|---|---|---|---|
| home-idle | 앱을 열면 보이는 홈. 오늘 할 일을 바로 시작함 | 헤더(로고 · 앱 이름 · 진도 화면으로 가는 버튼) · 진도 한 줄 요약(예: 「0 / 6 days · This week 0 / 7」) · 오늘의 연습 카드(TODAY'S PRACTICE · 「Day 1: listen and say it.」 · 설명 한 줄 · Start speaking · 「Day 1 · Units 1–21」) | 428x745 · 393x659 |
| home-practice | Start speaking 뒤 문장 연습. 카드가 화면 전체 | TODAY'S PRACTICE · ← Close · 「Day 1 · Units 1–21」 · 단원 이름(「Unit 15 · used to」) · KO · Auto · Manual 전환 묶음 · 「Sentence 3 / 5」 · 「Try 1」 · 문장(「We used to deploy by hand.」) · 말한 내용 실시간 줄(문장과 같은 글자) · 결과 줄(「All words matched」 또는 「Sentence:」) · ← Previous · Start/Try again · Next → | 428x745 · 393x659 |
| home-practice-ko | home-practice 에 KO 를 켠 상태 | 위와 같음 + 문장 아래 한국어 번역 한 줄(「우리는 예전에 손으로 배포하곤 했다.」) | 428x745 · 393x659 |
| progress | 홈에서 옮긴 상세 화면 | ← Home · Your progress(「0 / 6 days」 · 진도 막대 · Grammar course · This week 0 / 7 days · Best streak 1 day · 「Last week · Nov 2 – Nov 8」 Sessions 0 · Patterns 0 · History → · Weekly report →) · Continue your path(Day 1 · In progress · Units 1–21 / Day 2 · Up next · Units 22–41 · View all) · Focus patterns(빈 상태 「No patterns yet. Start speaking to find them.」) | 428x745 · 393x659 |

## Features in scope

- 오늘의 연습: Start speaking · Close · KO 켬/끔 · Auto/Manual · ① Listen → ② Say it(실시간 줄) → ③ Check → 판정 · Try again · ← Previous / Next → · Finish Day
- 진도 요약 한 줄(홈)과 상세 진도(progress 화면)
- 경로: Day 줄(누르면 그 Day 연습) · View all ↔ Show less
- Focus patterns 목록(빈 상태 포함)
- History → · Weekly report → (기존 화면으로 이동)
- 이 목록 밖의 것(Free talk · Weak spots · More practice · Practice a pattern · 영상)은 그리지 않음 — 사용자 결정으로 홈에서 숨김(TASK-338)

## Language and tone

UI 는 영어(기존 앱 그대로). 버튼은 동사로 시작하는 짧은 말(Start speaking · Try again · Next →). 섹션 라벨은 대문자 자간 넓힘(TODAY'S PRACTICE). 한국어는 번역 줄에만 나옴. 이모지 없음.

## Brand and mood

기존 앱의 색과 글꼴을 그대로 씀 — 새 브랜드를 만들지 않음.
- 남색 머리 카드 `--hero` #172b63(흰 글자 13.4:1) · 바탕 `--page` #f7f8fc · 카드 #ffffff · 테두리 #e7eaf1
- 강조(앞으로 가는 이동 · 선택된 전환) `--accent` #3263dc(흰 바탕 5.3:1) · 연한 강조 #edf2ff · 회색 버튼 바탕 #f2f4f9
- 글자 #172033 · 흐린 글자 #5b6478 · 위험 #cc0000
- 글꼴 Geist(없으면 시스템 sans) · 둥근 모서리 10 px 기준 · 버튼(omy-button) 36 px 안팎 · 13.6 px · 모서리 8 px
- 분위기: 조용하고 내용 우선. 연습 중에는 문장이 주인공.
- 로고: 남색 둥근 사각 안 반짝임(sparkles) 아이콘 + 「OhMyEnglish」 · 「SPEAK. REMEMBER. GROW.」

## Constraints

- 428×745 와 393×659 에서 세로 · 가로 스크롤 0. 가장 긴 상태(KO 켬 · 결과 줄 · 두 줄 문장)도 포함
- 연습 카드의 높이는 상태가 바뀌어도 변하지 않음(대기 → 듣기 → 말하기 → 판정에서 버튼이 튀지 않음 — 기존 결정 TASK-310·319)
- 터치 대상 최소 44 px 높이(아이폰 한 손 조작)
- WCAG AA 대비 · 밝은 테마만 · 이모지 없음
- iPhone 홈 막대·노치 영역(safe-area) 침범 없음

## Out of scope

- 데스크톱(1400) 배치 변경
- 기록 · 주간 · 영상 · 결과 · 세션 화면(이미 659 안에 들어감)
- 새 기능 · 새 문구 · 설정 화면

## Assumptions

- 진도 화면으로 가는 헤더 버튼의 이름과 아이콘은 작가가 고르되 기존 아이콘(trending-up)을 우선함
- 문장이 두 줄이 되는 긴 문장도 들어가야 함(가장 긴 문장 기준은 작가가 예시로 보임)
