---
id: TASK-153
title: '정리: 하네스 기준선 표 둘이 redstar 소유라 ohmy 가 읽지도 지우지도 못한다'
status: To Do
assignee: []
created_date: '2026-09-17 00:38'
labels: []
dependencies: []
ordinal: 214000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-41 이관 중에 발견. public 에 harness_pattern_baseline · harness_review_task_baseline 이 남았고 소유자가 redstar 다(다른 세션이 superuser psql 로 만들었다). 결과 셋: ① ohmy 로 pg_dump -n public 을 뜨면 permission denied for table harness_pattern_baseline 으로 죽는다(실측 — 백업을 redstar 로 떠야 했다) ② 하네스가 psql_cli(=ohmy)로 그 표를 drop/create 하려 하면 소유자가 아니라 막힌다 ③ 026 이 소유자로 걸러 옮기므로(R5) public 이 완전히 비지 않았다. ⛔ 그 표를 함부로 지우지 않는다 — browser_leg.md §8-0 이 「앞 회차 teardown 이 죽었으면 그 표가 원값의 유일한 사본」이라 무조건 drop 을 금지했다. 먼저 내용이 유효한 기준선인지 판정하고, 유효하면 소유자만 ohmy 로 바꾸고(alter table owner to) 아니면 지운 뒤 다음 회차가 다시 뜨게 한다. 소유자 변경은 superuser(redstar) 가 필요하다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 두 표의 내용이 살아 있는 기준선인지 판정한다 (앞 회차 teardown 이 끝났는지)
- [ ] #2 ohmy 소유로 바꾸거나 지운 뒤, ohmy 로 pg_dump -n public 이 exit 0 인 것을 보인다
- [ ] #3 하네스가 그 표를 ohmy 로 drop/create 할 수 있는 것을 보인다
<!-- AC:END -->
