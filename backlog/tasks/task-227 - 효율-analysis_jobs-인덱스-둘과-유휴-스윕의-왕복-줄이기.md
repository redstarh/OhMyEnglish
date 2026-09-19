---
id: TASK-227
title: '효율: analysis_jobs 인덱스 둘과 유휴 스윕의 왕복 줄이기'
status: Done
assignee: []
created_date: '2026-09-19 01:02'
updated_date: '2026-09-19 03:17'
labels: []
dependencies: []
ordinal: 288000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
정리 회차(TASK-222) 효율 지적 넷. 계측값은 그 노트가 정본이고 전부 EXPLAIN ANALYZE 실측이다. ⑴ analysis_jobs.utterance_id 를 종단 행까지 덮는 인덱스가 없어 결과 폴링(2초)과 유휴 스윕(1Hz)이 표 전체를 훑는다 — (utterance_id, job_type) 인덱스 하나가 두 조회를 덮는다. ⑵ claim_next 의 리퍼·claim 두 문장이 매초 전체 순차 스캔이다. ⛔ jobs.py:257-260 의 'one indexed UPDATE' 서술이 실제 계획과 어긋난다 — 부분 인덱스 (available_at) where status in ('pending','running') 로 좁히고 그 서술도 고친다. UNION ALL 재작성은 for update skip locked 를 실을 수 없어 기각됐다(직접 확인). ⑶ sweep_orphan_recording_files 가 세션 디렉터리마다 조회 2건인 N+1 이다 — any(::uuid[]) 두 문장으로 접는다. ⑷ 유휴 사이클이 pool.acquire() 를 네 번 여는데 asyncpg 가 release 마다 리셋 질의를 돌린다(순수 오버헤드 약 0.62ms/초) — 연결 하나를 세 스윕에 넘긴다. ⚠️ 유휴 스윕의 «간격» 을 늘리는 것은 동작변경=예 이므로 이 태스크에 넣지 않는다(회복 지연이 화면에 보인다). ⛔ 인덱스는 마이그레이션이므로 적용 전 pg_dump -n ohmyenglish 로 백업한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 인덱스 둘이 마이그레이션으로 들어가고 계획이 Seq Scan 을 벗어난 것을 실측한다
- [x] #2 jobs.py 의 어긋난 서술을 고친다
- [x] #3 스윕 N+1 과 연결 네 벌을 줄이고 전후 계측을 낸다
- [x] #4 게이트 여덟이 통과한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 인덱스 둘 — 마이그레이션 030 · 전후 계획을 직접 쟀음 (AC#1)

계측 방법: **테스트 DB 에서 트랜잭션을 열어 합성 20만 행을 넣고 `EXPLAIN ANALYZE` 를 전후로 돌린 뒤 롤백**했음(dev DB 는 111행이라 플래너가 언제나 Seq Scan 을 고름 — 그 크기에서는 그것이 맞는 계획임).

| 조회 | 전 | 후 |
|---|---|---|
| 결과 폴링(세션 1만 개 × 발화 20건) | Parallel Seq Scan + Hash Join · **7.417 ms** | Nested Loop + `(utterance_id, job_type)` Index Scan · **0.139 ms** |
| claim 대상 선택 | BitmapAnd+BitmapOr+Sort(3,973행) · **1.375 ms** | 부분 인덱스 `(available_at) where status in (pending,running)` Index Scan + Limit(1행) |

⛔ **지적이 틀린 자리 둘을 실측으로 갈랐음.**
1. 같은 인덱스가 **회복 스윕(`_FLUSH_ENDED_SESSIONS_SQL` 의 `not exists`)도 덮는다**고 적혀 있었으나 계획이 바뀌지 않았음(Hash Right Anti Join 유지 · 87.081 → 85.037 ms = 잡음). 한 세션에 발화 1,000건인 모양에서는 폴링도 계획이 안 바뀜 — 해시 조인이 실제로 싼 경우임.
2. **리퍼가 매초 전체 순차 스캔**이라는 지적도 크기 탓이었음 — 20만 행에서 리퍼는 `Index Scan using uq_analysis_jobs_pending_session`(0.075 ms · 0행)임.

dev DB 적용 확인: `schema_migrations` 최신 = `030_analysis_jobs_indexes.sql` · `pg_indexes` 에 두 인덱스 존재. 적용 전 백업: `/tmp/omy-backups/ohmyenglish-20260919-1159.sql`(`pg_dump -n ohmyenglish` · 184KB).

## AC#2 — 어긋난 서술을 계측값으로 바로잡았음

`jobs.claim_next` 의 「one indexed UPDATE」는 **거짓이 아니었음**. 위 ②의 실측을 그 독스트링에 적고, 「dev 크기에서 Seq Scan 인 것은 맞는 계획이며 그것을 결함으로 읽지 말 것」을 함께 못박았음.

## AC#3 — 왕복과 연결 (전후 실측)

- 고아 스윕 N+1: 세션 디렉터리 10개에서 DB 왕복 **20건 → 2건**(`any(::uuid[])` 두 문장). 같은 회차에서 지운 파일 수는 10건으로 동일함
- 유휴 회복 1회의 `pool.acquire()`: **3건 → 1건**(연결 하나를 세 스윕에 넘김 · 실패 격리는 호출마다 `try` 로 그대로 둠)
- ⚠️ 대가를 적어 뒀음: 연결이 사이클 도중에 깨지면 남은 회복도 같은 사이클에서 함께 실패함(다음 사이클이 새 연결로 다시 돎)
- 계측 스크립트는 `/tmp/sweep-roundtrips.py`·`/tmp/idle-acquires.py` 이고 둘 다 쓴 것을 롤백함

## 변이 — 구멍 하나를 찾아 메웠음

살아 있는 세션 가드는 덮여 있었음(3건 실패). **바깔 상한(`removed >= limit` 순회 중단)은 덮이지 않았음** — 기존 상한 단정이 파일 셋을 한 디렉터리에 두어 안쪽 상한만 쟀음. ⚠️ 첫 판(디렉터리 셋 · 개수만 확인)도 판별력이 없었음: 안쪽이 `limit - removed` 를 받으므로 **결과 수는 상한이 없어도 같음.** 그래서 「남은 디렉터리를 아예 들여다보지 않는다」를 호출 수로 재도록 고쳤고, 같은 변이에서 실패하는 것을 확인했음.

## 범위 밖으로 남긴 것

유휴 스윕의 **간격**을 늘리는 안(효율 지적 7)은 동작변경=예라 이 태스크에 넣지 않았음(회복 지연이 화면에 보임).

## 게이트 여덟 (직접 돌림)

`pytest` **1417**(직전 1416 · 새 단정 1건) · `ruff` 0 · `ruff format` 306 files · `ty` 0 · `tsc` 0 · `eslint` 0 errors/경고 1 · `next build` `/`=`○` Static.
<!-- SECTION:NOTES:END -->
