---
id: TASK-234
title: '결함: 음성 명령으로 연 세션도 started_via=''ui'' 로 기록되어 두 진입을 가릴 수 없다'
status: To Do
assignee: []
created_date: '2026-09-19 07:01'
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
- [ ] #1 음성 명령으로 연 세션의 started_via 가 voice_command 로 남고, 버튼으로 연 세션은 ui 로 남아 두 진입이 집계에서 갈린다
<!-- AC:END -->
