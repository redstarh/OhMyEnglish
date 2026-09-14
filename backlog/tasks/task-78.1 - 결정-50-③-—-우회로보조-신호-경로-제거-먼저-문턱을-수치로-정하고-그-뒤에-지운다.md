---
id: TASK-78.1
title: '결정 50 ③ — 우회로(보조 신호 경로) 제거: 먼저 문턱을 수치로 정하고 그 뒤에 지운다'
status: To Do
assignee: []
created_date: '2026-09-14 17:22'
updated_date: '2026-09-14 22:09'
labels: []
dependencies: []
parent_task_id: TASK-78
ordinal: 174000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
결정 100 이 이 일을 「지금 하지 않는다」로 정하고 새 태스크로 남겼다. 결정 50 은 「기준을 넘으면 우회로를 버린다」로 정했지만 그 기준을 숫자로 적어 두지 않았고, 같은 결정의 1항이 ⛔ 돌린 뒤에 문턱을 정하는 것을 금지한다. 실측은 이미 있다 — 코칭이 난 세션 11건에서 tool 11/11 · target_sound 11/11(결정 100 의 표). 그러나 같은 tool 이 실어 온 target_sound 가 코치 발화와 13/13 으로 어긋났고(TASK-116 AC#1) 그 오염 방어가 2026-09-15 에 막 들어갔다. ⚠️ 우회로는 애초에 입력을 받은 적이 없다(0/51) — 즉 제거의 이득은 단순화뿐이고 급하지 않다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 문턱을 «먼저» 수치로 못박는다 — tool 도착률과 target_sound 실림률의 최소값, 그리고 표본 수. ⛔ 이미 나온 값을 보고 문턱을 맞추지 않는다(결정 50 1항)
- [x] #2 오염 방어가 실사용에서 도는 것을 먼저 관측한다 — 결정 82·95·98·99 의 이행이 방금 끝났고 아직 관측되지 않았다
- [ ] #3 문턱을 넘으면 보조 신호 경로를 지우고, 지운 뒤 발음 신호가 0 이 되지 않는 것을 종단으로 확인한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
AC#2 관측 완료 2026-09-15 (세션 ohmyenglish-65) — 정본은 tests/harness/runs/2026-09-15-task78-1-defenses-in-use/README.md 임. 실물 사용 Nova 1세션 · Claude 계획 1회.

브라우저 레그(전용 Chrome :9333 + 프론트 사본 :3001 + 래퍼 백엔드 :8012 + 검증 전용 DB ohmyenglish_t781)에서 TASK-81 ARM-3 과 같은 조건(pq13→pq13a · 심은 키 f_as_p · 계획 focus=pronunciation_f_as_p)으로 일반 세션 1회를 돌렸음. 관측 넷이 함께 났음: sound_check=mismatched · error_patterns.next_review_at 이 전진하지 않음(review_tasks 도 stage 1 pending 그대로) · 결과 화면에 '기록만 했어요 · 복습에는 쓰지 않아요' · 백엔드 warning 1건.

대조: 같은 조건의 ARM-3(결정 98 이전)은 sound_check 빈칸 · 복습 시계 하루 전진 · 화면에 배제 문구 없음이었음. 판별력도 확인했음 — 같은 발화에 키만 r_as_l·l_as_r 로 바꾸면 None 이라 정상 기록을 배제하지 않음.

⛔ AC#1(문턱을 수치로 못박기)은 이 회차가 하지 않았음. 결정 50 1항이 돌린 뒤에 문턱을 정하는 것을 금지하므로, 이 회차의 도착률(tool 1/1 · target_sound 1/1 · 표본 1)을 보고 문턱을 맞추지 않아야 함. AC#1 은 사람의 결정이고 AC#3 은 그것의 후건임.

2026-09-15 파킹 유지 — 사용자 결정 101. AC#1(문턱을 수치로 못박기)을 지금 정하지 않음. 결정 99·100 은 사용자가 「유지」로 확정했으므로 이제 위임이 아니라 사용자가 고른 결정임. 다시 올릴 조건은 결정 100 의 남은 두 이유(target_sound 내용의 질 · 문턱 부재)가 해소되는 것임.
<!-- SECTION:NOTES:END -->
