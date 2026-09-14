---
id: TASK-61.3
title: '실물 회차 — 브라우저 레그에서 「Oh My English, 종료」가 실제로 도는가'
status: Done
assignee: []
created_date: '2026-09-14 22:24'
updated_date: '2026-09-14 23:14'
labels: []
dependencies:
  - TASK-61.1
parent_task_id: TASK-61
ordinal: 177000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
구현이 든 뒤 실물 Nova 로 확인한다. 이 태스크의 주체는 통합 테스트 세션이다. ⚠️ TASK-65 가 「파일이 아니라 순서가 ASR 언어를 정한다」를 확정했으므로 한국어 명령의 전사가 어떻게 잡히는지를 이 회차가 관측한다(결정 102 ④의 함정).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 브라우저 레그에서 영어 종료 명령이 확인 절차를 거쳐 세션을 닫는 것을 관측한다
- [x] #2 한국어 종료 명령의 전사문을 관측하고 인식되는지 판정한다 — 안 되면 결함 후보로 보고한다
- [x] #3 명령이 아닌 학습 발화로 세션이 닫히지 않는 것을 같은 회차에서 확인한다
- [x] #4 회차 기록을 tests/harness/runs/ 에 남기고 검증 전용 스택을 정리한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-15 회차 완료 (세션 ohmyenglish-65). 정본은 tests/harness/runs/2026-09-15-task61-3-voice-command-app-leg/README.md 임. 실물 Nova 4세션(상한 4 · 예비 1회를 ARM-A2 로 썼음) · Claude 0회.

확인된 것 셋: ① 실물 Nova 가 제어 tool 을 부른다(네 팔 모두 heard 기원 행이 남음 — 결정 46 의 수단이 실사용에서 성립함) ② confirmed 가 세션을 닫고 command_confirmation 이 남는다(ARM-A2·ARM-B) ③ 한국어 명령이 같은 경로를 탄다 — ASR 이 오마이잉글리시로 붙여 적었고 앱의 공백 제거 정규화가 그것을 잡았음.

⛔ 결함 다섯을 재현 절차와 함께 회차에 적었고 새 태스크(TASK-61.4)로 넘겼음: D1 같은 발화가 두 경로에서 중복 저장 · D2 확인 답이 learning 으로도 저장돼 분석 대상이 됨 · D3 코치가 확인 질문을 소리로 말하지 않음(audio 0) · D4 명령으로 분류된 발화에 final 프레임을 보내지 않아 화면이 비어 있음 · D5 모델이 표지 없이도 명령으로 읽고 앱이 tool 을 그대로 신뢰함.

⚠️ 가장 값어치 있는 관측: D5 에서 세션이 «닫히지 않았음» — 확인이 오지 않았기 때문임. 결정 102 ③이 오인식을 실제로 막았음.
⚠️ 상충 하나를 넘겼음: 표지의 ASR 이 불안정함(같은 픽스처 2회 중 1회는 all my english 로 왔음). tool 에도 표지를 요구하면 오인식을 막지만 정상 명령도 막는다 — 사용자 판단이 필요함.
<!-- SECTION:NOTES:END -->
