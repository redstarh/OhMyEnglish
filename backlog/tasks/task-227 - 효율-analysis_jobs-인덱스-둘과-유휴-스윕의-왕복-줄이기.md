---
id: TASK-227
title: '효율: analysis_jobs 인덱스 둘과 유휴 스윕의 왕복 줄이기'
status: To Do
assignee: []
created_date: '2026-09-19 01:02'
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
- [ ] #1 인덱스 둘이 마이그레이션으로 들어가고 계획이 Seq Scan 을 벗어난 것을 실측한다
- [ ] #2 jobs.py 의 어긋난 서술을 고친다
- [ ] #3 스윕 N+1 과 연결 네 벌을 줄이고 전후 계측을 낸다
- [ ] #4 게이트 여덟이 통과한다
<!-- AC:END -->
