# 회차 2026-11-01-b12 — 홈 Start speaking 의 카드 안 문장 연습 (`TASK-304`) · b11 D1 재확인 (`TASK-302`)

HEAD `5a3ff2d` 임. 회차 시작(12:12)과 끝(12:29) 모두 같았음. `app/frontend/{app,components,lib}` · `app/backend/app` 에서 12:12 이후 바뀐 소스는 0건임.

## 먼저 알릴 것

1. 이 회차는 전용 런처 없이 서브에이전트로 돌았음. 그래서 OS 샌드박스 보장이 없었고 정의 §1-1 규칙만 지켰음. 쓰기는 이 폴더와 `/private/tmp/_b12-*` 뿐이었고 임시 파일은 지웠음. 커밋·원장 갱신·결함 등록은 호출자 지시에 따라 하지 않았음.
2. 공유 판정: :3000(next dev, pid 43118) 과 :8002(pid 61182, 11:28:12 기동)는 호출자 소유임. 재기동·종료하지 않았음. 백엔드는 대상 커밋 전에 떴으나 `b83d19f..5a3ff2d` 의 `app/` 변경은 프런트 6개 파일뿐이라 백엔드 판이 어긋나지 않음.
3. 입력은 Chrome 가짜 장치(헤드리스 Chrome 156 · CDP)임. 누름은 모두 요소 가운데 좌표의 `Input.dispatchMouseEvent` 임. YouTube 재생도 iframe 가운데를 진짜 마우스로 눌러 시작했음. 영상 상태는 iframe 대상에 붙어 `<video>` 와 `#movie_player` 를 읽었음.
4. stub 세션은 약 70~170 ms 만에 끝남. 그래서 세션 중 상태(카드 안 패널·잠금·높이)는 MutationObserver 기록으로 쟀음. 연결 중은 `getUserMedia` 를 12초 늦춰, 실패는 한 번 거절해 만들었음(코치 진입 뒤 첫 호출에만 적용).
5. 시나리오 3 의 전제(위치가 0 이 아닌 진도)는 격리 DB 에 이미 있었음 — Day 4 `position_sec 54.4` · Day 1 `23.98`. 그래서 새로 만들지 않고 그 행을 썼음.
6. 드라이버 실수 3건은 앱 결함이 아님: Listen 뒤 `course-start` 를 찾은 순서 오류 · `<video>.play()` 의 약속이 끝나지 않아 멈춤(플레이어가 `unstarted`) · zsh 인자 밀림. 앞 2건은 고쳐 다시 돌렸고, 3건째로 생긴 증거 2개는 지웠음.

## 판정표

