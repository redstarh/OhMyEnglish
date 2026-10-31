---
id: TASK-287
title: '재검증: 문법 코스 스토리보드 v3 전체 조문 (회차 b3 · codex 리뷰)'
status: Done
assignee: []
created_date: '2026-10-31 15:21'
updated_date: '2026-10-31 16:22'
labels: []
dependencies: []
ordinal: 352000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
docs/design/2026-10-26-grammar-course-storyboard.html 의 화면 A·B 조문 전체를 시나리오로 뽑아 stub 스택에서 app-test-agent 로 다시 검증함. codex 로 문법 코스 코드를 리뷰함. 사용자 선택 2026-11-01.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 스토리보드 조문마다 시나리오가 있고 회차 b3 결과가 기록됨
- [x] #2 codex 리뷰 findings 를 기술적으로 검증해 수용·반박이 기록됨
- [x] #3 찾은 결함은 회귀 테스트와 함께 고쳐짐
- [x] #4 백엔드·프런트 게이트를 직접 돌려 통과함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-11-01 (KST 00시대)
- 스토리보드 원본(/private/tmp/ohmyenglish-giu-storyboard.html)은 디스크에서 지워졌음. 세션 18d36de2 기록상 마지막 조작이 docs/design/2026-10-26-grammar-course-storyboard.html 로의 복사였으므로 그 사본을 정본으로 씀.
- 회차 b3(tests/agent/runs/2026-11-01-b3): 회귀 R1~R8 PASS · D1(KST 완료 날짜) 고쳐짐 판별 확인. 새 결함 D3(앱 안 링크로 떠나면 위치 0 저장) · D4(수동 모드 Day 완료 불가) · D5(2회차가 Day 6) · D6(다른 단원 첫 문장 진도가 「아직 안 함」). 차단: 실제 시도 집계(stub 503).
- codex 리뷰 1차 6건: 수용 5(2회차 Day 1 · 수동 완료 · 늦은 저장 덮어씀 · 위치 상한 · 대기 막대 방향) · 반박 1(늦은 판정 응답이 횟수를 덮음 — run 이 postCourseAttempt 뒤 signal.aborted 로 반환하므로 setCounts 에 닿지 않음).
- 위치 상한은 거부 대신 Day 길이로 자름(실제 영상이 목차 끝보다 길 수 있음). 늦은 저장은 completed_count 스탬프로 버림.
- D3 원인: 자식 CoursePlayer 정리가 playerRef 를 비운 뒤 부모 언마운트 저장이 startRef(처음 연 위치)를 읽음.
- 게이트(수정 뒤): pytest 1476 passed · ruff 0 · ruff format 341 files · ty 0 · tsc 0 · eslint 오류 0(기존 경고 1). 백엔드 VOICE_ADAPTER=stub 으로 재기동.
- 미결: 「내가 말한 문장」의 밑줄을 원문 낱말에 칠지 학습자 낱말에 칠지(스토리보드 그림과 기존 쉐도잉 방식이 다름) — 결함으로 올리지 않음.

- codex 리뷰 2차(백엔드 diff): findings 0. 단 실행 기록에 프런트 파일을 연 흔적이 없어 프런트는 3차로 다시 받음.
- codex 리뷰 3차(프런트 diff, 파일 5개를 연 것 확인): LOW 1 — 완료 POST 가 실패해도 completedRef 가 오름. 고치지 않음 — 서버 조건이 p.completed_count <= 스탬프 라 스탬프가 커도 이후 저장은 반영되고, 그 세션 동안 늦은 저장 보호가 느슨해질 뿐임. React 정리 순서(자식 먼저)는 codex 가 설치된 런타임에서 확인함.

- 회차 b4(tests/agent/runs/2026-11-01-b4): D4·D6 고쳐짐 · D3·D5(화면 경로) 남음 · 새 결함 0. D3 진짜 원인은 React 가 언마운트 때 ref 를 effect 정리보다 먼저 떼는 것 — 부모 lastTimeRef 로 고치고 CoursePlayer 쪽 수정은 되돌림. D5 는 완료 뒤 주기·언마운트 저장이 updated_at 을 올려서였음 — 진행 중 판정을 「처음 자리를 벗어났는가」(목록 DayRow 와 같은 기준)로 바꿈.
- codex 리뷰 4차(D3·D5 변경분): 새 findings 0 · 3차와 같은 LOW 1 은 같은 근거로 고치지 않음.
- 회차 b5(tests/agent/runs/2026-11-01-b5): 실패 0 · D3·D5 고쳐짐(각 2/2 + 뒤로 가기 · 경계) · 회귀 전부 PASS · 콘솔 예외 0. 정리 뒤 진도 0행·attempts 0건을 내가 직접 조회함.
- 최종 게이트(마지막 코드 변경 뒤 직접 실행): pytest 1477 passed · ruff 0 · ruff format 341 files · ty 0 · tsc 0 · eslint 오류 0(기존 경고 1).
- 관찰(결함 아님): 저장 위치가 있는 Day 를 열면 seekTo 로 영상이 스스로 재생됨. 회차 Chrome 은 자동 재생 제한을 끈 상태였음 — 일반 브라우저 동작은 미확인.
- 남은 미검증: 실제 Nova 전사 경로(실제 시도 집계 · 「내가 말한 문장」) · 물리 마이크 경로. 스택은 VOICE_ADAPTER=stub 으로 떠 있음.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: Codex
created: 2026-10-31 15:56
---
Read-only review started for the requested uncommitted course progress changes.
---

author: Codex
created: 2026-10-31 15:56
---
Read-only review of the requested progress changes: one LOW finding in `app/frontend/app/course/[day]/page.tsx:223`—`completedRef` increments even when the fire-and-forget completion POST fails, allowing subsequent ordinary saves to claim the next completion stamp. Backend `_left_the_start` matches `DayRow`; Decimal comparison is valid; `lastTimeRef` is initialized/reset and receives `CoursePlayer.currentTime()`'s pre-ready start fallback; `CoursePlayer.tsx` has no uncommitted diff or leftover cleanup change. No tests run (review-only).
---
<!-- COMMENTS:END -->
