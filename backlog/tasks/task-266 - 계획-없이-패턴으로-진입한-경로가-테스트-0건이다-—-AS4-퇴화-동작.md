---
id: TASK-266
title: 계획 없이 패턴으로 진입한 경로가 테스트 0건이다 — AS4 퇴화 동작
status: Done
assignee: []
created_date: '2026-09-21 23:30'
updated_date: '2026-09-21 23:33'
labels: []
dependencies: []
ordinal: 330000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
handoff 의 「남은 것」 1번이 적어 둔 자리. api/ws.py 는 계획이 없으면 지시문을 지어내지 않고 「패턴만 세션 행에 남고 세션은 그대로 열린다」를 AS4 와 같은 규약으로 정해 두었으나, 그 조합(계획 없음 + 패턴 지정)을 재는 테스트가 0건이다. 있는 키·없는 키 두 경로는 계획이 있는 상태만 잰다. handoff 는 앱 WS 경로가 고정 사용자로 열려 격리 사용자로 우회가 안 되는 것을 근거로 관측을 미뤘으나, 테스트 앱에서는 계획을 심지 않는 것만으로 그 상태가 만들어진다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 계획을 심지 않고 패턴으로 연결한 세션이 열리고, session_started 에 focus_pattern 이 실리지 않으며, 팩토리로 가는 plan 이 None 인 것을 단정하는 테스트가 있다
- [x] #2 세션 행에는 그 패턴 키가 남는다는 현행 계약도 같은 테스트가 잰다
- [x] #3 일어나지 않은 대체를 보고하게 만드는 변이를 넣어 그 테스트가 실제로 실패하는 것을 직접 관측하고 되돌린다
- [x] #4 백엔드 게이트 넷이 exit 0 이다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
실측 증거 (2026-09-22 · 기준 24a18aa).

- 테스트는 `tests/integration/test_ws.py::test_ws_a_pattern_without_a_prepared_plan_records_the_key_and_replaces_nothing` 임. 패턴은 `error_patterns` 에 **실재하게** 심었음 — 없는 키로 심으면 TASK-265 의 테스트와 같은 것을 두 번 재게 되고 「계획이 없어서 대체가 없었다」를 「키가 없어서 없었다」와 구별하지 못함.
- 단정 넷: 세션이 열림 · 팩토리로 간 `plan` 이 `None` · `session_started` 에 `focus_pattern` 없음 · 세션 행에는 그 키가 남음.
- 변이 관측(AC#3): `api/ws.py` 의 `if plan is not None and requested_pattern is not None:` 을 `if requested_pattern is not None:` 으로 바꿔 계획이 없어도 대체를 보고하게 하니 **이 테스트 한 건만** 실패했음(`1 failed, 1430 passed`). `git checkout` 으로 되돌리고 442행을 눈으로 확인했음.
- 게이트: pytest 1431 passed · ruff 0 · ruff format --check 331 files · ty 0.

⚠️ 게이트에서 한 번 걸렸다가 고친 자리 하나. `ruff format --check` 가 `1 file would be reformatted` 를 냈음(내 새 단정 한 줄이 한 줄에 들어가는 길이였음). 명령을 `tail` 로 받으면 `$?` 가 `tail` 의 값이라 exit 0 으로 보이므로, 출력을 직접 읽어 잡았음.

⚠️ handoff 의 「남은 것」 1번은 **절반만** 해소됨 — 실물 앱 화면에서의 같은 경로 관측은 계획 생성을 끄는 스위치가 필요해 그대로 남음.
<!-- SECTION:NOTES:END -->
