---
id: TASK-61.1
title: 어댑터에 종료 명령 경로와 음성 확인을 만든다 (결정 102 ①②③)
status: Done
assignee: []
created_date: '2026-09-14 22:23'
updated_date: '2026-09-14 23:03'
labels: []
dependencies: []
parent_task_id: TASK-61
ordinal: 175000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
결정 102 가 정한 계약을 코드로 옮긴다. 표지는 「Oh My English」 접두어 하나이고, 명령은 종료 하나이고, 확인은 음성 한 번이며 그 답을 command_confirmation 발화로 남긴다. ⛔ 이 태스크의 주체는 개발 세션이다 — 통합 테스트 세션은 계약과 회차만 소유한다. 설계 판단(tool 스키마·프레임 계약·어느 파일이 소유하는가)은 이 태스크가 갖는다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 종료 명령이 Nova tool 로 도착하고 어댑터가 그것을 실행 경로로 받는다 (결정 46 의 수단)
- [x] #2 확인을 거치지 않고 종료되지 않는다 — 확인 발화가 command_confirmation 으로 저장된다
- [x] #3 「Oh My English」 접두어가 없는 학습 발화는 명령으로 실행되지 않는다
- [x] #4 한국어와 영어 두 표현을 모두 받는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-15 구현 완료 (세션 ohmyenglish-65 · 결정 103 으로 이 세션이 구현까지 함). TDD 로 진행했고 게이트 여섯을 직접 돌렸음 — pytest 1219 passed(13.5s) · ruff check · ruff format --check 49 files · ty · 프론트 tsc --noEmit · eslint(둘 다 0줄).

새 파일 둘: app/models/voice_command.py(이름·스키마·검증·표지 판정) · tests/unit/test_voice_command.py(10건).
고친 파일: audio_gateway/port.py(SessionCommandEvent 를 AdapterEvent 에 더함) · audio_gateway/nova.py(제어 tool 선언 · _on_control_tool_use · 대화 규칙 12~14) · audio_gateway/session.py(_handle_command · _save_command_utterance · 표지 붙은 학습자 final 을 voice_command 로 저장) · frontend/lib/ws.ts(voice_command 프레임을 ServerEvent 에 더함 · 화면 로직은 안 건드렸음).

설계 판단 셋을 적음:
1. 확인 절차를 발음 tool 과 «같은 두 번 호출» 형태로 만들었음 — stage requested → confirmed. 새 기제를 발명하지 않았고 이미 실증된 형태를 따랐음.
2. 세션을 닫는 방법을 새로 만들지 않았음 — 이벤트 펌프에서 돌아가면 기존 종료 경로(_close_and_record('completed') → session_ended)를 그대로 탐. 클라이언트의 end_session 과 같은 길이라 종료 상태·프레임 순서가 갈리지 않음.
3. 표지 판정을 «앱»이 함(is_wake_command). 모델의 규율에 맡기면 학습 발화가 learning 으로 저장되어 분석기가 명령을 교정 대상으로 봄. utterance_type='learning' 이 분석 대상의 유일한 조건이라 유형만 바꾸면 그 경로에서 빠짐.

⚠️ AC#1 의 「도착」은 단위 테스트가 실측 봉투 모양으로 확인한 것이고, 실물 Nova 가 이 tool 을 실제로 부르는지는 TASK-61.3 이 관측함. ⚠️ AC#4 도 같음 — 한국어 표기(잉글리시·잉글리쉬 둘을 받음)의 실물 전사는 61.3 의 관측 대상임.
<!-- SECTION:NOTES:END -->
