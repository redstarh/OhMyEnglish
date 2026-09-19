---
id: TASK-245
title: '고침: TS-29 AC 문면을 낭독 판정의 확정 계약에 맞춘다 (TASK-235)'
status: Done
assignee: []
created_date: '2026-09-19 07:49'
updated_date: '2026-09-19 08:09'
labels: []
dependencies: []
ordinal: 309000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
심각도 LOW · 테스트 AC 결함 · 뿌리 그룹 A(발음·낭독). 결함 정본은 TASK-235 임. 현상: TS-29 AC#3 이 「성공·실패·판정 불가」를 요구하나 낭독 판정의 값역은 낱말마다 match·missing·different 임. 연결하지 않는 것이 확정된 계약임 — 설계서 2026-09-18-read-aloud-judgment-design.md §5 가 「판정 확정(TASK-211): 연결하지 않음. v1 유예가 아니라 결론임」으로 적고 근거 셋을 가짐. PRD §10 의 성공·실패·판정 불가는 R10-2 의 재발화 값역이고 낭독 판정의 값역이 아님. ⇒ 코드가 아니라 AC 를 고침. 전례는 TASK-231 임.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 TS-29 AC 문면이 낱말 단위 값역과 전사문 저장으로 바뀜
- [x] #2 고친 근거(설계서 §5 와 PRD 조항의 구분)가 TS-29 노트에 적혀 있음
- [x] #3 그 AC 로 TS-29 가 판정돼 Blocked 가 풀림
<!-- AC:END -->
