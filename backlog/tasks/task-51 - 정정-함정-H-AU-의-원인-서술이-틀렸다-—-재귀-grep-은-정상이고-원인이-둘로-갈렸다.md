---
id: TASK-51
title: '정정: 함정 H-AU 의 원인 서술이 틀렸다 — 재귀 grep 은 정상이고 원인이 둘로 갈렸다'
status: In Progress
assignee: []
created_date: '2026-09-09 03:54'
updated_date: '2026-09-09 04:01'
labels: []
dependencies: []
ordinal: 54000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-50 에서 H-AU 를 「grep -r 이 파일을 조용히 빠뜨린다 · 원인 미확정」으로 적었으나 직접 재실험해 반증했다. 재귀 grep 은 docs/ops/pitfalls.md 를 정상적으로 잡는다(원출력 8줄에 포함). 누락은 두 기전이 겹친 것이었다. ⛔ 다른 세션(ohmyenglish-a7)이 제시한 gitignore 가설은 .superpowers/** 에 대해서만 맞고 pitfalls.md 에는 해당되지 않는다(git check-ignore → NOT ignored).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 기전 (가) 를 확정 기록한다 — 내 제외 필터 grep -v node_modules 가 본문에 그 낱말을 언급하는 정당한 줄을 함께 버렸다. pitfalls.md 에 node_modules 가 2건 있음을 직접 확인했다
- [x] #2 기전 (나) 를 확정 기록한다 — 셰임 grep 이 ugrep --ignore-files 로 불려 무시 대상을 빠뜨린다. .superpowers/ 가 .git/info/exclude:19 로 무시되고 command grep 에서만 잡히는 것을 직접 확인했다
- [x] #3 대응을 고친다 — git ls-files 는 추적 파일만 보므로 추적 밖(.superpowers/**)을 도리어 빠뜨린다. 범위별로 command grep · find 열거 · git ls-files 를 가려 쓴다
- [x] #4 제외 필터는 경로에만 건다는 규칙을 넣는다 — 내용 매칭이 정당한 줄을 버리는 것이 이 사고의 실제 원인이다
- [x] #5 handoff 착수 전 필수의 H-AU 요지와 프로젝트 메모리를 같은 내용으로 고친다 — 한쪽만 고치면 갈라진다
- [x] #6 H-AU 와 handoff 의 「재귀 grep 자체는 정상이다」를 조인다 — 그 문장만 읽으면 맨 grep -r 도 안전하다고 읽히는데 기전 (나)가 바로 셰임 grep -r 이 빠뜨리는 것이다. 다른 세션 리뷰가 찾았고 직접 확인했다
<!-- AC:END -->
