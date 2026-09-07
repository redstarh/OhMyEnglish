---
id: TASK-36
title: '관측: 기대 exchange 상한 20 이 10분 세션에서 실현 가능한지 실측한다 (캡틴 결정 20)'
status: Awaiting Decision
assignee: []
created_date: '2026-09-07 17:26'
updated_date: '2026-09-07 22:27'
labels: []
dependencies:
  - TASK-37
ordinal: 39000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
critic 재검증 2회차 R-6(MEDIUM). 캡틴 결정 17 로 기대값이 질문 3개→12 · 4개→16 · 5개→20 이 됐다(팀리드 실측 산식). PRD.md:21 은 '세션당 10분 이상' · :46 은 '오늘의 10분 Speaking 세션' 이라 20 exchange 는 하나당 30초다. 설계서에 세션 길이 정합을 따진 자리가 0건이었다(grep 확인). 캡틴 결정 20 이 '지금은 받아들이고 실제 로그로 판정한다' 로 닫았고, 실현 가능성 실측은 워커·실물 호출이 필요하므로 별도 승인 사안으로 미뤘다.

⛔ 이 태스크가 답할 것은 하나다: 미달 로그가 '모델이 지시를 어겼다' 인지 '상한이 애초에 불가능하다' 인지. 그 구분을 못 하면 불가능한 문턱을 향해 지시문을 고치게 되고 그것이 H-4 부류가 세 번째로 돌아오는 경로다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 스텁이 아니라 실물 세션 1회 이상의 exchange 수와 소요 시간을 재고 기록한다 — 워커·실물 호출이 필요하므로 착수 전 캡틴 확인을 받는다
- [ ] #2 20 exchange 가 10분에 닿는지 판정하고 근거를 남긴다 — 닿지 않으면 무엇을 바꿀지(drill_turns_min 하향 · 기대값 상한 · 세션 길이 재정의) 선택지를 캡틴에게 올린다
- [ ] #3 판정 결과를 설계서 §2.3·§5 와 captain-instruction-register 의 결정 20 에 반영한다 — 결정 20 이 기록한 모호함이 닫히는지 함께 적는다
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-09-07 22:17
---
정리(2026-09-08 팀리드): To Do → Awaiting Decision. 근거 — AC#1이 스스로 「워커·실물 호출이 필요하므로 착수 전 캡틴 확인을 받는다」고 적는데 상태가 To Do여서 브리핑이 「착수 가능」으로 올렸다. AC 본문과 상태가 서로 모순이었다. ⚠️ TASK-13·TASK-24와 같은 실물 세션 1회로 묶는다 — 세 태스크가 각각 세션을 켜면 비용을 세 번 낸다.
---

created: 2026-09-07 22:27
---
연관 감사(2026-09-08 팀리드): 선행 TASK-37 을 건다. AC#1 이 요구하는 「실물 세션 1회 이상의 exchange 수와 소요 시간」이 TASK-37 5차수의 Nova 실행에서 그대로 나온다 — 별도 세션이 필요 없다.
---
<!-- COMMENTS:END -->
