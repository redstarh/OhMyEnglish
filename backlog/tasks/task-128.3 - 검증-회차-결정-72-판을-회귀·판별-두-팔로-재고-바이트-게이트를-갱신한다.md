---
id: TASK-128.3
title: '검증 회차: 결정 72 판을 회귀·판별 두 팔로 재고 바이트 게이트를 갱신한다'
status: Done
assignee: []
created_date: '2026-09-12 03:54'
updated_date: '2026-09-12 14:20'
labels: []
dependencies:
  - TASK-128.2
parent_task_id: TASK-128
ordinal: 136000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
설계 정본: docs/design/2026-09-12-decision72-sound-as-candidate.md §4. ⛔ 상한과 해석 규칙은 그 회차 기록 §0 이 소유하고 설계서가 정하지 않는다.
⛔ 판별 팔의 성공 조건이 «이전과 반대» 다 — 지금까지는 「계획 키가 실린다」가 결함이었고 이제는 「계획 키가 실리지 않는다」가 성공이다.
⚠️ 후보 목록에 f_as_p 를 그대로 둔다 — 후보 기제가 「없는 소리를 발명하지 않는다」를 지키는지 함께 재기 때문이다. 빼면 그 판별력이 사라진다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 회귀 팔(pq06→pq12 · 후보 th_as_s)에서 코칭이 유지되는지 본다 — 기준선 ARM-A 4/4
- [x] #2 판별 팔(pq13→pq13a · 후보 f_as_p · 오디오에 없음)에서 기록된 target_sound 가 f_as_p 가 «아닌» 것이 되는지 본다 — 기준선은 f_as_p 3/3 x2회차
- [x] #3 상한과 해석 규칙을 돌리기 «전에» 회차 기록에 적는다
- [x] #4 결과로 TASK-116 을 닫거나 남긴다 — 닫으면 그 확정 근거를 그 태스크에 적는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-12 KST 결과 — 회차 기록이 정본: tests/harness/runs/2026-09-12-task128-sound-as-candidate.md (Nova 7세션 · 죽은 회차 0).
ARM-A(회귀) 코칭 4/4 · tool 4/4 ⇒ 문면을 되돌리지 않음. 바이트 게이트를 prompt_dedicated_v4.txt(후보 1건 · 1,825자)로 갱신했고 게이트 여섯이 전부 초록임(pytest 1078 passed · ruff 0·42 files · 게이트 밖 0·162 files · ty 0).
ARM-B(판별) 기록된 target_sound 가 3/3 으로 f_as_p 였음 ⇒ f_as_p 3/3 이 세 회차 연속임(TASK-120 · TASK-123 ARM-B · 이 회차).
⛔ 표에 없던 모양 하나: B1 에서 코치가 «early 의 f 소리» 를 말하고 «like in fine» 까지 댔음 — early 에는 /f/ 가 한 자리도 없음. 즉 후보가 기록만 오염시킨 것이 아니라 학습자에게 사실이 아닌 발음 지시를 내리게 했음. 그 세션은 발화와 기록이 «맞는» 유일한 세션이고 둘이 함께 틀렸음 ⇒ 「발화와 기록의 일치」를 건강 지표로 쓸 수 없음.
⛔ 세 방향(더하기·덜기·재료 바꾸기)이 모두 반증됐음 ⇒ 이 축은 프롬프트로 닫히지 않음. 남은 수단 둘은 기록 경로(코드)와 제품 요구사항 재검토이고 후자는 사용자 결정 사안임.
복습 오염 재현: pronunciation_f_as_p frequency=2 · next_review_at=2026-09-13 ⇒ TASK-116 을 닫지 않음(AC#4).
정리 확인: :8012·:8013 curl 000 · 검증 DB 둘 dropdb · 공유 dev DB 다섯 표가 회차 전과 같음(17·7·9·6·7).
<!-- SECTION:NOTES:END -->
