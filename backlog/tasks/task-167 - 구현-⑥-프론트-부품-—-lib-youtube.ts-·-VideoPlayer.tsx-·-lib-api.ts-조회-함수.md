---
id: TASK-167
title: '구현 ⑥: 프론트 부품 — lib/youtube.ts · VideoPlayer.tsx · lib/api.ts 조회 함수'
status: Done
assignee: []
created_date: '2026-09-17 17:17'
updated_date: '2026-09-17 17:49'
labels: []
dependencies:
  - TASK-165
ordinal: 228000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
설계서 §5 를 이행한다. ⛔ 프론트에 논리를 두지 않는다 — 프론트 테스트 러너가 없으므로 전송·표시·플레이어 제어만 맡는다. videoId 파싱은 서버가 갖는다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 lib/youtube.ts 에 fetchVideoMeta · thumbnailUrl · loadPlayerApi 를 만들었다
- [x] #2 ⛔ fetchVideoMeta 가 videoId 를 뽑지 않는다 — 파싱 규칙이 두 곳에 갈리지 않는다
- [x] #3 fetchVideoMeta 가 실패(400 포함)에 null 을 준다
- [x] #4 VideoPlayer.tsx 가 new YT.Player 로 플레이어를 만들고 onStateChange·onError 를 받는다
- [x] #5 구간 반복을 onStateChange 와 getCurrentTime 으로 구현했다 (IFrame API 에 반복 기능이 없다)
- [x] #6 ⛔ 플레이어 컨트롤을 가리지 않는다 (정책 III.I.6)
- [x] #7 lib/api.ts 에 엔드포인트 여섯의 조회 함수를 더했다 (전용 화면은 실패를 null 로 — 기존 관례)
- [x] #8 npx tsc --noEmit 와 npx eslint . 가 통과한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 이행 (2026-09-18)

- `app/frontend/lib/youtube.ts` — `fetchVideoMeta` · `thumbnailUrl` · `loadPlayerApi` · 최소 타입.
- `app/frontend/lib/api.ts` — 영상 함수 다섯과 타입 다섯을 더했음.
- `app/frontend/app/VideoPlayer.tsx` — 플레이어와 구간 반복.

### ⛔ 규율 하나 — 프런트에 논리를 두지 않았음

프런트에 테스트 러너가 없으므로(`TASK-159` 6항) 판정은 서버가 가짐. 특히 **`fetchVideoMeta` 가
videoId 를 뽑지 않음** — URL 을 그대로 oEmbed 와 서버에 넘김. 파싱 규칙이 두 곳에 있으면 갈라짐.

### 쓰기 함수에만 결과형을 둔 근거

기존 조회 함수는 실패에 `null` 을 줌(전용 화면 관례). 쓰기는 그럴 수 없음 — 설계서 §7 이 문구를
**갈라** 정했고(「이 링크에서 영상을 찾지 못했어요」 vs 「지금 확인할 수 없어요」) `null` 하나로는
그 둘을 가릴 수 없음.
⇒ `WriteResult<T>` = `{ok: true, value}` | `{ok: false, reason}` 이고 `reason` 은
`refused`(422) · `unavailable`(그 밖)임.
⚠️ **204 에는 몸통이 없어 `json()` 이 던짐** — `writeJson` 이 그 상태를 따로 다룸.

### 구간 반복 — 우리가 만드는 유일한 기능

IFrame API 에 반복이 없고 `endSeconds` 는 「그 지점에서 멈춤」이라 반복이 되지 않음.
⇒ `setInterval`(**100ms**)로 `getCurrentTime()` 을 보고 끝점을 넘으면 `seekTo(시작점)` 함.
⇒ 그리고 `onStateChange` 의 `PLAYER_ENDED` 도 함께 다룸 — 끝점이 영상 끝과 같으면 시각 감시가 그
자리를 못 잡음.

### ⛔ 되짚은 함정 둘

1. **`onReady`·`onEmbedBlocked` 를 `useEffect` 의존성에 넣지 않았음.** 부모가 매 렌더에 새 함수를
   만들면 플레이어가 그때마다 파괴·재생성되어 **재생이 끊김.** 영상이 바뀔 때만 다시 만듦.
   (`eslint-disable-next-line react-hooks/exhaustive-deps` 를 근거와 함께 달았음.)
2. **적재가 끝나기 전에 화면을 떠난 경우**를 `cancelled` 로 막음 — 붙일 자리가 없는데 플레이어를
   만들면 누수가 됨.

### `@types/youtube` 를 들이지 않은 근거

쓰는 메서드가 여섯 개뿐이라 그 패키지를 관리하는 비용이 값어치를 넘음. 최소 타입을 직접 선언했고,
⚠️ **여기 없는 메서드를 부르려면 그 타입을 먼저 넓혀야 함** — 그것이 「무엇을 쓰는지」를 한자리에
남기는 장치임.

### 게이트 (이 턴에 직접 돌린 출력)

`tsc` **exit 0** · `eslint` **exit 0**.
⚠️ **프런트에 단위 테스트가 없으므로 실제 거동은 `TASK-169` 의 통합 테스트가 잼** — 여기서 「돈다」고
주장하지 않음.
<!-- SECTION:NOTES:END -->
