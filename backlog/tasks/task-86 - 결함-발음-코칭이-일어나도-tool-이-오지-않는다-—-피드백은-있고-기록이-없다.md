---
id: TASK-86
title: '결함: 발음 코칭이 일어나도 tool 이 오지 않는다 — 피드백은 있고 기록이 없다'
status: In Progress
assignee: []
created_date: '2026-09-10 04:29'
updated_date: '2026-09-10 17:00'
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
2026-09-10 ⛔ 앞 노트의 「살아남는 재료」도 좁힘 — 세션 ohmyenglish-40 이 그것에서 순환을 찾았고 옳음.

내가 「앱 프롬프트 팔의 toolUse 0건이 픽스처를 12종으로 통제해도 유지됨」을 경계 해석에 의존하지 않는 새 표본으로 적었는데, 그 12종(pq*)은 결정 52 가 「규칙 9 가 글자로 배제한 구간」으로 정한 자리임. 즉 그 구간의 0건은 프롬프트와 무관하게 예상되는 값이고, 그러면 프롬프트 탓인지 픽스처 탓인지 구별하지 못함.

⛔ 판별력이 생기는 조건: 같은 픽스처로 기반(스파이크) 프롬프트 팔에서 tool 이 나야 함. 그런데 pq* 로는 그 대조군을 만들 수 없음 — 결정 52 대로면 양쪽 다 0 이 예상됨.

⛔ 그래서 이 회차가 이 태스크에 줄 수 있는 문면은 한 줄뿐임. 인용할 때 그대로 씀:
「pq* 구간(규칙 9 가 배제한 자리)에서 앱 프롬프트 팔의 toolUse 가 0/12 임.」
이것을 「앱 프롬프트가 tool 을 막는다」의 근거로 쓰지 않음 — 순환임.

⇒ 결국 AC#2 를 잴 수 있는 자리는 *k/p2m 구간뿐임. 결정 52 가 이미 그렇게 정했고 이 절이 그 이유를 하나 더 보탬.

⚠️ 이 회차에서 자기 반증이 두 번 났고 기전이 같음 — 결과를 이미 예측하는 조건에서 얻은 관측을 다른 원인의 근거로 쓴 것임. 정본은 tests/harness/runs/2026-09-10-task90-pq-phoneme.md §12.1·§12.3 임.
<!-- SECTION:NOTES:END -->
