---
id: TASK-169
title: '정리·검증 ⑧: /simplify 로 정리하고 Test Agent 로 통합 테스트한다 (사용자 지시 2026-09-18)'
status: To Do
assignee: []
created_date: '2026-09-17 17:17'
updated_date: '2026-09-17 17:17'
labels: []
dependencies:
  - TASK-168
ordinal: 230000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 지시 — 주요 개발이 끝나면 simplify 로 정리하고 Test Agent 기반으로 꼼꼼히 테스트한다. 게이트 수치로 통합 테스트를 대체하지 않는다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 /simplify 를 돌려 지적된 것을 처리했다 (기각한 것은 근거를 적었다)
- [ ] #2 게이트 일곱을 직접 돌려 exit 0 을 확인했다 (pytest · ruff · format · ty · tsc · eslint · 수집)
- [ ] #3 백엔드를 재기동하고 app-test-agent 로 통합 테스트를 돌렸다 (--reload 가 없으므로 재기동이 선행된다)
- [ ] #4 실제 YouTube 링크로 영상을 담고 구간과 문장을 담고 연습까지 한 바퀴를 돌린 증거가 있다
- [ ] #5 결함이 나오면 재현 절차와 함께 원장에 등록했다
<!-- AC:END -->
