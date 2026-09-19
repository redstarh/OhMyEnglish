---
id: TASK-234
title: '결함: 음성 명령으로 연 세션도 started_via=''ui'' 로 기록되어 두 진입을 가릴 수 없다'
status: Done
assignee: []
created_date: '2026-09-19 07:01'
updated_date: '2026-09-19 08:08'
labels: []
dependencies: []
ordinal: 298000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
재현(3단계): ① 브라우저에서 추가 학습 '쉐도잉' 버튼을 눌러 세션을 연다 ② 다른 세션에서 소켓 경계에 서버 프레임 {"type":"voice_command","command":"start_additional","stage":"confirmed","target":"shadowing"} 와 session_ended 를 흘려 화면이 새 세션을 열게 한다(결정 110 ③ 경로) ③ 두 세션 행을 견준다. / 기대: 001 마이그레이션이 learning_sessions.started_via CHECK 에 voice_command 를 최초부터 담았고, services/sessions.create_session docstring 이 'started_via 는 인자로 받지 않는다 ... 음성 명령 진입(voice_command)이 생기는 턴에 그때 더한다 — 그 시점이 이 결정을 뒤집을 유일한 근거다' 라고 조건을 적어 두었다. 그 진입은 결정 110 ③(TASK-61.8)으로 이미 구현되어 이 회차에 종단으로 동작했다. / 실제: 두 행이 완전히 같다 — 음성으로 연 f5f832a5 와 버튼으로 연 f2b9d9fb 가 mode=shadowing · learning_source=additional · started_via=ui · 클립 붙음까지 동일했다. started_via 의 voice_command 값을 쓰는 생산 코드가 여전히 0건이다(TASK-61 이 그 부재를 '경로(0곳)' 으로 적었고 그 태스크는 Done 이다). 배선이 끊긴 자리도 하나로 좁혀진다: 프런트 SessionEntry 에 진입 수단 필드가 없고(app/frontend/lib/config.ts:24-31) sessionSocketUrl·entryQuery 가 mode·source·item 셋만 싣는다. / 대가: PRD.md:76 이 요구하는 '추천 과제와 자유 과제를 구분해 번아웃 분석에 쓴다' 는 learning_source 로 성립하지만, '버튼으로 골랐는가 음성으로 말했는가' 는 어느 컬럼으로도 셀 수 없다 — 음성 제어가 실제로 쓰이는지 잴 수단이 없다. / 증거: tests/agent/runs/2026-09-19-b5/evidence/31-ts33-ac3-browser.txt · 32-ts33-ac3-page-text.txt / HEAD: 78f7a6c (앱 소스 무변경) / 시나리오: TS-33 AC#3 관측에서 파생 / 제안: SessionEntry 에 진입 수단을 실어 entryQuery→sessionSocketUrl→api/ws.py→create_session 으로 넘기고 create_session 에 started_via 인자를 더한다. ⚠️ 그 docstring 이 '항상 같은 값을 넘기는 인자' 를 경계로 적어 두었으므로, 값이 둘이 되는 지금이 그 경계가 풀리는 시점인지 사람이 확인해야 함. ⛔ 고치지 않았음 — 이 회차는 관측만 함
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 음성 명령으로 연 세션의 started_via 가 voice_command 로 남고, 버튼으로 연 세션은 ui 로 남아 두 진입이 집계에서 갈린다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
고쳐졌음 (2026-09-19 · TASK-242).

기전: started_via CHECK 는 001 이 voice_command 를 최초부터 담았으나 그 값을 쓰는 생산 코드가 0곳이었음. 배선이 끊긴 자리는 프런트 SessionEntry 에 진입 수단 필드가 없다는 것 하나였음.

고침 다섯 자리:
- _CREATE_SESSION_SQL 에 started_via 를 더하고 _insert_session 이 그것을 받음. 기본값은 앱 상수 _DEFAULT_STARTED_VIA='ui' 로 두어 _DEFAULT_LEARNING_SOURCE 와 같은 관용을 따랐음(컬럼이 not null 이라 None 을 그대로 넣을 수 없고, SQL 에 coalesce 를 두면 기본값이 두 곳에 생김).
- create_session 과 start_shadowing_session 이 started_via 를 키워드로 받음. create_session docstring 의 「인자로 받지 않는다」를 뒤집고, 그 문장이 조건으로 적어 둔 「음성 명령 진입이 생기는 턴」이 채워졌음을 그 자리에 적었음.
- api/ws.py 가 ?via= 를 읽어 두 진입 함수에 넘김. 값역을 열거하지 않고 DB CHECK 에 맡기는 기존 관례를 따랐음.
- 프런트 SessionEntry 에 via?: "voice_command" 를 더하고 entryQuery·entryFromQuery 양쪽에 실었음(TASK-168 의 「인코더와 디코더가 같은 표를 본다」 관례).
- entryForTarget 이 via 를 덧붙임. 표 ADDITIONAL_LEARNING 의 entry 에 넣지 않은 것이 판단임 — 표에 넣으면 같은 항목의 화면 버튼도 음성으로 기록돼 결함의 반대 방향이 됨. 공유 상수를 제자리에서 바꾸지 않도록 새 객체를 만듦.

검사: tests/integration/test_ws.py 의 test_ws_records_voice_command_entry_and_keeps_ui_as_the_default 가 팔 둘로 잼 — 음성 팔은 voice_command, 대조 팔은 ui 를 요구함. 팔을 둘 둔 것이 판별력임(음성 팔만 재면 모든 세션을 voice_command 로 적는 구현이 통과하고 그것은 같은 결함의 반대 방향임). 고치기 전 코드에서 그 검사가 실패함을 먼저 확인했음(voice_command 기대에 ui 가 왔음).

게이트: pytest 1421 통과 · ruff 0 · ruff format 322 files · ty 0 · tsc 0 · eslint 0 errors(경고 1은 기준선) · next build 정상.

관측 한계: 이 리포는 프런트 자동 E2E 를 만들지 않는 것이 규약이라(AC 문서 U-검증) 프런트 세 자리는 tsc·eslint·build 와 코드 검토로만 확인했음. 백엔드 검사는 ?via= 질의값부터 DB 행까지 종단으로 덮음.
<!-- SECTION:NOTES:END -->
