---
id: TASK-145
title: '갈라냄: db.tx() 가 주입된 pool 을 받지 않아 트랜잭션 경계 9곳이 그것을 못 쓴다 — 설계 판단 필요'
status: Done
assignee: []
created_date: '2026-09-16 15:29'
updated_date: '2026-09-16 22:35'
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
- [x] #1 세 길 중 하나를 사용자가 고른다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 완료 (2026-09-17 · 사용자 결정: 안 쓰는 함수 지움)

지운 것: app/db.py 의 tx() 와 그에만 쓰이던 import 둘(contextlib · AsyncIterator).
함께 고친 것: services/__init__.py 의 머리말이 그 함수를 「경계를 여는 수단」으로 지목하고 있었음 —
실제와 맞추고, 다시 만들려면 pool 을 인자로 받아야 하는 이유를 남겼음.

게이트: pytest 1274 passed · ruff exit 0 · format exit 0 · ty exit 0.
<!-- SECTION:NOTES:END -->
