---
id: TASK-5
title: '신규 기능: 학습 시나리오 생성기 (5회 질문으로 사용자 전용 주제 생성)'
status: In Progress
assignee: []
created_date: '2026-09-06 00:12'
updated_date: '2026-09-12 12:34'
labels:
  - caps-req
dependencies:
  - TASK-25
  - TASK-4
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
캡틴 노트 항목 8. 신규 기능이다. 학습자에게 5회 정도 질문해서 학습하고자 하는 시나리오를 생성한다. 사용자 전용 주제를 만드는 경로가 지금 0곳이다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 질문 5회의 흐름과 각 질문이 무엇을 좁히는지 정의
- [ ] #2 생성된 시나리오의 저장 위치와 기존 learning_scenarios와의 관계 정의(별도 표인가 같은 표인가)
- [ ] #3 생성 주체(글 모델인지 규칙인지)와 거부 경계 정의 — 모델이 만들 수 없는 값을 요구하지 않는다
- [ ] #4 요구사항 상세화 + 설계 반영. 트랙 A(풀)이므로 4 Lenses 전체를 설계서에 담는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
관계 정리 2026-09-12 (세션 ohmyenglish-f4). ⛔ 이 태스크는 TASK-102 의 AC#2 (사용자와 대화형 시나리오 생성) 와 같은 것이다. TASK-102 가 캡틴 요구사항 원문(2026-09-10)이고 이 태스크가 그 조각의 실행체다 — 둘을 따로 설계하면 갈라진다.

선행이 풀렸다: TASK-25·TASK-4 둘 다 Done 이다(TASK-4 는 2026-09-12 · 커밋 f2e9d83). TASK-4 가 정한 것이 이 태스크의 착지 지점이다 — 생성된 시나리오는 learning_scenarios 의 행 하나가 되고, 배치 규칙(결정 73·74)이 그것을 신규 후보로 집는다.

⛔ 착수 전에 읽을 것: docs/design/2026-09-12-scenario-rotation-70-30-design.md §3(시드 배열 순서가 제품 동작이다 · 결정 76) 과 §9(범위 밖 — 이 태스크가 그 자리를 가진다).
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-09-07 22:27
---
연관 감사(2026-09-08 팀리드): 선행에 TASK-4 를 더했다(기존 TASK-25 보존 — --dep 이 replace 라 한 번 지워졌다가 되돌렸다). 근거: 이 태스크가 만드는 「사용자 전용 시나리오」가 들어갈 자리를 TASK-4 가 정한다(주제 9종 분류 + 반복 70 대 신규 30 배치). 정책 없이 생성기를 만들면 생성물이 배치 비율 밖에 떨어진다.
---
<!-- COMMENTS:END -->
