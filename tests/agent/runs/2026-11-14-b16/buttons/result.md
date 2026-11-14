# 회차 2026-11-14-b16 · 버튼 탭 결과 (`TASK-316.2`)

## 0. 먼저 볼 것

- 동작 판정은 97건임. 통과 96건 · 실패 1건(D1)임. 실패로 찍힌 3건 중 2건(F2 · S2 @1400)은 드라이버 결함이라 다시 판정했음(§4).
- 모양 판정에서 `omy-button` 기준을 벗어난 이동·실행 버튼은 7묶음임(§5 · D2~D4).
- 결함은 4건임. D1 은 1400×900 에서 Start speaking 이 창을 움직이는 결함임. D2 는 홈의 `→` 이동에 파란 바탕이 없는 결함임. D3 은 `omy-button` 이 아닌 실행 버튼 묶음임. D4 는 `End lesson` · 실패 화면 `Try again` 에 testid 가 없는 결함임.
- 문서 불일치 1건이 있음(§6). 설계서 §3 「세션 화면의 번복」은 세션 중 View all 이 잠긴다고 적음. 실제로는 잠기지 않음.

## 1. 환경

| 항목 | 값 |
|---|---|
| 시작 HEAD | `3c54359`(`e26e89d` 이후) |
| 끝 HEAD | `a5ac4bf` — 회차 중 3커밋이 늘었음. `git diff --stat 3c54359..a5ac4bf -- app` 출력 0줄이므로 앱 코드는 같음. 작업 트리의 `app` · `docs` 도 미변경 |
| 앱 · 백엔드 | `localhost:3000`(next dev) · `localhost:8002`(격리 DB `ohmyenglish_course_paid` · Nova) — 호출자가 띄웠고, 나는 재기동·종료하지 않았음 |
| 브라우저 | CDP `127.0.0.1:9402` · HeadlessChrome 157.0.8103.52 · Playwright 1.58.2 `connectOverCDP` · 페이지만 열고 닫음 |
| 폭 | 1400×900 · 390×844(probe 에서 1400×700 추가) |
| 공유 | 화면 탭이 같은 앱·같은 격리 DB 를 씀. 그래서 DB 판정은 개수가 아니라 세션 ID 로 했음 |
| 쓰기 경계 | 쓰기는 `runs/2026-11-14-b16/buttons/` 아래뿐임. 앱 소스·`docs/`·리포 원장은 고치지 않았고 커밋하지 않았음 |

DB 조회 기록: 처음 2건은 `psql -h 127.0.0.1` 로 읽기 전용 SELECT 를 했음(결과 화면용 세션 ID 조회). 호출자 안내 뒤로는 `runs/2026-11-01-b10/db.py paid snap|sql` 만 씀.

## 2. 버튼·링크 목록 (`evidence/inventory.json` · 화면마다 1400·390)

모양 열은 1400 에서 잰 값(높이 px · 글자 크기)임. 390 은 사이드바 `nav-home` 이 없는 것과 `quick-videos` 높이가 68 인 것(다른 빠른 카드는 70)만 다름.

