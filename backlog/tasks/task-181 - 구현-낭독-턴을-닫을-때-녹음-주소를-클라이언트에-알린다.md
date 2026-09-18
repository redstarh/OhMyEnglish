---
id: TASK-181
title: '구현: 낭독 턴을 닫을 때 녹음 주소를 클라이언트에 알린다'
status: Done
assignee: []
created_date: '2026-09-18 01:40'
updated_date: '2026-09-18 01:48'
labels: []
dependencies: []
ordinal: 242000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
_close_recording_turn 이 발화 행을 만들고 파일을 승격하지만 클라이언트에 아무 이벤트도 보내지 않는다. 그래서 화면은 자기가 방금 만든 녹음의 utterance_id 를 알 길이 없다. shadowing_recording 이벤트 하나로 그 주소를 알린다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 낭독 턴이 정상 저장되면 서버가 shadowing_recording 이벤트로 utterance_id 를 보낸다
- [x] #2 저장할 바이트가 없거나 DB 저장이 실패한 턴에는 이벤트를 보내지 않는다
- [x] #3 프런트 ServerEvent 에 그 갈래가 있고 tsc 가 통과한다
<!-- AC:END -->
