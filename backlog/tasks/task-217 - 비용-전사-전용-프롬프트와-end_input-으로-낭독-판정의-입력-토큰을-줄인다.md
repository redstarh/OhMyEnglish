---
id: TASK-217
title: '비용: 전사 전용 프롬프트와 end_input() 으로 낭독 판정의 입력 토큰을 줄인다'
status: Done
assignee: []
created_date: '2026-09-18 07:50'
updated_date: '2026-09-18 19:22'
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
- [x] #1 전사 전용 프롬프트 갈래를 팩토리에 둔다
- [x] #2 같은 픽스처 A/B 로 전사 품질이 유지되는 것을 실물로 확인한다
- [x] #3 줄어든 입력 토큰을 llm_calls 로 실측해 설계서 §6 을 갱신한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 실물 A/B (2026-09-19 · Bedrock Nova 세션 2회 · 사용자 사전 승인)

드라이버 `tests/harness/p_transcribe_prompt_ab.py` · 산출물
`tests/harness/runs/2026-09-19-task217-transcribe-prompt-ab.json`.
같은 PCM(시드 클립 201 낭독 · 476,626바이트 · 14.89초 · 45낱말)을 두 프롬프트로 각 1회 전사.

| | A 코치 지시문 + tool 스펙 | B 전사 전용 | 차이 |
|---|---|---|---|
| 지시문 | 5,364자 | 200자 | -96.3% |
| 입력 토큰 | 2,143 | 897 | **-1,246 (-58.1%)** |
| 입력 글 | 1,633 | 395 | -1,238 (-75.8%) |
| 입력 음성 | 510 | 502 | -8 (오디오가 같음) |
| 출력 토큰 | 418 | 92 | **-326 (-78.0%)** |
| 출력 합성음성 | 278 | 23 | -255 |
| 낱말 판정 | 맞음 44 빠짐 1 | 맞음 44 빠짐 1 | 같음 |

⛔ **전사문이 두 팔에서 글자까지 같았음** — AC2 의 답. 기전은 학습자 전사가 ASR 산출이라
지시문이 바꾸지 않는 것임. 두 팔이 함께 놓친 낱말 하나(`coffee`)가 ASR 한계 귀속의 근거임.

⚠️ AC3 정본은 `llm_calls` 임 — `purpose='nova'` 행이 16 → 18 로 정확히 둘 늘었고 값이 위와 같음.
행이 둘인 것은 `TASK-215` 의 멱등 보장이 실물에서도 선 것을 함께 뜻함.

회차 잔재 없음(실측): pending job 0 · active 세션 0 · 발화 증가 0. 세션을 만들지 않는 경로임.

## 범위 밖으로 남긴 것

`end_input()` 으로 침묵 2초·조용함 3초를 없애는 것은 **재지 않았음.** 설명에 「함께」로 적혔지만
AC 셋에 없고 별 A/B 가 필요함(contentEnd 만으로 VAD 가 발화를 닫는지). `audioOutputConfiguration`
제거도 미검증으로 남김 — 출력이 이미 -78% 이므로 남은 이득이 작음.
<!-- SECTION:NOTES:END -->
