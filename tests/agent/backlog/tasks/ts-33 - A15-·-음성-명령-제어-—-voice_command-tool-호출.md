---
id: TS-33
title: A15 · 음성 명령 제어 — voice_command tool 호출
status: Done
assignee: []
created_date: '2026-09-19 05:22'
updated_date: '2026-09-19 07:05'
labels: []
dependencies: []
ordinal: 33000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
영역 A15. 대상: WS 세션 안의 voice_command tool 호출. 근거: PRD 「UI와 음성 제어」 — 화면 기능 여덟을 음성으로도 제어할 수 있어야 함(추가 연습 시작·질문 다섯 개 더·천천히 다시 말해줘·힌트 줘·다음 문제·오늘 학습 끝낼게). 학습 답변과 음성 명령이 섞이지 않아야 함(명령 버튼 또는 Oh My English 호출어). ⚠️ 자동 테스트는 unit/test_voice_command.py 의 페이로드 검증뿐이라 종단은 미확인임.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 명령 여섯 가운데 최소 넷이 세션 안에서 실제로 동작함
- [x] #2 학습 답변이 음성 명령으로 오인되지 않는 경계가 성립함
- [x] #3 화면 버튼과 음성 명령이 같은 기능에 닿음
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-19 배치 B5 — 전건 통과. ⛔ 계측 수단을 밝힘: /ws/session + VOICE_ADAPTER=stub 으로는 관측 불가임(StubVoiceAdapter.events() 가 SessionCommandEvent 를 만들지 않음 · 그 이벤트는 어댑터만 만들 수 있음). 실물 Nova 가 이 배치에서 금지되어 제어 이벤트를 흘리는 어댑터 대역을 드라이버에 넣고 SessionRunner 를 그대로 돌렸음(runs/2026-09-19-b5/ts33_voice_command_driver.py). 지나가지 않은 것 둘: Nova toolUse→SessionCommandEvent 번역 · /ws/session 소켓 층(AC#3 브라우저 다리는 이 층을 지나감). AC#1 — 여섯 전부 동작(최소 넷 요구): next_question·show_report 는 세션을 닫지 않고 executed=True, pause 는 DB status 를 옮겨 정지 중 발화가 저장되지 않았고 resume 뒤 다시 저장됨, end·start_additional 은 confirmed 에서만 닫힘. AC#2 — 경계 셋: 표지 없는 턴의 end 는 voice_command_ignored + reason=no_wake_word 로 버려지고 그 발화는 learning 으로 저장됨 · 문장 가운데의 앱 이름은 표지가 아님 · cancelled 는 닫지 않고 대화를 이음. AC#3 — 버튼이 있는 명령 둘 다 같은 자리에 닿았음: 음성 start_additional 로 연 세션 f5f832a5 와 쉐도잉 버튼으로 연 f2b9d9fb 가 mode·learning_source·started_via·클립까지 동일(브라우저 실시간) · 버튼 end_session 프레임과 음성 end/confirmed 를 느린 어댑터로 같은 조건에서 견줘 둘 다 completed·ended_at·adapter_closed·마지막 프레임 session_ended 로 일치. ⚠️ 첫 종료 대조는 판별력이 없었음(픽스처가 45ms 에 소진되어 종료 원인이 언제나 어댑터 소진) — 고친 형태가 ts33_end_paths_compare.py 임. 파생 결함: TASK-234(두 진입이 started_via 로 갈리지 않음). 회차 문서 runs/2026-09-19-b5/result.md §6.
<!-- SECTION:NOTES:END -->