| 화면 | testid(없으면 문구) | 태그 | href | 모양 |
|---|---|---|---|---|
| 공통 틀 | 로고 「OhMyEnglish」 | a | `/` | 메뉴(범위 밖) |
| 공통 틀(1400) | `nav-home` | a | `/` | 메뉴(범위 밖) |
| 홈 | `start-session` 「Start speaking」 | button | - | 36 · 14px · 흰 바탕(남색 카드) |
| 홈 | `home-history` 「History →」 · `home-weekly` 「Weekly report →」 | a | `/history` · `/history/weekly` | omy 36.4 · 13.6px · 회색 |
| 홈 | `home-path-all` 「View all / Show less」 | button | - | ghost 32 · 12px |
| 홈 | `path-day-N` 「Day N · …」 | button | - | Day 경로 카드(범위 밖) 58 |
| 홈 | `focus-practice` 「Practice a pattern」 | button | - | ghost 32 · 12px |
| 홈 | `quick-shadowing` · `quick-weak-patterns` | button | - | 카드 70 |
| 홈 | `quick-videos` 「Listen & notice」 | a | `/videos` | 카드 70(390 68) |
| 홈 | `practice-free_talk` · `-weak_patterns` · `-five_questions` · `-pronunciation` · `-shadowing` · `-course` · `-roleplay`(disabled) | button | - | outline 36 · 14px |
| 홈 | `practice-videos` 「Learn with videos」 | a | `/videos` | outline 36 · 14px |
| 홈 문장 연습 | `practice-close` 「← Close」 | button | - | omy 36.4 · 13.6px |
| 홈 문장 연습 | `course-mode-auto` · `course-mode-manual` | button | - | 토글 27.2 · 12.8px |
| 홈 문장 연습 | `course-prev` · `course-start`/`course-retry` · `course-next`(primary) · `course-finish`(primary) | button | - | omy 36.4 · 13.6px(기준) |
| 실패 화면 | testid 없음 「Try again」 · `session-failed-home` 「← Home」 | button | - | omy 36.4 |
| 세션 화면 | testid 없음 「End lesson」 | button | - | 40.4 · 16px · 둥근 알약 |
| `/history` | 「Weekly report →」(primary) · 「← Home」 | a | `/history/weekly` · `/` | omy |
| `/history/weekly` | 「← History」 | a | `/history` | omy |
| `/results/<id>` | 「← Home」 · 「History →」(primary) | a | `/` · `/history` | omy |
| `/course` | 「← Home」 · 「Continue ▶」(현재 Day · primary) · 「Start」×5 | a | `/` · `/course/N` | omy |
| `/course/1` | `course-back` 「← Back」 + 문장 연습 버튼(홈과 같음) | a/button | `/course` | omy |
| `/videos` | 「← Home」 · 「Check」 · 영상 제목 · 「Delete」 | a/button | `/` · `/videos/<id>` | Check·Delete 는 34 · 16px 기본 버튼 |
| `/videos/<id>` | 「← Videos」 · 「Mark start」(→ 「Mark end」 · 「Mark again」) | a/button | `/videos` | Mark 계열은 34 · 16px 기본 버튼 |

## 3. 동작 판정 (`evidence/*.json` 의 행 ID)

### 홈 (`home-1400.json` · `home-390.json`)

| ID | 동작 | 기대 | 1400 | 390 |
|---|---|---|---|---|
| H1 | Start speaking | 카드에 문장 연습 · 주소 `/` · scrollY 불변 | **실패**(scrollY 40→0 · D1) | 통과(40→40) |
| H2 | Listen/Slow 부재 | testid·문구 모두 0 | 통과 | 통과 |
| H3 | Start speaking 뒤 강조 | `path-day-1` `data-selected=true` | 통과 | 통과 |
| H4 | ← Close | `data-mode=idle` · 강조 0 | 통과 | 통과 |
| H5 | View all ↔ Show less | 2 → 6(`aria-expanded=true`) → 2 | 통과 | 통과 |
| H6 | Day 4 줄 | 주소 `/` · Day 4 연습 · 그 줄만 파란 테두리 | 통과 | 통과 |
| H7 | 연습 중 Day 2 줄 | 카드가 Day 2 · 강조 이동 | 통과 | 통과 |
| H8 | Grammar course | 현재 Day 1 연습 · 주소 `/` | 통과 | 통과 |
| H9 | Work role-play | disabled | 통과 | 통과 |
| H10~H13 | History → · Weekly report → · Listen & notice · Learn with videos | 그 주소로 이동 | 통과 | 통과 |
| H14 | 사이드바 Home | `/history` → `/` | 통과 | 해당 없음(설계상 메뉴 없음) |
| H15 | 로고 | `/history` → `/` | 통과 | 통과 |

### 문장 연습 (`practice-1400.json` · 홈 카드)

| ID | 동작 | 관측 | 판정 |
|---|---|---|---|
| P1 | Manual | manual `aria-pressed=true` · localStorage `manual` | 통과 |
| P2 | Start(수동) | 단계 `idle>listen>repeat>judge>done` · Start 자리가 Try again · 끝나도 같은 문장 | 통과 |
| P3 | Try again | `done>listen>repeat>judge>done` | 통과 |
| P4 | Next → | 문장 5/5 → 다음 단원 1/5 · 단계 표시 사라짐 · Start 보임 | 통과 |
| P5 | ← Back | 앞 문장으로 돌아감 | 통과 |
| P6 | Auto · Start | done 뒤 다음 문장으로 넘어가 listen 재개 | 통과 |
| P7 | 자동 연습 도중 ← Close | `data-mode=idle` | 통과 |
| P8 | Finish Day(Day 6) | Next 64회 뒤 Unit 113 5/5 에서 Next 가 Finish Day(파란 바탕)로 바뀜 · done 전 disabled → done 뒤 enabled · 「You finished this Day!」 · Unit 101 1/5 로 되감음 | 통과 |

### 홈 밖 이동 (`nav-1400.json` · `nav-390.json` · 두 폭 같음)

