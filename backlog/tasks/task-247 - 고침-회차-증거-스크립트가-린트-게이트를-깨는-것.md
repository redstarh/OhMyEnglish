---
id: TASK-247
title: '고침: 회차 증거 스크립트가 린트 게이트를 깨는 것'
status: Done
assignee: []
created_date: '2026-09-19 07:56'
updated_date: '2026-09-19 07:58'
labels: []
dependencies: []
ordinal: 311000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
통합테스트 회차(TASK-229)가 남긴 증거 스크립트가 tests/agent/runs/ 에 커밋되면서 ruff 검사 범위에 들어와 15건 위반으로 게이트가 깨졌음(2026-09-19 직접 관측 · pytest 1420 통과인데 ruff 15 errors). ⛔ 그 파일들을 사후에 고치는 것은 기록된 증거를 바꾸는 일이라 하지 않음 — 판정 근거의 무결성이 서식보다 셈. tests/harness/runs/** 는 제외 없이 통과해 왔으므로 관례는 「증거도 린트를 지킨다」이나, 그 관례는 사람이 손으로 쓴 드라이버를 전제함. ⇒ tests/agent/runs/** 만 좁게 제외하고 그 근거를 설정에 적음. ⚠️ tests/harness/runs/** 는 제외하지 않음 — 지금 통과하고 있고 넓히면 관례가 조용히 죽음.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ruff check 와 ruff format --check 가 0 으로 돌아옴
- [x] #2 제외 범위가 tests/agent/runs 아래로 한정되고 harness 쪽은 그대로임
- [x] #3 제외한 근거(증거를 사후 편집하지 않음)가 설정에 적혀 있음
<!-- AC:END -->
