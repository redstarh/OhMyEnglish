---
id: TASK-217
title: '비용: 전사 전용 프롬프트와 end_input() 으로 낭독 판정의 입력 토큰을 줄인다'
status: To Do
assignee: []
created_date: '2026-09-18 07:50'
labels: []
dependencies:
  - TASK-214
ordinal: 278000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
/simplify 효율·고도 각도(2026-09-18). 전사 한 줄을 얻으려고 코치 세션 전체를 조립한다 — 실측 입력 1,853 토큰 가운데 음성이 229 이고 약 1,600 이 코치 페르소나·규칙·tool 스펙이다. 게다가 audioOutputConfiguration 때문에 코치가 실제로 말하고 그 출력 토큰과 합성 오디오가 전량 폐기된다. 전례가 같은 파일에 있다 — pronunciation_mode 와 build_pronunciation_prompt 가 「짧은 지시문 모드」를 그렇게 만들었다. 함께: VoiceAdapter.end_input() 을 신설하면(프로토콜에 이미 있는 오디오 contentEnd 를 떼어 냄) 침묵 2초와 조용함 3초 상수가 사라질 수 있다. ⛔ 둘 다 실물 Nova 회차가 선행해야 한다 — 프롬프트를 줄였을 때 전사 품질이 유지되는지, contentEnd 만으로 VAD 가 발화를 닫는지를 같은 픽스처 A/B 로 재야 한다(p_readback_leg.py 가 그 틀을 가짐).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 전사 전용 프롬프트 갈래를 팩토리에 둔다
- [ ] #2 같은 픽스처 A/B 로 전사 품질이 유지되는 것을 실물로 확인한다
- [ ] #3 줄어든 입력 토큰을 llm_calls 로 실측해 설계서 §6 을 갱신한다
<!-- AC:END -->
