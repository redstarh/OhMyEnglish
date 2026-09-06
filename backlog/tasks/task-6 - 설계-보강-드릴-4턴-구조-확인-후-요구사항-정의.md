---
id: TASK-6
title: '설계 보강: 드릴 4턴 구조 확인 후 요구사항 정의'
status: In Progress
assignee: []
created_date: '2026-09-06 00:12'
updated_date: '2026-09-06 22:39'
labels:
  - caps-req
dependencies: []
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
캡틴 노트 항목 9. 드릴마다 4턴 이상을 요구하는데 턴 구조를 정하는 코드·지시문이 0곳이다. 구조를 먼저 확인하고 없으면 추가 요구사항을 정의해 설계에 반영한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 현재 턴 구조를 정하는 자리가 있는지 코드로 확인해 결과를 적는다(있다/없다 + 근거)
- [ ] #2 없으면 요구사항을 정의하고 설계에 반영
- [x] #3 지시문에 실을지 코드로 강제할지 근거와 함께 선택(교정 상한이 문구로만 좁힌 선례를 참고)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-07 설계 착수 (brainstorming architectural 경로). AC#3 닫는다 — 선택과 근거가 기록됐다: 캡틴 결정 1(코드로 강제 · 드릴 횟수는 설정값)이 방식을 정했고, 그 결정이 상세설계로 이연한 '미달일 때 무엇을 할지'를 이번에 캡틴에게 물어 결정 10으로 닫았다: 기록하고 드러낸다, 종료를 막지 않는다. 정본은 docs/design/2026-09-06-captain-decisions.md §1 행 1 + §2 + §5 결정 10이다.

결정 10의 근거(재론하지 않는다): 4턴 시퀀스를 만드는 주어는 학습자가 아니라 대화 모델이므로 미달은 모델이 지시를 안 지킨 것이다 — 학습자를 막으면 엉뚱한 사람을 벌한다. 결과 화면 톤 계약이 '채점하지 않습니다, 시범합니다'라 점수처럼 보이면 안 된다. 런타임 개입(agent_reprompt)은 미구현이라 의지하지 않는다.

남은 것은 AC#2(요구사항 정의 + 설계 반영)이고 TASK-25 와 같은 설계서에 함께 쓴다 (캡틴 결정 §2 '결정 2·3은 같은 자리를 건드린다').

착수 전 확인한 사실: 앱 코드에 drill/드릴 0건 · SYSTEM_PROMPT 규칙 전문에 4턴 시퀀스 없음 · session.py 의 턴 경계 감지는 분석 작업 배치용이고 드릴 카운터가 아니다 · 구멍이 둘이다(재료 미전달 + 조립 지시 부재, gap-investigation 항목 9). 세는 자리는 이미 있다.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-09-06 05:05
---
감사 세션이 전달한 캡틴 명령에 따라 정리한다: 01:35 UTC 부터 In Progress 였으나 AC 1/3 에서 진전이 없고 notes 도 없다. 실제 작업은 TASK-31 에만 걸려 있어 상태만 켜둔 것이 원장을 거짓말하게 만든다 → To Do 로 되돌린다. AC #1(현재 턴 구조 확인)은 이미 닫혔으므로 남은 것은 #2·#3 이고, handoff 가 지목한 대로 TASK-25 와 같은 자리를 건드리니 함께 설계한다.
---
<!-- COMMENTS:END -->

## 캡틴 결정 (2026-09-06) — 재론하지 않는다

**드릴 4턴을 코드로 강제한다. 드릴 횟수는 설정값(config·env)에 따로 두고 읽는다.**
⚠️ 새 설정 체계를 만들지 마라 — `app/backend/app/config.py`의 `Settings`에 필드를 더한다.
⚠️ "코드로 강제"의 범위와 미달 시 동작은 docs/design/2026-09-06-captain-decisions.md §2가 소유한다(자유 발화 턴 수는 사후 관측만 가능하다).
**결정 2와 같은 자리를 건드린다** — 질문 전달과 함께 설계한다.
