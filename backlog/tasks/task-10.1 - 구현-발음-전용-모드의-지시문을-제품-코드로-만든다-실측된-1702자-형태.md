---
id: TASK-10.1
title: '구현: 발음 전용 모드의 지시문을 제품 코드로 만든다 (실측된 1,702자 형태)'
status: Done
assignee: []
created_date: '2026-09-11 15:29'
updated_date: '2026-09-11 15:42'
labels: []
dependencies: []
parent_task_id: TASK-10
ordinal: 114000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-12 KST 사용자 결정 64. 실측 근거는 tests/harness/runs/2026-09-11-task86-dedicated-session.md 와 …-length-boundary.md 임 — 역할 문단 + 규칙 8~11(9·11 은 유보를 걷은 문면) + 소리 줄로 짠 1,702자 판이 Nova 실물 왕복 4/4 로 tool 을 부르고 target_sound 가 계획이 준 키 그대로 실렸음. 같은 문면이 5,078자 판에서는 0/76 임. ⛔ 문면을 «측정된 그대로» 옮긴다 — 다듬으면 그 근거가 사라지므로 다듬을 것은 별 태스크로 재고 옮긴다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 nova 에 전용 모드 지시문 조립기를 두고 단위 테스트로 잰다 — 규칙 1~7 이 실리지 않는 것과 규칙 10·소리 줄이 실리는 것을 «둘 다» 잰다(음성 케이스가 판별력을 만든다)
- [x] #2 소리 키의 출처를 정하고 없을 때의 거동을 정한다 — 계획의 발음 초점 · 놓친 소리 목록 · 둘 다 없으면 어떻게 하는가
- [x] #3 진입 표면을 TASK-45 가 만든 ?mode= 문에 붙이고 알 수 없는 값의 기존 거동을 깨지 않는다
- [x] #4 ⛔ 지표 오염을 막는다 — 결정 37 이 쉐도잉에 대해 정한 것과 같은 이유로 drill_turns_expected 를 이 모드에 쓰지 않는다(질문이 없으므로 기대값이 애초에 성립하지 않는다)
- [x] #5 게이트를 직접 돌려 통과를 확인하고 수치를 적는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-12 KST 구현 완료. 설계 근거와 한계는 docs/design/2026-09-12-pronunciation-mode-design.md 가 소유함.

만든 것: nova.PRONUNCIATION_MODE_PROMPT(고정부) + nova.build_pronunciation_prompt(sound) · factory 의 pronunciation_sound 인자 · ws._pronunciation_sound_or_none(순수 함수) · ?mode=pronunciation 진입.

테스트: 단위 7건 + 통합 5건. ⛔ 음성 케이스를 함께 넣었음 — 일반 세션 지시문이 무너지지 않는 것 · 소리가 없으면 None · 모드가 아니면 전용 지시문을 쓰지 않는 것. **변이 검사로 판별력을 확인했음**: pronunciation_requested 를 항상 True 로 바꾸자 2건이 깨졌고(그중 1건이 내 음성 케이스) 되돌리니 통과했음.

게이트(app/backend cwd 에서 직접 돌림): pytest **956 passed**(17.20s) · ruff check exit 0 · format --check exit 0(172 files) · ty exit 0 · 프론트 tsc exit 0 · eslint exit 0.

⛔ 알고 남긴 것 셋(설계서 §5): 세션 행 mode 는 여전히 speaking · 규칙 11 이 없는 규칙 4 를 가리킴(측정된 문면이라 그대로 옮겼음) · 화면·버튼이 없음.
<!-- SECTION:NOTES:END -->
