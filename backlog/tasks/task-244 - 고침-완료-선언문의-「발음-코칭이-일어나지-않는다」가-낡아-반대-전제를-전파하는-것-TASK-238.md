---
id: TASK-244
title: '고침: 완료 선언문의 「발음 코칭이 일어나지 않는다」가 낡아 반대 전제를 전파하는 것 (TASK-238)'
status: Done
assignee: []
created_date: '2026-09-19 07:49'
updated_date: '2026-09-19 08:09'
labels: []
dependencies: []
ordinal: 308000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
심각도 MEDIUM · 문서 결함 · 뿌리 그룹 A(발음·낭독). 결함 정본은 TASK-238 임. 현상: docs/design/2026-08-25-first-slice-acceptance-criteria.md:169 가 「발음 코칭이 지금 어떤 프롬프트 조건에서도 일어나지 않는다(실물 왕복 28회 · 조건 넷 전부 0)」와 「TASK-75 가 소유한다」를 그대로 두고 있으나, 2026-09-19 실측에서 mode=pronunciation 세션 1회에 pronunciation 프레임이 1/1 도착하고 pronunciation_attempts 1행·error_patterns 1행이 생겼음. TASK-75 는 2026-09-10 에 Done 임. ⛔ 실제로 오독을 만들었음 — 이 통합테스트의 배치 지시가 그 문장을 인용해 발음 영역을 「실패를 예상하는 자리」로 계획했음. ⛔ 28회 왕복 관측 자체는 그 시점에 참이었으므로 지우지 않고 「그 뒤에 무엇이 바뀌었는지」를 함께 적음.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 그 문장이 낡았음과 무엇이 바뀌었는지가 같은 자리에 적혀 있음
- [x] #2 28회 왕복 관측이 지워지지 않고 시점과 함께 남아 있음
- [x] #3 TASK-75 가 무엇으로 그것을 풀었는지와 설계 정본 경로가 적혀 있음
- [x] #4 TASK-238 에 고친 커밋을 적어 이음
<!-- AC:END -->
