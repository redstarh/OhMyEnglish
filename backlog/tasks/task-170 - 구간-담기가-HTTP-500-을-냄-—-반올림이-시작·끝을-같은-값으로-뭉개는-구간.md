---
id: TASK-170
title: 구간 담기가 HTTP 500 을 냄 — 반올림이 시작·끝을 같은 값으로 뭉개는 구간
status: To Do
assignee: []
created_date: '2026-09-17 18:11'
labels: []
dependencies: []
ordinal: 231000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
현상: 두 시각의 차가 0.005초 미만이면 서버가 500 을 내고 사용자는 「구간 끝이 시작보다 뒤여야 해요」 대신 일반 실패 문구(UNAVAILABLE_NOTICE)를 봄.

재현 (3단계):
1. 영상을 담음 — POST /api/videos {url,title,channel_name}
2. 그 영상 id 로 POST /api/videos/<id>/phrases 에 {"transcript":"x","clip_start_sec":5.0,"clip_end_sec":5.001} 을 보냄
3. 응답이 500 Internal Server Error 임 (2/2 재현 · 간헐 아님)

기대: 422 + 「구간 끝이 시작보다 뒤여야 해요」 (설계서 docs/design/2026-09-18-video-learning-design.md §7 의 표)
실제: 500 Internal Server Error. 백엔드 로그에 asyncpg.exceptions.CheckViolationError: violates check constraint "shadowing_items_span_ordered" (Failing row 의 두 값이 5.00, 5.00)

기전: models/video.py PhraseCreateRequest 의 _span_is_ordered_and_bounded 가 **원본 값**으로 clip_end_sec > clip_start_sec 를 판정하고, 반올림은 그 뒤 services/videos.py add_phrase 가 함. 원본은 순서가 맞아도 둘째 자리로 접으면 같은 값이 되어 스키마 CHECK 가 잡음. 그 모듈 docstring 이 스스로 «스키마가 거부하면 사용자는 500 에 가까운 실패를 본다» 고 적어 둔 자리임.

사용자 도달 경로: app/frontend/app/videos/[videoId]/page.tsx 의 markEnd 가 at <= spanStart 만 봄(원본 float). 즉 [구간 시작]·[구간 끝] 을 재생 시각 5ms 미만 간격으로 누르면 프론트가 통과시키고 서버가 500 을 냄. API 를 직접 부르면 자명하게 재현됨. 화면에서의 도달은 좁지만 재생 속도 0.25배에서 넓어짐.

값역 상한(90초)에는 같은 구멍이 없음 — 반올림 이득의 최대가 0.01 이고 검증기가 원본 span <= 90 을 이미 요구하므로 접은 span 이 90 을 넘을 수 없음(실측: 0.004..90.0 · 0.0049..89.999 둘 다 0.00..90.00 로 저장되고 201).

증거: tests/agent/runs/2026-09-18-0303/evidence/TS-12-rounding-collapse.txt
HEAD: 29aeaeb
시나리오: TS-12 (테스트 원장 /Users/redstar/MyProject/OhMyEnglish/tests/agent)

제안: 반올림을 검증 «앞» 으로 옮기거나(모델이 접은 값으로 순서를 판정), 서비스가 접은 뒤 다시 판정해 422 로 번역함. 스키마 CHECK 는 그대로 둠 — 마지막 겹이 그것임.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 clip_start_sec=5.0 · clip_end_sec=5.001 로 POST 하면 422 이고 응답 문구가 구간 순서 오류를 가리킨다
- [ ] #2 접은 값이 같아지는 다른 조합(0.001..0.004 · 1.001..1.002 · 12.3401..12.3449)도 전부 422 다
- [ ] #3 정상 구간(1.234..5.678)은 그대로 201 이고 1.23..5.68 로 저장된다
<!-- AC:END -->