| ID | 화면 → 버튼 | 결과 | 판정 |
|---|---|---|---|
| N1 · N2 | `/history` → Weekly report → · ← Home | `/history/weekly` · `/` | 통과 |
| N3 | `/history/weekly` → ← History | `/history` | 통과 |
| N4 · N5 | `/results/<id>` → ← Home · History → | `/` · `/history` | 통과 |
| N6~N8 | `/course` → ← Home · Continue ▶ · Start(Day 3) | `/` · `/course/1` · `/course/3` | 통과 |
| N9 | `/course/1` → ← Back(`course-back`) | `/course` | 통과(1400 첫 실행은 내 대기 조건 탓에 불확실이었고, 고쳐 다시 돌렸음) |
| N10 · N11 | `/videos` → ← Home · 영상 제목 | `/` · `/videos/<id>` | 통과 |
| N12 | `/videos/<id>` → ← Videos | `/videos` | 통과 |
| N13 | 결과 화면의 드릴 링크 | 이 세션에 드릴 항목이 없어 출구 2개만 있음 | 통과(드릴 링크는 미관측) |
| N14 | 영상 화면 「Open on YouTube」 | 재생 가능해 링크가 그려지지 않음 | 통과(미관측) |
| N15 | Mark start → Mark again | 「Mark end」 · 「Mark again」 이 나타남 → 되돌리면 「Mark start」 만 남음(저장 안 함) | 통과 |
| N16 | `/videos` Check | 빈칸 disabled → 주소 입력 뒤 enabled(누르지 않음) | 통과 |

### 세션 (`session-1400.json` · `session-390.json` · `entries-1400.json`)

| ID | 동작 | 관측 | 1400 | 390 |
|---|---|---|---|---|
| F1 | Free talk(마이크 거부 · 소켓 없음) | 카드 안 `session-failed` · `data-reason=microphone_permission_denied` | 통과 | 통과 |
| F2 | 실패 화면 동안 잠금 | 링크 4개 `aria-disabled=true` · 세션 버튼·Day 줄 disabled · nav `data-locked=true`. 대조로, 열기 전에는 모두 풀려 있었음 | 통과(다시 판정 · §4) | 통과 |
| F3 | 잠긴 History → 를 DOM 클릭 | 주소 `/` 그대로 | 통과 | 통과 |
| F4 | Try again | `getUserMedia` 호출 1→2 · 다시 실패 화면 | 통과 | 통과 |
| F5 | ← Home | `idle` · 잠금 모두 풀림 | 통과 | 통과 |
| M1 · M2 | 아래쪽 Day 2 줄 · Grammar course | 카드 bottom −98 · −403 → top 0 · 연습 열림 | 해당 없음 | 통과 |
| S1 | Free talk | 1400: 연 문장 연습이 먼저 닫히고 카드 안 세션. 390: 맨 아래(카드 top −893)에서 누르자 top 0 | 통과 | 통과 |
| S2 | 세션 중 잠금 | F2 와 같음 | 통과(다시 판정 · §4) | 통과 |
| S3 | 잠긴 Weekly report → DOM 클릭 | 주소 `/` · 세션 유지 | 통과 | 통과 |
| S4 | End lesson | 누른 직후 「Ending...」 → `/results/<id>`. id 가 `session_started` 의 ID 와 같음 | 통과 `3126ad0a…` | 통과 `13869294…` |
| E1~E8 | Free talk · Weak spots · 5 questions · Pronunciation · Shadowing · Shadow a sentence · Repair your mistakes · Practice a pattern | 가짜 소켓에 실린 질의가 `additionalLearning.ts` 의 진입과 같음. 예: 5 questions `mode=scenario_intake&source=additional` · 빠른 쉐도잉 `mode=shadowing&source=additional` | 통과 8/8 | 미실행(진입이 폭과 무관함) |

실제 Nova 세션은 2개(S 1400 · S 390)임. 둘 다 DB 에 `ended_at` 이 있음(06:25:09 · 06:26:08 UTC). E1~E8 은 이 페이지의 `/ws/session` 소켓만 가짜로 바꿔 서버에 붙지 않았음. 그 뒤 시작된 세션은 `db.py sql` 로 0건임.

## 4. 관측 수단의 양성 대조 · 드라이버 정정

