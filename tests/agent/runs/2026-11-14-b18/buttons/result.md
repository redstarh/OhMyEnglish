# 회차 2026-11-14-b18 · 버튼 탭 결과 (`TASK-330`)

## 0. 먼저 볼 것

- 동작 판정은 146건임. 통과 143 · 차단됨 2 · 불확실 1 · 실패 0 임.
- 차단됨 2건은 두 폭의 N17 임. 헤드리스에서 영상 재생 위치가 0:00 에 머물러 「구간 끝」 성공 경로를 세우지 못했음(§3 · §4).
- 불확실 1건은 1400×900 의 H1 임. 이 크기는 문서 높이가 창 높이와 같아(900) 스크롤 여지가 없음. 그래서 같은 판정을 1400×860 · 1400×700 · 390 에서 했고 모두 통과했음.
- b16 결함 D1 · D2 · D3 은 고쳐졌음. D4 는 일부만 고쳐졌음. b16 의 문서 불일치(세션 중 View all)는 설계서 정정(`TASK-320`)과 동작이 일치함(§5).
- 새 결함은 1건임(B18-D1 · 영상 화면들의 버튼에 testid 없음 · D4 잔여). 판정 밖 관찰은 2건임(§6).

## 1. 환경

| 항목 | 값 |
|---|---|
| 시작 · 끝 HEAD | `0428af4` 그대로임. 회차 끝 `git status --short -- app docs` 출력 0줄 |
| 앱 · 백엔드 | `localhost:3000` 200 · `localhost:8002/health` 200. 호출자가 띄웠고 나는 재기동·종료하지 않았음 |
| 브라우저 | CDP `127.0.0.1:9462` · HeadlessChrome 157.0.8103.52 · Playwright 1.58.2 `connectOverCDP`. 페이지만 열고 닫았음 |
| 폭 | 1400×900 · 1400×860 · 1400×700(H1 용) · 390×844 |
| 공유 | 화면 탭이 같은 앱·같은 격리 DB 를 씀. 회차 중 남의 세션 2개(`5e7e1ed1…` · `75fc1f96…`)와 남의 문장 시도 2건(UTC 12:24:48 · 12:25:02)이 생겼음. 내 세션은 ID 로만 가렸음 |
| 쓰기 경계 | `runs/2026-11-14-b18/buttons/` 아래뿐임. 앱 소스·`docs/`·리포 원장·테스트 원장은 고치지 않았고 커밋하지 않았음(공통 지시 4) |
| DB 조회 | `db.py paid sql|snap` · `db.py dev snap` 만 씀(읽기 전용). psql 은 쓰지 않았음 |
| 런처 | 전용 런처 세션임(샌드박스 쓰기 경계 적용) |

## 2. 버튼·링크 목록 (`evidence/inventory.json` · `inventory-summary.txt`)

모양은 1400 에서 잰 값임. 390 은 사이드바 `nav-home` 이 없는 것만 다름. 기준 `omy-button` 은 36.4 px · 13.6 px · 회색 `rgb(242, 244, 249)` · 파란 바탕 `rgb(50, 99, 220)` 임.

