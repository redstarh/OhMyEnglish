---
id: TASK-66.5
title: '구현 5: 엔드포인트 GET /api/shadowing/clips/{item_id}/audio'
status: Done
assignee: []
created_date: '2026-09-13 22:11'
updated_date: '2026-09-13 22:39'
labels: []
dependencies:
  - TASK-66.4
parent_task_id: TASK-66
ordinal: 153000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
계획서 Task 5. 세션 경로 밖에 둔다 — 클립은 여러 세션이 공유하는 제품 자산이라 세션 경계를 쓰지 않는다. StaticFiles 를 쓰지 않는다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 API 단정 넷이 통과한다 — 200 바이트·Content-Type · 404 셋 · 경로 모양 거부
- [x] #2 라우터 등록을 지워 red 를 보고 되돌린다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
완료 2026-09-14 (세션 ohmyenglish-f4).

red 를 먼저 봤음 — 첫 단정이 assert 404 == 200 으로 실패. ⚠️ 404 를 기대하는 넷은 라우트가 없어도 통과하므로 첫 건의 빨강이 이 단계의 유일한 신호였음(계획서가 그것을 미리 적어 뒀음).

단정 다섯: 200 의 바이트와 Content-Type(audio/wav) · 없는 클립 404 · 파일 없음 404 · 포인터 null 404(⚠️ 파일이 뿌리에 있어도 404 여야 함 — 「뿌리를 훑어 파일이 있으면 준다」는 구현을 배제함) · 경로 모양 item_id 가 파일시스템에 닿지 않음.

라우터는 /api/shadowing 을 따로 씀 — 클립은 세션에 매이지 않은 제품 자산이라 세션 경계를 흉내 내지 않음. StaticFiles 를 쓰지 않은 근거는 recording_url 주석이 이미 정한 방향임.

판별력: include_router(shadowing_router) 한 줄을 지워 1 failed 4 passed 를 보고, 되돌린 뒤 H-BS 대로 __pycache__ 까지 지우고 5 passed 를 다시 읽었음.

게이트: 5 passed · ruff check 0 · format 정합 · ty 0.
<!-- SECTION:NOTES:END -->
