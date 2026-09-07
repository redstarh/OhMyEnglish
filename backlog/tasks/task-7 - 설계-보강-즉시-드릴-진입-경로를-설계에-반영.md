---
id: TASK-7
title: '설계 보강: 즉시 드릴 진입 경로를 설계에 반영'
status: Done
assignee: []
created_date: '2026-09-06 00:12'
updated_date: '2026-09-07 17:53'
labels:
  - caps-req
dependencies: []
ordinal: 7000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
캡틴 노트 항목 10. '질문 더 주세요'로 즉시 드릴을 생성하는 경로가 0곳이다(음성 명령 경로 자체가 3단계로 이연됐다). 없으면 설계에 반영한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 음성 명령 없이도 즉시 드릴을 낼 수 있는 경로가 있는지 확인
- [x] #2 음성 명령 이연 결정과 충돌하지 않는 진입 방식을 정한다(화면 버튼 등)
- [x] #3 설계에 반영하고 어느 슬라이스에서 구현할지 지정
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-08 AC#2·#3 닫는다 — 산출물 docs/design/2026-09-08-immediate-drill-entry-design.md. 핵심 판단: PRD.md:70(질문 더 주세요) 요청은 Voice Control 절(:79-85, 3단계 이연 대상)이 아니라 Additional Learning 절(:72-77)에 있고, 그 절이 이미 '질문 답변 5개' 메뉴 항목을 명세해 뒀다(drill_count 기본값 5·캡틴 결정 17과 정확히 일치, config.py:92 직접 확인). 그래서 AC#2 결론은 '새 버튼을 만들지 않고 그 기존 메뉴 항목을 쓴다'다 — Voice Control 절 자신이 '버튼이 1차, 음성은 미러'라고 명시해(:81) 이연과 충돌하지 않는다. 세션 안 자연어 요청(경로 A)과 세션 밖 진입(경로 B)을 갈랐다 — 전자는 gap-investigation.md:79-86이 이미 싼 처방(대화 규칙 한 줄)을 적어 뒀지만 TASK-6이 다루지 않아 소유자가 없다(범위 밖 발견, §6). 후자만 이 태스크가 답한다: 새 세션(시스템 프롬프트가 factory.py:63-70에서 생성자 인자로 굳고 setter가 없어 세션 중 갈아 끼울 수 없다) · 계획은 load_prepared_plan 재사용(새 계획 생성 없음, R11-4 준수) · drill_turns_expected는 특별 취급 없이 기존 공식 그대로. AC#3: 백엔드는 TASK-6·25 설계(Batch A/B/C, 지금 구현 중)가 이미 커버해 TASK-7이 새로 만들 것이 없고, 남는 진입 배선은 TASK-10이 추가 학습 진입점을 구조화한 뒤 그 구조 안에서 함께 구현한다 — 별도 슬라이스를 만들지 않는다. TASK-10에 요구 목록(learning_source 후보 2개 중 택1·started_via=ui·질문답변5개=새 세션 전제) 넘김. 기대값 관측과의 맞물림: 공식은 안 바뀌지만 즉시 드릴 세션이 조기 종료될 가능성이 높아 집계 미달 신호(결정10)가 learning_source 미세그멘테이션 시 오염될 위험을 §7에 기록 — 지금은 집계 job 자체가 없어(세션당 로그 1줄뿐) 즉시 조치할 자리가 없고 향후 집계 구현자에게 요구만 남긴다. 캡틴 결정 필요 없음(공개 계약·톤 계약 변경 없음). 상태는 In Progress로 둔다 — 리뷰·병합 판단은 팀리드 몫.

2026-09-08 정정 — 위 노트의 '상태는 In Progress로 둔다'는 낡았다. Stop 훅 G2(AC 전부 충족인데 In Progress)가 턴 종료를 막아 Done으로 올렸다 — 이 설계는 캡틴 결정이 필요 없고(§9) 공개 계약·톤 계약도 안 건드려 별도 캡틴/critic 게이트가 걸리지 않는다고 판단했기 때문이다. 팀리드가 검토 후 이견이 있으면 재오픈한다.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-09-06 05:05
---
TASK-6 과 같은 사유로 To Do 로 되돌린다(캡틴 명령, 감사 세션 전달). AC #1 은 닫혔고 #2·#3 은 음성 명령 이연 결정과 맞물린 설계 판단이라 별도 설계 회차가 필요하다. 상태만 In Progress 로 켜둔 채 방치하지 않는다.
---
<!-- COMMENTS:END -->
