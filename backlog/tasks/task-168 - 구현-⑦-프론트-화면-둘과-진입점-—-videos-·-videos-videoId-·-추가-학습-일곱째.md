---
id: TASK-168
title: '구현 ⑦: 프론트 화면 둘과 진입점 — /videos · /videos/[videoId] · 추가 학습 일곱째'
status: To Do
assignee: []
created_date: '2026-09-17 17:17'
updated_date: '2026-09-17 17:17'
labels: []
dependencies:
  - TASK-166
  - TASK-167
ordinal: 229000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
설계서 §5 를 이행한다. 화면을 셋 이상으로 늘리지 않는다. 대시보드 항목에 href 를 더하고 업무 역할극 빈 칸이 휩쓸리지 않게 렌더 조건을 좁힌다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 app/videos/page.tsx 를 만들었다 (목록 · URL 붙여넣기 · 미리보기 · 담기 · 지우기 · 빈 상태)
- [ ] #2 app/videos/[videoId]/page.tsx 를 만들었다 (플레이어 · 구간 담기 · 문장 입력 · 담은 문장 목록 · 연습하기)
- [ ] #3 ADDITIONAL_LEARNING 에 href 를 더하고 일곱째 항목 「영상으로 배우기」를 넣었다
- [ ] #4 ⛔ 렌더 조건을 좁혀 업무 역할극 칸의 note 와 비활성이 그대로다
- [ ] #5 설계서 §7 의 오류 문구 아홉이 화면에 실제로 나타난다
- [ ] #6 구간 90초 초과와 빈 문장을 프론트가 미리 막는다 (서버 검사와 겹으로 둔다)
- [ ] #7 npx tsc --noEmit 와 npx eslint . 가 통과한다
<!-- AC:END -->
