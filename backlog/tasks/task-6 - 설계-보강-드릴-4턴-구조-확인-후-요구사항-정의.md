---
id: TASK-6
title: '설계 보강: 드릴 4턴 구조 확인 후 요구사항 정의'
status: In Progress
assignee: []
created_date: '2026-09-06 00:12'
updated_date: '2026-09-06 00:19'
labels: []
dependencies: []
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
캡틴 노트 항목 9. 드릴마다 4턴 이상을 요구하는데 턴 구조를 정하는 코드·지시문이 0곳이다. 구조를 먼저 확인하고 없으면 추가 요구사항을 정의해 설계에 반영한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 현재 턴 구조를 정하는 자리가 있는지 코드로 확인해 결과를 적는다(있다/없다 + 근거)
- [ ] #2 없으면 요구사항을 정의하고 설계에 반영
- [ ] #3 지시문에 실을지 코드로 강제할지 근거와 함께 선택(교정 상한이 문구로만 좁힌 선례를 참고)
<!-- AC:END -->

## 캡틴 결정 (2026-09-06) — 재론하지 않는다

**드릴 4턴을 코드로 강제한다. 드릴 횟수는 설정값(config·env)에 따로 두고 읽는다.**
⚠️ 새 설정 체계를 만들지 마라 — `app/backend/app/config.py`의 `Settings`에 필드를 더한다.
⚠️ "코드로 강제"의 범위와 미달 시 동작은 docs/design/2026-09-06-captain-decisions.md §2가 소유한다(자유 발화 턴 수는 사후 관측만 가능하다).
**결정 2와 같은 자리를 건드린다** — 질문 전달과 함께 설계한다.
