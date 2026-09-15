---
id: TASK-61.5
title: '결함: 한국어 명령에서 코치가 확인 질문을 소리로 말하지 않는다 (누적 0/3)'
status: To Do
assignee: []
created_date: '2026-09-15 05:04'
labels: []
dependencies: []
parent_task_id: TASK-61
ordinal: 180000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
정본은 tests/harness/runs/2026-09-15-task61-4-refix-verify §6-2·§6-3 임. 결정 104(D3)의 프롬프트 고침은 영어 명령에서 4/4 로 들었지만 한국어 명령에서는 세 세션 모두 코치 오디오가 0 이었다. 확인 발화가 흐른 것은 하네스가 시간으로 밀어 넣었기 때문이고, 실제 학습자는 무엇을 확인해야 하는지 듣지 못한다.

⚠️ 원인 미확정. 후보 둘 — ① 시스템 프롬프트가 영어이고 규칙 13 이 영어 예시만 든다 ② Nova 가 한국어 입력 턴에서 발화를 만들지 않는 거동이 있다. ⛔ 통계를 늘리기 전에 어느 쪽인지 가르는 관측을 고른다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 원인 후보 둘을 가르는 관측을 먼저 정한다 — 프롬프트에 한국어 예시를 더한 판과 그대로인 판을 같은 픽스처로 대조한다
- [ ] #2 고친 뒤 한국어 명령에서 코치가 확인을 소리로 묻는 것을 실물로 관측한다
- [ ] #3 영어 경로가 회귀하지 않은 것을 같은 회차에서 확인한다
<!-- AC:END -->
