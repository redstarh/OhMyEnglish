# 회차 2026-11-01-b12r — b12 결함 수정 재확인 (`TASK-304`)

HEAD `bf6b938` 임. 회차 시작과 끝 모두 같았음. 12:34 이후 바뀐 앱 소스는 0건임. 스택은 b12 와 같음(:3000 pid 43118 · :8002 pid 61182, stub · 격리 DB). 재기동·종료하지 않았음.

## 먼저 알릴 것

1. 전용 런처 없이 서브에이전트로 돌았음. OS 샌드박스 보장은 없었고 §1-1 규칙만 지켰음. 쓰기는 이 폴더와 `/private/tmp/_b12r-*` 뿐이었고 임시 파일은 지웠음. 커밋·원장 갱신은 하지 않았음.
2. 드라이버는 b12 판(헤드리스 Chrome 156 · CDP · 가짜 장치)을 이 폴더로 옮겨 씀. 항목 3 은 `getUserMedia` 와 `MediaStreamTrack.prototype.stop` 을 감싸 시각을 기록했음. 항목 4 의 닫기·다시 열기는 페이지 안 타이머로 `el.click()` 을 불렀음(간격을 ms 단위로 맞추기 위함).
3. 항목 4 의 판별력: localhost 에서는 저장이 수 ms 만에 끝나 경쟁이 생기지 않을 수 있음. 그래서 CDP `Fetch` 로 진도 POST 를 800 ms · 1500 ms 붙잡는 변형을 더 돌렸음.

## 판정표

| # | 확인 | 판정 | 근거 |
|---|---|---|---|
| 1 | Finish Day → Close 직후 대기 카드 Day 줄 · 진도 카드 · Continue your path 가 `/api/course` 와 맞음 · 다시 열면 카드의 Day | 통과 (2/2) | 1차: Day 1 마침 → API `current_day 2` · `cycle 2` · 이번 회차 완료 1. 닫은 뒤 11 ms 에 카드 「Day 2 · Units 22–41」 · 「1 / 6 days」 · 경로 첫 칸 `path-day-2` · 다시 열면 「Day 2 · Units 22–41」. 2차: Day 2 마침 → `current_day 1` · 완료 2 → 카드 「Day 1」 · 「2 / 6 days」 · 경로 `path-day-1`(Day 2 · Done) · 다시 열면 Day 1. 두 번 모두 새로 고친 카드와 글자까지 같음 (`I1-r1.json` · `I1-r2.json` · `I1-r*-after-close.png`) |
| 2 | 연결 중·실패 카드 높이 ≥ 대기 높이 | 통과 (4/4) | 1400: 대기 283 · 연결 중 283 · 실패 283. 390: 대기 293 · 연결 중 293 · 실패 293. MutationObserver 기록의 모든 프레임에서 대기 높이 아래로 내려간 적 없음 · 아래 카드 y 변화 0 (`I23-h-1400-delay` · `h-1400-deny` · `h-390-delay` · `h-390-deny`) |
| 3 | 연습 마이크가 살아 있을 때 Free talk → 연습 트랙 `ended` 가 세션 `getUserMedia` 호출보다 먼저 | 통과 (3/3) | 1400 plain: 연습 트랙 `stop` 7981.6 ms → 세션 호출 7982.1 ms · 호출 시점 연습 트랙 `ended`. 1400 delay: 7996.5 → 7997.2 · `ended`. 390 plain: 8028.9 → 8029.4 · `ended`. 세 번 모두 `stop` 직전 상태가 `live` 였음 — 기록 수단이 살아 있는 트랙을 `live` 로 읽음을 같은 기록이 보임 (`I23-m-1400-plain` · `m-1400-delay` · `m-390-plain` 의 `end.gum.events`) |
| 4 | 문장 넘김 → Close → ~50 ms 안에 다시 열기 | 통과 (5/5) | 간격 19 · 28.9 · 51.7 ms: 다시 연 문장이 넘긴 문장임 · 이후 8초 동안 POST 3건 모두 넘긴 자리 · 옛 자리 쓰기 0. 저장 붙잡기 800 ms(간격 52.6 ms) · 1500 ms(16.2 ms, 단원 경계 1-5 → 2-1): 다시 열기의 `GET /api/course` 가 붙잡은 저장이 풀린 뒤(752 → 760 ms · 1493 → 1498 ms)에 나감 · 다시 연 문장이 넘긴 문장 · 옛 자리 쓰기 0 · 끝 저장값도 넘긴 자리 (`I4-d0` · `d20` · `d50` · `h50` · `h0`) |

콘솔: 모든 증거의 기록에서 앱 예외 0 · 하이드레이션 경고 0 · 비네트워크 오류 0 임(stub 의 시도 503 제외).

## 회귀

- b12 D1(Finish Day 뒤 낡은 카드): **고쳐짐**.
- b12 D2(390 폭 카드 5 px 줄어듦) · b11 D1: **고쳐짐**.
- 호출자가 더한 마이크 겹침 · 닫기 직후 진도 역행: 이 회차에서 실패 관측 0건임. 수정 전 판에서 재현하지는 않았음.
- 새 결함 0건.

## 관찰

- 1400 폭의 연결 중 카드가 b12 의 288 px 에서 283 px(대기와 같음)로 바뀜. 기대(≥ 대기)에 맞음.
- 연습을 다시 열 때 `GET /api/course` 가 3번 나감. next dev 의 Strict Mode 이중 마운트와 `reloadCourse` 가 겹친 것으로 보임. 기능에는 영향이 없음.

## 격리 DB (`ohmyenglish_course_paid`)

- learning_sessions 76 → 81 · utterances 479 → 509. 새 세션 5행은 모두 내 드라이버가 관측한 결과 id 임(`a0eafb63` · `be0ea2bd` · `947f249b` · `b9b81ba2` · `552a3cc4`).
- Day 1 · Day 2 를 각각 한 번 더 마쳤음(2회차 진입). 끝의 Day 1 진도는 Unit 2 문장 1 임. 행은 남겨 둠.

## dev DB (`ohmyenglish`)

시작·끝 모두 sessions 19 · utterances 144 · progress 0 · attempts 0 · `max(started_at)` 02:10:38 UTC 임 (`evidence/devdb-start.json` · `devdb-end.json`).

## 파일

- 드라이버: `lib.mjs` · `h.mjs` · `chrome.sh` · `i1.mjs` · `s5.mjs`(항목 2·3) · `i4.mjs`
- 증거: `evidence/I1-*` · `I23-*` · `I4-*` · `*db-*.json` · `chrome-stderr-main.log`
