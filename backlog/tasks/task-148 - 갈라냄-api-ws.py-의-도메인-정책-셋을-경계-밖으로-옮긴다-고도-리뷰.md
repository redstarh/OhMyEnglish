---
id: TASK-148
title: '갈라냄: api/ws.py 의 도메인 정책 셋을 경계 밖으로 옮긴다 (고도 리뷰)'
status: To Do
assignee: []
created_date: '2026-09-16 15:36'
updated_date: '2026-09-16 23:01'
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 방향 확정 (2026-09-17 · 결정 122)

사용자가 「기능을 쪼개」로 정했음 — 즉 이 태스크는 「할지 말지」가 아니라 「어떻게 쪼개는가」만 남았음.
착수하지 않았으므로 상태를 To Do 로 되돌림(진행 중이 아님).

쪼갤 것 넷(고도 리뷰 R4 의 발견 + FIXED_USER_ID):
① _pronunciation_candidates(180-216) → services/pronunciation.py (순수 함수라 위험 낮음)
② session_socket(336-513) 의 모드별 정책 → services 쪽 표·전략 (범위가 커서 다시 쪼개야 함)
③ 세션 mode 값역 → models/ 에 Literal 신설 (001 CHECK 와 짝을 맞춤)
④ FIXED_USER_ID 를 ws.py 밖으로 (지금 형제 라우터 둘이 옆으로 참조함)

⛔ 착수 순서 권고: ③ → ① → ④ → ②. ②가 가장 크고 나머지 셋이 그 준비가 됨.
<!-- SECTION:NOTES:END -->
