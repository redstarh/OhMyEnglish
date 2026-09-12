---
id: TASK-116.1
title: '구현: 어긋난 target_sound 가 복습 단계를 전진시키지 못하게 한다 (결정 82)'
status: In Progress
assignee: []
created_date: '2026-09-12 15:17'
updated_date: '2026-09-12 16:09'
labels: []
dependencies: []
parent_task_id: TASK-116
ordinal: 145000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
설계 정본: docs/design/2026-09-13-decision82-record-path-verification.md. 결정 82 를 이행함 — 프롬프트로 세 방향이 반증됐으므로 기록 경로에서 막음.
기제는 새로 만들지 않음: review.py:188 의 signal_source = 'nova_tool' 필터가 「자격 없는 기록을 단계 전진에서 배제하는」 선례임(결정 59 · TASK-74). 그 자리에 조건 한 줄을 더함.
⛔ 형태 검사를 하지 않음 — TASK-97 AC#3 이 기각한 방향임. 이 태스크가 쓰는 것은 «발화 대조» 이고 재료가 둘이라 어긋남이 정의됨.
⛔ 후보 대조(키가 우리가 준 후보 안인지 보는 것)를 하지 않음 — 결함이 정확히 「후보를 되풀이하는 것」이라 판별력이 0 임(설계서 §3 C).
측정된 판별력: 회차 원본에서 2/3(설계서 §5). 맹점은 발화와 기록이 «함께» 틀린 경우임.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 검증 상태를 둘 자리를 정하고 signal_source 에 넣지 않는 근거를 남긴다 — 「어느 신호인가」와 「검증됐는가」는 다른 축이다
- [x] #2 TDD 로 반대 방향 두 단정을 먼저 쓴다 — 어긋난 기록이 전진하지 못한다 · 맞는 기록은 그대로 전진한다(음성 대조)
- [x] #3 대조는 «어긋남을 증명할 수 있을 때만» 배제한다 — 「맞다」를 판정하지 않는다(잘못된 배제가 더 비싸다)
- [x] #4 회차 원본 세 세션을 픽스처로 쓰고 B1 의 맹점을 테스트가 명시한다 — 발화가 오디오와 어긋나는 것은 이 태스크가 못 잡는다
- [ ] #5 검증에 걸린 기록의 화면 표시는 사용자 승인을 받는다 — 복습 큐에서 빼는 것은 결정 82 가 이미 정했으므로 묻지 않는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-13 KST 착수 전 확인 — **대조를 «언제» 하는지를 코드로 답했고 설계서 §4-1 이 정본임.**
기록 시점이 아님: tool 이 코칭 발화와 «동시에» 오므로(`TASK-78`) `record_attempt` 가 도는 시점에
대조할 발화가 아직 저장되지 않았을 수 있고, 그 경합은 조용히 「어긋남 없음」으로 통과함.
⇒ **세션 종료 패스에 얹음** — `resolve_dangling` 이 `audio_gateway/session.py:228` 에서 종료 기록과
같은 트랜잭션으로 돌고, 러너가 `_pending_saves` 를 종료 기록 «전»에 기다리므로 그 시점에는 전사문이
저장돼 있음. 새 job·새 호출 지점을 만들지 않음.
⛔ **그래서 `review.py` 조건의 «방향»이 정해짐 — 「어긋남으로 표시된 것을 제외」이고 「검증된 것만
포함」이 아님.** 후자로 쓰면 진행 중 세션의 시도가 전부 배제됨(검증이 세션 중에는 없음).
⚠️ 참고 선례: `review.py:188` 의 `signal_source = 'nova_tool'` 필터가 같은 문장의 앞 사례임(결정 59).
<!-- SECTION:NOTES:END -->
