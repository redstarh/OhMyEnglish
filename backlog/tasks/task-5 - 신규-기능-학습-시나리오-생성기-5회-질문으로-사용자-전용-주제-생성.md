---
id: TASK-5
title: '신규 기능: 학습 시나리오 생성기 (5회 질문으로 사용자 전용 주제 생성)'
status: Done
assignee: []
created_date: '2026-09-06 00:12'
updated_date: '2026-09-12 15:04'
labels:
  - caps-req
dependencies:
  - TASK-25
  - TASK-4
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
캡틴 노트 항목 8. 신규 기능이다. 학습자에게 5회 정도 질문해서 학습하고자 하는 시나리오를 생성한다. 사용자 전용 주제를 만드는 경로가 지금 0곳이다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 질문 5회의 흐름과 각 질문이 무엇을 좁히는지 정의
- [x] #2 생성된 시나리오의 저장 위치와 기존 learning_scenarios와의 관계 정의(별도 표인가 같은 표인가)
- [x] #3 생성 주체(글 모델인지 규칙인지)와 거부 경계 정의 — 모델이 만들 수 없는 값을 요구하지 않는다
- [x] #4 요구사항 상세화 + 설계 반영. 트랙 A(풀)이므로 4 Lenses 전체를 설계서에 담는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
관계 정리 2026-09-12 (세션 ohmyenglish-f4). ⛔ 이 태스크는 TASK-102 의 AC#2 (사용자와 대화형 시나리오 생성) 와 같은 것이다. TASK-102 가 캡틴 요구사항 원문(2026-09-10)이고 이 태스크가 그 조각의 실행체다 — 둘을 따로 설계하면 갈라진다.

선행이 풀렸다: TASK-25·TASK-4 둘 다 Done 이다(TASK-4 는 2026-09-12 · 커밋 f2e9d83). TASK-4 가 정한 것이 이 태스크의 착지 지점이다 — 생성된 시나리오는 learning_scenarios 의 행 하나가 되고, 배치 규칙(결정 73·74)이 그것을 신규 후보로 집는다.

⛔ 착수 전에 읽을 것: docs/design/2026-09-12-scenario-rotation-70-30-design.md §3(시드 배열 순서가 제품 동작이다 · 결정 76) 과 §9(범위 밖 — 이 태스크가 그 자리를 가진다).

진행 2026-09-12 (세션 ohmyenglish-f4 마감). 계획서 docs/design/2026-09-12-scenario-generator-plan.md 의 여섯 중 다섯이 끝났다 — 018 마이그레이션 · 배치 정렬 앞자리(결정 80) · 파서 parse_scenario · 프롬프트 조립 build_scenario_prompt · job 처리 process_scenario + 워커 분기.

⛔ 남은 것은 Task 6 하나다: 질문 5개 블록을 세션 프롬프트에 싣고 진입을 배선한다. 그것만 nova.py·factory.py·ws.py 를 만진다.

⛔ 착수 전에 발음 축(세션 ohmyenglish-d9 · TASK-128.1·.2)이 커밋했는지 확인한다. factory.create_voice_adapter 가 유일한 겹침이고 그쪽이 먼저 닿기로 합의했다. 그쪽이 넘긴 최종 시그니처: pronunciation_sound: str | None = None → pronunciation_mode: bool = False 이고 나머지 인자(settings·known_sounds·plan·questions·scenario·usage_sink)는 이름·순서·기본값 그대로다. 블록 재료는 그 뒤에 붙인다.

⚠️ 전용 모드에서 known_sounds 의 내용이 달라진다(소켓이 후보 목록을 넘긴다) — 시그니처는 그대로지만 그 인자를 읽는 자리가 늘었다.

⛔ 조립 규약 둘을 지킨다(설계서 §6 Dependency): 재료를 인자로 받고 기본값을 두지 않는다 · 「실을지 말지」 판단을 조립기에 두지 않고 소켓이 데이터로 넘긴다.

⚠️ 진입 표지는 mode='scenario_intake' 다(018). learning_source='additional' 로는 가릴 수 없다 — 추가 학습 메뉴 여섯 중 다섯이 그 값이고 그중 셋이 mode 를 갖지 않는다.

완료 2026-09-13 (세션 ohmyenglish-f4). 계획서 docs/design/2026-09-12-scenario-generator-plan.md 의 여섯이 모두 끝났음. Task 6 커밋은 2b7d2a4 임.

Task 6 이 넣은 것: nova.py 의 _SCENARIO_INTAKE_INSTRUCTION(설계서 §3 의 다섯 축 그대로) · build_system_prompt 의 필수 인자 scenario_intake 와 _with_scenario_intake(반환 지점이 둘이라 뽑았음) · factory 가 그 값을 조립기로 옮김 · ws.py 의 SCENARIO_INTAKE_MODE 판정과 세션 행 mode 기록 · 프런트 「질문 답변 5개」 항목에 mode 추가와 SessionEntry 값역 확장.

⛔ 무대 정하기 세션에는 드릴 질문과 무대를 넘기지 않음. 드릴 질문은 「하나씩 물어라」를 받는 두 번째 목록이 되어 다섯 축이 섞이고, 무대는 코치에게 역할극을 지시하는데 이 세션은 학습자의 실제 필요를 묻는 자리임. 계획은 그대로 넘김 — 목표 수준·힌트 시점은 질문하는 동안에도 유효함. ⚠️ 이 판단은 설계서가 명시하지 않은 자리이고 조립 규약 ⑵(소켓이 데이터로 정한다)에 따라 소켓에 뒀음.

⛔ ws.py 가 SCENARIO_INTAKE_MODE 를 sessions.py 에서 import 함(위 셋과 달리 지역 상수로 두지 않음). 소켓이 쓰고 종료 경로가 읽는 값이라 리터럴을 두 곳에 두면 갈라지고, 갈라지면 세션은 정상으로 열리고 질문도 실리는데 job 만 안 걸림 — 게이트가 침묵하는 부류임.

판별력을 무력화로 확인했음: 소켓이 플래그를 늘 False 로 넘기게 하니 진입 테스트가 red 였고 판별력 테스트는 초록으로 남았음. 대역 둘 다 기본값 없이 받아 배선 누락을 잡음.

⚠️ 미검증으로 남은 것 하나 — 실물 모델이 다섯을 «하나씩» 묻는지는 재지 않았음. 조립·배선·job 경로는 게이트가 덮지만 「문면이 실제로 그 행동을 유도하는가」는 실물 세션이 필요함(결정 50 이 스파이크만으로 닫지 않기로 정한 부류임). TASK-102.1 이 그 회차를 갖음.

게이트(이 턴 직접 실행): pytest 1088 passed · ruff 안 0 · 밖 0 · format 0 · ty 0 · 프런트 tsc exit 0 · eslint exit 0.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-09-07 22:27
---
연관 감사(2026-09-08 팀리드): 선행에 TASK-4 를 더했다(기존 TASK-25 보존 — --dep 이 replace 라 한 번 지워졌다가 되돌렸다). 근거: 이 태스크가 만드는 「사용자 전용 시나리오」가 들어갈 자리를 TASK-4 가 정한다(주제 9종 분류 + 반복 70 대 신규 30 배치). 정책 없이 생성기를 만들면 생성물이 배치 비율 밖에 떨어진다.
---
<!-- COMMENTS:END -->
