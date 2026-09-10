---
id: TASK-86
title: '결함: 발음 코칭이 일어나도 tool 이 오지 않는다 — 피드백은 있고 기록이 없다'
status: In Progress
assignee: []
created_date: '2026-09-10 04:29'
updated_date: '2026-09-10 07:46'
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
2026-09-10 둘째 시도 — AC#2 또 판정 불가임. 정본은 tests/harness/runs/2026-09-10-task86-reminder-control.md 임.

⛔ 대조군을 함께 돌려 원인 후보 하나를 지웠음. 팔이 넷인 것을 원자료 stem 으로 확정했음 — §8.5 가 「누적 15회 2건」으로 합산한 것이 계획과 리마인더 두 변수를 섞은 것이었음. §10 의 8회는 「질문 겨냥 + 리마인더」이고 이 회차의 7회는 「질문 미겨냥 + 리마인더」임.

계획을 통제하면 리마인더 효과가 사라짐 — 미겨냥끼리 15회 2건 대 7회 0건이고 Fisher 양측 p=1.0 임. 도중에 세운 「리마인더 역효과」 가설을 같은 시점 대조군 6회(0건)로 반증하고 철회했음.

⛔ AC#2 를 이 조건에서 닫을 수 없음. 4팔 누적 33회에 코칭 2건 = 6.1% 이고 코칭 2건까지 기대 회차가 약 30회임. 코칭 0회라 tool 조건이 발동하지 않았음.

⚠️ 「코칭률이 13%보다 낮다」로 적지 않음 — 팔 B 안에서 시점을 비교하면 Fisher p=0.4857 로 구별되지 않음.

의존 방향을 뒤집었음 — TASK-87(빈도)이 먼저임. 근거가 21회(§10 의 8 + 이 회차 13)로 커졌음. handoff 가 「표본 8이라 지금 뒤집지 않았다」로 남긴 판단을 이 회차가 받침.

하지 않은 것: 소스 수정 · toolChoice 강제 · 우회로 제거 · 워커 기동. 스파이크 직결은 동료 세션에 넘겼고 팔 이름 둘을 전달했음.
<!-- SECTION:NOTES:END -->
