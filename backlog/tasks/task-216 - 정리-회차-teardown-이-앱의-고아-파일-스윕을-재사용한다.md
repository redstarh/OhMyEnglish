---
id: TASK-216
title: '정리: 회차 teardown 이 앱의 고아 파일 스윕을 재사용한다'
status: Done
assignee: []
created_date: '2026-09-18 07:50'
updated_date: '2026-09-18 19:11'
labels: []
dependencies: []
ordinal: 277000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
/simplify 재사용·고도 각도(2026-09-18). teardown_session.py 의 _remove_recordings 가 삭제 규칙을 다시 구현했고 정책이 서비스와 다르다 — recordings.sweep_orphan_recording_files 는 「이름 규칙에 맞지 않는 파일은 지우지 않고 남긴다」로 되돌릴 수 없는 삭제를 막는데 하네스는 디렉터리의 모든 파일을 지운다. 행을 지운 뒤 같은 연결로 그 함수를 부르면 정책이 한 자리에 남는다. ⚠️ 그 함수는 뿌리 전체를 순회하고 기본 limit 이 100 이므로 세션 단위 개수를 잃는다 — 개수가 필요하면 사설 헬퍼 둘을 공개로 올린다. ⚠️ 동작이 바뀐다(삭제 범위가 좁아진다).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 삭제 규칙의 소유를 services/recordings 한 자리로 되돌린다
- [x] #2 세션 단위 개수를 보고할 방법을 정한다
- [x] #3 이름 규칙 밖 파일이 남는 것을 확인한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## AC3 실측 (2026-09-19 · 이 턴에 직접 돌림)

**서비스 함수 (`remove_orphan_recordings_in`)** — 파일 5건을 심고 `live=set()` 으로 부름:

| 결과 | 파일 | 무엇 |
|---|---|---|
| 지워짐 | `<uuid>.pcm` | 우리 것 · 완성 |
| 지워짐 | `<uuid>.pcm.part` | 우리 것 · 중단된 쓰기 |
| 남음 | `not-a-uuid.pcm` | 확장자는 맞고 이름이 UUID 가 아님 |
| 남음 | `notes.txt` | 우리 것이 아님 |
| 남음 | `readme` | 확장자 없음 |

지운 개수 **2** · 디렉터리 **남음**(조사의 신호).

**하네스 래퍼 (`_remove_recordings`)** — 임시 뿌리에 `SHADOWING_AUDIO_ROOT` 를 걸고 직접 부름:

- 우리 파일 3건 + `keep.md` → 보고 개수 **3** · 남은 파일 `['keep.md']`
- 빈 세션 디렉터리 → 개수 **0** · 디렉터리 **걷힘**
- 디렉터리가 없는 세션 → 개수 **0**

⇒ AC2 의 답: **세션 단위 개수는 래퍼의 반환값이다.** 사이클 상한에 닿는 동안 이어 부르고 더하므로
그 세션의 전량이 세어진다 — 그 함수가 보장하는 멱등성을 근거로 함.

⛔ **동작이 바뀐 것**: 삭제 범위가 좁아짐. 이전 판은 디렉터리의 모든 파일을 지웠음.
<!-- SECTION:NOTES:END -->
