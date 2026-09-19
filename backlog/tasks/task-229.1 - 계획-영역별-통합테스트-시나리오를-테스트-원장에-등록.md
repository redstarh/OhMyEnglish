---
id: TASK-229.1
title: '계획: 영역별 통합테스트 시나리오를 테스트 원장에 등록'
status: Done
assignee: []
created_date: '2026-09-19 05:11'
updated_date: '2026-09-19 05:22'
labels: []
dependencies: []
parent_task_id: TASK-229
ordinal: 291000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
개발된 영역을 빠짐없이 훑어 영역별로 시나리오 태스크를 테스트 원장(BACKLOG_CWD=tests/agent · 접두사 ts)에 만듦. 확인 단계는 AC 체크박스로 씀.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 영역 목록이 라우터·화면·job·음성경로·AC 문서를 근거로 확정됨
- [x] #2 영역마다 테스트 원장에 시나리오 태스크가 만들어짐
- [x] #3 실물 외부 호출이 필요한 영역이 별도로 표시됨
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
⚠️ 계획을 세운 뒤 넓혔음 (2026-09-19). 영역 목록을 라우터·화면·job 으로 독립 계수해 14개(TS-19~TS-32)를 세웠는데, 같은 목록을 따로 조사한 결과와 대조하니 **내가 넷을 빠뜨렸음** — 음성 명령 제어(voice_command) · 발음 코칭(mode=pronunciation) · 시나리오 생성·진행(generate_scenario) · 추가 학습 진입(source=additional). 빠뜨린 기전: 라우터·화면·job 을 셌으나 **WS 세션 안의 mode·source 분기를 세지 않았음** — 그 넷은 HTTP 경로를 갖지 않아 OpenAPI 계수에 걸리지 않음. TS-33~TS-36 으로 추가해 영역 18개가 됐음. ⇒ 교훈: 표면을 OpenAPI 로만 세면 WebSocket 안의 분기가 통째로 빠짐.
<!-- SECTION:NOTES:END -->
