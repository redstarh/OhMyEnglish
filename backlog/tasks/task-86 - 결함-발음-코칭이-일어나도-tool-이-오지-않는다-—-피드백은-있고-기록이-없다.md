---
id: TASK-86
title: '결함: 발음 코칭이 일어나도 tool 이 오지 않는다 — 피드백은 있고 기록이 없다'
status: In Progress
assignee: []
created_date: '2026-09-10 04:29'
updated_date: '2026-09-10 16:48'
labels: []
dependencies:
  - TASK-87
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
- [x] #1 코칭이 난 회차에서 tool 이 오지 않는 이유를 규칙 10 의 조건으로 설명하거나 반증한다
- [ ] #2 고친 뒤 코칭 회차에서 tool 이 오는 것을 실물 왕복으로 확인한다 — 최소 2회 같은 방향
- [ ] #3 ⛔ 우회로를 걷어내지 않는다 — 이 태스크가 닫히기 전에는 보조 신호가 유일한 기록 경로다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-10 선행(TASK-87)이 결정 52 로 닫혔음 — 이 태스크의 AC#2 를 닫는 경로가 좁아진 것을 적어 둠. ⛔ 상태를 바꾸지 않았음(소유가 다른 갈래임).

결정 52: 규칙 9 의 「알아들을 만한 발음은 코칭하지 않는다」 방침을 유지하고 낮은 코칭률은 설계값임.

그래서 AC#2(고친 뒤 코칭 회차에서 tool 이 오는 것을 최소 2회 같은 방향으로 확인)에 두 제약이 붙음.

1. ⛔ 코칭 빈도를 올려서 관측 기회를 늘리는 경로가 막혔음 — 그것이 결정 52 위반임. 이 태스크 노트가 「코칭률이 낮아 tool 도착을 잴 기회가 드묾」을 판정 불가의 사유로 적었는데, 그 사유가 이제 결함이 아니라 설계값임.
2. ⛔ 그래서 남은 경로는 「규칙 9 의 문턱을 넘는 픽스처로 다중 턴 세션을 돌리는 것」임 — *k(한국어 억양) 또는 p2m(전사가 무너진 판)임. 결정 50 의 판정 기준이 이미 다중 턴을 요구하고 결정 52 가 픽스처 조건을 더함.

⚠️ TASK-90 회차가 이 태스크에 주는 재료: 앱 프롬프트를 그대로 실은 팔의 toolUse 0건 표본이 픽스처를 12종으로 통제해도 유지됨(그 팔은 지금까지 픽스처를 바꾼 적이 없었음). 그리고 원자료 전체를 세니 tool 도착 3건이 전부 ae5e832 앞이고 그 뒤 21회가 연속 0건임 — ⛔ 픽스처 교란이 있어 단정하지 않음(같은 픽스처로 좁히면 Fisher p=0.0545 로 구별되지 않음). 정본은 tests/harness/runs/2026-09-10-task90-pq-phoneme.md §12 임.
<!-- SECTION:NOTES:END -->
