---
id: TS-33
title: A15 · 음성 명령 제어 — voice_command tool 호출
status: To Do
assignee: []
created_date: '2026-09-19 05:22'
labels: []
dependencies: []
ordinal: 33000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
영역 A15. 대상: WS 세션 안의 voice_command tool 호출. 근거: PRD 「UI와 음성 제어」 — 화면 기능 여덟을 음성으로도 제어할 수 있어야 함(추가 연습 시작·질문 다섯 개 더·천천히 다시 말해줘·힌트 줘·다음 문제·오늘 학습 끝낼게). 학습 답변과 음성 명령이 섞이지 않아야 함(명령 버튼 또는 Oh My English 호출어). ⚠️ 자동 테스트는 unit/test_voice_command.py 의 페이로드 검증뿐이라 종단은 미확인임.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 명령 여섯 가운데 최소 넷이 세션 안에서 실제로 동작함
- [ ] #2 학습 답변이 음성 명령으로 오인되지 않는 경계가 성립함
- [ ] #3 화면 버튼과 음성 명령이 같은 기능에 닿음
<!-- AC:END -->
