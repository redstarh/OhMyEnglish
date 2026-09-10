---
id: TASK-90
title: '하네스: Qwen3 중간지대 픽스처로 P계층 발음 케이스를 실행해 코칭률을 잰다'
status: In Progress
assignee: []
created_date: '2026-09-10 13:51'
updated_date: '2026-09-10 14:19'
labels: []
dependencies:
  - TASK-89
ordinal: 93000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-89 가 만든 픽스처로 실물 왕복을 돌려 「발음 코칭이 나는 조건」을 픽스처 축에서 잰다.

기준선: 4팔 누적 33회에 코칭 2건 = 6.1% (TASK-86 노트 · runs/2026-09-10-task86-reminder-control.md §5). 그 회차들은 전부 p1k·p2k·p1m·p2m 을 썼음. 픽스처를 바꾼 팔이 없음.

⛔ 무엇을 판정하고 무엇을 판정하지 않는지: 코칭률이 픽스처에 따라 달라지는지만 잼. 목표 빈도는 TASK-87 AC#1 의 사용자 결정 몫이고 여기서 발명하지 않음.

⛔ 안전 제약 (runs/2026-09-10-worker-cost-judgment.md 가 정본): 워커를 켜지 않음. 보존 세션 C3a(210233be · analyzing 유일 표본) · C3e(d127dece · no_utterances 유일 표본)를 파괴하지 않음. 스파이크 직결은 learning_sessions 를 만들지 않아 안전하고 앱 경로는 새 세션만 만듦.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 스파이크 직결(spike_nova_protocol.py --tools --app-prompt)로 케이스별 실물 왕복을 돌려 Nova ASR 전사가 오류 음소를 남기는지 관측한다 — 원자료는 회차마다 다른 이름으로 남긴다
- [x] #2 케이스별로 ① 발음 코칭 발화 여부 ② toolUse 도착 여부를 세고 기준선 6.1% 와 대조한다
- [x] #3 코칭률이 픽스처 축에서 달라지는지 판정한다 — 표본이 작으면 「구별되지 않음」으로 적고 단정하지 않는다
- [x] #4 ⛔ 워커를 켜지 않고 보존 세션 둘을 파괴하지 않는다 — DB 는 SELECT 만 하고 그 사실을 회차 기록에 적는다
- [ ] #5 앱 경로 확인은 스파이크가 신호를 보인 케이스로 좁혀 돌린다 — 비용 때문에 전 케이스를 앱 경로로 돌리지 않는다
<!-- AC:END -->
