---
id: TASK-316
title: >-
  회차 b16: Playwright 로 현재 화면 스토리보드를 새로 만들고 화면·버튼 통합 시험을 Paseo 탭 둘에서 TestAgent 로
  돌림 (사용자 지시 2026-11-14)
status: In Progress
assignee: []
created_date: '2026-11-14 05:30'
updated_date: '2026-11-14 06:15'
labels: []
dependencies: []
ordinal: 381000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 지시: localhost:3000 을 Playwright 로 현재 구성된 화면의 스토리보드를 확인하고 없으면 만들어 시험함 · 버튼과 화면을 별도 Paseo 탭으로 나눠 실제 시험 · TestAgent 활용 가능 여부 확인. 기존 보드 docs/ux/2026-11-01-user-scenarios 는 e2e86c0 기준이라 TASK-308~315 뒤 화면과 다름(메뉴·Day 줄·Grammar course).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 TestAgent 전용 런처(run.sh)가 Playwright 를 돌릴 수 있는지 확인함
- [ ] #2 두 탭의 회차 결과를 받아 판정을 직접 대조함
- [ ] #3 새 스토리보드를 docs/ux 에 남김
- [ ] #4 회차 뒤 사용자 스택을 복원함
- [ ] #5 스토리보드에서 흐름이 불명확하거나 사람이 쓰기에 논리적으로 맞지 않는 곳과 보완안을 HTML 보고서로 냄 (사용자 지시 2026-11-14)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
TestAgent 확인: 전용 런처 run.sh(OS 샌드박스) 안에서 chromium.launch 는 SIGTRAP 으로 죽음(default·no-sandbox·chrome 채널 모두 · 샌드박스 밖은 셋 다 OK). 샌드박스 밖 헤드리스 Chrome 에 connectOverCDP 는 OK(cdp-smoke.txt). 헤드리스 -p 모드는 복합 명령에 승인을 요구 → 단일 명령만. 시험용 백엔드 launchctl(격리 DB) · Chrome 9401(화면)/9402(버튼).

2026-11-14 사용자 지시(인터넷 끊김 예정)로 일시 정지: 두 탭 TestAgent 를 Escape 로 중단(세션 유지 · Paseo 터미널 「b16 화면」 3aaa8338 · 「b16 버튼」 13265073), 모니터 종료. 시험용 백엔드(launchctl local.ohmyenglish.testbackend · 격리 DB)와 Chrome 9401/9402 는 띄운 채 둠. 재개: 각 탭에 「이어서 진행함」 입력. 마치면 launchctl remove → 아이콘으로 사용자 스택 복원.
<!-- SECTION:NOTES:END -->
