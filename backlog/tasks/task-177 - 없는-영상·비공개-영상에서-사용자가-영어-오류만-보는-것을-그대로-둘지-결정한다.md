---
id: TASK-177
title: 없는 영상·비공개 영상에서 사용자가 영어 오류만 보는 것을 그대로 둘지 결정한다
status: Awaiting Decision
assignee: []
created_date: '2026-09-17 22:35'
updated_date: '2026-09-17 22:36'
labels: []
dependencies: []
ordinal: 238000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-176 실측: 없는 videoId 는 IFrame API 가 onReady·onError·onStateChange 를 하나도 보내지 않는다(대조군은 onReady 수신). 그래서 우리 코드로는 감지할 수 없고, 사용자는 YouTube 가 영어로 보이는 'An error occurred…' 만 본다. 담아 둔 영상이 나중에 삭제·비공개되면 이 상태가 된다. 감지 방법은 onReady 타임아웃 추론뿐이고 느린 회선에서 오탐이 나 정상 영상에 '재생할 수 없어요' 가 뜬다 — 오탐이 무응답보다 나쁘다. 그래서 기능을 더하지 않는 쪽을 권고한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 타임아웃 추론을 넣을지 사용자가 결정함
<!-- AC:END -->