| 화면 | testid(없으면 문구) | 태그 | href | 모양 |
|---|---|---|---|---|
| 공통 틀 | 로고 「OhMyEnglish」 · `nav-home`(1400) | a | `/` | 메뉴(범위 밖) |
| 홈 | `start-session` 「Start speaking」 | button | - | 36 · 14px · 남색 카드 위 흰 바탕 |
| 홈 | `home-history` 「History →」 · `home-weekly` 「Weekly report →」 | a | `/history` · `/history/weekly` | omy · 파란 바탕 |
| 홈 | `home-path-all` 「View all / Show less」 · `focus-practice` 「Practice a pattern」 | button | - | omy · 회색 |
| 홈 | `path-day-N` | button | - | Day 경로 카드 58(범위 밖) |
| 홈 | `practice-free_talk` · `-weak_patterns` · `-five_questions` · `-pronunciation` · `-shadowing` · `-roleplay`(disabled) | button | - | omy · 회색 |
| 홈 | `practice-videos` 「Learn with videos」 | a | `/videos` | omy · 회색 |
| 홈 문장 연습 | `practice-close` 「← Close」 | button | - | omy · 회색 |
| 홈 문장 연습 | `course-translation` 「KO」 · `course-mode-auto` · `course-mode-manual` | button | - | 전환 27.2 · 12.8px · 모서리 6px · 켜짐만 파란 바탕 |
| 홈 문장 연습 | `course-prev` 「← Previous」 · `course-start`/`course-retry` | button | - | omy · 회색 |
| 홈 문장 연습 | `course-next` 「Next →」 · `course-finish` 「Finish Day」 | button | - | omy · 파란 바탕 |
| 실패 화면 | `session-failed-retry` 「Try again」 · `session-failed-home` 「← Home」 | button | - | omy · 회색 |
| 세션 화면 | `session-end` 「End lesson」 | button | - | omy 36.4 · 13.6px · 회색 |
| `/history` | `history-weekly` 「Weekly report →」 · `history-home` 「← Home」 | a | `/history/weekly` · `/` | omy · 파란 / 회색 |
| `/history` | 날짜 줄 `history-day-group`(summary) · `history-session-link` · 대역에서 `history-day-link` | details/a | `/results/<id>` | 목록 항목(범위 밖) |
| `/history/weekly` | `weekly-history` 「← History」 · `weekly-home` 「← Home」 | a | `/history` · `/` | omy · 회색 |
| `/results/<id>` 발화 있음 | `results-home` 「← Home」 · `results-history` 「History →」 | a | `/` · `/history` | omy · 회색 / 파란 |
| `/results/<id>` 발화 0 | 위 둘 + `results-start-again` 「Start again →」 | a | `/` | omy · 파란 |
| `/course` · `/course/1` | 홈으로 넘어감 — 도착 화면의 목록이 홈과 같음 | - | - | - |
| `/videos` | `videos-home` 「← Home」 · 「Check」 · 「Delete」 · 영상 제목 | a/button | `/` · `/videos/<id>` | omy(제목은 범위 밖) |
| `/videos/<id>` | `video-back` 「← Videos」 · 「Mark a hard part」(→ 「End the hard part here」 · 「Cancel」 · Save) | a/button | `/videos` | omy · 회색 |

## 3. 동작 판정 (`evidence/*.json` 의 행 ID)

### 홈 (`home-1400x900.json` · `home-1400x860.json` · `home-1400x700.json` · `home-390x844.json`)

| ID | 동작 | 기대 | 1400×900 | 1400×860 | 1400×700 | 390 |
|---|---|---|---|---|---|---|
| H1 | Start speaking | 1.5초 동안 매 프레임 scrollY 가 시작값 · 카드 높이가 대기 높이(513.6) 아래로 안 감 · 주소 `/` | 불확실(스크롤 여지 0 · y 0) | 통과(34 고정 · 90프레임) | 통과(194 = 최대값 고정 · 89프레임) | 통과(40 고정) |
| H2 | 현재 Day 줄 강조 | `path-day-1` 만 `data-selected` | 통과 | 통과 | 통과 | 통과 |
| H3 | ← Close | `idle` · 강조 0 | 통과 | 통과 | 통과 | 통과 |
| H4 | View all ↔ Show less | 2 → 6(`aria-expanded=true`) → 2 | 통과 | 통과 | 통과 | 통과 |
| H5 | Day 4 줄 | 주소 `/` · Day 4 연습 · 그 줄만 파란 테두리 | 통과 | 통과 | 통과 | 통과 |
| H6 | 연습 중 Day 2 줄 | 카드가 Day 2 · 강조 이동 | 통과 | 통과 | 통과 | 통과 |
| H7 | More practice 구성 | `practice-course` 0 · 「Grammar course」 0 · `quick-*` 0 | 통과 | 통과 | 통과 | 통과 |
| H8 | Work role-play | disabled | 통과 | 통과 | 통과 | 통과 |
| H9 | 아래쪽 Day 2 줄(390) | 카드 bottom −94 → top 0 · 연습 열림 | - | - | - | 통과 |
| H10 · H11 | History → · Weekly report → | 파란 바탕 · 그 주소 | 통과 | 통과 | 통과 | 통과 |
| H12 | Learn with videos | `/videos` | 통과 | 통과 | 통과 | 통과 |
| H13 · H14 | 사이드바 Home · 로고 | `/history` → `/` | 통과 | 통과 | 통과 | 통과(H14 만) |

