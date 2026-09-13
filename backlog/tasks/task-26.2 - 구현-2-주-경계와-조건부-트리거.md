---
id: TASK-26.2
title: '구현 2: 주 경계와 조건부 트리거'
status: Done
assignee: []
created_date: '2026-09-13 23:35'
updated_date: '2026-09-13 23:46'
labels: []
dependencies:
  - TASK-26.1
parent_task_id: TASK-26
ordinal: 161000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
계획서 Task 2. services/weekly_report.py 가 주 경계를 한 곳에서 소유하고, enqueue 는 「지난 주 행이 없으면」을 한 문장의 not exists 로 함께 건다(두 왕복으로 하면 중복이 생긴다).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 단정 넷이 통과한다 — 지난 주 월요일 · 타임존이 주를 가르는 성질 · 없으면 걸림 · 있으면 안 걸림
- [x] #2 not exists 절을 지워 red 를 보고 되돌린다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
완료 2026-09-14 (세션 ohmyenglish-f4).

red 를 먼저 봤음 — 수집 단계 ImportError.

단정 여섯이 통과함(계획의 넷에 둘을 더했음): 지난 주 월요일인가 · 타임존이 주를 가르는가 · 없으면 걸림 · 있으면 안 걸림 · ⛔ «다른 주»의 행은 가드에 걸리지 않는가 · ⛔ 남의 행이 내 job 을 막지 않는가. 뒤의 둘을 더한 이유: 그것이 없으면 not exists 가 「그 사용자의 행이 하나라도 있으면 넘긴다」로 쓰여도 통과하고, 그러면 둘째 주부터 리포트가 영원히 안 만들어짐.

⛔ 주 경계 값을 상수로 고정하지 않고 «성질»을 쟀음 — 월요일인가 · 오늘로부터 7~13일 전인가 · 두 타임존의 차이가 0 또는 7일인가. 고정하면 하루 뒤 낡음(H-O 의 부류).

⚠️ 주 경계 SQL 이 두 자리에 있음 — 정본은 weekly_report.py 이고 jobs.py 의 가드가 한 문장이어야 해서 복제했음. 그 복제를 주석에 적고, 「다른 주의 행」 단정이 갈림을 잡게 뒀음.

⚠️ asyncpg 함정 둘을 밟았음: date - interval 은 timestamp 를 내고, $2 - 7 은 $2 를 정수로 추론하게 함 — $2::date - 7 로 못박았음.

판별력: not exists 가드를 지워 1 failed 를 보고, 되돌린 뒤 __pycache__ 를 지우고 6 passed 를 다시 읽었음.

게이트: pytest 1162 passed · ruff check 0 · format 219 files · ty 0.
<!-- SECTION:NOTES:END -->