| # | 시나리오 | 판정 | 근거 |
|---|---|---|---|
| 1 | 홈 대기: 문구 · Day 줄 · 추천 코치 시작 없음 | 통과 | 제목 「Day 4: listen and say it.」 · `home-hero-day` 「Day 4 · Units 63–82」 가 `/api/course` 의 `current_day 4` · `first_unit`/`last_unit` 과 같음. 카드 문구는 영어뿐임. `home-hero-reason`·`home-level` 0개 · 카드 안 coach/recommend 0개 · `next-plan` 요청 0건 · Start speaking 누름에 소켓 0개(1400 · 390) (`S1-r1.json` · `S1-r2-390.json`) |
| 2a | 카드 안 문장 연습 · 영상 없음 · Day/단원/문장 대조 | 통과 | `data-mode=practice` · `sentence-practice` 가 `home-hero` 안 · 화면 iframe 0개 · `practice-day` 「Day 4 · Units 63–82」 · 단원·문장 번호·문장이 `/api/course/days/4` 의 저장 위치와 같음(1400 Day 4 · 390 Day 1) |
| 2b | Auto/Manual 토글 · 새로 고침 뒤 유지 | 통과 | Manual → 새로 고침 → `aria-pressed` Manual · Auto → 새로 고침 → Auto (`S2-r2.json`) |
| 2c | Start(수동) · Again · Listen · Slow | 통과 | 넷 모두 `listen → repeat → judge → done` 후 멈춤 · 문장 번호 그대로 · 시도 POST 1건씩 503 → 「I can't check your speaking now. You can keep going.」 |
| 2d | Next/Back | 통과 | 2/5 → 3/5 → 2/5 · 단계 idle · 안내 지워짐 |
| 2e | 자동 한 흐름 | 통과 | 63-2 → 63-3 → 63-4 → 63-5 → 64-1 로 이어짐 · 시도 POST 4건 |
| 2f | ← Close 로 대기 복귀 · 다른 카드 자리 | 통과 | 자동 도는 중에 닫음 → `data-mode=idle` · 6초 동안 시도 요청 0건(닫힘 저장 1건뿐). 연습 중 카드 높이 283 → 369~395 · 다른 카드는 x·폭 같고 y 만 내려감 · 진도 카드 그대로. 닫으면 상자가 대기 값과 픽셀까지 같음. 390 폭: 카드 top 24 로 끌어옴 · 가로 넘침 0 |
| 2g | 마지막 문장 Finish Day → 완료 +1 · 카드/진도 갱신 | **실패 → D1** | `done` 전 비활성 · 뒤 활성 · 누르면 「You finished this Day!」 · Unit 63 문장 1 · `completed_count 0→1` · `position_sec 0`. 그러나 닫은 뒤 대기 카드·진도 카드·경로가 갱신되지 않음 |
| 3 | 영상 위치 보존 | 통과 (2/2) | Day 4: 54.4 → 다음·다음·이전·닫기 → 54.4 그대로 · 문장 0 → 1. POST 본문 넷 모두 `position_sec 54.4`. Day 화면 iframe `start=54` · Unit 63 문장 2/5 에서 시작. Day 1(390): 23.98 그대로 · 문장 1 → 2 · Day 화면도 그 문장 (`S1-r1.json` · `S1-r2-390.json`) |
| 4 | 코스 Day 화면 회귀 | 통과 | Day 3(`S4-r2.json`): iframe `start=168` · 영상 재생 중 Start → 영상 `paused`(171.47) · 연습 중 영상 재생 → 단계 idle · 단원 43 으로 옮기고 6.5초 → 「Go to Unit 42 (where the video is)」 → 누르니 Unit 42 문장 1 · 12초 더 재생 후 ← Back → 저장 192.47 (직전 192.99 · 차 0.52) · 마지막 문장 Finish Day → +1 · 영상 0초 정지 · 6초 뒤와 ← Back 뒤에도 0 유지 |
| 5a | More practice Free talk → 카드 안 세션 → 결과 | 통과 | `session-panel` 이 `home-hero` 안 · 잠금 `true` · 소켓 `?source=additional` · `/results/<id>` 로 이동 뒤 잠금 풀림 (`S5-a-plain.json`) |
| 5b | 문장 연습이 열린 채 진입 → 연습 닫힘 · 세션 시작 | 통과 | Free talk · Practice a pattern · Quick shadowing(`?mode=shadowing`) 셋 모두 연습이 세션 첫 기록(14~33 ms)에서 사라지고 세션이 시작됨. 연습에서 마이크를 잡은 뒤 진입하면 그 트랙이 연결 중에 이미 `ended` 임 (`S5-b-started` · `c-delay-started` · `g-focus` · `h-quick`) |
| 5c | 세션 중 잠금 | 통과 | 연결 중 진짜 마우스로 Practice 메뉴 · Pronunciation 을 누름 → 이동 0 · 새 소켓 0 · 학습 버튼 9개 `disabled` (1400 · 390) |
| 5d | 연결 중/실패 카드 높이 ≥ 대기(b11 D1) | 1400 통과 · **390 실패 → D2** | 1400: 대기 283 · 연결 중 288 · 실패 288. 390: 대기 293 · 연결 중 288 · 실패 288 (2/2) |
| 6 | 콘솔 앱 예외 0 · 하이드레이션 경고 0 | 통과 | 증거 JSON 의 기록에서 예외 0 · 하이드레이션 0 · 비네트워크 오류 0. 네트워크 오류는 stub 의 시도 503 19건뿐임. 그 밖은 YouTube postMessage 경고 1건임. 수집기 판별력: 같은 수단이 `console.error` 와 잡히지 않은 예외를 잡았음 (`PROBE-logs.json`) |

## 결함

### D1 · 홈에서 Finish Day 뒤 닫으면 대기 카드·진도 카드가 옛 Day 를 보이고, 다시 열면 다른 Day 가 열림 — 중간(MEDIUM)

- 근거: 호출자 시나리오 2 「Finish Day(→ 완료 횟수 +1 · 카드/진도 갱신)」 · 설계서 §3 TASK-304 절(대기 카드 문구는 `current_day` 로 정함).
- 재현: 1) 홈에서 Start speaking 2) Manual · 마지막 문장까지 Next 3) Start → done 4) Finish Day 5) ← Close.
- 기대: 대기 카드가 새 `current_day` 를 보이고, 진도 카드의 완료 Day 수가 하나 늚.
- 실제(1차, Day 4 마침): API 는 `current_day 4 → 5` · 완료 2 → 3 임. 카드는 「Day 4: listen and say it.」 · 「2 / 6 days」 · 경로 「Day 4 · In progress」 그대로임. 새로 고치면 「Day 5」 · 「3 / 6 days」 가 됨 (`S2-r2.json` 의 `cardAfterFinish`).
- 실제(2차, Day 5 마침): API `current_day 5 → 1` · 완료 3 → 4. 카드는 「Day 5」 · 「3 / 6 days」 그대로임. 이어서 새로 고치지 않고 Start speaking 을 누르니 `practice-day` 가 「Day 1 · Units 1–21」 이었음 — 카드가 말한 Day 와 열린 Day 가 다름 (`D1-r1.json` · `D1-r1-stale.png`).
- 재현 횟수: 2/2.
- 추정 위치(확인하지 않은 가설): `HomeDashboard` 의 `course` 는 `useLoad(fetchCourse)` 로 마운트 때 한 번만 읽음. `HomeCoursePractice` 는 열 때마다 새로 읽음. 그래서 둘이 어긋남.
- 제안: 연습 칸을 닫을 때(또는 Finish Day 때) 홈의 코스 개요를 다시 읽음. 또는 카드 라벨과 연습이 같은 출처를 씀.

