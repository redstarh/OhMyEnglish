---
id: TASK-349
title: '리뷰·실기기: TASK-347·348 따라 읽기 개정의 codex 리뷰 반영과 아이폰 확인'
status: In Progress
assignee: []
created_date: '2026-11-17 13:09'
updated_date: '2026-11-17 13:21'
labels: []
dependencies: []
ordinal: 416000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
대상 6e343e6..c1384bf 의 app/frontend. 아이폰에서 볼 것: Start speaking 한 번에 소리가 나는지(사용자 활성화 제한) · 낱말 경계 신호로 색칠되는지.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 codex 리뷰 결과를 받음
- [x] #2 CRITICAL·HIGH 를 고치거나 근거를 들어 반박함
- [ ] #3 아이폰 실기기에서 바로 시작 · 낱말 색칠 · 맞으면 다음 · 틀리면 다시 들음을 사용자가 확인함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-11-17 codex 리뷰(6e343e6..c1384bf) 4건 모두 수용·수정. HIGH① 다 맞은 뒤 1.5초 동안 닫으면 정리 저장이 끝낸 문장(N)을 다시 씀 → 기다리기 전에 positionRef 를 다음 자리로 옮김(readback-flow ⑦: 고치기 전 마지막 저장 sentence_index 1 · 고친 뒤 2). HIGH② lastSavedRef 를 요청 전에 갱신해 실패한 자리를 다시 안 보냄 → 성공 뒤에만 기억(progress-idle-save: 고치기 전 [2] · 고친 뒤 [2,2]). MEDIUM③ 색칠 일정이 소리보다 앞섬 → utterance.onstart 에서 시작 · 경계 신호가 오면 켜지 않음. LOW④ 합성 없는 경로가 취소를 무시하고 새 연습의 색칠을 지움 → abort 반영 · 끊긴 연습은 setSpokenWords 를 건드리지 않음(③④는 코드로 확인). 회귀: readback-flow 8 · progress-idle-save 4 · mobile-fit 16 ALL PASS · tsc 0 · eslint 0 · node --test 64 · next build 0. 남은 것: AC3 아이폰 실기기 확인.
<!-- SECTION:NOTES:END -->
