---
id: TASK-26.3
title: '구현 3: 사실 모으기 — metrics'
status: Done
assignee: []
created_date: '2026-09-13 23:35'
updated_date: '2026-09-13 23:50'
labels: []
dependencies:
  - TASK-26.1
parent_task_id: TASK-26
ordinal: 162000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
계획서 Task 3. 주 경계를 [week_start, +7) 반열림으로 쓴다. ⛔ between 을 쓰지 않는다 — 끝을 포함해 다음 주 월요일이 들어온다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 단정 넷이 통과한다 — 주 밖 배제 · 상위 정렬과 동수 가름 · 0건 주 · 다른 사용자 배제
- [x] #2 반열림을 between 으로 바꿔 red 를 보고 되돌린다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
완료 2026-09-14 (세션 ohmyenglish-f4).

red 를 먼저 봤음 — load_week_facts 부재로 수집 실패.

단정 넷이 통과함: 주 밖 배제(경계 양쪽 하루를 찔렀음 — 앞 하루와 다음 주 월요일) · 상위 정렬과 동수 가름 · 0건 주가 값을 줌 · 남의 오류가 새지 않음.

⚠️ 값역 둘을 실제 CHECK 에 맞췄음 — error_patterns.category 는 verb_tense(tense 아님) · error_occurrences.severity 는 medium(minor 아님). 계획서가 추측으로 적은 값이었고 DB 를 조회해 고쳤음.

⚠️ TOP_PATTERN_LIMIT=5 는 발명값임 — PRD 가 개수를 정하지 않았고 근거는 「상위」를 보이는 화면이 목록으로 덮이지 않을 크기임. 전체 수는 occurrence_count·pattern_count 가 따로 들고 있어 목록을 세지 않음.

⚠️ asyncpg 가 jsonb 를 문자열로 주는 자리를 «모양의 소유자»가 흡수했음(TASK-62 의 규율) — 호출자마다 json.loads 를 적으면 한 곳이 빠뜨림.

판별력: 반열림 창을 between 으로 바꿔 1 failed 를 보고 되돌려 10 passed 를 다시 읽었음. ⚠️ 그 확인에서 내 grep 검증은 셸 이스케이프 때문에 양쪽 다 0을 내 «무력»했음 — 증거는 red/green 전환이고 변이 적용 자체는 파이썬의 s2 != s 단정이 보장했음.

게이트: pytest 1166 passed · ruff check 0 · format 219 files · ty 0.
<!-- SECTION:NOTES:END -->