### D2 · 390 폭에서 연결 중·실패 카드가 대기 카드보다 5 px 짧음 — 낮음(LOW) · b11 D1 의 잔여

- 재현: 1) 390 폭에서 홈을 엶 2) More practice 의 Free talk(또는 Shadowing)를 누름 3) 마이크 응답 전(연결 중) 또는 거절 뒤(실패) 카드 높이를 잼.
- 기대: 대기 높이(293 px) 이상.
- 실제: 288 px(`min-h-72`). 아래 카드가 모두 5 px 올라감. 1400 폭은 대기가 283 px 이라 문제가 없음.
- 재현 횟수: 2/2 (`S5-e-390-deny.json` · `S5-f-390-delay.json`).
- 영향: b11 의 117~215 px 에 비해 크게 줄었음. 눈에 띄는 출렁임은 거의 없음.
- 제안: 고정 `min-h-72` 대신 대기 카드의 실제 높이(390 에서 줄바꿈으로 293)를 받음. 또는 최소 높이를 대기 카드의 가장 큰 값 이상으로 둠.

## 관찰 (결함으로 올리지 않음)

- O1 · 문장 연습 카드(369~426 px)에서 코치 세션으로 넘어가면 카드가 288 px 로 줄어 아래 카드가 80~140 px 올라감. 기대 기준이 「대기 카드보다 줄지 않음」이라 결함으로 올리지 않음.
- O2 · 연습을 열 때 `GET /api/course` · `GET /api/course/days/<n>` 가 두 번씩 나가고 POST 진도 1건이 즉시 나감. next dev 의 Strict Mode 이중 마운트로 보임. 운영 빌드에서는 재지 않았음.
- O3 · 연습을 열기만 해도 5초 주기 저장과 닫힘 저장이 `updated_at` 을 갱신함. 그래서 b11 O3 처럼 홈에서 연 Day 가 「진행 중」이 될 수 있음(백엔드 규칙대로).
- O4 · stub 이라 「Try N」 은 시도 뒤에도 0 이고 `course_attempts` 도 7 그대로임.
- O5 · 단원 제목 일부가 한국어임(`Unit 83 · 형용사 위치`). 콘텐츠 데이터이고 범위 밖임.

## 차단

- 실제 판정 경로(전사 · 단어 판정 · 시도 횟수) — stub 스택이라 범위 밖.
- 사람 목소리 · 실제 Nova 대화 — 범위 밖.

## 격리 DB (`ohmyenglish_course_paid`)

| 표 | 시작 | 끝 |
|---|---|---|
| learning_sessions | 70 | 76 |
| utterances | 443 | 479 |
| course_day_progress | 6 | 6 |
| course_attempts | 7 | 7 |
| youtube_videos | 1 | 1 |

- 새 세션 6행은 모두 내 드라이버가 관측한 결과 id 와 같음(`936c58c4` · `2a47004d` · `9b9a3e98` · `105745e5` · `a983f8a6` · `cc5c4a9a`). 출처 미상 세션은 0행임.
- 남긴 변화: Day 3 · 4 · 5 의 완료 +1(위치 0). Day 1 은 Unit 4 문장 3. 끝 상태는 `current_day 1` 이었음. 근거: `evidence/paiddb-start.json` · `paiddb-end.json`.

## dev DB (`ohmyenglish`) — 읽기 전용 대조

| 표 | 시작 | 끝 |
|---|---|---|
| learning_sessions | 19 | 19 |
| utterances | 144 | 144 |
| course_day_progress | 0 | 0 |
| course_attempts | 0 | 0 |

호출자 기준선과 같고 `max(started_at)` 02:10:38 UTC 그대로임. 근거: `evidence/devdb-start.json` · `devdb-end.json`.

## 회귀

- b11 D1(연결 중·실패 카드가 줄어듦): 1400 은 **고쳐짐**(133/207 → 288 ≥ 283). 390 은 117/215 → 288 이나 대기 293 보다 5 px 짧음 → **부분적으로 여전히 실패**(D2).
- 코스 Day 화면(b5 D3 · D4 · C1 · b11 따라가기): 공용 컴포넌트로 옮긴 뒤에도 **새로 실패 0건**.
- 테스트 원장은 호출자 지시로 갱신하지 않았음. 그래서 원장 기준 회귀 판정은 하지 않았음.

## 파일

- 드라이버: `lib.mjs`(b11 판 복사) · `h.mjs` · `s1.mjs` · `s2.mjs` · `d1.mjs` · `s4.mjs` · `s5.mjs` · `probe.mjs` · `blank.mjs` · `chrome.sh` · `db.py`
- 증거: `evidence/` — `S1-*` · `S2-*` · `D1-*` · `S4-r2*` · `S5-*` · `PROBE-logs.json` · `*db-*.json` · `chrome-stderr-main.log`
