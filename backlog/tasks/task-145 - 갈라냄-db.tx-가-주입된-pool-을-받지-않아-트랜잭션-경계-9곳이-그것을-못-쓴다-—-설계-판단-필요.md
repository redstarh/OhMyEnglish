---
id: TASK-145
title: '갈라냄: db.tx() 가 주입된 pool 을 받지 않아 트랜잭션 경계 9곳이 그것을 못 쓴다 — 설계 판단 필요'
status: To Do
assignee: []
created_date: '2026-09-16 15:29'
labels: []
dependencies: []
ordinal: 206000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
R1(재사용) 리뷰가 「경계 9곳이 db.tx() 를 재구현한다」로 지목했고 services/__init__.py:6 docstring 이 그 헬퍼를 설계 의도로 직접 가리킨다. ⛔ 그런데 팀리드가 직접 읽어 확인한 사실은 다르다: tx() 는 인자를 받지 않고 db.pool() 로 «프로세스 전역 pool» 을 스스로 얻는다. 9곳은 주입된 pool: asyncpg.Pool 을 쓰므로 그대로 바꾸면 테스트가 주입한 pool 이 무시되고 전역 pool(개발 DB)로 붙는다 — 즉 동작변경이고 테스트 격리가 깨진다. 고르는 길 셋: ① tx(pool) 을 받는 판을 만든다 ② docstring 을 실제와 맞춘다 ③ tx() 를 지운다(호출 0건). 어느 쪽이든 설계 판단이라 정리 회차 밖이다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 세 길 중 하나를 사용자가 고른다
<!-- AC:END -->
