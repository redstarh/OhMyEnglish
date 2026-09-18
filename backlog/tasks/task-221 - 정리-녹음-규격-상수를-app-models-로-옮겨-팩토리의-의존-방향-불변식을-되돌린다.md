---
id: TASK-221
title: '정리: 녹음 규격 상수를 app/models 로 옮겨 팩토리의 의존 방향 불변식을 되돌린다'
status: To Do
assignee: []
created_date: '2026-09-18 19:56'
labels: []
dependencies: []
ordinal: 282000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
codex 품질 리뷰의 altitude 지적 3(2026-09-19 · LOW). services/sessions.py 가 「audio_gateway/factory.py·nova.py 가 app.models 만 알고 app.services 가 그 값을 채우는 기존 방향」을 불변식으로 적어 두었는데, TASK-214 가 신설한 audio_gateway/transcribe.py 가 app.services.recordings 에서 RECORDING_SAMPLE_RATE_HZ·RECORDING_BYTES_PER_SAMPLE·RECORDING_CHANNELS 를 가져오고 factory.py 가 transcribe 를 import 하므로 그 불변식이 전이로 깨졌다. 셋은 서비스 거동이 아니라 형식 데이터이므로 app/models 로 옮기고 services/recordings 가 그쪽에서 읽게 한다. ⚠️ audio_gateway/session.py 는 이미 services 를 자유롭게 import 하므로 패키지 전체가 순수했던 적은 없다 — 깨진 것은 factory·nova 로 좁힌 불변식 하나다. 그래서 LOW 이고 별 작업으로 뺐다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 녹음 규격 상수 셋이 app/models 에 있고 services/recordings 가 그쪽에서 읽는다
- [ ] #2 audio_gateway/transcribe.py 가 app.services 를 import 하지 않는다
- [ ] #3 게이트 여덟이 통과한다
<!-- AC:END -->
