---
id: TASK-86
title: '결함: 발음 코칭이 일어나도 tool 이 오지 않는다 — 피드백은 있고 기록이 없다'
status: In Progress
assignee: []
created_date: '2026-09-10 04:29'
updated_date: '2026-09-10 16:55'
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
2026-09-10 ⛔ 앞 노트에서 내가 적은 재료 ⑵ 를 철회함 — 「tool 도착 3건이 전부 ae5e832 앞이고 그 뒤 21회 연속 0건」의 인과 읽기가 반증됐음.

코드로 확인한 것 둘: ⑴ ae5e832 는 SYSTEM_PROMPT 를 0줄 바꿨음(계획 블록의 소리 줄만 바꿈) — 4줄 바꾼 것은 1e6cbf6 임 ⑵ spike_nova_protocol.py:398 이 --app-prompt 에서 nova.SYSTEM_PROMPT 만 넘기고 계획 블록을 싣지 않음. 그래서 ae5e832 는 그 팔에 영향이 없음.

경계를 실제 변경 시점(1e6cbf6)으로 옮기면 19회 중 3 대 12회 중 0 이고 Fisher 양측 p=0.2645 로 구별되지 않음. 신호가 있는 경계(p=0.0187)는 프롬프트를 안 바꾼 커밋임. ⛔ 게다가 경계·부분집합을 네 번 시험한 다중 비교임 — 자유도가 있으면 유의한 p 를 만들 수 있음.

⛔ 살아남는 재료는 하나뿐임: 앱 프롬프트를 그대로 실은 팔의 toolUse 0건이 픽스처를 12종으로 통제해도 유지됨. 그 팔은 지금까지 픽스처를 바꾼 적이 없었으므로 새 표본이고 경계 해석에 의존하지 않음.

⛔ 그리고 앞 노트에서 내가 결정 52 의 경계를 넓혀 적은 것을 정정함. 세션 ohmyenglish-40 의 표본(P4 p2k 한글 전사 · P6 p2m 무너진 전사)은 결정 52 가 설계값으로 인정한 구간이 아니고, 오히려 결정 52 가 결정 50 의 ②를 재는 픽스처로 지목한 그 둘임. 즉 그 구간의 코칭 0건은 설계값이 아니라 측정 대상임.

정본은 tests/harness/runs/2026-09-10-task90-pq-phoneme.md §12.1·§12.2 임. 반증을 제안한 것은 그 세션임.
<!-- SECTION:NOTES:END -->
