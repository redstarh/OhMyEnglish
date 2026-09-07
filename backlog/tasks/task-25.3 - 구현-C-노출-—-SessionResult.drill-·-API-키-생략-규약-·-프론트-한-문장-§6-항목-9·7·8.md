---
id: TASK-25.3
title: '구현 C: 노출 — SessionResult.drill · API 키 생략 규약 · 프론트 한 문장 (§6 항목 9·7·8)'
status: Done
assignee: []
created_date: '2026-09-07 14:21'
updated_date: '2026-09-07 16:43'
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
- [x] #1 services/results.py 에 SessionResult.drill + exchange 세기 SQL — 코치 발화 바로 뒤에 온 '사용자' 발화를 센다(설계서 4판이 3판 방향을 뒤집었다) · utterance_type='learning' 함께 거른다 · 조회를 라우터에 두지 않는다
- [x] #2 판별력 5건 — (A A U)는 1 · 사용자 발화 0건이고 코치만 있는 세션은 0(H-3 이 뚫은 자리) · learning 아닌 행 제외 · 사용자 발화만 있는 세션은 0 · 정확히 12라운드 세션이 12를 낸다(3판 방향이면 11 이라 FAIL 하는 단위 일치 tripwire)
- [x] #3 R2 상태 3개(analyzing·connection_failed·no_utterances)에서 drill 키가 부재한다 — 기대값이 있어도 그렇다 (D5-4)
- [x] #4 프론트 결과 화면 — 미달일 때만 숫자 없는 한 문장 · 주어는 세션 · 미달 아니면 아무것도 그리지 않는다 (유도 10)
- [x] #5 백엔드 게이트 유지/증가 + 프론트 npx tsc --noEmit · npx eslint app lib 둘 다 exit 0
- [x] #6 미달이면 warning 한 줄에 두 수를 적는다 (INFO 금지 — H-Z). 단 R2 상태 3개에서는 로그도 내지 않는다 — critic B-4 판정: 3판은 D5-4 를 API 키에만 적용해 리퍼가 닫은 세션마다 미달 warning 이 쌓이고 결정 10 이 정한 '지시문 수정 입력' 신호가 오염된다. 키 생략과 로그 억제는 같은 조건을 쓴다
<!-- AC:END -->
