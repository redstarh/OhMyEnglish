---
id: TASK-148
title: '갈라냄: api/ws.py 의 도메인 정책 셋을 경계 밖으로 옮긴다 (고도 리뷰)'
status: To Do
assignee: []
created_date: '2026-09-16 15:36'
labels: []
dependencies: []
ordinal: 209000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
R4(고도) 리뷰 발견 셋. ① _pronunciation_candidates(180-216)가 순수 도메인 정책인데 「이 파일은 얇다」고 선언한 전송 계층에 있다 → services/pronunciation.py ② session_socket(336-513)에 WebSocket 프로토콜과 모드 셋의 도메인 정책이 누적됐고 그 자리에서 결정 67→72 반전 이력이 있다(범위가 넓어 쪼개야 한다) ③ 세션 mode 값역만 models/ 에 Literal 정본이 없다 — 다른 모든 CHECK 기반 값역은 그 관례를 따른다. ⛔ 정리 회차에서 갈라낸 이유: ②는 범위가 크고 ③은 타입 신설이라 둘 다 형태 정리를 넘는다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 셋 중 어느 것을 언제 할지 사용자가 정한다
<!-- AC:END -->
