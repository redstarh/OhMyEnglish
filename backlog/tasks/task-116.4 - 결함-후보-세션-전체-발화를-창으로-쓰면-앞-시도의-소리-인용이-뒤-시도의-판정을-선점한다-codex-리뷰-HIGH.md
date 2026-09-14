---
id: TASK-116.4
title: '결함 후보: 세션 전체 발화를 창으로 쓰면 앞 시도의 소리 인용이 뒤 시도의 판정을 선점한다 (codex 리뷰 HIGH)'
status: Done
assignee: []
created_date: '2026-09-14 16:08'
updated_date: '2026-09-14 17:06'
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
- [x] #1 실패 시나리오를 단위 테스트로 재현한다 — 한 세션에 소리 둘이 인용된 발화와 시도 둘을 만들어 뒤 시도가 배제되는 것을 관측한다
- [x] #2 창을 시도별로 좁힐지 정한다 — ⛔ 좁히면 TASK-128.3 실측(코치가 판정 턴에서 소리를 인용했다)이 다시 문제가 되므로 그 회차를 근거로 함께 판단한다
- [x] #3 정한 방향을 구현하고 반대 방향 두 단정으로 지킨다 — 선점이 사라지는 것과 판정 턴의 인용이 여전히 잡히는 것
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
재현·결정·구현 2026-09-15 (세션 ohmyenglish-65).

AC#1 재현됨 — 순수 함수 수준에서 확인했음. 발화 First practice the "er" sound. Later repeat "fine". 에 키 f_as_p 를 주면 mismatched 였고, ⚠️ 같은 발화에서 낱말만 남긴 판(Later repeat "fine".)은 이미 None 이었음. 즉 소리 토큰이 «더 있는 것»이 판정을 나쁘게 만들었음. ⇒ 세션 창을 좁히는 문제가 아니라 «증거 선점» 문제임이 드러났음.

AC#2 정했음 — ⛔ 창을 시도별로 좁히지 않음. 이유 둘: ① 좁히려면 시도-발화 연결이 필요한데 nova_tool 시도에는 그 연결이 0/4 임(TASK-88 실측) ② TASK-128.3 이 「코치가 판정 턴에서 소리를 인용했다」를 실측했으므로 창을 시범 턴으로 좁히면 그 회차의 어긋남을 하나도 못 잡음. 대신 «증거가 갈리면 배제하지 않는다» 규칙을 넣었음 — 이 함수의 계약(어긋남을 증명할 수 있을 때만)에서 곧바로 따라옴. ⚠️ 이것은 구현 판단이고 사용자 결정이 아님(결정 82 의 전제를 뒤집지 않고 그 전제를 더 엄격히 지킴).

AC#3 구현·단정 완료 — 반대 방향을 함께 못박았음: 같은 발화에 키 th_as_s 는 여전히 mismatched(fine 이 그 소리를 담지 않음). 무력화로 판별력도 확인했음(그 갈래를 지우면 대상 테스트가 실패하고 되돌리면 통과 · MUTANT 흔적 0건).

게이트 넷 다 exit 0 — pytest 1199 passed · ruff check · ruff format --check 48 files · ty check.
<!-- SECTION:NOTES:END -->
