---
id: TASK-176
title: 재생 오류 전부에 안내와 YouTube 링크를 보인다 — 지금은 101·150 만 처리해 사용자가 영어 오류만 본다
status: Done
assignee: []
created_date: '2026-09-17 22:28'
updated_date: '2026-09-17 22:35'
labels: []
dependencies: []
ordinal: 237000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-173 의 실물 관측에서 찾았다. 없는 영상(ZZZZZZZZZZZ)을 담아 재생을 시도하면 YouTube iframe 이 'An error occurred. Please try again later.' 를 영어로 보이는데 우리 화면은 role=alert 가 0개다 — 한국어 안내도 YouTube 링크도 없다. lib/youtube.ts 주석은 '나머지 코드(2·5·100)는 사용자가 손쓸 수 없는 것이라 같은 문구로 모은다' 고 적었지만 VideoPlayer 의 onError 는 PLAYER_EMBED_BLOCKED=[101,150] 일 때만 콜백을 부른다 — 주석과 구현이 어긋났다. 사용자가 할 수 있는 일은 어느 코드에서나 'YouTube 에서 보기' 하나로 같으므로 코드 구분을 없앤다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 onError 를 코드 구분 없이 안내 경로로 모으고 PLAYER_EMBED_BLOCKED 상수를 없앰
- [x] #2 이름이 거짓이 되지 않게 콜백 이름을 실제 의미에 맞게 고침
- [x] #3 없는 영상은 onError 도 onReady 도 오지 않는 것을 대조군과 함께 실측하고 그 한계를 기록함
- [x] #4 tsc·eslint·next build 가 exit 0 인 것을 파이프 없이 확인함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 실측 2026-09-18 — 없는 영상은 IFrame API 가 «아무 이벤트도» 보내지 않는다

관측 장치: 같은 페이지에서 `window.YT.Player` 로 프로브 플레이어를 만들어 `onReady`·`onError`·`onStateChange` 를 수집했음.
⛔ **화면 밖(`left:-9999px`)에 두면 초기화되지 않아 대조군까지 timeout 이 됨** — `main` 안에 붙여야 함.

| 프로브 | videoId | 결과 |
|---|---|---|
| 대조군 | `jNQXAC9IVRw` | `onReady` 수신 |
| 시험 | `ZZZZZZZZZZZ` (없는 영상) | 20초 동안 `onReady`·`onError`·`onStateChange` **0건** |

⇒ 이전 주석이 적은 「`100` 영상 없음」은 **이 경로로 오지 않음.** 사용자 화면에서는 YouTube iframe 이 영어로
"An error occurred. Please try again later. (Playback ID: …)" 를 보이고 우리 안내는 0건임 —
⛔ **우리가 감지할 수 없으므로 코드 수정으로 닫히지 않음.**

## 이 태스크가 실제로 바꾼 것

`onError` 에서 코드 목록(`[101, 150]`)을 없앴음. 실효는 **`2`(잘못된 파라미터)·`5`(HTML5 오류)** 가 이제 안내로
모이는 것과 목록 유지 비용이 사라진 것임. ⚠️ **그 둘을 실물로 발화시켜 확인한 것은 아님** — 발화 경로를 만들
방법이 없음. 회귀 위험은 없음(이전에 통과했던 101·150 은 무조건 통과함).

게이트: `tsc` exit 0 · `eslint` exit 0 · `next build` exit 0(`/` 가 `○` Static 유지).
<!-- SECTION:NOTES:END -->
