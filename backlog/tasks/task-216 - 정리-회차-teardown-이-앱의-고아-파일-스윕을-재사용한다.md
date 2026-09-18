---
id: TASK-216
title: '정리: 회차 teardown 이 앱의 고아 파일 스윕을 재사용한다'
status: To Do
assignee: []
created_date: '2026-09-18 07:50'
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
- [ ] #1 삭제 규칙의 소유를 services/recordings 한 자리로 되돌린다
- [ ] #2 세션 단위 개수를 보고할 방법을 정한다
- [ ] #3 이름 규칙 밖 파일이 남는 것을 확인한다
<!-- AC:END -->
