---
id: TASK-32
title: '정리: handoff/HANDOFF.md 를 120줄 상한으로 되돌린다 (현재 245줄)'
status: To Do
assignee: []
created_date: '2026-09-07 11:47'
labels: []
dependencies: []
ordinal: 32000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
CLAUDE.md <work_continuity> 가 handoff 에 ~120줄 상한을 두는데 현재 245줄로 2배다(직접 wc -l). 상한의 목적은 세션 시작에 당장 안 쓸 내용이 통째로 로드되는 것을 막는 것이고, 지금은 그 목적이 깨져 있다. 축소 후보 2개는 이미 정본이 따로 있다: '브라우저 회차 4규약' 과 '모드 전환' 절 — tests/harness/browser_leg.md(679줄)가 VOICE_ADAPTER=stub_unresponsive · Page.bringToFront · Emulation.setEmulatedMedia 를 전부 소유하는 것을 직접 grep 으로 확인했다. 두 곳에 적으면 한쪽이 조용히 낡는다(관측된 사고). 제안 출처는 작업세션이고 설계 범위 밖이라 별도 태스크로 분리했다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 handoff/HANDOFF.md 가 120줄 이하다 — wc -l 출력을 근거로 적는다
- [ ] #2 걷어낸 내용마다 정본 파일을 가리키는 한 줄이 남아 있다 (내용을 두 곳에 두지 않는다)
- [ ] #3 다음 한 걸음 절과 인계 지표 4개 절은 보존한다 — 이 둘이 handoff 의 존재 이유다
- [ ] #4 걷어낸 것과 그 정본을 커밋 메시지에 적는다 (다음 세션이 무엇이 어디로 갔는지 안다)
<!-- AC:END -->
