---
id: TASK-124
title: '구현: Nova 호출도 llm_calls 에 적는다 — 지금 비용의 큰 쪽이 표에 없다'
status: Done
assignee: []
created_date: '2026-09-12 01:02'
updated_date: '2026-09-12 02:09'
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
- [x] #1 Nova 응답에서 사용량이 어디에 오는지 실물 1회로 확인한다 — 오지 않으면 그 사실을 적고 대안(오디오 길이·세션 수)을 정한다. ⛔ 오지 않는데 0 으로 적지 않는다
- [x] #2 audio_gateway 경로가 purpose=nova 로 적는다 — 배선 누락을 잡는 게이트 테스트를 함께 둔다(TASK-60 의 lifespan 게이트와 같은 형태)
- [x] #3 실물 세션 1회로 행이 쌓이는 것을 직접 조회해 확인한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-12 세션 ohmyenglish-f4 — 사용자 결정 68(토큰 열 넷을 더함)로 닫았음. 정본 회차 기록은 tests/harness/runs/2026-09-12-task124-nova-usage.md 임.

AC#1: ⛔ 라이브 없이 닫았음 — Nova 의 usageEvent 모양을 «이미 있는» 실물 산출물에서 찾았음(runs/2026-09-11-task97-tool-payload/B0-r2.json). totalInputTokens·totalOutputTokens·totalTokens 와 details.total/delta 의 speechTokens·textTokens 분해가 옴. ⚠️ 그 이벤트는 한 세션에서 여러 번 오고 값이 «누적» 이라 마지막 값 하나를 세션 끝에 적음 — 이벤트마다 적으면 합계가 부풀어 오름.

AC#2: 번역기가 usageEvent 를 기억하고(NovaEventTranslator.last_usage) 어댑터가 close() 에서 한 번 적음. ⛔ 스트림을 닫기 «전에» 적음 — 종료 절차가 예외로 빠지면 그 세션의 비용이 통째로 사라짐. sink 는 주입임(팩토리 → 어댑터). 배선 게이트 셋: 소켓→팩토리(test_ws) · 팩토리→어댑터(test_gateway) · 스텁은 sink 를 받지 않음. ⚠️ 팩토리→어댑터 구간이 «무보호» 였음을 뮤테이션으로 확인했음(인자를 떼도 138건 전부 초록) — records_usage 속성과 그 테스트가 그 구멍을 닫았음. 뮤테이션 다섯 전부 실패로 잡힘(delta 읽기 · 총계 없으면 0 · 팩토리 누락 · 소켓 누락 · 분해를 0 으로 저장).

AC#3 실물 1세션(직접 조회): purpose=nova 행이 정확히 1건. input_tokens 216 = input_speech 150 + input_text 66. 분해 넷이 전부 not-null 이라 파서가 details.total 의 양쪽을 실제로 읽었음. 학습 데이터 다섯 표는 전후 무변경.

⛔ §0 에 미리 적은 조건 하나가 어긋났고 끼워 맞추지 않았음 — output_tokens=0 임. 원인은 기록 경로가 아니라 세션 진행임: 픽스처 뒤에 무음이 없어 endpointing 이 걸리지 않아 모델이 응답 발화를 하기 전에 끝났음(받은 포트 이벤트가 SpeechBoundaryEvent 1건뿐). 「응답까지 받은 세션에서 출력 토큰이 채워지는가」는 실사용에서 자연히 쌓임 — 계속 0 이면 그때 새 태스크로 세움.

마이그레이션 015 를 발급·적용했음(그 순간 schema_migrations 최대가 014). ⛔ migrate.py 를 돌리지 않고 psql 로 파일만 적용했음(시드 upsert 부수효과 회피).

게이트 다섯: pytest 999 passed(12.66s) · ruff check 0 · format --check 38 files · 게이트 밖 ruff 0 · 게이트 밖 format --check 는 동료 세션 파일 1건만 남음 · ty 0.
<!-- SECTION:NOTES:END -->
