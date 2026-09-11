---
id: TASK-109
title: '결함 후보: 모델이 없는 키 하나를 붙이면 계획 전체가 버려진다 — extra=forbid 와 level.reason_note 실측'
status: To Do
assignee: []
created_date: '2026-09-11 11:35'
labels: []
dependencies: []
ordinal: 112000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-11 세션 ohmyenglish-7f 후속이 이 턴에 직접 관측했다. 같은 재료로 계획을 생성한 첫 호출에서 모델이 level.reason_note: null 을 붙였고 PlanOutput 계열의 extra='forbid' 가 계획 전체를 거부했다(실측 사유: 'level.reason_note Extra inputs are not permitted'). 프롬프트는 이미 'Do not add any key that is not listed above — one unknown key makes the whole response invalid' 를 말하고 있는데도 났다 — 즉 문구로 막는 방식이 실패하는 것을 관측했다. ⚠️ 값이 null 이었다는 것이 중요하다: 내용이 없는 키 하나 때문에 유효한 초점·질문·수준 판정이 통째로 버려지고 job 은 'plan contract violated' 로 실패한다. ⛔ 원장에 올리는 것은 관측이고 처방이 아니다 — 미지의 키를 무시할지, null 인 것만 떨어낼지, 지금처럼 전부 거부할지는 계약 결정이라 이 태스크가 근거를 세워 정한다. 근거 정본: runs/2026-09-11-task86-sound-shaped-questions.md §1.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 실패율을 먼저 센다 — 같은 프롬프트로 몇 회 중 몇 건이 없는 키로 거부되는지 실측한다(1회 관측을 비율로 읽지 않는다)
- [ ] #2 계약을 유지할지 완화할지 정하고 근거를 적는다 — 완화하면 무엇을 잃는지(모르는 키가 조용히 통과하는 것) 함께 적는다
- [ ] #3 ⛔ 사후 처리로 키를 지우는 방식을 쓸 때는 지운 사실을 job 사유나 로그에 남긴다 — 조용히 삼키면 프롬프트가 잘못 유도되고 있다는 신호를 잃는다
<!-- AC:END -->
