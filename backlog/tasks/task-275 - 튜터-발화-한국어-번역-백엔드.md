---
id: TASK-275
title: 튜터 발화 한국어 번역 백엔드
status: To Do
assignee: []
created_date: '2026-09-26 04:24'
labels: []
dependencies: []
ordinal: 339000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
말풍선 [번역] 버튼의 백엔드. 발화는 (session_id, sequence_no) 로 가리킴
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 GET 또는 POST /api/sessions/{id}/utterances/{seq}/translation 이 한국어 번역을 줌
- [ ] #2 번역은 한 번만 만들고 저장해 재사용함(마이그레이션 포함)
- [ ] #3 LLM 호출 비용이 llm_calls 에 기록됨
- [ ] #4 화면 [번역] 버튼을 연결하고 번역문을 말풍선 안에 보여 줌
- [ ] #5 단위 테스트와 게이트 통과
<!-- AC:END -->
