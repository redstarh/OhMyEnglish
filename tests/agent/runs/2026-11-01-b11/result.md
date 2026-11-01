# 회차 2026-11-01-b11 — 모든 화면의 메뉴·버튼 전수 (`TASK-302`) · 오늘의 연습 카드 안 세션 (`TASK-301`)

HEAD `b83d19f` 임. 회차 시작(11:29)과 끝(12:07) 모두 같았음. `app/frontend/{app,components,lib}` · `app/backend/app` 에서 11:28 이후 바뀐 소스는 0건임.

## 먼저 알릴 것

1. 이 회차는 전용 런처 없이 서브에이전트로 돌았음. 그래서 OS 샌드박스 보장이 없었고 정의 §1-1 규칙만 지켰음. 쓰기는 이 폴더와 `/private/tmp/_b11-*` 뿐이었고 임시 파일은 지웠음. 커밋·원장 갱신·결함 등록은 호출자 지시에 따라 하지 않았음.
2. 공유 판정: :3000 과 :8002 는 호출자 소유의 스택이었음. 그래서 재기동·종료하지 않았음. 백엔드 pid 61182 는 11:28:12 에 떴음. stub 동작(세션마다 발화 6행 · 수십 ms 안에 종료)은 DB 행으로 확인했음.
3. **내 드라이버가 열지 않은 세션 4개가 격리 DB 에 생겼음.** 11:40:20 · 11:40:30 · 11:40:56 · 11:41:05 KST 이고, 모두 `speaking`·`recommended` 임(`527cccd4` · `8ed2885c` · `9db10867` · `6f08a23a`). 그 시각에 내 1차 Chrome 은 `/history`·`/history/weekly` 의 링크를 누르고 있었음. 그래서 같은 경로(`/history` → Home, `/history/weekly` → 로고)를 소켓 시각 기록과 함께 다시 돌렸음. 소켓은 0개였음(`PROBE_history-nav-home-1400.json` · `PROBE_history_weekly-logo-1400.json`). 같은 시각에 다른 세션이 이 리포의 작업 원장에 `TASK-304` 를 만들었음(11:52, 파일 mtime). 그래서 다른 클라이언트의 세션으로 판정함. 단 출처를 특정하지는 못했음. 세션 대조표는 아래 「격리 DB」 절에 있음.
4. 입력은 Chrome 가짜 장치이고 사람의 목소리는 재지 않았음. 연결 중·실패 상태는 `getUserMedia` 래퍼로 만들었음(첫 호출을 12초 늦추거나 `NotAllowedError` 로 한 번 거절함). stub 은 세션을 약 70 ms 만에 끝냄. 그래서 진행 중 상태의 잠금과 카드 상자는 MutationObserver 로 쟀음.
5. 1차 Chrome(:9345)과 2차 Chrome(:9347)은 각각 백그라운드 시간 상한(30분)에 걸려 멈췄음. 멈춘 시각은 쓸 증거를 다 받은 뒤였음. 남은 영상·Day 확인은 다시 띄운 :9345 에서 했고, 끝에 종료했음.

## 수단

- 헤드리스 Chrome 156 + CDP 드라이버임. 누름은 모두 요소 가운데 좌표로 보낸 `Input.dispatchMouseEvent` 임. `el.click()` 은 쓰지 않았음 — 잠긴 링크의 `pointer-events:none` 이 진짜 마우스에만 걸리기 때문임.
- 목록 수집: `enum.mjs` 는 `a[href]` · `button` · `input` · `iframe` · `tabindex` 요소와 React `onClick` 이 붙은 요소를 셈. 보이는 것만 남김. `inventory.mjs` 가 화면 13개 × 폭 2개를 돌았음.
- 누름 기록: `click.mjs` 는 요소마다 화면을 새로 열고 한 번 누름. 그 뒤 2.5초 동안 경로·API 요청·세션 소켓 URL·대화 상자를 기록함. 세션이 열리면 결과 화면이 뜰 때까지 기다림. 225번 눌렀고 6개(입력 칸·삽입 영상)는 별도 흐름에서 다룸.
- 화면별 흐름: `day.mjs`(Day 6 심층) · `follow.mjs`(영상 위치 따라가기) · `videos.mjs`(영상 추가·삭제) · `phrase.mjs`(구간·문장·연습) · `s301.mjs`(TASK-301).

## 요소 목록 — 1400 폭과 390 폭이 같았음