### 문장 연습 (`practice-1400.json` · `practice-390.json` · 두 폭 같음)

가짜 `SpeechRecognition`(b17 `live.mjs` 방식)을 심었음. 판정 요청 `**/attempts/text` 와 진도 저장 `**/days/*/progress` 는 **`page.route` 로 막았음**(가짜 응답 · 횟수 = 100 + 요청 순번). 그래서 내 실행은 격리 DB 에 시도·진도를 남기지 않았음.

| ID | 동작 | 관측 | 판정 |
|---|---|---|---|
| K1 | KO 켬 | `aria-pressed=true` · 「저희는 세 시에 회의가 있어요.」 · localStorage `on` · 카드 513.6 → 558.4(34.9rem). 대조로, 켜기 전 번역 0개 | 통과 |
| K2 | 새로 고침 → Start speaking | KO 켜진 채 · 번역 보임 · 대기 카드도 558.4 | 통과 |
| K3 | KO 끔 → 새로 고침 | 끈 직후 번역 0 · 새로 고친 뒤에도 끔 | 통과 |
| P1 | Manual | manual `true` · auto `false` · localStorage `manual` | 통과 |
| P2 | Start → ① → ② → ③ → 판정 | 단계 `idle>listen>repeat>judge>done` · repeat 중 실시간 줄 「We have」(그때 POST 0) · POST 1 · 판정 낱말 6 · 실시간 줄 지움 · Try 2→101 · Start 자리가 Try again · 같은 문장 | 통과 |
| P3 | Try again | `done>listen>repeat>judge>done` · POST +1 · Try 101→102 | 통과 |
| U1 | 말 없음 | 약 5.3초 뒤 「I couldn't hear you. Press "Try again" and say it again.」 · POST 0 · Try 102→102 | 통과 |
| P4 | Next → | 3/5 → 4/5 · 단계 표시 없음 · Start 보임 · 앞 안내 지움 | 통과 |
| P5 | ← Previous | 문구 「← Previous」 · 4/5 → 3/5 | 통과 |
| P6 | Auto · Start | done 뒤 3/5 → 4/5 · listen 재개 | 통과 |
| P7 | 자동 연습 도중 ← Close | `idle` · 인식기 `abort` 호출 | 통과 |
| P8 | Finish Day(Day 6) | Next 64회 뒤 Unit 113 5/5 · Next 사라지고 Finish Day(파란 바탕) · done 전 disabled → 뒤 enabled · 「You finished this Day!」 · Unit 101 1/5 · 완료 저장 요청 `completed=true` 1건(막았음) | 통과 |

### 홈 밖 이동 (`nav-1400.json` · `nav-390.json` · 두 폭 같음)

