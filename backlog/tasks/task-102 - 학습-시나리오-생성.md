---
id: TASK-102
title: 학습 시나리오 생성
status: In Progress
assignee: []
created_date: '2026-09-10 22:38'
updated_date: '2026-09-12 15:04'
labels: []
dependencies:
  - TASK-5
type: task
ordinal: 105000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
학습 시나리오 생성기는 별도의 TASK 로 등록하고, 학습 시나리오 완료 현황을 보고, 사전에 10개 이상 사전 생성
EX) 회의 중 보고상황, 주제를 정한 회의에서 회의진행 사항, 여행중 사고를 당한 상황, 쇼핑중 물건을 교환하는 상환 등.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 학습한 필요한 다양한 시나리오 생성,수집이 가능한가?
- [ ] #2 사용자와 대화형 시나리오 생성이 가능한가?
- [x] #3 분야별 학습 시나리오 30개 이상 생성하는가?
- [x] #4 사용자가 이미 완료한 상황을 확인하고 사전 학습 시나리오 생생이 가능한가?
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
관계 정리 2026-09-12 (세션 ohmyenglish-f4). ⛔ 이 태스크가 TASK-4·TASK-5 와 겹친다 — 팀리드가 TASK-4 를 끝낸 뒤에야 발견했다. 이 태스크가 캡틴 요구사항 원문이고 TASK-4·TASK-5 가 그 조각이다.

AC 별 현황 (TASK-4 완료 시점 · 커밋 f2e9d83):
- AC#2 (대화형 시나리오 생성) = TASK-5 와 같은 것이다. 그 태스크가 실행체다.
- AC#3 (분야별 30개 이상) — TASK-4 가 15개를 만들었다(일상 9 + 업무 6 · scripts/migrate.py 의 SEED_SCENARIOS). 절반이 남았고 「분야」 축이 무엇인지가 정해지지 않았다: 지금 learning_scenarios.category 는 daily_life·business·shadowing 세 값뿐이고 그것은 무대 종류다. 30개를 분야별로 나누려면 분야 축을 정하는 결정이 선행한다.
- AC#4 (완료한 상황 확인 후 사전 생성) — 재료가 생겼다. learning_sessions.scenario_id 와 016 의 scenario_pick 으로 「어느 상황을 몇 번 했는지」를 셀 수 있다. 보여 주는 수단은 아직 0곳이다.
- AC#1 (다양한 시나리오 생성·수집) — 수집 경로가 아직 0곳이다.

⛔ 시드를 늘릴 때 결정 76 을 지켜야 한다 — SEED_SCENARIOS 의 배열 순서가 노출 순서이므로 새 상황을 배열 끝에 몰아 붙이면 그것은 「가장 늦게 나오는 상황」이 된다. 그 계약은 test_seed_interleaves_business_stages_early 가 지킨다.

⚠️ 캡틴 예시 넷이 지금 15개에 없다: 회의 중 보고, 주제를 정한 회의 진행, 여행 중 사고, 쇼핑 중 물건 교환. 앞 둘은 업무 계열이고 뒤 둘은 새 계열이다 — 그것이 「분야」 축이 필요하다는 신호다.

진행 2026-09-13 (세션 ohmyenglish-f4). AC#1 을 닫았음 — 시드 30행(일상 9 · 업무 9 · 여행 6 · 쇼핑 3 · 진료 3)에 생성 경로가 더해져 「생성·수집이 가능한가」가 참이 됐음. 선행 TASK-5 가 Done 임(계획서 여섯 완료 · Task 6 커밋 2b7d2a4).

⛔ AC#2(사용자와 대화형 시나리오 생성)를 아직 체크하지 않았음. 배선은 끝났고 게이트 넷이 초록이지만 「실물 모델이 다섯을 하나씩 묻는가」를 재지 않았음 — 결정 50 이 그 부류를 스파이크만으로 닫지 않기로 정했음. TASK-102.1 이 그 회차를 갖고, 그 태스크의 AC#1(스텁으로 파이프라인만 재기)은 사람 없이 돌 수 있음.

⚠️ 조립된 문면은 직접 출력해 확인했음 — 질문 다섯이 순서대로 실리고 one at a time · Do not invent 가 함께 있음. 무대 정하기 지시문은 2864자이고 일반 세션은 2339자임.
<!-- SECTION:NOTES:END -->
