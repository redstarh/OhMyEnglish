---
id: TASK-269
title: 발음교정중 상태에서 학습이 멈춤
status: Done
assignee: []
created_date: '2026-09-26 02:30'
updated_date: '2026-09-26 02:41'
labels: []
dependencies: []
ordinal: 333000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 신고 2026-09-26: 실사용 스택에서 발음교정중 표시 뒤 진행되지 않음
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 멈춤의 근본 원인을 로그·코드로 확정함
- [x] #2 재현 테스트를 먼저 세우고 수정함
- [x] #3 백엔드 게이트 통과
- [x] #4 리뷰 결과를 반영하고 커밋함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
원인: 발음 tool(report_pronunciation_coaching) 호출에 toolResult 를 돌려주지 않았음(결정 109 의 범위). 세션 6d09b03f 에서 11:30:21 학습자 재발화 직후 턴 끝에 pending 호출이 왔고 그 뒤 에이전트 발화·학습자 전사 0건. 설계서 2026-08-27-pronunciation-echo-design.md §9 미결 1 이 예고한 다중 턴 거동임. 수정: PronunciationEvent.tool_use_id 추가 · 번역기가 싣고 NovaAdapter._pump_output 이 곧바로 {status: recorded} 결과를 보냄. 게이트: pytest 1433 passed · ruff 0 · ruff format 통과 · ty 0. 백엔드 :8002 재기동(PID 50020). 미확인: 실물 Nova 가 결과를 받은 뒤 이어 말하는지는 다음 실사용 대화에서 확인해야 함.

리뷰(opus) CRITICAL·HIGH 0건. MEDIUM 1건 반영: 결과를 toolUse 즉시가 아니라 contentEnd(TOOL) 뒤에 보냄(공식 샘플 순서) · 시점 단정 테스트 추가. 최종 게이트: pytest 1434 passed · ruff 0 · ruff format 통과 · ty 0. 백엔드 :8002 재기동(PID 69622).
<!-- SECTION:NOTES:END -->
