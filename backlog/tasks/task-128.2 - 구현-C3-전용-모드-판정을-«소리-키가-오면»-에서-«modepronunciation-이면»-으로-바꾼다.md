---
id: TASK-128.2
title: '구현 C3: 전용 모드 판정을 «소리 키가 오면» 에서 «mode=pronunciation 이면» 으로 바꾼다'
status: To Do
assignee: []
created_date: '2026-09-12 03:54'
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
- [ ] #1 TDD — mode=pronunciation 이고 소리가 «없어도» 전용 지시문이 조립되는 것을 먼저 단정한다
- [ ] #2 음성 대조 — mode 가 없으면 여전히 일반 지시문인 것을 단정한다(모든 세션이 발음 세션이 되지 않게)
- [ ] #3 factory.py·ws.py 의 계약 주석을 함께 고친다 — 「소리 키가 오면 그 모드」 서술이 낡는다
<!-- AC:END -->
