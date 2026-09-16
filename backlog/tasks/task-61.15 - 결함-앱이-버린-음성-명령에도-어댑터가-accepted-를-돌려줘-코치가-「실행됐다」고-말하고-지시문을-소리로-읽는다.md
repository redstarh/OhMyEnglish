---
id: TASK-61.15
title: '결함: 앱이 버린 음성 명령에도 어댑터가 accepted 를 돌려줘 코치가 「실행됐다」고 말하고 지시문을 소리로 읽는다'
status: In Progress
assignee: []
created_date: '2026-09-15 23:17'
updated_date: '2026-09-16 05:21'
labels: []
dependencies: []
parent_task_id: TASK-61
ordinal: 190000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
관측 정본은 runs/2026-09-16-task61-14-prompt-change-regression §3-② 다(팔 end-en). 표지가 인식되지 않아 앱이 end 명령을 버린 턴에서, 코치가 「the session has been ended as requested」라 말하고 이어서 지시문 문장(「The app closes the session only on 'confirmed', so never skip that second call.」)과 자기 내부 추론을 그대로 소리로 읽었다. 그 팔의 recv.session_ended 는 종료 클릭 전까지 0 이고 audio 1189 · final 20 이다. 기전은 코드로 확인했다: 어댑터가 번역기의 이벤트만 보고 {status:accepted} 를 Nova 로 돌려주는데(audio_gateway/nova.py _flush_tool_results) 실행 판정은 그 뒤 앱 층에서 하고(audio_gateway/session.py 표지 게이트 · 결정 104 D5) 표지가 없으면 버린다. nova.py 의 _remember_tool_use docstring 이 이 위험을 이미 적어 뒀지만 그 방어는 번역기가 버린 경로만 덮는다. ⚠️ 표본 1이므로 크기를 모른다. ⚠️ TASK-61.13 과 같은 부류(코치의 말과 앱 상태가 갈림)이고 결정 112 의 근거를 넓힌다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 그 모양의 크기를 실물 회차로 센다 — 표지가 버려진 턴에서 코치가 실행됐다고 말하는 비율
- [x] #2 지시문·내부 추론이 학습자에게 읽히는 것이 그 팔에서만 나는지, 표지 정상 팔에서도 나는지 가른다
- [x] #3 고치는 자리를 정한다: accepted 를 앱의 실행 판정 뒤로 미룰지, 버린 턴에 실패를 돌려줄지
- [x] #4 고치면 실물 회차로 관측한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 회차 2 — 되돌릴 수 있는 명령 둘 (2026-09-16 KST · 같은 세션)

정본은 같은 회차 디렉터리 §4 임. 팔 넷(`show_report`·`next_question` × 두 언어)을 표지 없는 새 픽스처로 밟았음 — 제어 이벤트 4건 · warning 4건 · 프레임 0건 · 발화 유형은 전부 `learning`.

⛔ **네 명령이 같은 층에서 같은 이유로 버려지는데 학습자가 겪는 것은 다름**: `end` 는 되돌릴 수 없는 것을 됐다고 듣고 · `show_report` 는 볼 수 없는 것을 봤다고 듣고(패널이 없는 것을 화면에서 직접 확인했음) · `next_question` 은 코치가 실제로 다음 질문을 하므로 화면 갈림이 없음. ⇒ AC#3(고치는 자리)에 「명령별로 나누는 안」이 재료로 들어감.

새 픽스처 넷을 리포에 남겼음: vc29_report_nomarker_en · vc30_report_nomarker_ko · vc31_next_nomarker_en · vc32_next_nomarker_ko.

2026-09-16 — AC#4 를 닫았음(정본 runs/2026-09-16-task61-16-divergence-surface). 팔 s7(표지 없는 end + 「예」)과 s2(표지 없는 show_report)에서 화면 알림이 뜨는 것을 스크린샷으로 확인했음. ⛔ AC#3(고치는 자리 — accepted 를 앱의 판정 뒤로 미룰지)은 그대로 열려 있음: 이 회차가 만든 것은 알림이고 어댑터가 「받았다」를 먼저 돌려주는 구조는 바뀌지 않았음. ⚠️ 지시문 낭독이 s5b 에서 다시 났고 표본이 하나 늘었음(그 팔의 audio 1004).

## 결정 118 — ②안으로 고쳤음 (2026-09-16 KST)

사용자가 ②(버린 턴에 실패를 돌려주기)를 골랐음. 한 것 셋:
1. 결정 109 의 «시점»만 뒤집었음 — 어댑터가 번역 직후에 결과를 보내지 않고 게이트웨이의 실행 보고를 받을 때 보냄. 결정 109 의 요구(결과 없으면 모델이 그 턴을 이어 말하지 못함)는 그대로임.
2. 버린 턴에는 {status:rejected, command, reason} 을 보냄 — 이유를 실어 학습자가 할 일을 가름(no_wake_word · pause_state_not_written).
3. 포트에 report_command_outcome 을 더하고 SessionCommandEvent 에 tool_use_id 를 실었음. 게이트웨이는 finally 로 보고하고, 보고 없이 스트림이 끝나면 어댑터가 warning 으로 셈.

지시문에 「rejected 면 안 됐다고 말하고 표지를 붙여 다시 말해 달라고 하라」를 넣었음.
⚠️ 이 고침이 보장하는 것은 «모델에게 맞는 사실을 주는 것»까지임 — 학습자에게 보이는 보장은 결정 113 의 화면 알림이 갖음(결정 112).

단정 다섯 신설: 보고 전에는 결과가 안 나감 · 이벤트가 tool_use_id 를 실음 · 보고 뒤 accepted · 거절 시 rejected+reason · 두 번 보고해도 결과는 한 번. 통합 단정 둘: 버린 명령이 거절로 보고됨 · 정상 명령이 실행으로 보고됨.
게이트 여섯 초록 — pytest 1263 passed · ruff · format 49 files · ty · tsc 0 · eslint 0.
AC#4(고치면 실물 회차로 관측)는 다음 단계임.
<!-- SECTION:NOTES:END -->
