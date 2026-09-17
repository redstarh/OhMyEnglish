---
id: TASK-171
title: 설계서 §3 의 문장 담기 요청 필드 이름이 구현과 다름 — start_sec vs clip_start_sec
status: To Do
assignee: []
created_date: '2026-09-17 18:11'
labels: []
dependencies: []
ordinal: 232000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
현상: docs/design/2026-09-18-video-learning-design.md §3 표의 5행이 POST /api/videos/{video_id}/phrases 의 몸통을 {transcript, start_sec, end_sec} 로 적었으나 구현과 프런트는 clip_start_sec · clip_end_sec 를 씀.

재현 (1단계):
curl -sS -X POST http://127.0.0.1:8002/api/videos/<id>/phrases -H 'Content-Type: application/json' -d '{"transcript":"x","start_sec":1.234,"end_sec":5.678}'
→ 422 {"detail":[{"type":"missing","loc":["body","clip_start_sec"]...},{"type":"extra_forbidden","loc":["body","start_sec"]...}]}

기대: 설계서가 정본이므로 문서와 구현이 같은 이름을 가리킴
실제: 구현·프런트(app/frontend/lib/api.ts storePhrase)·모델(app/backend/app/models/video.py PhraseCreateRequest)이 셋 다 clip_* 로 일치함. 즉 **동작에는 영향이 없고 설계서 한 줄만 낡음.** models/video.py 의 docstring 이 clip_* 를 고른 근거(쉐도잉 이벤트 payload 와 이름을 맞춤)를 적어 두었으므로 구현이 옳고 문서를 고치는 쪽임.

영향: 이 문서를 근거로 클라이언트를 쓰는 사람이 422 를 만남. 실제로 이 회차의 첫 요청이 그것으로 실패했음.

증거: tests/agent/runs/2026-09-18-0303/evidence/TS-11-post-phrase.txt
HEAD: 29aeaeb
시나리오: TS-11 (테스트 원장)

제안: 설계서 §3 표의 5행을 {transcript, clip_start_sec, clip_end_sec} 로 고치고, 이름을 그렇게 고른 근거를 §4 에 한 줄로 남김.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 설계서 §3 표 5행의 몸통 필드 이름이 구현과 같다
<!-- AC:END -->
