---
id: TASK-214
title: '정리: 좁은 Transcriber 포트를 도입해 결정 131 의 경계 약속을 실제로 만든다'
status: Done
assignee: []
created_date: '2026-09-18 07:50'
updated_date: '2026-09-18 18:58'
labels: []
dependencies: []
ordinal: 275000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
/simplify 고도 각도(2026-09-18). 결정 131 은 「배치 STT 로 옮기면 전사 함수 하나만 갈면 된다」를 경계로 약속했는데 지금 Callable[[], VoiceAdapter] 가 HTTP 층까지 새어 results.py 가 대화형 포트를 안다. Transcriber = Callable[[bytes], Awaitable[str]] 를 두고 침묵·조용함·프레임 크기·어댑터 수명을 그 Nova 구현이 소유하게 한다. ⚠️ 동작을 바꾸지 않는 리팩터링이고 스텁으로 검증된다. 부수 이득: 낭독 경로가 report_command_outcome 을 이행하지 않은 채 대화형 포트를 쓰는 어긋남도 사라진다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Transcriber 포트를 두고 judge_readback 이 그것을 받는다
- [x] #2 results.py 가 VoiceAdapter 를 import 하지 않는다
- [x] #3 기존 테스트가 그대로 통과한다
<!-- AC:END -->
