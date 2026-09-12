---
id: TASK-131
title: '정리: 값역 단정 한 자리가 따옴표 없이 부분 일치를 쓴다 — utterance_type (전수 결과 마지막 하나)'
status: Done
assignee: []
created_date: '2026-09-12 13:10'
updated_date: '2026-09-12 13:16'
labels: []
dependencies: []
ordinal: 139000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-12 KST · 전수로 세었음. pg_get_constraintdef 로 값역을 재는 테스트는 tests/unit/test_schema.py 하나뿐이고 그 안의 단정이 셋임.

- :409 test_scenario_category_domain_includes_the_new_fields → f"'{value}'" (고쳐짐)
- :514 test_session_mode_domain_includes_scenario_intake → f"'{value}'" (고쳐짐)
- :1268 test_utterance_type_domain_includes_shadowing_recording → ⛔ value in definition (남음)

기전: 값역 정의 문자열에 대한 «맨» 부분 일치는 다른 값이 그 문자열을 품고 있으면 통과함. 동료 세션이 가짜 정의로 실측했음 — 값역에 pronunciation_drill 이 있고 pronunciation 이 없을 때 맨 비교는 True, 따옴표 비교는 False.
⚠️ 지금은 안전함: 그 값역이 ('learning','voice_command','command_confirmation','shadowing_recording') 이고 서로의 부분 문자열이 아님. ⛔ 그런데 voice_command_confirm 이나 learning_drill 같은 값이 늘면 voice_command·learning 이 «사라져도» 통과함. 값역을 늘리는 일이 이미 세 번 있었음(014·017·018).

⛔ 순서 주의: 이 파일을 동료 세션이 018 커밋으로 담는 중임(2026-09-12). 그 커밋이 올라간 «뒤» 에 고칠 것 — 안 그러면 같은 파일을 동시에 만져 충돌함.
⚠️ 그리고 이 자리는 쉐도잉 축이라 소유자가 불분명함. 동료 세션이 「자기 것이 아니라 알림만 한다」고 했고 내가 전수를 세어 등록했음.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 단정을 f"'{value}'" 로 바꾸고 실패 메시지에 그 단정이 왜 필요한지를 적는다 — 쓰는 코드가 없는 값이라 다른 테스트가 잡지 않는다는 것
- [x] #2 판별력을 실측한다 — 가짜 정의(learning_drill 이 있고 learning 이 없음)로 맨 비교가 True 이고 따옴표 비교가 False 인 것을 직접 본다. ⛔ 초록만 보고 닫지 않는다
- [x] #3 전수를 다시 돌려 남은 자리가 0인지 확인한다 — grep -rn "in definition" tests/ 로 세 자리가 전부 따옴표 형태여야 한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-12 KST — 고쳤음. 동료 세션의 018 커밋(a2e16a6)이 올라간 뒤에 손댔으므로 충돌 0건임.

AC#1 — :1268 을 f"'{value}'" 로 바꿨음. ⛔ 실패 메시지는 동료 세션 문장을 «그대로 옮기지 않았음» — 그 값역의 사정이 mode 와 다르기 때문임. 직접 확인한 값:
  learning             코드가 씀(session.py·analysis.py) · dev DB 128행
  voice_command        언급 4 · 0행
  command_confirmation 언급 1 · 0행
  shadowing_recording  코드가 씀(recordings.py·session.py) · 0행
⇒ 「쓰는 코드가 없는 값이라」는 이 자리에 맞지 않음(둘은 코드가 씀). 정확한 근거는 «행» 이므로 메시지를 그렇게 적었음 — dev DB 의 실제 행이 learning 뿐이라 나머지 셋은 데이터로는 삭제를 알아채지 못함.

AC#2 — 판별력을 직접 쟀음(가짜 정의: learning 이 빠지고 learning_drill 이 들어온 판).
  맨 비교      'learning' in definition     -> True   (오통과)
  따옴표 비교  "'learning'" in definition   -> False  (잡음)
그리고 진짜 정의에서 넷 다 따옴표 비교가 True 임 — 오탐을 잡으면서 정상 통과를 깨지 않는 것까지 확인했음.

AC#3 — 전수 재확인: grep 'in definition' 이 :409·:514·:1273 세 자리이고 «전부» 따옴표 형태임(1270 은 주석). ⇒ 이 부류가 0 이 됐음.

게이트(전부 app/backend cwd · 여섯 다 exit 0): pytest 1039 passed(12.00s) · ruff check . 0 · format --check . 0 · ruff check ../../tests ../../scripts 0 · format --check ../../tests ../../scripts 157 files · ty 0.
⚠️ H-X 규약대로 pytest 를 돌리기 전에 동료 세션에 알렸고 그쪽 것이 끝난 뒤에 돌렸음 — 이 회차에 InvalidCatalogNameError 재현 0건.
<!-- SECTION:NOTES:END -->
