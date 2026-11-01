# 회차 2026-11-01-b12r3 — 진도 저장이 끝나지 않을 때 조회 대기 상한(3000 ms) 확인 (`TASK-304`)

HEAD `bf6b938` + 미커밋 `app/frontend/lib/api.ts`(`SETTLE_LIMIT_MS = 3000`) 임. next dev 가 반영한 판을 쟀음. 스택은 그대로이고 재기동하지 않았음. 전용 런처 없이 서브에이전트로 돌았음(§1-1 규칙만 지킴). 쓰기는 이 폴더와 `/private/tmp/_b12r3-*` 뿐이었고 임시 파일은 지웠음.

## 절차

- `hold`: CDP `Fetch` 로 `POST /api/course/days/*/progress` 를 붙잡고 끝까지 풀지 않음(OPTIONS 는 통과). 그 상태로 홈에서 Start speaking → Manual → Next → Close → 300 ms 뒤 Start speaking 을 누름. 누름은 모두 진짜 마우스임. 시각은 두 번째 누름 기준임.
- `nohold`: 같은 절차를 붙잡지 않고 돌림.
- 각각 2번씩 돌렸음 (`evidence/I5-hold1.json` · `I5-hold2.json` · `I5-nohold1.json` · `I5-nohold2.json`).

## 측정

| 실행 | 다시 열기 `GET /api/course` | 다시 열기 `GET /api/course/days/1` | 연습이 열린 시각 | 콘솔 |
|---|---|---|---|---|
| hold1 | 2707 ms(닫기의 다시 읽기) · 3023 ms(연습) | 6028 ms | 6043 ms | 예외 0 |
| hold2 | 2710 · 3022 ms | 6031 ms | 6047 ms | 예외 0 |
| nohold1 | 24 ms | 28 ms | 36 ms | 예외 0 |
| nohold2 | 23 ms | 29 ms | 46 ms | 예외 0 |

2707 ms 의 조회는 닫기 때의 `reloadCourse` 임. 닫기가 누름보다 약 300 ms 앞이라 닫기 기준으로 약 3.0 초임.

## 판정

| 기대 | 판정 |
|---|---|
| 붙잡힌 상태에서도 다시 열기의 조회가 나감(영원히 막히지 않음) | 통과 (2/2) |
| 연습이 열림 | 통과 (2/2) — 단 6.04 초 걸림 |
| `/api/course` 가 약 3 초에 나감 | 통과 (2/2) — 3022~3023 ms |
| `/api/course/days/N` 이 약 3 초에 나감 | **실패 (2/2)** — 6028~6031 ms |
| 콘솔 예외 0 | 통과 (4/4) |
| 붙잡지 않으면 다시 열기 조회 < 200 ms | 통과 (2/2) — 23~24 ms |

### 실패의 기전 (코드로 확인함)

`HomeCoursePractice` 는 `fetchCourse()` 를 마친 뒤 `fetchCourseDay()` 를 부름. 두 함수가 모두 `settleSaves()` 를 먼저 기다림(`lib/api.ts` 의 `fetchCourse` · `fetchCourseDay`). 붙잡힌 저장이 그대로 남아 있으므로 상한 3 초를 두 번 이어서 기다림. 그래서 연습이 열리기까지 약 6 초가 걸림. 연습이 열린 뒤의 5초 주기 저장도 붙잡혀 남으므로, 뒤이은 조회마다 다시 3 초씩 기다릴 것으로 보임(재지 않았음).

제안: 상한을 「조회마다」가 아니라 「같은 저장 묶음에 한 번」으로 둠. 또는 `loadCurrentDay` 에서 한 번만 기다린 뒤 두 조회를 부름. 또는 상한을 넘긴 저장을 `pendingSaves` 에서 뺌.

## 관찰

- 붙잡힌 상태에서 다시 연 문장은 넘기기 전 문장이었음(hold1: 넘김 2/5 → 다시 열기 1/5 · hold2: 4/5 → 3/5). 저장이 서버에 닿지 않았으니 서버 값을 읽은 것임. 상한 주석이 밝힌 위험(「옛 진도를 읽을 위험」)과 같음. 그래서 결함으로 올리지 않음.
- 그 상태에서 새로 연 칸의 저장은 옛 자리(hold1 `sentence_index 0`)를 보냄. 붙잡힌 Next 저장(`1`)이 나중에 풀리면 순서에 따라 진도가 바뀔 수 있음. 이 회차에서는 풀지 않았으므로 재지 않았음.

## dev DB

시작·끝 모두 19 · 144 · 0 · 0 임 (`evidence/devdb-start.json` · `devdb-end.json`). 붙잡은 POST 는 서버에 닿지 않았음.
