---
id: TASK-61.11
title: 음성 명령 「학습 계속」 — 세션을 잇는 개념 자체가 리포에 없다
status: In Progress
assignee: []
created_date: '2026-09-15 16:17'
updated_date: '2026-09-16 04:52'
labels: []
dependencies: []
parent_task_id: TASK-61
ordinal: 186000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
PRD §Voice Control 의 남은 명령 셋 가운데 하나다.

⛔ 지금 열 자리가 아닌 이유: learning_sessions.status 에 되돌아오는 전이가 없고(active→completed·failed 만) 버려진 세션은 잇는 것이 아니라 reap_orphan_sessions 가 failed 로 걷는다. 프론트의 시작 계열 버튼 셋은 전부 새 세션을 여는 것이고 기존 세션을 잇는 표면은 없다.

⚠️ 「계속」이 무엇을 뜻하는지가 먼저다 — ① 닫힌 세션의 대화 문맥을 이어받는 새 세션인가 ② 정지된 세션을 되살리는 것인가(그러면 TASK-61.9 와 같은 선행 조건을 가진다). ①이면 Nova 의 conversation history 주입(공식 문서: 시스템 프롬프트 뒤·오디오 전에 한 번)이 수단이 될 수 있고 그것은 새 설계다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 「계속」의 뜻을 사용자 판단으로 확정한다 — 문맥 이어받기인가 정지 세션 되살리기인가
- [x] #2 정한 뜻에 맞는 수단을 설계한다 (문맥 주입이면 그 계약을 정본 문서에 적는다)
- [ ] #3 명령을 만들면 실물 회차로 관측한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-16 — 결정 117 로 뜻을 확정했음(정지된 그 세션을 그대로 이음) ⇒ TASK-61.9 와 한 기능이고 구현도 그쪽에 함께 들어갔음. AC#1·#2 를 닫았음. AC#3(실물 회차)은 61.9 AC#3 과 같은 회차가 닫음.
<!-- SECTION:NOTES:END -->