| ID | 화면 → 버튼 | 결과 | 판정 |
|---|---|---|---|
| N1 · N2 | `/history` → Weekly report →(파란) · ← Home | `/history/weekly` · `/` | 통과 |
| N3 · N4 | `/history/weekly` → ← History · ← Home(`weekly-home`) | `/history` · `/` | 통과 |
| N5 | 세션 여럿인 날 줄 | 닫힘(보이는 링크 0) → 펼침 → 링크 수 = 「8 lessons」 · 제목 있음(예 「Exchanging something you bought →」) → 첫 제목 `/results/3e460593…` | 통과 |
| N6 | 세션 하나인 날 줄(대역) | `history-day-link` 「2026-11-14 · Studied →」 · omy 아님 · `/results/3e460593…` | 통과(대역 응답) |
| N7 · N8 | `/results`(발화 있음) → ← Home · History →(파란) | `/` · `/history` | 통과 |
| N9 | `/results`(발화 0) 문구 | 「We didn't hear you this time.」 · `results-done` 0 · 「Check your microphone, then start a new lesson from Home.」 | 통과 |
| N10 · N10b | Start again →(파란) | `/` · 도착한 카드가 `idle`(세션을 스스로 열지 않음) | 통과 |
| N11 · N12 | `/course` · `/course/1` 직접 열기 | 요청 사슬 `/course(/1)` → `/` · 홈 카드 있음 | 통과 |
| N13 | `/videos` → ← Home | `/` | 통과 |
| N14 | `/videos` Check(누르지 않음) | 빈칸 disabled → 주소 입력 뒤 enabled | 통과 |
| N15 | 영상 제목 | `/videos/b502eaf3…` | 통과 |
| N16 | Mark a hard part → Cancel | 「The hard part starts at 0:00. Press the button when it ends.」 + End the hard part here + Cancel(모두 omy) → Cancel 로 처음 상태 | 통과 |
| N17 | Mark a hard part → End the hard part here → Cancel | 재생 위치가 0:00 그대로라 앱이 「The end must come after the s…」 안내를 냄. Cancel 은 처음 상태로 되돌림 | 차단됨(§4) |
| N18 | ← Videos | `/videos` | 통과 |

### 세션 (`session-1400.json` · `session-390.json` · `entries-*.json`)

| ID | 동작 | 관측 | 1400 | 390 |
|---|---|---|---|---|
| F1 | Free talk(마이크 거부) | 카드 안 `session-failed` · `microphone_permission_denied` | 통과 | 통과 |
| F2 | 실패 화면 동안 잠금 | 링크 3개 `aria-disabled=true` · 세션 버튼·Day 줄 disabled · 로고·`nav-home` 잠김 · nav `data-locked=true`. 대조로, 열기 전에는 모두 풀림 | 통과 | 통과 |
| F3 | 잠긴 History → DOM 클릭 | 주소 `/` 그대로 | 통과 | 통과 |
| F4 | `session-failed-retry`(testid 로 고름) | `getUserMedia` 1→2 · 다시 실패 화면 | 통과 | 통과 |
| F5 | ← Home | `idle` · 잠금 모두 풀림 | 통과 | 통과 |
| S1 | Free talk | 1400: 연 문장 연습이 닫히고 카드 안 세션. 390: 맨 아래(top −655)에서 눌러 top 0 | 통과 | 통과 |
| S2 · S3 | 세션 중 잠금 · 잠긴 Weekly report → DOM 클릭 | F2 와 같음 · 주소 `/` · 세션 유지 | 통과 | 통과 |
| S4 | 세션 중 View all | 펼쳐짐 · Day 줄 6개 모두 disabled · 세션 유지(`TASK-320` 정정과 같음) | 통과 | 통과 |
| S5 | End lesson(`session-end`) | 누른 직후 「Ending...」 → `/results/<id>`. id 가 `session_started` 의 ID 와 같음 | 통과 `b65b8d2b…` | 통과 `48fdc44d…` |
| E1~E6 | Free talk · Weak spots · 5 questions · Pronunciation · Shadowing · Practice a pattern | 가짜 소켓 질의가 `additionalLearning.ts` 의 진입과 같음. 390 은 카드 밖(top −367~−543)에서 눌러 top 0 | 통과 6/6 | 통과 6/6 |