두 폭에서 모든 화면의 요소 목록(testid · 문구 · href · 비활성)이 같았음. 390 폭은 사이드바 대신 위쪽 막대 4칸이 보였음. 13개 화면 모두 `scrollWidth = clientWidth` 였음(1400·390). 근거는 `evidence/INV-1400.json` · `INV-390.json` 과 화면별 `INV-*.png` 임.

| 화면 | 요소 수 |
|---|---|
| `/` | 21 |
| `/course` | 12 |
| `/course/1`~`/course/6` | 14 (각각) |
| `/videos` | 10 |
| `/videos/b502eaf3…` | 8 (구간 표시 전) |
| `/history` | 7 |
| `/history/weekly` | 6 |
| `/results/c7482f05…` | 12 |

모든 화면에 공통 5개가 있음 — 로고(`/`) · `nav-home` · `nav-practice` · `nav-review` · `nav-progress`. 아래 표에서는 이것을 「공통 5」로 적음.

## 화면별 결과

판정 기호 대신 「통과」·「실패」·「관찰」로 적음. 경로는 누른 뒤 2.5초 안에 바뀐 값임. 근거는 `evidence/CLICK-<폭>_<화면>.json` 임.

### 공통 5 — 모든 화면 × 두 폭

| 요소 | 결과 | 판정 |
|---|---|---|
| 로고 · Home | `/` 로 이동 · 홈 API 5개 요청(`next-plan`·`history`·`weekly-report`·`course`·`daily-summary`) · 홈에서는 제자리 | 통과 |
| Practice | `/course` · `GET /api/course` | 통과 |
| Review | `/history` · `GET /api/history` | 통과 |
| Progress | `/history/weekly` · `GET /api/weekly-report` | 통과 |
| 활성 항목 | 각 화면에서 `aria-current=page` 가 하나였음. Home `/` · Practice `/course*`·`/videos*` · Review `/history`·`/results*` · Progress `/history/weekly` 로 설계서 §3 의 대응과 같았음 | 통과 |

13화면 × 4메뉴 × 2폭 + 로고에서 어긋난 것은 0건임. Day 화면에서 떠날 때마다 `POST /api/course/days/<n>/progress` 가 먼저 나갔음 — 위치 저장임.

### `/` 홈 (1400 · 390)

| 요소 | 결과 | 판정 |
|---|---|---|
| `start-session` Start speaking | 소켓 `?source=recommended` → `/results/<id>` | 통과 |
| `home-path-all` View all | `/course` | 통과 |
| `path-day-<n>` (진행 중 Day · 다음 Day) | `/course/<n>` · `GET /api/course/days/<n>` | 통과 |
| `focus-practice` Practice a pattern | 소켓 `?source=additional` → 결과 화면 | 통과 · 관찰 O2 |
| `quick-shadowing` | `?mode=shadowing&source=additional` → 결과 · DB `shadowing_item_id` 채워짐 | 통과 |
| `quick-videos` | `/videos` | 통과 |
| `quick-weak-patterns` | `?source=additional` → 결과 | 통과 · 관찰 O2 |
| `practice-free_talk` | `?source=additional` → 결과 | 통과 |
| `practice-weak_patterns` | `?source=additional` → 결과 | 통과 · 관찰 O2 |
| `practice-five_questions` | `?mode=scenario_intake&source=additional` → 결과 · DB `mode=scenario_intake` | 통과 |
| `practice-pronunciation` | `?mode=pronunciation&source=additional` → 결과 · DB `mode=pronunciation` | 통과 |
| `practice-shadowing` | `?mode=shadowing&source=additional` → 결과 · DB `shadowing` | 통과 |
| `practice-videos` | `/videos` | 통과 |
| `practice-course` | `/course` | 통과 |
| `practice-roleplay` (Not ready yet) | `disabled` · 누름이 버튼에 닿지 않고 이동 없음 | 통과 |

### `/course`

| 요소 | 결과 | 판정 |
|---|---|---|
| ← Home | `/` | 통과 |
| Day 1~6 의 Start · Continue ▶ | 각각 `/course/<n>` · `GET /api/course/days/<n>` | 통과 · 관찰 O3 |

### `/course/1` (전 요소) · `/course/2`~`/course/6` (공통 5 + ← Back)

