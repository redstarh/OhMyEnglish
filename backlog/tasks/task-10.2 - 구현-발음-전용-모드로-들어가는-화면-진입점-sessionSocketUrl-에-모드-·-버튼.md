---
id: TASK-10.2
title: '구현: 발음 전용 모드로 들어가는 화면 진입점 (sessionSocketUrl 에 모드 · 버튼)'
status: Done
assignee: []
created_date: '2026-09-11 15:42'
updated_date: '2026-09-11 16:57'
labels: []
dependencies: []
parent_task_id: TASK-10
ordinal: 115000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-12 KST — TASK-10.1 이 지시문과 ?mode=pronunciation 진입 표면까지 만들었고 화면이 없음. TASK-10 노트가 이미 지목한 공백 둘과 같은 자리임: 「어느 화면·어느 버튼이 그 모드로 연결하는가」와 「sessionSocketUrl() 에 모드를 붙이는 URL 조립」. ⛔ 쉐도잉도 같은 공백을 갖고 있으므로 두 모드의 진입을 «같은 문» 으로 두는지가 먼저임 — 그 판정은 TASK-10 의 AC#1 이 소유하고 이 태스크는 그 결정을 구현함. 근거 문서: docs/design/2026-09-12-pronunciation-mode-design.md §5 항목 3.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 TASK-10 AC#1 이 정한 배치대로 진입 버튼을 만들고 sessionSocketUrl 이 모드를 붙이게 한다
- [x] #2 소리를 고를 수 없는 사용자에게 이 버튼이 무엇을 보이는지 정한다 — 서버는 말하기로 떨어뜨리므로 화면이 침묵하면 사용자가 다른 세션을 받은 것을 모른다
- [x] #3 브라우저 레그로 실제 진입을 확인한다 — 단위·통합만으로 닫지 않는다
- [x] #4 create_session 에 learning_source='additional' 과 started_via='ui' 를 넘긴다 — 두 컬럼은 001 의 CHECK 로 열려 있으나 쓰는 코드가 0건이다(진입점 설계서 §4)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-12 KST 구현·검증 완료. 정본은 tests/harness/runs/2026-09-12-task10-2-entry-browser-leg.md 이고 배치 근거는 docs/design/2026-09-12-additional-learning-entry-design.md 임.

만든 것: lib/config.ts 의 SessionEntry + sessionSocketUrl(entry) · lib/ws.ts 의 SessionSocket(handlers, entry)와 session_started.pronunciation_focus · app/page.tsx 의 추가 학습 메뉴 여섯과 진입 안내 두 문면 · 백엔드는 create_session/start_shadowing_session 의 learning_source 인자와 ws.py 의 ?source= · SessionRunner 의 pronunciation_sound.

⛔ AC#4 를 한 부분 좁혀 이행했음 — started_via 는 인자로 받지 않았음. 001 의 기본값이 이미 'ui' 이고 지금 이 함수를 부르는 경로가 전부 그 값이므로 인자를 늘리면 «항상 같은 값을 넘기는 인자» 가 됨. 음성 명령 진입이 생기는 턴에 더함(그 근거를 create_session docstring 에 적었음). 브라우저 레그에서 started_via='ui' 로 기록된 것을 확인했음.

브라우저 레그(전용 Chrome + 사본 프론트 :3001 + 래퍼 백엔드 :8012 + 검증 전용 DB): 버튼 일곱(학습 시작 + 추가 학습 여섯)이 뜨고 업무 역할극만 비활성임. hasBeenActive=True. 소리가 있을 때 「발음 연습으로 시작했어요…」, 지운 뒤 「오늘 다룰 소리가 아직 없어서 일반 대화로…」가 떴고 서버 경고가 1건 났음. learning_sessions 4행이 전부 learning_source='additional' 임.

⛔ **H-BD 가 좁혀졌음** — 마이크는 열 수 있음. 막힌 것은 CDP 가 아니라 그 Chrome 에 오디오 장치가 없는 것이었고, --use-fake-device-for-media-stream 으로 띄우면 getUserMedia 가 resolve 함. 그 사실을 pitfalls 의 H-BD 에 붙였음(원 서술은 지우지 않았음).

⚠️ 안내 줄을 폴링으로는 놓쳤음 — 클릭 전에 MutationObserver 를 심어 잡았음. 「창이 짧은 것」을 「부재」로 오독하는 형태였음.

게이트: pytest 964 passed · ruff·format·ty exit 0 · 프론트 tsc·eslint exit 0. 정리: 스택 전부 종료·DB drop·사본 삭제하고 공유 dev DB 무변경(17·9)을 대조했음.
<!-- SECTION:NOTES:END -->
