---
id: TASK-17
title: '프론트엔드 검증 T6: 검증 에이전트 정의를 만든다'
status: In Progress
assignee: []
created_date: '2026-09-06 00:13'
updated_date: '2026-09-06 02:12'
labels:
  - caps-req
dependencies:
  - TASK-18
priority: high
ordinal: 17000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
캡틴 노트 항목 2가 '프론트엔드 테스트 Agent 존재여부 먼저 판단'을 요구했다. 판단 결과: 없다. 전역에 testagent·en-coach-reviewer·hermes만 있고 셋 다 브라우저 제어 도구가 없다(직접 확인). 계획서 T6이 이 일을 소유하고 캡틴이 이미 '만든다'로 확정했다. 절차 정본은 추적되는 tests/harness/browser_leg.md이고 에이전트 파일은 커밋하지 않는다(캡틴 결정).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 브라우저 제어 도구를 가진 에이전트 정의를 만든다
- [x] #2 절차를 에이전트 정의에 재서술하지 않고 browser_leg.md를 가리킨다
- [x] #3 에이전트를 실제로 1회 호출해 재현시키고 호출자가 단정 하나를 직접 재현해 대조
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
⚠️ 외부 감사(claude_air_1-4) 1회차가 AC#3 미이행을 잡았다 — 팀리드가 근거를 직접 확인해 수용했다. 에이전트 호출과 결과 수용은 일어났으나 회차 기록을 만들지 않아 리포에 호출 증거가 0건이었다(1회차 기록의 커밋 10:28:38 이 에이전트 파일 생성 10:33:05 보다 4분 이르다 — 에이전트가 없을 때 만든 기록이다). 증거 없는 판정은 무효라는 규약대로 되돌렸고 tests/harness/runs/2026-09-06-browser-leg-2-agent.md 를 만들었다. 교훈: 방식이 지시된 태스크는 그 방식이 실행됐다는 산출물을 리포에 남기는 것까지가 이행이다 — 대화 기록은 제3자가 볼 수 없다.
<!-- SECTION:NOTES:END -->