| 요소 | 결과 | 판정 |
|---|---|---|
| `course-back` ← Back | `/course` (Day 6개 × 두 폭) | 통과 |
| `course-mode-auto` · `course-mode-manual` | 제자리 · `aria-pressed` 전환 | 통과 |
| `course-listen` · `course-slow` · `course-start` | 제자리 · 단계가 `listen → repeat → done` 으로 감 | 통과 |
| `course-prev` (문장 1) | `disabled` | 통과 |
| `course-next` | 문장 번호 증가 | 통과 |
| 삽입 영상 | YouTube iframe 이 뜨고 재생 누름에 위치가 생김 | 통과 |

Day 6 심층(`DAY6-1400.json`):
- 문장 2/5 에서 재개해 열렸음. 수동 Start → `listen → repeat → done`. 시도 기록은 `POST /api/course/sentences/u101-s2/attempts` 였고 503 을 받았음(stub). 안내 「I can't check your speaking now. You can keep going.」 이 떴음.
- Try again(`course-retry`) · Slow · Listen 도 같은 단계 열을 냈음. Next → 3/5 · ← Back → 2/5 로 움직였음.
- 자동 모드 Start 는 문장 2→3→4→5 로 이어졌음.
- Next 60번으로 마지막 문장(Unit 113 · 5/5)까지 감. `course-finish` 는 `done` 전에는 비활성이고 뒤에는 활성이었음. 마치기 → 「You finished this Day!」 · Unit 101 문장 1 로 돌아감. ← Back → `/course`.
- 「Try N」 칸은 시도 뒤에도 `Try 0` 이었음. 판정을 받지 못한 시도(503)는 세지 않는 것으로 보임 — stub 환경이라 결함으로 올리지 않음.

영상 위치 따라가기(`FOLLOW-day3.json`): Day 3 에서 Unit 44 로 넘긴 뒤 영상을 재생함. 「Go to Unit 42 (where the video is)」 가 나타났고, 누르니 Unit 42 문장 1 로 감 — 통과.

### `/videos` · `/videos/<id>`

`VIDEOS-1400.json` · `VIDEOS-phrase-1400.json` · 첫 흐름의 표준 출력.

| 요소 | 결과 | 판정 |
|---|---|---|
| ← Home | `/` | 통과 |
| Check (빈 칸) | `disabled` | 통과 |
| 링크 칸 + Check (`https://example.com/not-a-video`) | oEmbed 404 → 「I couldn't find a video at this link.」 | 통과 |
| 링크 칸 + Check (`youtube.com/watch?v=jNQXAC9IVRw`) | oEmbed 200 → 미리보기 「Me at the zoo · jawed」 + Save · Cancel | 통과 (외부 YouTube 접속 성공) |
| Cancel | 미리보기 닫힘 · 요청 없음 | 통과 |
| Save | `POST /api/videos` → 「Saved!」 · 목록에 추가 | 통과 |
| 영상 제목 링크 | `/videos/<id>` · iframe `youtube.com/embed/<id>?enablejsapi=1` | 통과 |
| Delete → 확인 취소 | 대화 상자 「Delete this video from the list? Your saved sentences will stay.」 · 요청 없음 · 목록 그대로 | 통과 |
| Delete → 확인 | `DELETE /api/videos/<id>` → 목록에서 빠짐 | 통과 |
| ← Videos | `/videos` | 통과 |
| Mark start (영상 정지 상태) | 「Start: 0:00」 · Mark end · Mark again | 통과 |
| Mark end (같은 0:00) | 「The end must come after the start.」 | 통과 |
| Mark start → 재생 → Mark end | 「Playing 0:09–0:13 again and again.」 · 받아쓰기 칸 + Save(빈 칸이면 비활성) · Cancel | 통과 |
| Mark again | 표시가 지워지고 Mark start 로 돌아감 | 통과 |
| Save (문장) | `POST …/phrases` → 목록에 문장 · `0:09~0:13` · Listen to this part · Practice · Delete | 통과 |
| 단어 누름(`test`) | `POST /api/vocab/lookup` 200 · `{"meaning":null}` → 「test — I couldn't find it. Tap again.」 | 통과 (stub 환경의 빈 뜻) |
| Listen to this part | 요청 없음 · 화면 그대로(재생은 iframe 안이라 판정 수단 없음) | 차단(판정 불가) |
| Practice | `/?mode=shadowing&source=additional&item=<문장 id>` → 홈이 소켓을 같은 질의로 열고 결과 화면으로 감. DB `shadowing_item_id` 가 그 문장 id 이고 `shadowing_items` 에 있음 | 통과 |
| Delete (문장) | `DELETE …/phrases/<id>` · 확인 상자 없음 → 「No saved sentences yet.」 | 통과 |

