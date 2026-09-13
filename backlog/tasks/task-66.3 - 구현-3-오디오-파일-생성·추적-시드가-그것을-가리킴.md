---
id: TASK-66.3
title: '구현 3: 오디오 파일 생성·추적 + 시드가 그것을 가리킴'
status: To Do
assignee: []
created_date: '2026-09-13 22:11'
labels: []
dependencies: []
parent_task_id: TASK-66
ordinal: 151000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
계획서 Task 3. TTS 회차 1회가 필요하다(2026-09-09 생성물이 /tmp 에서 사라졌음). 잰 길이가 16.64 와 다르면 그것이 새 실측이고 clip_end_sec 을 그 값으로 고친다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 assets/clips/<id>.wav 가 추적되고 git check-ignore 가 무시하지 않는다
- [ ] #2 시드 단정 둘이 통과한다 — 파일명 규약과 파일 존재·추적
- [ ] #3 파일을 옮겨 red 를 보고 되돌린다
<!-- AC:END -->
