---
id: TASK-128.2
title: '구현 C3: 전용 모드 판정을 «소리 키가 오면» 에서 «mode=pronunciation 이면» 으로 바꾼다'
status: Done
assignee: []
created_date: '2026-09-12 03:54'
updated_date: '2026-09-12 14:04'
labels: []
dependencies:
  - TASK-128.1
parent_task_id: TASK-128
ordinal: 135000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
설계 정본: docs/design/2026-09-12-decision72-sound-as-candidate.md §2 C3. 결정 72 가 전용 모드의 뜻을 「오늘의 소리를 다룬다」에서 「발음만 다룬다」로 바꿨으므로, 소리가 없으면 모드가 안 열리는 지금 규약이 그 뜻과 어긋난다.
만지는 자리: app/api/ws.py(_pronunciation_sound_or_none 의 역할을 「오늘의 소리를 고른다」에서 「후보 목록에 계획의 초점을 더한다」로 바꿈 · 삭제하지 않는다) · app/audio_gateway/factory.py(모드 판정을 명시 플래그로).
⚠️ factory.py 주석이 「소리 키가 오면 그 모드다」를 계약으로 적어 뒀으므로 그 주석도 함께 고친다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 TDD — mode=pronunciation 이고 소리가 «없어도» 전용 지시문이 조립되는 것을 먼저 단정한다
- [x] #2 음성 대조 — mode 가 없으면 여전히 일반 지시문인 것을 단정한다(모든 세션이 발음 세션이 되지 않게)
- [x] #3 factory.py·ws.py 의 계약 주석을 함께 고친다 — 「소리 키가 오면 그 모드」 서술이 낡는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-12 KST 착수 전 확인 — learning_sessions.mode 값역을 «조회로» 읽었음. 코드 상수에서 옮겨 적지 말 것.

조회값: CHECK ((mode = ANY (ARRAY['speaking','shadowing','review','pronunciation',...]))) — 018 이 scenario_intake 를 더해 다섯임.
⛔ 그 가운데 «review» 는 코드가 이름을 하나도 갖지 않음. ws.py 의 상수는 SPEAKING_MODE·SHADOWING_MODE·PRONUNCIATION_MODE 셋뿐이고 'review' 를 mode 값으로 쓰는 코드는 grep 0건임. 출처는 001_initial_schema.sql:36 이고 설계됐으나 구현되지 않은 모드임.
⚠️ 공유 dev DB 의 실제 행은 speaking x17 뿐 — shadowing·review·pronunciation 은 0행임. 즉 그 값이 사라져도 «행으로는» 아무도 모름.
⇒ 이 태스크가 ws.py 의 모드 판정을 만질 때 «코드 상수 셋» 을 값역으로 착각하지 않음. 값역은 조회가 정본이고 H-BH 가 같은 부류의 함정임.

⚠️ 그 값역을 못박는 가드는 «이미 있음» — tests/unit/test_schema.py 의 test_session_mode_domain_includes_scenario_intake 가 다섯 값을 포함으로 재고 음성 대조까지 가짐(동료 세션이 018 과 함께 넣었음). ⛔ 나도 같은 가드를 썼다가 «중복이라 버렸음» — 같은 축을 두 곳에서 못박으면 한쪽이 조용히 낡음. 그 테스트를 고쳐야 할 일이 생기면 그 하나만 고침.
<!-- SECTION:NOTES:END -->