같은 문장을 지운 뒤에는 세션 행의 `shadowing_item_id` 가 null 이 됨. FK 가 `ON DELETE SET NULL` 이어서 생기는 일임(`63eaae79`). 그래서 연결 확인은 지우기 전 20초 동안 읽은 `b10e78a2` 로 했음.

### `/history` · `/history/weekly`

| 요소 | 결과 | 판정 |
|---|---|---|
| Weekly report → | `/history/weekly` | 통과 |
| ← Home | `/` | 통과 |
| ← History (주간) | `/history` | 통과 |

`/history` 에는 세션 행으로 가는 링크가 없음 — 눌 수 있는 것은 공통 5와 위 2개뿐임.

### `/results/<id>` (`c7482f05`)

| 요소 | 결과 | 판정 |
|---|---|---|
| Practice this × 5 | `/?source=additional&pattern=<key>` → 소켓이 같은 질의로 열림 → 새 결과 화면. DB `focus_pattern_key` 가 5개 키와 하나씩 같음 | 통과 |
| ← Home | `/` | 통과 |
| History → | `/history` | 통과 |

## TASK-301 판정표

근거는 `evidence/S301-<라벨>.json` 과 스크린샷 `S301-<라벨>-session.png` · `-failed.png` 임.

| # | 확인 | 판정 | 근거 |
|---|---|---|---|
| 1 | Start speaking → 세션이 `home-hero` 안의 `session-panel` 에서 진행 | 통과 | 1400·390 모두 `data-mode=session` · `panelInHero=true` · `session-overlay` 0개 · 화면 30% 넘는 fixed 요소 0개. 대화 줄 6개가 카드 안에 그려진 뒤 결과로 감(`a-plain` · `h-390-plain`) |
| 2 | 다른 카드 자리 그대로 | 통과 · 결함 D1 | 진행 중(대화 6줄): 1400 은 진도 카드·연속일이 픽셀까지 같음. 나머지 카드는 x·폭이 같고 y 만 +510 이었음(카드 높이 283→793). 390 은 모든 카드의 x·폭이 같고 아래 카드가 +539 내려감(`j-active` · `k-390-active`). 단 **연결 중·실패 동안에는 카드가 줄어듦** → D1 |
| 3 | 세션 중 사이드바·막대 링크 잠김 | 통과 | 연결 중·진행 중·실패 세 상태 모두 `nav[data-locked=true]` · title 「End the lesson first」. 링크 11개(로고·nav 4·View all·Day 2·quick-videos·practice-videos·practice-course)는 `aria-disabled=true` · `tabindex=-1` · `pointer-events:none`. 진짜 마우스로 16곳(로고 포함)을 눌렀고 이동 0 · 새 소켓 0 (`b-delay` · `d-denyhome` · `f-390-…` · `g-390-…` · `i-390-…` · `c-…`) |
| 4 | 대시보드의 다른 학습 버튼 잠김 | 통과 | `focus-practice` · `quick-shadowing` · `quick-weak-patterns` · `practice-*` 버튼 9개가 모두 `disabled` 였음. 눌러도 새 소켓 0 |
| 5 | 키보드로도 못 감 | 통과 | 연결 중 Tab 25번: 초점이 잠긴 링크에 한 번도 가지 않음. 실패 상태에서는 Try again ↔ ← Home 만 돎 |
| 6 | 세션 끝 → 결과 화면 이동 · 잠금 풀림 | 통과 | 모든 진입에서 `/results/<id>` 로 감. 이동 직후 `data-locked` 가 사라짐(MO 기록 `147 ms → 155 ms`) |
| 7 | 마이크 거부 → 카드 안 실패 상자 | 통과 | `session-failed` 가 `home-hero` 안에 있음 · `data-reason=microphone_permission_denied` · 「Could not connect. / Please allow the microphone and try again.」 · 1400·390 |
| 8 | Try again → 같은 학습 | 통과 | `quick-shadowing` 실패 뒤 Try again → 소켓 `?mode=shadowing&source=additional` → 결과(`c-denyretry-shadow`). b9 의 D1(추천으로 바뀜)이 고쳐짐 |
| 9 | ← Home → 잠금 풀림 | 통과 | `data-mode=idle` · `data-locked` 없음 · 링크 `aria-disabled` 없음 · 버튼 활성(roleplay 만 비활성). 그 뒤 Practice 를 누르니 `/course` 로 감(`d-denyhome` · `g-390-denyhome`) |
| 10 | 쉐도잉·More practice 진입도 카드 안 | 통과 | `quick-shadowing`(1400·390) · `practice-pronunciation`(1400) · `practice-five_questions`(390) 모두 `panelInHero=true` · 덮개 0 (`e-shadow` · `e-pron` · `f-390-delay-shadow` · `i-390-more`) |
| 11 | 390 폭: 시작 시 카드가 화면에 보이게 스크롤 | 통과 | 아래 카드에서 시작함. `quick-shadowing`: scrollY 979 → 216 · 카드 top −739 → 24. `practice-five_questions`: 1278 → 216 · −1038 → 24. 1400 에서도 아래 카드로 시작하면 top −51 → 24 |
| 12 | 콘솔 앱 예외 0 · 하이드레이션 경고 0 | 통과 | 증거 JSON 48개를 셌음. 예외 0 · 하이드레이션 0 · 비네트워크 console.error 0. 네트워크 오류 19건은 stub 의 발화 판정 503 18건과 내가 넣은 잘못된 링크의 oEmbed 404 1건뿐임. 그 밖은 YouTube iframe 의 postMessage 경고 2건임 |

