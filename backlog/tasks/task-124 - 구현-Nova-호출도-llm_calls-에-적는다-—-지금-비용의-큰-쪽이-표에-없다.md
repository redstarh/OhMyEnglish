---
id: TASK-124
title: '구현: Nova 호출도 llm_calls 에 적는다 — 지금 비용의 큰 쪽이 표에 없다'
status: To Do
assignee: []
created_date: '2026-09-12 01:02'
labels: []
dependencies: []
ordinal: 129000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-12 TASK-60 이 남긴 것. 013 의 purpose 값역에 nova 자리는 있으나 아직 한 행도 안 적힘. ⛔ Claude 경로의 추출기(workers/claude_client.extract_usage)를 그대로 쓸 수 없음 — Nova 는 양방향 스트리밍이고 응답 모양이 다름. ⚠️ 비용의 큰 쪽이 이쪽일 수 있음: 동료 세션이 2026-09-12 하루에 Nova 63세션을 돌렸음(HANDOFF-pronunciation ④ 의 기록). 즉 지금 llm_calls 는 「비용을 볼 수 있다」를 절반만 이룸.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Nova 응답에서 사용량이 어디에 오는지 실물 1회로 확인한다 — 오지 않으면 그 사실을 적고 대안(오디오 길이·세션 수)을 정한다. ⛔ 오지 않는데 0 으로 적지 않는다
- [ ] #2 audio_gateway 경로가 purpose=nova 로 적는다 — 배선 누락을 잡는 게이트 테스트를 함께 둔다(TASK-60 의 lifespan 게이트와 같은 형태)
- [ ] #3 실물 세션 1회로 행이 쌓이는 것을 직접 조회해 확인한다
<!-- AC:END -->
