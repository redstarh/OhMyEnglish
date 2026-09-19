---
id: TS-34
title: A16 · 발음 코칭 — mode=pronunciation 실시간 판정
status: To Do
assignee: []
created_date: '2026-09-19 05:22'
labels: []
dependencies: []
ordinal: 34000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
영역 A16. 대상: WS mode=pronunciation · services/pronunciation.py. 근거: PRD §10. ⛔ 알려진 상태: Phase 1 완료 선언문이 「발음 기능은 미동작」이라 적었고 TASK-75 가 미해결임 — 그러므로 이 영역은 실패를 예상하는 자리이고, ⛔ 그 예상이 관측을 대신하지 않음. ⛔ 스텁은 학습자 발화를 발명하므로 발음 오류를 만들 수 없음 — 실물 또는 p8_inject_pronunciation.py 우회가 필요함. ⛔ 채점·점수는 비범위임(PRD §10.3).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 발음 오류에 대해 올바른 발음 시범이 돌아옴
- [ ] #2 따라 말한 결과가 성공·실패·판정 불가 가운데 하나로 기록됨
- [ ] #3 전사문에 한글이 섞인 경우와 되물음이 신호로 기록됨 (PRD §10.2)
- [ ] #4 미동작이면 무엇이 어디서 끊기는지 증거와 함께 적음 (TASK-75 와 이어 줌)
<!-- AC:END -->