## 결함

### D1 · 연결 중·실패 동안 오늘의 연습 카드가 줄어들어 아래 카드가 위로 튐 — 낮음(LOW)

- 근거 문서: 설계서 §3 「세션의 번복」 — 「카드의 격자 자리와 너비는 그대로이고 높이만 늘어남」.
- 재현: 1) 390 폭에서 홈을 엶 2) Start speaking 을 누름 3) 마이크 요청이 응답하기 전(연결 중)에 카드 높이를 잼.
- 기대: 카드 높이가 대기 때(283 px) 이상이어야 함.
- 실제: 연결 중 117 px(390) · 133 px(1400) 이었고, 실패 상자 상태에서는 215 px(390) · 207 px(1400) 이었음. 390 에서는 아래 카드 전부가 166 px 올라갔다가 대화가 시작되면 539 px 내려감. 1400 에서는 진도 카드 옆이 비고 아래 칸(경로·패턴·빠른 카드)은 그대로였음(격자 `items-start`).
- 재현 횟수: 연결 중 7/7(`a-plain` · `b-delay` · `e-pron` · `e-shadow` 는 133 px, `f-390-delay-shadow` · `h-390-plain` · `i-390-more` 는 117 px). 실패 3/3(`c-denyretry-shadow` · `d-denyhome` 207 px · `g-390-denyhome` 215 px).
- 증거: `evidence/S301-f-390-delay-shadow.json` 의 `idleBoxes`/`sessionBoxes` · `S301-g-390-denyhome.json` · `S301-f-390-delay-shadow-session.png`.
- 영향: 실제 Nova 에서는 연결 중이 수 초 걸릴 수 있음. 그동안 좁은 화면의 내용이 위아래로 크게 움직임. 기능은 정상임.
- 제안: 세션 카드에 대기 카드 높이를 `min-height` 로 줌. 또는 연결 중 문구 칸에 대기 카드와 같은 높이를 둠.

새로 찾은 기능 결함은 D1 뿐임.

## 관찰 (결함으로 올리지 않음)

- O1 · stub 은 판정을 503 으로 주므로 Day 화면의 「Try N」 은 시도 뒤에도 0 이었음. 실제 판정 경로에서는 재지 않았음.
- O2 · `focus-practice`(Practice a pattern) · `quick-weak-patterns`(Repair your mistakes) · `practice-weak_patterns`(Weak spots) 는 `practice-free_talk` 와 같은 진입을 보냄 — 소켓 `?source=additional` 이고 패턴이 없음. 그래서 DB 행(`mode=speaking` · `focus_pattern_key=null`)으로 네 진입을 가를 수 없음. PRD §75 는 「약점 패턴 집중」을 별도 선택지로 둠. 다만 `additionalLearning.ts` 의 주석이 이미 이 구별 불가를 적고 있고 이번 변경보다 오래된 일임. 그래서 새 결함으로 올리지 않음. 결과 화면의 Practice this 는 `pattern=<key>` 를 정상으로 넘김.
- O3 · Day 화면을 열고 아무것도 하지 않은 채 ← Back 을 눌러도 그 Day 가 「진행 중」이 됨. 측정: `/course/4` 를 열고 바로 나오니 `current_day` 가 5 → 4 로 바뀜. `/course` 의 Continue ▶ 와 홈의 Continue your path 도 따라 바뀜. 나갈 때 위치를 다시 저장해 `updated_at` 이 갱신되는 탓이고, 백엔드 규칙(「처음 자리를 벗어난 Day 가운데 가장 최근에 손댄 것」)대로임. 둘러보기만 한 것을 「손댄 것」으로 볼지는 사용자 결정 사항임. 이번 회차에서 내 클릭이 진행 Day 를 여러 번 바꿨음(시작 때 Day 5 → 회차 중 Day 1·4 등).
- O4 · `/videos/<id>` 의 「Listen to this part」 는 iframe 안에서만 재생함. 그래서 화면 바깥에서 판정할 수단이 없었음(위 표의 「차단」).
- O5 · Day 화면의 단원 제목(`Unit 101 · 시간의 at · on · in` 등)과 영상 제목은 한국어임. 콘텐츠 데이터이고 설계서 §6 의 범위 밖임.

