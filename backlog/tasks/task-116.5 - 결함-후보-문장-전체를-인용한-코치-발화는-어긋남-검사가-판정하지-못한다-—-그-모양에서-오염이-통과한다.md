---
id: TASK-116.5
title: '결함 후보: 문장 전체를 인용한 코치 발화는 어긋남 검사가 판정하지 못한다 — 그 모양에서 오염이 통과한다'
status: To Do
assignee: []
created_date: '2026-09-14 17:19'
updated_date: '2026-09-14 17:27'
labels: []
dependencies: []
parent_task_id: TASK-116
ordinal: 173000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
codex 리뷰(2026-09-15)가 MEDIUM 으로 지목하고 단위 테스트가 이름을 붙여 둔 구멍이다(test_a_whole_sentence_quote_is_still_not_judged). _QUOTED_TOKEN_RE 는 토큰에 공백을 넣지 않으므로 I hear you say "my brother will arrive early tomorrow morning." 같은 문장 전체 인용은 잡히지 않고 판정이 None 이 된다 ⇒ 그 세션의 어긋난 기록이 복습 시계를 그대로 전진시킨다. 실측에서 브라우저 레그 코치가 실제로 그 모양을 썼다(runs/2026-09-15-task81-app-leg §7). ⛔ 문장을 낱말로 쪼개 넣는 안은 기각했다 — 한 문장에는 낱말이 여럿이라 어느 낱말이든 키의 조각을 담을 확률이 높아지고 갈래 ②가 사실상 언제나 None 이 되어 판정력이 사라진다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 그 모양이 실제로 얼마나 자주 오는지 센다 — 이미 있는 회차 기록의 코치 발화를 세어 비율을 얻는다(새 회차를 돌리지 않는다)
- [x] #2 닫을 자리를 고른다 — 검사(문장에서 소리를 얻는 다른 수단)인지 프롬프트(코치가 소리를 인용하게 만드는 것)인지 가른다. ⛔ 후자는 결정 82 가 「프롬프트를 더 고치지 않는다」로 막은 방향이므로 뒤집으려면 사용자 판단이 필요하다
- [ ] #3 정한 방향을 구현하고 반대 방향 두 단정으로 지킨다 — 문장 인용이 잡히는 것과 정상 기록이 배제되지 않는 것
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
측정·판단 2026-09-15 (세션 ohmyenglish-65) — 정본은 tests/harness/runs/2026-09-15-task116-5-quote-shapes/README.md 임. 실물 모델 사용 0.

AC#1 측정됨: 기존 프레임 증거 66파일의 코치 발화 120건을 제품 문턱으로 분류했음 — sound 44/120 · word 10/120 · sentence_only 5/120 · none 61/120. ⚠️ 판정은 세션 단위로 도므로 결정에 걸리는 수치는 세션 단위임: 판정 가능 37/59 · ⛔ 문장 인용만 있어 막힌 세션 2/59 · 인용 전혀 없음 20/59. ⇒ 이 태스크가 겨냥한 구멍은 2/59 이고, 더 큰 미판정 덩어리(20/59)는 설계가 받아들인 자리라 결함이 아님.

AC#2 정했음(위임받음): ⛔ 지금 닫지 않음. 검사 쪽 안(문장을 낱말 자루로 쪼갬)은 이득이 0 임 — 낱말이 여럿이라 갈래 ②가 거의 항상 None 이 되어 지금과 같음. 프롬프트 쪽 안은 결정 82 가 막았고 2/59 로 그 판단을 요청할 근거가 약함. ⇒ 수치를 남기고 To Do 로 파킹함.

⛔ AC#3(구현)은 하지 않았으므로 체크하지 않았고 태스크를 닫지 않았음 — 결과에 맞춰 AC 문면을 고치지 않음. 다시 올릴 조건은 이 비율이 커지는 것이고 그때 같은 스크립트로 다시 셈.
<!-- SECTION:NOTES:END -->
