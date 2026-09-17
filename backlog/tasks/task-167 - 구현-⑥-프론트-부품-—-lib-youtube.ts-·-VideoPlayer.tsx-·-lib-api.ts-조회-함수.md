---
id: TASK-167
title: '구현 ⑥: 프론트 부품 — lib/youtube.ts · VideoPlayer.tsx · lib/api.ts 조회 함수'
status: To Do
assignee: []
created_date: '2026-09-17 17:17'
updated_date: '2026-09-17 17:17'
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
- [ ] #1 lib/youtube.ts 에 fetchVideoMeta · thumbnailUrl · loadPlayerApi 를 만들었다
- [ ] #2 ⛔ fetchVideoMeta 가 videoId 를 뽑지 않는다 — 파싱 규칙이 두 곳에 갈리지 않는다
- [ ] #3 fetchVideoMeta 가 실패(400 포함)에 null 을 준다
- [ ] #4 VideoPlayer.tsx 가 new YT.Player 로 플레이어를 만들고 onStateChange·onError 를 받는다
- [ ] #5 구간 반복을 onStateChange 와 getCurrentTime 으로 구현했다 (IFrame API 에 반복 기능이 없다)
- [ ] #6 ⛔ 플레이어 컨트롤을 가리지 않는다 (정책 III.I.6)
- [ ] #7 lib/api.ts 에 엔드포인트 여섯의 조회 함수를 더했다 (전용 화면은 실패를 null 로 — 기존 관례)
- [ ] #8 npx tsc --noEmit 와 npx eslint . 가 통과한다
<!-- AC:END -->
