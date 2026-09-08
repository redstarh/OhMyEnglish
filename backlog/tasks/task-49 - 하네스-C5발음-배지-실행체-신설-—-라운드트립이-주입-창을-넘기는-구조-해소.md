---
id: TASK-49
title: '하네스: C5(발음 배지) 실행체 신설 — 라운드트립이 주입 창을 넘기는 구조 해소'
status: To Do
assignee: []
created_date: '2026-09-08 19:30'
labels: []
dependencies: []
ordinal: 52000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
5차수 브라우저 다리가 실측으로 드러냈음(2026-09-09 · tests/harness/runs/2026-09-09-run-5-browser.md 3차 시도). C1·C2·C3·C4 는 실행체가 있는데 C5(발음 배지 A5-1·A5-2)만 없음. 그래서 판정을 여러 번의 대화형 왕복으로 해야 하고, 이 환경 실측 라운드트립이 20,635 ms 인데 주입 창은 10,000 ms 라 창을 반드시 넘김. 회차는 CDP 클릭으로 user activation 을 만든 뒤 같은 문서에서 다시 시도를 합성 클릭하는 우회로 성립시켰고, 그 결과 A5-1 의 음성 대조 ①(주입 전 배지 부재)이 오염됐음 — PASS 는 대조 ②(4 outcome 순차 주입에 같은 요소가 매번 바뀜)를 근거로 냈고 한계를 기록했음. 곁가지 관측: H-AE 가 양쪽으로 갈렸음 — 합성 클릭은 hasBeenActive false 로 active 미도달, CDP 클릭은 true 이고 AudioContext 가 running. 그 함정은 이미 그 갈림을 담고 있어 고칠 것이 없었음.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 C5 실행체를 c2_render_hierarchy.py·c3_results_screen.py 와 같은 형태로 만든다 — 한 번의 프로세스 실행 안에서 주입·판독을 끝내 라운드트립이 창에 영향을 주지 않게 한다
- [ ] #2 A5-1 의 음성 대조 ①(주입 전 배지 요소 부재)을 오염 없이 평가한다 — 같은 문서에서 재시도를 합성 클릭하지 않는다
- [ ] #3 판별력을 확인한다 — 배지 문구를 어긋나게 만든 변형에서 실행체가 exit 1 을 내는 것을 관측하고 그 출력을 첨부한다
- [ ] #4 browser_leg.md §5 C5 표에 실행체 경로와 사용법을 적고, 우회 경로를 쓰던 서술을 지운다
<!-- AC:END -->
