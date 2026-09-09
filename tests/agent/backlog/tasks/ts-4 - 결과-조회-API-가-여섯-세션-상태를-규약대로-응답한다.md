---
id: TS-4
title: 결과 조회 API 가 여섯 세션 상태를 규약대로 응답한다
status: Done
assignee: []
created_date: '2026-09-09 08:23'
updated_date: '2026-09-09 08:23'
labels: []
dependencies: []
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
기준 커밋 3ce3e62 · 추적 미커밋 0건. GET /api/sessions/<id>/results (app/backend/app/api/results.py:131 · prefix 47행). 보존 세션 6건 재방문이라 실물 호출 0회. 증거는 runs/2026-09-09-1712/evidence/ 의 응답 본문 원본이고 메인이 직접 읽어 대조했다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 210233be 가 analyzing 이고 corrections 키가 부재다
- [x] #2 6225ddaf 가 final 이고 corrections 1건이다
- [x] #3 b2f0d169 가 partial_failure 이고 corrections 가 빈 배열이다
- [x] #4 76d9ef31 가 connection_failed 이고 corrections 키가 부재다
- [x] #5 d127dece 가 no_utterances 이고 corrections 키가 부재다
- [x] #6 e0c5e580 가 final 이고 corrections 2건이다
<!-- AC:END -->
