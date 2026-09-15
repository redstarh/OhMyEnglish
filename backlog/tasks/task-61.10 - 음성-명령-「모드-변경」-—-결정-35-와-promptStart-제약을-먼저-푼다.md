---
id: TASK-61.10
title: 음성 명령 「모드 변경」 — 결정 35 와 promptStart 제약을 먼저 푼다
status: Done
assignee: []
created_date: '2026-09-15 16:17'
updated_date: '2026-09-15 18:27'
labels: []
dependencies: []
parent_task_id: TASK-61
ordinal: 185000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
PRD §Voice Control 의 남은 명령 셋 가운데 하나다.

⛔ 지금 열 자리가 아닌 이유 둘: ① 「모드를 러너가 다시 판정하지 않는다」가 규약이다(결정 35 · audio_gateway/session.py 의 _shadowing·_pronunciation_sound 주석 둘이 같은 근거를 적어 둔다) ② Nova 지시문은 promptStart 에 한 번만 실려 세션 중 교체가 성립하지 않는다. ⇒ 세션 중 모드 변경은 사실상 「세션을 닫고 새로 여는 것」이고 그것은 TASK-61.8 의 「추가 학습」이 이미 한다.

⚠️ 그래서 이 태스크의 첫 물음은 「모드 변경이 추가 학습과 다른 기능인가」다. 다르지 않다면 PRD 목록에서 이 항목이 추가 학습으로 흡수되는지 사용자 판단을 받는다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 모드 변경이 「추가 학습」과 다른 기능인지 사용자 판단을 받는다
- [x] #2 다르다면 결정 35 와 promptStart 제약을 어떻게 푸는지 정한다
- [x] #3 명령을 만들면 실물 회차로 관측한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 2026-09-16 — 결정 111 로 닫았음 (세션 `ohmyenglish-42`)

- **AC#1**: 사용자 판단이 「같음 — 추가 학습으로 흡수」임(결정 111). 정본은 `docs/ops/captain-instruction-register.md` 임.
- **AC#2 는 조건 불성립으로 닫음** — 「다르다면」이 전제이고 답이 「같음」이라 결정 35·promptStart 제약을 풀 필요가 없어졌음. ⛔ 미결로 남기지 않는 이유: 그 둘은 흡수의 **근거**이지 장애물이 아님.
- **AC#3**: 회차 `tests/harness/runs/2026-09-16-task61-10-mode-change` 가 닫음. 두 언어 **2/2** 로 새 세션의 `mode='pronunciation'` · `learning_source='additional'` 을 관측했음. 화면도 직접 열어 확인했음.
- 구현은 커밋 `6e04887` 임 — `ControlCommand` 에 명령을 더하지 않고 규칙 13 에 절 하나만 더했음.
- ⚠️ **미충족 관측 둘을 회차 §3 이 갖음**: ① 확인을 질문이 아니라 예고로 말했음(계약은 앱이 지킴) ② 종류를 말하지 않은 요청에 되묻지 않았음 → **`TASK-61.12` 로 등재했음.**
<!-- SECTION:NOTES:END -->
