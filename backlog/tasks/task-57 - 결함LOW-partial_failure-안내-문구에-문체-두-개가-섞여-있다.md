---
id: TASK-57
title: '결함(LOW): partial_failure 안내 문구에 문체 두 개가 섞여 있다'
status: To Do
assignee: []
created_date: '2026-09-09 08:33'
labels: []
dependencies: []
ordinal: 60000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-09 사용자 여정 회차에서 관측. app/frontend/app/results/[sessionId]/page.tsx:30 의 PARTIAL_FAILURE_NOTICE 가 일부 발화는 분석하지 못했다 — 재시도되지 않습니다 로 앞은 해라체, 뒤는 합쇼체다. 같은 화면의 다른 문구는 ~어요·~습니다 로 통일돼 있다(:39·:48·:54-56·:173). 관측 경로는 b2f0d169(partial_failure) 를 여는 것이다. 메인이 그 줄을 직접 열어 확인했다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 한 문장 안의 문체를 통일한다 — 예: 분석하지 못한 발화가 있습니다 — 재시도되지 않습니다
- [ ] #2 같은 화면의 다른 문구와 어투가 어긋나지 않는다
<!-- AC:END -->
