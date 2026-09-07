---
id: TASK-25.3
title: '구현 C: 노출 — SessionResult.drill · API 키 생략 규약 · 프론트 한 문장 (§6 항목 9·7·8)'
status: To Do
assignee: []
created_date: '2026-09-07 14:21'
labels: []
dependencies:
  - TASK-25.2
parent_task_id: TASK-25
ordinal: 35000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
설계서 §6 의 9·7·8. 브리프 정본은 .superpowers/sdd/.../batch-C-brief.md. 읽기 경로다 — 기대값은 B 가 쓰고 여기서는 읽고 세고 노출/감춘다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 services/results.py 에 SessionResult.drill + 전이 세기 SQL(사용자→코치 전이 · utterance_type='learning' 함께 거른다) · 조회를 라우터에 두지 않는다
- [ ] #2 판별력 4건 — 코치 연속 2건은 1만 · 코치 선발화 제외 · learning 아닌 행 제외 · 사용자 발화만 있는 세션은 0
- [ ] #3 R2 상태 3개(analyzing·connection_failed·no_utterances)에서 drill 키가 부재한다 — 기대값이 있어도 그렇다 (D5-4)
- [ ] #4 미달이면 warning 한 줄에 두 수를 적는다 (INFO 금지 — H-Z)
- [ ] #5 프론트 결과 화면 — 미달일 때만 숫자 없는 한 문장 · 주어는 세션 · 미달 아니면 아무것도 그리지 않는다 (유도 10)
- [ ] #6 백엔드 게이트 유지/증가 + 프론트 npx tsc --noEmit · npx eslint app lib 둘 다 exit 0
<!-- AC:END -->
