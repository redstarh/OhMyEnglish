---
id: TASK-147
title: '성능: review.py 의 순차 왕복을 배치화한다 — 최빈 쓰기 경로에서 발화당 5~24회'
status: To Do
assignee: []
created_date: '2026-09-16 15:36'
labels: []
dependencies: []
ordinal: 208000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
R3(효율) 리뷰의 실측. recompute(497-552)가 category·history·apply·ladder(최대 3)·supersede·abandon 로 5~8회 순차 왕복하고, analysis 가 touched 패턴마다 그것을 부르므로 발화 하나 분석에 5~24회가 나간다. store_attempts(465-476)도 attempts 길이만큼 순차 INSERT 다. ⛔ 팀리드 판정으로 정리 회차에서 «갈라냈다»: ① SQL 을 unnest 로 바꾸는 것은 형태 정리가 아니라 성능 변경이고 ② store_attempts 의 건당 warning(패턴이 사라진 key 를 이름으로 남긴다)이 배치화하면 충실도가 떨어진다 — 이 리포는 로그 건수를 지표로 쓴다(함정 H-Z). ③ ladder upsert 를 한 문장으로 합치면 배치 안 중복 충돌 규칙(ON CONFLICT DO UPDATE 가 같은 행을 두 번 못 건드린다)이 새 조건으로 들어온다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 ladder upsert 배치화 전후로 recompute 의 왕복 수를 계측해 전·후 수치를 낸다
- [ ] #2 store_attempts 배치화가 건당 warning 을 잃지 않는 형태인지 정한다
- [ ] #3 test_review.py 의 멱등·순서 단정이 배치판에서도 통과하는 것을 보인다
<!-- AC:END -->
