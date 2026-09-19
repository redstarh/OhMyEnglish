---
id: TS-36
title: A18 · 추가 학습 진입과 즉시 드릴 — source=additional
status: In Progress
assignee: []
created_date: '2026-09-19 05:22'
updated_date: '2026-09-19 11:43'
labels: []
dependencies: []
ordinal: 36000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
영역 A18. 대상: 추가 학습 진입 경로(?source=additional)와 즉시 드릴 진입. 근거: PRD §7 Additional Learning · 설계서 2026-09-12-additional-learning-entry-design.md · 2026-09-08-immediate-drill-entry-design.md. ⛔ 세션 화면을 ?mode=… 쿼리로 열지 않음 — 페이지 로드 즉시 getUserMedia 가 불려 마이크 대체를 심을 틈이 없음(함정 H-CC). 쿼리 없이 / 로 열어 대체본을 먼저 심고 화면의 진입 버튼을 누를 것.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 하루 학습량을 채운 뒤에도 추가 학습을 시작할 수 있음
- [x] #2 추가 학습 종류(자유 대화·질문 다섯 개 더·자주 틀리는 패턴·업무 역할극·쉐도잉) 가운데 최소 셋이 진입됨
- [ ] #3 자주 틀리는 패턴에서 즉시 드릴을 만드는 경로가 성립함 (requirements-summary 「이 문법으로 연습 만들어줘」)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-19 배치 B5 — AC#1·#2 확인, AC#3 미확인이라 Blocked. ⚠️ AC#3 은 「관측 차단」이 아니라 「기능 부재로 인한 실패」임 — 원장 상태를 Blocked 로 둔 것은 이 배치의 지시(AC 하나라도 미확인이면 Blocked)를 따른 것임. AC#1 — 회차 시작 시 오늘(KST) 완료 0건이었고 TS-20 의 스텁 세션이 앱 경로로 그것을 채웠음(daily-summary completed_today=true · completed_scenarios=1). 그 상태에서 추가 학습 버튼 다섯이 모두 세션을 열었고 집계가 2→6 으로 늘었음. 화면에 권장량 게이트가 애초에 없음. AC#2 — 다섯이 진입됨(최소 셋 요구): 자유 대화 e7eb8948(speaking) · 약점 패턴 집중 7523a66f(speaking) · 질문 답변 5개 5eb0702e(scenario_intake · generate_scenario job 이 더 걸려 4건) · 발음 집중 072f8489(pronunciation) · 쉐도잉 f2b9d9fb(shadowing). 다섯 모두 learning_source=additional · started_via=ui. 업무 역할극은 disabled 이고 그것은 설계가 정한 빈 칸이라 결함이 아님. 자유 대화와 약점 패턴 집중이 같은 행을 남기는 것도 진입점 설계서 §2 의 의도임. AC#3 미확인 — 결과 화면이 패턴을 보여 주기만 하고 동작이 없음 · pattern_key 가 React key 로만 쓰임 · SessionEntry 에 패턴을 실을 자리가 없음 · practice_current_pattern 이 app/ 안 0건. PRD.md:70 이 글자로 요구하고 TASK-7 이 소유자 없음으로 적어 둔 자리임 ⇒ 결함 TASK-233 등록. ⛔ 브라우저는 쿼리 없이 localhost:3000/ 로 열어 마이크 대체본을 먼저 심었음(H-CC·H-CA). 회차 문서 runs/2026-09-19-b5/result.md §6.
<!-- SECTION:NOTES:END -->