## 차단

- 「Listen to this part」 의 실제 재생 여부 — YouTube iframe 안의 재생 상태를 읽을 수단이 없었음.
- 진행 중 상태에서 진짜 마우스로 잠긴 요소를 누르는 것 — stub 세션이 약 70 ms 만에 끝나므로 누를 틈이 없었음. 그래서 진행 중 잠금은 MutationObserver 의 `data-locked=true` 기록으로만 확인했음. 진짜 마우스 누름은 같은 잠금 코드가 걸리는 연결 중·실패 상태에서 했음.
- 실제 Nova 대화 · 사람 목소리 — 범위 밖(stub 스택).

## 격리 DB (`ohmyenglish_course_paid`)

| 표 | 시작 | 끝 |
|---|---|---|
| learning_sessions | 30 | 70 |
| utterances | 203 | 443 |
| course_day_progress | 6 | 6 |
| course_attempts | 7 | 7 |
| youtube_videos | 1 | 1 |

- 11:30 이후 세션은 40행임. 그중 35행은 내 드라이버가 결과 화면 id 로 관측한 것임. 1행(`63eaae79`)은 표준 출력으로 관측했고 증거 JSON 은 다음 실행이 덮었음. 나머지 4행이 「먼저 알릴 것」 3의 출처 미상 세션임.
- 남긴 행: 내 세션 36행과 그 발화. 영상 「Me at the zoo」 는 추가 뒤 UI 로 지웠음. 문장 3개는 추가 뒤 UI 로 지웠음. Day 6 은 마치기로 `completed_count` 가 하나 늘었음. 여러 Day 의 위치(`updated_at`)가 바뀌었음.
- 근거: `evidence/paiddb-start.json` · `paiddb-end.json`.

## dev DB (`ohmyenglish`) — 읽기 전용 대조

| 표 | 시작 | 끝 |
|---|---|---|
| learning_sessions | 19 | 19 |
| utterances | 144 | 144 |
| course_day_progress | 0 | 0 |
| course_attempts | 0 | 0 |
| youtube_videos | 1 | 1 |

호출자가 준 기준선과 같고, 회차 동안 바뀌지 않았음(`max(started_at)` 02:10:38 UTC 그대로). 근거: `evidence/devdb-start.json` · `devdb-end.json`.

## 회귀

- b9 의 D1(실패 뒤 Try again 이 추천 학습으로 바뀜)은 **고쳐짐** — `c-denyretry-shadow` 에서 `mode=shadowing` 을 유지함.
- b9 의 O1(수동 Next 뒤 앞 문장 안내가 남음)은 **고쳐짐** — Day 6 에서 Next 를 누르니 `course-notice` 가 null 이었음.
- 테스트 원장(`tests/agent/backlog/`)은 호출자 지시로 갱신하지 않았음. 그래서 원장 기준의 회귀 판정은 하지 않았음.

## 파일

- 드라이버: `lib.mjs` · `enum.mjs` · `inventory.mjs` · `click.mjs` · `day.mjs` · `follow.mjs` · `videos.mjs` · `phrase.mjs` · `s301.mjs` · `probe.mjs` · `chrome.sh` · `db.py` · `dbcount.py`
- 증거: `evidence/` — `INV-*` · `CLICK-*` · `DAY6-1400*` · `FOLLOW-day3` · `VIDEOS-*` · `S301-*` · `PROBE*` · `*db-*.json` · `chrome-stderr-*.log`
