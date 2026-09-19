---
id: TASK-241
title: '신설: 자주 틀리는 패턴에서 즉시 드릴을 만드는 경로 (TASK-233)'
status: To Do
assignee: []
created_date: '2026-09-19 07:49'
updated_date: '2026-09-19 08:02'
labels: []
dependencies: []
ordinal: 305000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
심각도 HIGH · 기능 부재 · 뿌리 그룹 B(진입·기록). 결함 정본은 TASK-233 임. PRD.md:70 이 글자로 요구하고(「사용자는 자주 틀리는 패턴을 직접 보고 해당 패턴으로 즉시 학습을 만들 수 있음」) TASK-7 이 소유자 없음으로 적어 둔 자리임. 관측: 결과 화면이 패턴을 보여 주기만 하고 동작이 없음 · pattern_key 가 React key 로만 쓰임 · SessionEntry 에 패턴을 실을 자리가 없음 · practice_current_pattern 이 app 안 0곳. ⛔ 기능 신설이라 설계가 먼저임 — 진입점 설계서(2026-09-12-additional-learning-entry-design.md)와 즉시 드릴 설계서(2026-09-08-immediate-drill-entry-design.md)를 읽고 기존 진입 경로를 재사용하는 쪽을 먼저 본다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 결과 화면의 패턴에서 그 패턴으로 학습을 시작하는 경로가 있음
- [ ] #2 그 경로로 연 세션이 어떤 패턴에서 왔는지 DB 에 남음
- [ ] #3 기존 추가 학습 진입 경로를 재사용했는지 또는 왜 못 했는지가 적혀 있음
- [ ] #4 TASK-233 에 고친 커밋과 판정을 적어 이음
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
설계 판단 (2026-09-19 · 코드를 읽고 정함 · 사용자에게 묻지 않음 — 요구사항 변경이 아니라 PRD.md:70 의 구현 방식 선택이므로 사전 승인 범위임).

TASK-233 이 갈림 둘을 적어 두었음: (1) 결과 화면 패턴 카드에 동작을 붙여 패턴 키를 세션 진입에 실음 (2) 세션 안 자연어 요청(경로 A)으로 처방함.
=> (1) 을 고름. 근거 셋:
  가. requirements-summary:53-54 가 「자주 틀리는 패턴을 직접 보고 즉시 학습을 만들 수 있음」으로 적어 화면 기점을 가리킴.
  나. 경로 A 는 TASK-7 이 범위 밖으로 갈라 둔 쪽이고 실물 Nova 없이는 관측이 안 됨(스텁이 학습자 발화를 발명함).
  다. (1) 은 기존 진입 기반(mode·source·item 세 질의값이 이미 같은 모양)을 그대로 재사용해 새 층을 만들지 않음.

읽어서 확정한 배선:
- 진입은 /ws/session 의 새 질의값 pattern=<pattern_key> 임 — _requested_item_or_none 과 같은 관례로 형태가 틀리면 무시함.
- 지시문은 SessionInstruction.focus (list[InstructionFocus] · pattern_key + target_form) 가 코치가 드릴하는 자리임. 고른 패턴으로 그 목록을 대체함.
- 준비된 계획이 없으면 plan 이 None 이라 접목할 자리가 없음. 그때 지시문을 새로 지어내지 않음 — target_level·sentence_length·hint_timing·contexts 는 프롬프트 문구 결정이고 이 태스크의 범위가 아님. 계획이 없으면 패턴만 세션 행에 적고 세션은 그대로 진행함(기존 AS4 계약 「계획이 없어도 학습은 시작됨」과 같은 규약).
- DB: learning_sessions 에 nullable focus_pattern_key text 를 더함(마이그레이션 031). 기존 관용(started_via·learning_source·scenario_pick)과 같은 모양임. 적용 전에 pg_dump -n ohmyenglish 백업을 먼저 뜸.
- summary jsonb 에 얹지 않음 — 그 칸은 세션 종료가 덮으므로 진입 기록이 사라짐.

착수 순서를 뒤로 미룸: 이것이 이번 묶음에서 가장 큰 일이고, 확실한 작은 수정 넷(TASK-242·243·244·245)을 먼저 닫은 뒤 이 태스크와 TASK-240 에 집중하는 것이 같은 시간에 더 많은 결함을 닫음. 판단은 위에 적어 두었으므로 미루는 동안 잃는 것이 없음.
<!-- SECTION:NOTES:END -->
