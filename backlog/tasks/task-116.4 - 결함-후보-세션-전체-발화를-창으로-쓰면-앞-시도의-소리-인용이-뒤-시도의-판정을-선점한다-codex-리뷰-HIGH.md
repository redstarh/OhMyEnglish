---
id: TASK-116.4
title: '결함 후보: 세션 전체 발화를 창으로 쓰면 앞 시도의 소리 인용이 뒤 시도의 판정을 선점한다 (codex 리뷰 HIGH)'
status: To Do
assignee: []
created_date: '2026-09-14 16:08'
labels: []
dependencies: []
parent_task_id: TASK-116
ordinal: 171000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
codex 리뷰가 2026-09-15 에 지목했고 나는 코드로 확인해 «결정 98 이전부터 있던 것»으로 판정했다 — 이 세션의 변경이 만든 것이 아니다. check_recorded_sounds 는 세션의 agent 발화 전부를 이어 붙여 한 문자열로 만들고 그것을 그 세션의 «모든» 미판정 시도에 같이 쓴다(창을 넓게 둔 것은 의도이고 근거는 그 함수 주석과 설계서 4-1 이다). 그런데 한 세션에서 소리 둘을 코칭하면 앞 시도가 인용한 짧은 소리가 갈래 ①을 선점해 뒤 시도의 정상 기록이 mismatched 로 배제될 수 있다. 실패 시나리오: 발화가 First practice the er sound. Later repeat fine. 이고 뒤 시도의 키가 f_as_p 인 경우 — er 이 f_as_p 안에 없어 어긋남으로 판정된다. ⚠️ 갈래 ②(낱말)는 반대로 안전하다 — 낱말 하나라도 키의 조각을 담으면 None 이 되어 배제하지 않는다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 실패 시나리오를 단위 테스트로 재현한다 — 한 세션에 소리 둘이 인용된 발화와 시도 둘을 만들어 뒤 시도가 배제되는 것을 관측한다
- [ ] #2 창을 시도별로 좁힐지 정한다 — ⛔ 좁히면 TASK-128.3 실측(코치가 판정 턴에서 소리를 인용했다)이 다시 문제가 되므로 그 회차를 근거로 함께 판단한다
- [ ] #3 정한 방향을 구현하고 반대 방향 두 단정으로 지킨다 — 선점이 사라지는 것과 판정 턴의 인용이 여전히 잡히는 것
<!-- AC:END -->
