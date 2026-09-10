---
id: TASK-86
title: '결함: 발음 코칭이 일어나도 tool 이 오지 않는다 — 피드백은 있고 기록이 없다'
status: To Do
assignee: []
created_date: '2026-09-10 04:29'
labels: []
dependencies: []
ordinal: 89000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-10 TASK-75 판정에서 확정했음. 근거는 tests/harness/runs/2026-09-10-task75-rule9-rule11-replacement.md §8.6 임.

규칙 9·4 대체가 실린 판 누적 15회에서 발음 코칭 2건이 났는데 둘 다 toolUse 가 0 임. 즉 학습자는 발음 피드백을 받았는데 pronunciation_attempts 행도 error_patterns 갱신도 없고 복습 시계가 돌지 않음.

⚠️ TASK-78 의 「문장 되말하기 ⟺ tool」 11/11 을 무효로 보지 않음 — 그 회차는 기반 프롬프트 범위였고 지금은 계획 블록과 규칙 9·4 대체가 실린 조건임. 관계의 범위가 좁혀진 것으로 읽음.

⛔ 결정 50 의 순서 ③(우회로 제거)을 이것이 막음. tool 만 믿으면 그 두 코칭마저 사라짐.

첫 확인 지점: 규칙 10 이 「Call report_pronunciation_coaching twice: once with outcome pending right after you have modeled the sentence」로 «문장 시범 직후»를 조건으로 거는데, 관측된 두 코칭이 그 조건을 만족하는지임. 하나는 문장을 시범했고(schwa 회차) 하나는 낱말만 격리했음 — 후자가 조건을 못 만족할 수 있음.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 코칭이 난 회차에서 tool 이 오지 않는 이유를 규칙 10 의 조건으로 설명하거나 반증한다
- [ ] #2 고친 뒤 코칭 회차에서 tool 이 오는 것을 실물 왕복으로 확인한다 — 최소 2회 같은 방향
- [ ] #3 ⛔ 우회로를 걷어내지 않는다 — 이 태스크가 닫히기 전에는 보조 신호가 유일한 기록 경로다
<!-- AC:END -->
