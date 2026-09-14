---
id: TASK-61.2
title: 판별력을 게이트로 고정한다 — 학습 발화가 종료로 오인되지 않는 음성 대조 (AC#5)
status: Done
assignee: []
created_date: '2026-09-14 22:24'
updated_date: '2026-09-14 23:03'
labels: []
dependencies:
  - TASK-61.1
parent_task_id: TASK-61
ordinal: 176000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
AC#5 가 요구하는 판별력이다. 접두어가 없는 학습 발화와 접두어가 있는 명령 발화를 같은 게이트에서 대조해, 무력화하면 실패하는 단정으로 둔다. ⛔ 테스트 코드 작성의 주체는 개발 세션이다 — 통합 테스트 세션은 그 게이트가 실제로 반증력을 갖는지 회차로 확인한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 접두어 없는 학습 발화가 종료를 실행하지 않는 단정이 있다
- [x] #2 접두어 있는 명령이 종료를 실행하는 단정이 있다 — 반대 방향을 함께 못 박는다
- [x] #3 단정을 일부러 무력화하면 게이트가 실패하는 것을 확인한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-15 완료 (세션 ohmyenglish-65). TASK-61.1 과 같은 TDD 흐름에서 게이트를 함께 세웠으므로 별도 회차를 열지 않았음.

AC#1(접두어 없는 학습 발화가 종료를 실행하지 않음): test_speech_without_the_wake_phrase_is_not_a_command · test_my_english_alone_is_not_the_wake_phrase · test_the_marker_must_be_at_the_front_not_anywhere_in_the_sentence · test_a_marked_user_final_is_stored_as_a_command_not_learning · test_a_requested_end_command_does_not_close_the_session.
AC#2(접두어 있는 명령이 종료를 실행함): test_a_confirmed_end_command_closes_the_session · test_a_confirmed_control_tool_use_becomes_a_session_command_event.
AC#3(무력화하면 게이트가 실패함) — 여섯을 직접 돌려 확인했고 전부 잡혔음:
① 모르는 command 를 받아들이게 함 → test_an_unknown_command_is_dropped_instead_of_guessed 실패
② 모르는 stage 를 requested 로 강등 → test_an_unknown_stage_is_dropped_instead_of_demoted 실패
③ 표지 판정을 포함 검사로 바꿈 → test_the_marker_must_be_at_the_front... 실패
④ requested 에서도 세션을 닫음 → test_a_requested_end_command_does_not_close_the_session 실패
⑤ 확인 발화를 명령과 같은 유형으로 적음 → test_the_confirmation_is_stored_as_a_command_confirmation 실패
⑥ 표지 판정을 끔 → test_a_marked_user_final_is_stored_as_a_command_not_learning 실패
⚠️ ③은 처음 테스트 집합이 «잡지 못했음» — 그 무력화를 보고 「맨 앞」을 못 박는 테스트를 새로 더했음. 즉 무력화가 실제로 구멍을 찾았음.
<!-- SECTION:NOTES:END -->