- 모양 측정의 양성 대조: 기준 버튼(`course-prev/start/next` · `practice-close`)은 같은 측정기로 36.4px · 13.6px 임. 그래서 어긋남 값은 측정기 탓이 아님.
- 잠금 측정의 양성 대조: 같은 함수가 대기 상태에서는 모두 「풀림」으로 읽었음(F2 의 `before free=true` · F5).
- F2 · S2 @1400 정정: 버튼 선택자 `[data-testid^="quick-"]` 가 링크 `quick-videos` 를 잡아 `disabled=null` 을 「안 잠김」으로 셌음. 같은 기록에서 그 링크는 `aria-disabled=true` 임. 그래서 두 건을 통과로 다시 판정했음. 선택자를 `button[...]` 으로 고친 390 실행은 그대로 통과했음. 실제 세션 상한 때문에 1400 실행은 다시 돌리지 않았음.
- 단계 기록은 MutationObserver 로 했음(폴링 누락 없음). P2 · P3 · P6 의 단계열이 그 기록임.
- H1 반증: `probe-scroll.json` 은 DOM `el.click()` 과 Playwright 클릭을 대조했음. 두 방법 모두 40→0 이고, 390 은 두 방법 모두 불변임. 그래서 드라이버의 클릭 전 스크롤은 원인이 아님. `probe-scroll2.json` 은 원인을 보임(D1).

## 5. 모양 판정 — 기준 `omy-button`(36.4px · 13.6px · 앞으로 가는 이동만 파란 바탕)

맞음: 홈 문장 칸 버튼 · ← Close · 실패 화면 두 버튼 · `/history` · `/history/weekly` · `/results` · `/course` · `/course/<day>` · `/videos` · `/videos/<id>` 의 ←·→ 이동.

범위 밖(설계서 §3 「섹션 라벨과 이동 버튼의 기준은 홈」): 사이드바 메뉴 · 로고 · Day 경로 카드 · 영상 제목 링크.

| # | 버튼 | 관측 | 판정 |
|---|---|---|---|
| 1 | 홈 `home-history` 「History →」 · `home-weekly` 「Weekly report →」 | omy 이지만 회색임. 같은 문구의 이동이 `/results`(History →)와 `/history`(Weekly report →)에서는 파란 바탕임 | 어긋남 — D2 |
| 2 | 홈 More practice 8개(`practice-*`) | shadcn outline 36px · 14px · 흰 바탕 | 어긋남 — D3 |
| 3 | 홈 `home-path-all` · `focus-practice` | ghost 32px · 12px · 파란 글자 | 어긋남 — D3 |
| 4 | 세션 「End lesson」 | 40.4px · 16px · 둥근 알약 | 어긋남 — D3 |
| 5 | `/videos` 「Check」 · 「Delete」, `/videos/<id>` 「Mark start」 · 「Mark end」 · 「Mark again」 | 브라우저 기본 버튼 34px · 16px | 어긋남 — D3 |
| 6 | 홈 `start-session` | 36px · 14px · 남색 카드 위 흰 바탕 | 불확실 — 남색 카드 위 예외가 설계에 없음 |
| 7 | `course-mode-auto/manual` · 빠른 카드 3개 | 토글 27.2px · 카드 70px | 불확실 — 이동·실행 버튼인지 설계가 정하지 않음 |
| 8 | `/course` 「Start」(Day 2~6) | omy 회색. 앞으로 가는 이동이지만 현재 Day(Continue ▶)만 파란 바탕임 | 불확실 — 「현재 Day 강조」 의도로 읽힘 |

## 6. 결함과 문서 불일치

### D1 · 1400×900 에서 Start speaking 이 창 스크롤을 0 으로 옮김

- 재현: 1400×900 으로 홈을 엶 → `window.scrollTo(0, 40)` → Start speaking.
- 기대: scrollY 40 유지(설계서 §3 `TASK-305` · `TASK-308`: 「Start speaking 은 창을 움직이지 않음」).
- 실제: 약 340ms 뒤 scrollY 가 0 이 됨. home.mjs 1회와 probe 4회(DOM 클릭 2 · Playwright 클릭 2)에서 같았음. 그래서 간헐 결함이 아님.
- 기전(`probe-scroll2.json`): 클릭 직후 한 프레임 동안 문장 연습이 로딩 상태라 카드가 433→335px 로 줄었음. 같은 프레임에 문서 높이가 951→900(창 높이와 같음)이 되어 scrollY 가 0 으로 클램프됐음. 다음 프레임에 높이가 돌아와도 스크롤은 돌아오지 않았음.
- 대조: 1400×700 · scrollY 200 에서는 200→153→200 으로 한 프레임 튀고 돌아왔음. 390 은 문서가 길어 움직이지 않았음. 그래서 클램프가 일어나는 조건은 「스크롤 여유가 줄어드는 높이(약 98px)보다 작을 때」로 봄.
- 증거: `evidence/home-1400.json` H1 · `probe-scroll.json` · `probe-scroll2.json`.
- 고쳐진 것으로 볼 조건: 같은 절차에서 scrollY 가 40 으로 남음. 그리고 클릭 뒤 매 프레임 `home-hero` 높이가 335 로 내려가지 않음.
- 제안: 연습의 로딩 상태(`HomeCoursePractice` 의 「Loading…」)에도 대기 카드 높이(`HERO_HEIGHT`)나 같은 최소 높이를 줌.

