---
id: TASK-66.6
title: '구현 6: has_audio 를 session_started payload 에 싣기'
status: Done
assignee: []
created_date: '2026-09-13 22:11'
updated_date: '2026-09-13 22:42'
labels: []
dependencies:
  - TASK-66.1
parent_task_id: TASK-66
ordinal: 154000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
계획서 Task 6. 파일명을 프런트에 내려보내지 않는다 — 화면이 알아야 하는 것은 소리가 있는가 하나다. ShadowingClip 을 만드는 이웃 테스트가 깨질 수 있고 그것은 내 변경이 옳아서다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 단정 둘이 통과한다 — has_audio 의 두 상태와 payload 키 집합
- [x] #2 전체 게이트가 초록이고 tsc exit 0 이다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
완료 2026-09-14 (세션 ohmyenglish-f4).

red 를 먼저 봤음 — AttributeError · TypeError 로 2 failed. ⚠️ 처음 -k has_audio 로 걸렀더니 1건만 선택됐음(다른 단정 이름에 그 낱말이 없었음) — 함정을 알고 있어 -k "has_audio or audio_exists" 로 넓혀 둘 다 red 임을 확인했음.

고친 자리 넷: _SELECT_SESSION_CLIP_SQL 에 i.audio_filename · ShadowingClip.has_audio 필드 · load_session_clip 의 매핑(포인터가 not null 인가) · as_event_payload 의 키 하나. 프런트 타입 ShadowingSetup.has_audio 도 같은 턴에 고쳤음.

⚠️ 이웃 7건이 깨졌고 전부 test_gateway.py 였음 — 원인은 계약이 키 하나 늘어난 것이라 재던 축을 그대로 고쳤음: _shadowing_turns 헬퍼에 has_audio=kw.get(..., True) 하나와 payload 단정에 "has_audio": True 하나. ⛔ 「내 변경이 틀렸다」로 읽지 않았음.

전체 게이트(이 턴 직접 실행 · 종료코드 확인): pytest 1152 passed(exit 0 · 변경 전 1145+7failed) · ruff check exit 0 · ruff format exit 0(216 files) · ty exit 0 · 프런트 tsc exit 0 · eslint exit 0.
<!-- SECTION:NOTES:END -->
