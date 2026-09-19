---
id: TS-30
title: A12 · 단어 조회 — vocab/lookup
status: In Progress
assignee: []
created_date: '2026-09-19 05:19'
updated_date: '2026-09-19 05:36'
labels: []
dependencies: []
ordinal: 30000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
영역 A12. 대상: POST /api/vocab/lookup. 실물 외부 호출이 필요한지는 구현을 읽어 먼저 가름 — 필요하면 그 사실을 적고 1건만 씀.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 정상 단어 조회가 규약대로 응답함
- [x] #2 빈 문자열·과도한 길이 같은 값역이 422 로 거부됨
- [ ] #3 찾을 수 없는 단어의 경계가 오류가 아니라 빈 결과로 나옴
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
판정: 부분 (AC 2/3). 회차 2026-09-19-b1 · HEAD 74fb5c0 · 공유 인스턴스. ⛔ Done 이 아님 — AC#3 이 차단됨.
AC#1 통과. POST /api/vocab/lookup 에 {"word":"book","sentence":"I need to book a table for two at seven."} 를 보내 200 · {"meaning":"(자리를) 미리 예약하다"} 를 받았음. 응답 모양이 규약대로 meaning 한 키이고 한국어 한 줄이며 사전 표제어 형식이 아님. 다의어를 고른 것이 판단임 — book 이 예약 문맥에서 「책」이 아니라 「예약하다」로 왔으므로 문맥 문장을 함께 보내는 계약이 동작함을 같은 호출로 함께 확인했음. ⛔ 실물 Bedrock 호출 1건을 썼고 그것이 허용된 전부임: llm_calls 가 32→33 · vocab 6→7 로 늘었고 그 행이 purpose=vocab · us.anthropic.claude-opus-5 · 입력 197 · 출력 15 임(호출 전후로 직접 셈). 부수로 usage_sink 배선이 살아 있음을 확인했음.
AC#2 통과 · 실물 호출 0회. pydantic 이 모델 호출 앞에서 막으므로 값역 검사는 비용이 없음. 422 를 받은 입력 여덟: word 빈 문자열 · sentence 빈 문자열 · 둘 다 빈 문자열 · word 81자(상한 80) · sentence 601자(상한 600) · word 누락 · sentence 누락 · word 가 숫자 · 몸통이 객체가 아님. ⚠️ word 가 공백만("   ")인 갈래는 422 가 아니라 400 「낱말이 비어 있다」임 — min_length=1 을 통과해 lookup_word 의 ValueError 로 떨어짐. AC 문면의 「빈 문자열」은 "" 이고 그것이 422 이므로 AC 는 충족됨. 사용자 영향이 0인 것을 확인해 결함으로 올리지 않았음(프런트 postJson 이 !ok 를 한 갈래로 접어 400·422 를 구분하지 않음 · app/frontend/lib/api.ts:423). 그 400 갈래도 모델을 부르지 않음.
AC#3 차단됨 — 실패가 아님. 모델이 뜻을 주지 않은 응답을 받아야 판정되는데 그것은 AC#1 과 입력이 달라 같은 호출로 덮이지 않고, 실물 호출 예산 1건을 AC#1 에 이미 썼음. except Exception 갈래도 같은 200·meaning null 을 내지만 그것을 타게 하려면 클라이언트나 .env 를 건드려야 해 쓰기 경계에 걸림. VOICE_ADAPTER=stub 은 음성 경로에만 걸리고 낱말 조회는 Bedrock 을 직접 부름. ⇒ 코드를 고치지 않는 전제에서 관측 수단이 실물 호출 하나뿐임. 호출 1건을 승인받으면 무의미 낱말로 즉시 판정할 수 있음 — 호출 세션에 승인을 요청해 둔 상태임.
증거: runs/2026-09-19-b1/evidence/TS-30-*.
<!-- SECTION:NOTES:END -->
