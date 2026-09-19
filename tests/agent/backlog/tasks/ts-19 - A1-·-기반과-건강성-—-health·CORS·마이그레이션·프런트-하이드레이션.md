---
id: TS-19
title: A1 · 기반과 건강성 — health·CORS·마이그레이션·프런트 하이드레이션
status: Done
assignee: []
created_date: '2026-09-19 05:18'
updated_date: '2026-09-19 05:33'
labels: []
dependencies: []
ordinal: 19000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
영역 A1. 대상: GET /health · CORS 프리플라이트 · 마이그레이션 030 적용 상태 · 프런트 / 화면. 실물 외부 호출 없음. 회차: 2026-09-19 전영역.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 GET /health 가 200 이고 본문이 status ok 임 (version 키가 있으면 StockAgent 포트라 실패로 적음)
- [x] #2 OPTIONS 프리플라이트가 /api/videos 의 POST 와 DELETE 를 허용함 (TS-18 회귀)
- [x] #3 analysis_jobs 인덱스 둘이 dev DB 에 존재함 (마이그레이션 030)
- [x] #4 http://localhost:3000/ 이 200 이고 하이드레이션이 성립함 (클라이언트 전용 문구로 판정 · H-CA)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
판정: PASS (AC 4/4). 회차 2026-09-19-b1 · HEAD 74fb5c0 · 공유 인스턴스.
AC#1 GET /health → 200 · {"status":"ok"} · version 키 부재로 OhMyEnglish 포트임을 확인함.
AC#2 OPTIONS /api/videos 프리플라이트가 POST·DELETE 를 200 으로 허용함(access-control-allow-methods: GET, POST, DELETE). 판별력 증명: 같은 수단으로 PUT·PATCH 를 보내 400 을 받음 — 검사가 반증할 수 있음.
AC#3 마이그레이션 030 의 인덱스 둘이 스키마 ohmyenglish 에 존재함. analysis_jobs_claimable_available_at_idx 는 부분 인덱스 조건(status in pending,running)까지 일치함. schema_migrations 적용 기록 2026-09-19 03:02:41 UTC. 판별력 증명: 없는 인덱스 이름을 같은 질의에 넣어 0건을 받음.
AC#4 http://localhost:3000/ 200 · main 하위 노드 14개 전부에 React 내부 키(__reactFiber$·__reactProps$)가 있어 하이드레이션 성립함. 판별력 증명: H-CA 대조군으로 http://127.0.0.1:3000/ 을 같은 수단으로 재니 0/13 이었음 — 함정 H-CA 를 그대로 재현했고 검사가 반증할 수 있음을 보임.
증거: runs/2026-09-19-b1/evidence/TS-19-*.
<!-- SECTION:NOTES:END -->
