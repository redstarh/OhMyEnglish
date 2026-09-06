---
id: TASK-18
title: '프론트엔드 검증 T1: browser_leg.md 신설 (절차 정본)'
status: To Do
assignee: []
created_date: '2026-09-06 00:13'
labels: []
dependencies: []
ordinal: 18000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
계획서 docs/design/2026-09-05-frontend-test-agent-plan.md T1. 착수 조건은 닫혔다(N-1~N-4 + M-a~M-c 반영, 커밋 78cbba9). 프리플라이트 + C1~C5 단정 + 음성 대조 표를 담는다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 자기검증 기준은 인용 유무가 아니라 유도 방식이다 — 각 수치가 픽스처 연역·런타임 유도·불가 사유 중 하나를 갖는다
- [ ] #2 모든 단정에 음성 대조가 짝지어져 있는지 표에서 빈칸을 센다(빈칸 0)
- [ ] #3 health 응답과 .env.local 포트를 직접 돌려 출력을 문서에 적는다
- [ ] #4 스택 3개(DB·백엔드·프론트)를 띄운 상태에서 수행한다
<!-- AC:END -->