실제 Nova 세션은 2개(S 1400 · S 390)임. 둘 다 DB 에 `ended_at` 이 있음(UTC 12:34:14 · 12:34:33). E1~E6 은 그 페이지의 `/ws/session` 만 가짜로 바꿔 서버에 붙지 않았음.

## 4. 관측 수단의 양성 대조 · 판정 정정

- H1 프레임 기록기: `probe-frames.json` 에서 같은 기록기가 390 아래쪽 Day 2 줄(스크롤이 일어나는 입구)에서 scrollY 값 25개(697 → 89)를 잡았음. 그래서 H1 의 「값 1개」는 기록기가 눈먼 결과가 아님.
- 모양 측정: 기준 버튼(`course-prev/start/next` · `practice-close`)이 같은 측정기로 36.4 px · 13.6 px 임.
- 잠금 측정: 같은 함수가 대기 상태에서는 모두 「풀림」으로 읽었음(F2 의 `before free=true` · F5).
- 판정 요청 대역: 문장 연습의 Try 값이 대역이 준 101 · 102 였음. 그리고 회차 중 격리 DB 에 생긴 문장 시도 2건은 내 문장 연습 실행(KST 21:28~21:30) 전인 21:24:48 · 21:25:02 임. 그 사이 돈 내 스크립트(목록 · 홈)는 Start 를 누르지 않음.
- 목록 측정기 정정: 첫 목록은 닫힌 `details` 안의 세션 링크 104개를 「보임」으로 셌음(문구가 빈 칸). `checkVisibility()` 를 더해 다시 떴고 지금의 `inventory.json` 이 그 결과임.
- N17 정정: 기록상 「실패」를 차단됨으로 다시 판정함. 앱은 끝 ≤ 시작을 막는 안내를 정상으로 냈음. 프로그램의 오동작이 아니라, 성공 경로에 필요한 재생 위치 이동을 헤드리스에서 세우지 못한 것임.
- H1@1400×900: 문서 높이 900 = 창 높이라 `scrollTo(0, 40)` 이 0 으로 남았음. b16 은 같은 크기에서 문서 951 이었음. 홈 내용 높이가 줄어 이 크기에서는 D1 의 전제가 성립하지 않음.

## 5. b16 결함 대조

| b16 | 내용 | 이번 관측 | 분류 |
|---|---|---|---|
| D1 | 1400×900 Start speaking 이 scrollY 를 0 으로 옮김 | 1400×860(34) · 1400×700(최대 194) · 390(40)에서 매 프레임 그대로이고, 카드 최소 높이가 513.6 이라 335 로 내려가지 않음. 고쳐진 것으로 볼 조건 2개를 모두 만족함 | 고쳐짐 |
| D2 | 홈 History → · Weekly report → 가 회색 | 두 링크 `omy-button-primary` · `rgb(50, 99, 220)` | 고쳐짐 |
| D3 | `omy-button` 이 아닌 실행 버튼 묶음 | More practice 7개 · View all · Practice a pattern · End lesson · Check · Delete · Mark 계열 모두 omy 36.4 · 13.6px | 고쳐짐 |
| D4 | testid 없는 실행 버튼 | `session-end` · `session-failed-retry` · `history-*` · `weekly-*` · `results-*` · `videos-home` · `video-back` 이 생겼음. 영상 화면들의 Check · Delete · 영상 제목 · Mark a hard part · End the hard part here · Cancel · Save 는 여전히 없음 | 일부 고쳐짐 → B18-D1 |
| 문서 불일치 | 세션 중 View all 잠김 | 설계서가 `TASK-320` 으로 정정했고 동작(S4)이 정정과 같음 | 해소 |

b16 의 모양 불확실 셋 중 둘은 대상이 사라졌음(빠른 카드 제거 · `/course` 리다이렉트). 남은 하나(`start-session`)는 §6 에 적음.

## 6. 새 결함 · 관찰

