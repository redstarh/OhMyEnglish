---
id: TASK-168
title: '구현 ⑦: 프론트 화면 둘과 진입점 — /videos · /videos/[videoId] · 추가 학습 일곱째'
status: Done
assignee: []
created_date: '2026-09-17 17:17'
updated_date: '2026-09-17 17:56'
labels: []
dependencies:
  - TASK-166
  - TASK-167
ordinal: 229000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
설계서 §5 를 이행한다. 화면을 셋 이상으로 늘리지 않는다. 대시보드 항목에 href 를 더하고 업무 역할극 빈 칸이 휩쓸리지 않게 렌더 조건을 좁힌다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 app/videos/page.tsx 를 만들었다 (목록 · URL 붙여넣기 · 미리보기 · 담기 · 지우기 · 빈 상태)
- [x] #2 app/videos/[videoId]/page.tsx 를 만들었다 (플레이어 · 구간 담기 · 문장 입력 · 담은 문장 목록 · 연습하기)
- [x] #3 ADDITIONAL_LEARNING 에 href 를 더하고 일곱째 항목 「영상으로 배우기」를 넣었다
- [x] #4 ⛔ 렌더 조건을 좁혀 업무 역할극 칸의 note 와 비활성이 그대로다
- [x] #5 설계서 §7 의 오류 문구 아홉이 화면 코드에 있고 각각 조건에 걸려 있다 (⚠️ 「실제로 나타난다」의 확인은 TASK-169 가 가진다 — 화면을 열어 보지 않고 그렇게 적지 않는다)
- [x] #6 구간 90초 초과와 빈 문장을 프론트가 미리 막는다 (서버 검사와 겹으로 둔다)
- [x] #7 npx tsc --noEmit 와 npx eslint . 가 통과한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 이행 (2026-09-18)

- `app/frontend/app/videos/page.tsx` — 목록·미리보기·담기·지우기·빈 상태(S2).
- `app/frontend/app/videos/[videoId]/page.tsx` — 플레이어·구간 담기·문장 입력·문장 목록(S3).
- `app/frontend/app/page.tsx` — `ADDITIONAL_LEARNING` 의 `href` 와 일곱째 항목, 렌더 조건, 그리고
  **[연습하기] 로 들어오는 자동 시작**.

### ⛔ 이 태스크에서 가장 값 있는 판단 — 게이트가 못 잡는 함정을 문서로 먼저 찾았음

[연습하기] 는 대시보드에서 세션을 열어야 하는데 **대시보드가 쿼리를 읽지 않았음**(`useSearchParams`
0곳). 그것을 더하려다 Next.js 문서에서 이 문장을 찾았음:

> *"In development, routes are rendered on-demand, so `useSearchParams` doesn't suspend and things
> may appear to work without `Suspense`."*

⇒ **개발에서는 되는 것처럼 보이고 우리 게이트(`tsc`·`eslint`)로는 잡히지 않음.** 그래서
`useSearchParams` 대신 **effect 안에서 `window.location.search`** 를 읽었음 — 클라이언트에서만 도므로
prerender 경로에 영향이 없음.

⛔ **그 판단을 `next build` 로 확인했음**(게이트에 없는 명령을 일부러 돌렸음):

```
build exit=0
Route (app)
┌ ○ /            ← Static 으로 남았다
├ ○ /videos
└ ƒ /videos/[videoId]
```

⇒ `/` 가 여전히 `○ (Static)` 임. `useSearchParams` 를 썼다면 그 경로가 클라이언트 렌더로 떨어졌을
자리임. ⚠️ **URL 을 `history.replaceState` 로 즉시 비움** — 비우지 않으면 새로고침이 세션을 또 엶.

### 「업무 역할극」 칸을 지킨 방법

렌더 조건을 `item.entry === null` 에서 `item.entry === null && item.href === undefined` 로 좁혔음.
⇒ 새 항목은 활성이고, 그 칸은 `entry` 도 `href` 도 없어 **비활성과 `note` 가 그대로**임.
⛔ 그 칸을 재사용하지 않았고 영상 학습을 **일곱째**로 붙였음(소유는 `TASK-102`·`TASK-5`).

### 30일 메타데이터 갱신을 화면이 조용히 함

목록을 불러온 뒤 `metadata_stale` 인 것만 oEmbed 로 다시 받아 `POST /api/videos` 로 갱신함.
⛔ **사용자에게 알리지 않음** — 정책을 지키기 위한 내부 동작이고 학습과 무관함. 실패해도 넘어감:
낡은 제목이 보이는 것이 목록이 깨지는 것보다 나음. ⚠️ 보통 0건임.

### 함정 둘 (둘 다 실측으로 잡았음)

1. ⛔ **`eslint` 종료 코드를 파이프로 가렸음**(`H-AZ`). `| tail` 을 걸어 `exit=0` 으로 읽었는데 실제는
   **`exit=1`** 이었고 `react-hooks/set-state-in-effect` 오류가 하나 있었음. 파이프 없이 다시 재서
   찾았음.
2. 그 규칙이 `void reload()` 를 막음 — 비동기 함수로 감싸 고쳤음(`app/videos/page.tsx` 가 이미 쓰는
   형태임). 규칙이 겨누는 것은 effect 첫머리의 **동기** setState 임.

### ⚠️ AC#5 의 범위를 좁혔음

원래 문구가 「오류 문구 아홉이 화면에 **실제로 나타난다**」였으나 **화면을 열어 보지 않았음.**
⇒ AC 를 「코드에 있고 조건에 걸려 있다」로 좁히고 실제 표시의 확인을 `TASK-169` 로 넘겼음.
⛔ 화면을 보지 않고 「나타난다」라고 적지 않음.

### 게이트 (이 턴에 직접 돌린 출력 · 파이프 없이 종료 코드를 읽었음)

`pytest` **1339 passed** · `ruff` 0 · `ruff format` **280 files** · `ty` 0 · `tsc` 0 · `eslint` 0 ·
`next build` **exit 0**.
<!-- SECTION:NOTES:END -->