### D2 · 홈의 「History →」 · 「Weekly report →」 만 파란 바탕이 아님

- 재현: 1400 홈과 `/results/<id>`(또는 `/history`)의 같은 문구 버튼 바탕색을 비교함.
- 기대: 앞으로 가는 이동(→)은 `omy-button-primary` 임(설계서 §3 · `globals.css` 주석).
- 실제: 홈은 `rgb(242, 244, 249)` 이고, 다른 화면은 `rgb(50, 99, 220)` 임. 소스는 `HomeDashboard.tsx` `ProgressCard` 의 `className="omy-button"` 임.
- 고쳐진 것으로 볼 조건: 홈의 두 링크가 `omy-button-primary` 를 가짐. 또는 설계서가 홈 예외를 적음.

### D3 · `omy-button` 이 아닌 이동·실행 버튼 묶음

- §5 의 2~5행임. More practice 8개 · View all · Practice a pattern · End lesson · 영상 화면들의 Check · Delete · Mark 계열이 기준(36.4px · 13.6px)과 다름.
- 근거는 `evidence/inventory.json` 과 `session-1400-meta.json` 의 `endStyle` 임.
- 고쳐진 것으로 볼 조건: 사용자가 이 버튼들을 기준 범위에 넣을지 정함. 넣으면 그 버튼들이 `omy-button` 을 씀.
- ⚠️ 이 묶음이 결함인지는 「이동·실행 버튼」의 범위 결정에 달림. 설계서는 범위 밖으로 메뉴·영상 제목·Day 카드 셋만 적었음.

### D4 · testid 가 없는 실행 버튼

- 세션 화면 「End lesson」(`SessionChat.tsx`)과 실패 화면 「Try again」(`page.tsx`)은 testid 가 없어 문구로 골랐음(공통 지시 5).
- 홈 밖 화면(`/history` · `/results` · `/course` · `/videos*`)의 이동 링크도 `course-back` 을 빼면 testid 가 없음.
- 고쳐진 것으로 볼 조건: 위 버튼에 `data-testid` 가 있음.

### 문서 불일치 · 세션 중 View all

- 설계서 §3 「세션 화면의 번복」(`TASK-301`)은 세션 동안 View all 이 잠긴다고 적음.
- 실제(F2 · S2)로는 `home-path-all` 이 세션 중에도 눌림. 펼쳐 나온 Day 줄은 모두 disabled 임.
- `TASK-314` 로 View all 이 화면 이동이 아니라 제자리 펼침이 됐으므로 동작은 타당해 보임. 설계서의 그 목록이 낡은 것으로 봄. 판정은 불확실임.

### 관찰(판정 밖)

- 단원 주제가 한국어로 보임(예: 「Unit 113 · 구동사 2 put on · take off · turn on」 · 「Unit 101 · 시간의 at · on · in」). 설계서 §6 이 백엔드에서 오는 한국어를 범위 밖(미결)으로 둠.

## 7. 미실행 · 남긴 자료

- 미실행: `/videos` 의 Check 실행·Save·Cancel(바깥 조회와 저장) · Delete(파괴) · 구간 Save(저장) · 문구 줄 Listen/Practise/Delete(`phrase_count` 0 이라 없음) · Day 화면의 「Go to Unit」(영상 재생 필요) · 세션 화면 안의 다시 듣기·번역·쉐도잉·리포트 버튼(Free talk 에 발화가 없어 그려지지 않음) · E1~E8 의 390.
- 격리 DB 에 남은 것: 홈 문장 연습·`/course/1` · `/course/3` 진도 저장 · 문장 시도(P2·P3·P6·P8 · 가짜 마이크 소리) · Day 6 완료 1회(P8 — cycle 의 완료 수가 늘었음) · 코치 세션 2개와 그 분석 작업.
- dev DB `ohmyenglish` 는 건드리지 않았음.
- 스크립트: `lib.mjs` · `inventory.mjs` · `home.mjs` · `practice.mjs` · `nav.mjs` · `session.mjs` · `entries.mjs` · `probe-scroll.mjs` · `probe-scroll2.mjs`. 증거는 `evidence/` 에 있음.
- 원장: 공통 지시 4에 따라 리포 원장과 테스트 원장을 고치지 않았음. 결함 등록과 `TASK-316.2` 의 상태 갱신은 호출자 몫임.