### B18-D1 · 영상 화면들의 버튼에 testid 가 없음 (b16 D4 잔여)

- 재현: `/videos` 와 `/videos/<id>` 를 열고 `[data-testid]` 가 없는 button · a 를 셈.
- 기대: 실행 버튼은 testid 로 고를 수 있음(공통 지시 5 · 다른 화면은 모두 고쳐졌음).
- 실제: `/videos` 의 「Check」 · 「Delete」 · 영상 제목 링크, `/videos/<id>` 의 「Mark a hard part」 · 「End the hard part here」 · 「Cancel」 · Save 에 testid 가 없음. 그래서 N14~N17 은 문구로 골랐음.
- 증거: `evidence/inventory.json` 의 `videos` · `video` 항목 · 소스 `app/videos/page.tsx` · `app/videos/[videoId]/page.tsx`.
- 고쳐진 것으로 볼 조건: 위 버튼과 링크에 `data-testid` 가 있음.
- 제안: `videos-check` · `videos-delete` · `videos-title` · `video-mark-start` · `video-mark-end` · `video-mark-cancel` · `video-span-save` 같은 이름을 줌.

### 관찰(판정 밖)

- `start-session` 「Start speaking」 은 여전히 omy 가 아님(36 px · 14 px · 남색 카드 위 흰 바탕). 설계서 `TASK-323` 목록에 없고 남색 카드 위 예외도 적혀 있지 않음. 불확실로 둠.
- 「Learn with videos」(`practice-videos`)는 다른 화면으로 가는 링크인데 회색임. More practice 묶음이 모두 회색이라 의도로 읽히지만, 「앞으로 가는 이동만 파란 바탕」 규칙에 이 경우가 적혀 있지 않음.
- KO · Auto · Manual 은 같은 모양임(27.2 px · 12.8 px · 모서리 6 px · 켜짐만 파란 바탕). KO 는 테두리 묶음이 따로이고 Auto/Manual 왼쪽에 있음. 설계서 `TASK-328` 과 같음.
- 단원 주제가 여전히 한국어로 보임(「Unit 113 · 구동사 2 put on · take off · turn on」). 설계서 §6 이 범위 밖으로 둠.

## 7. 미실행 · 남긴 자료

- 미실행: `/videos` Check 실행·Save·Cancel(바깥 조회와 저장) · Delete(파괴) · 구간 Save(저장) · 「Open on YouTube」(재생 가능 판정이라 그려지지 않음) · 결과 화면 드릴 링크(표본 세션에 없음) · 세션 화면 안의 다시 듣기·번역·쉐도잉·리포트 버튼(가짜 마이크라 발화 없음).
- 격리 DB 에 내가 남긴 것: 코치 세션 2개(`b65b8d2b-04ed-4e5f-afcb-351108e24d9f` · `48fdc44d-09e0-43e3-bdf9-df8c9de252d6`)와 그 분석 작업. 그리고 `session.mjs 1400` 이 Free talk 전에 문장 연습을 열어 Day 1 진도 저장(같은 위치)이 있었을 수 있음 — 그 페이지는 저장을 막지 않았음. 끝 스냅샷: 세션 112 · 시도 16 · 진도 6 행.
- dev DB `ohmyenglish` 는 기준선(`db-dev-start.json`)과 같음(세션 25 · 시도 68).
- localStorage 의 KO · 모드는 practice.mjs 가 처음 값으로 되돌렸음(`practice-*-storage.json`).
- 스크립트: `lib.mjs` · `inventory.mjs` · `summarize.mjs` · `home.mjs` · `probe-frames.mjs` · `practice.mjs` · `nav.mjs` · `entries.mjs` · `session.mjs`. 증거는 `evidence/` 에 있음.
- 원장: 공통 지시 4에 따라 리포 원장과 테스트 원장을 고치지 않았음. B18-D1 등록과 `TASK-330` 상태 갱신은 호출자 몫임.
