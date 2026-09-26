---
id: TASK-274
title: 튜터 발화 음성 다시 듣기 백엔드
status: To Do
assignee: []
created_date: '2026-09-26 04:24'
labels: []
dependencies: []
ordinal: 338000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
말풍선 [음성] 버튼의 백엔드. 발화는 (session_id, sequence_no) 로 가리킴 — final 프레임이 이미 sequence_no 를 실음. 화면은 같은 화자의 연속 final 을 한 줄로 합치므로 한 줄이 여러 sequence_no 일 수 있음
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 방식을 정해 docs/design 에 남김 — Nova 출력 오디오를 발화별로 보관할지 TTS 로 다시 합성할지
- [ ] #2 GET /api/sessions/{id}/utterances/{seq}/audio 가 그 발화의 오디오를 줌
- [ ] #3 보존 기한이 기존 낭독 녹음 규약(당일 삭제)과 맞음
- [ ] #4 화면 [음성] 버튼을 연결하고 합쳐진 줄은 순서대로 재생함
- [ ] #5 단위 테스트와 게이트 통과
<!-- AC:END -->
