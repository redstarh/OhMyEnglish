---
id: TASK-129
title: '관측: 계획 블록의 복습 목록이 발음 키를 이름으로 내는 둘째 경로 — 일반 세션에서 되풀이를 일으키는지 잰다'
status: Awaiting Decision
assignee: []
created_date: '2026-09-12 03:54'
updated_date: '2026-09-14 14:59'
labels: []
dependencies: []
ordinal: 137000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-12 KST · 설계 정본 docs/design/2026-09-12-decision72-sound-as-candidate.md §3 이 이것을 «범위 밖» 으로 둔 이유를 갖는다.
plan.py:319-321 이 due 패턴을 계획 블록에 실을 때 발음이면 «target sound "키"» 로 키를 이름으로 낸다. 결정 72 가 없앤 것은 _SOUND_INSTRUCTION 의 단수 지목이고 이 경로는 남아 있다.
⛔ 이번에 건드리지 않은 이유 셋: ① 그 줄은 모든 카테고리의 복습 목록을 만드는 공용 기제다 ② pattern_id 를 함께 실어야 하는 계약이 리뷰 Critical-1 로 걸려 있다 ③ 발음만 빼면 「복습 예정인데 계획에 안 실린 패턴」이 생겨 다른 결함을 만든다.
⚠️ 그리고 이 경로는 «전용 모드에 존재하지 않는다» — 계획 블록을 싣지 않으므로. 즉 결정 72 의 판별 회차는 이 경로를 재지 못한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 일반 세션(모드 없음)에서 계획의 복습 목록에 발음 패턴이 실렸을 때 기록된 target_sound 가 그 키를 되풀이하는지 «센다» — 전용 모드가 아니라 일반 세션이 관측 대상이다
- [x] #2 되풀이가 있으면 그것이 결정 72 의 구멍인지(같은 고리) 아니면 조건부 재사용의 정상 작동인지 가른다 — 오디오에 «없는» 소리를 계획에 실어 판별한다
- [ ] #3 결과에 따라 그 줄을 고칠지 정한다 — ⛔ 고치는 안은 카테고리 공용 기제를 깨지 않는 것이어야 한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-14 KST 세션 ohmyenglish-65 — 실물 Nova 왕복 비용을 사용자가 승인했음(결정 96). 승인은 비용에 대한 것이고 관측 방법은 이 태스크의 AC 셋이 가짐. 착수 주체는 정해지지 않았음.

회차 2026-09-14 (세션 ohmyenglish-65) — 정본은 tests/harness/runs/2026-09-14-task129-plan-review-key/README.md 임. 여기서 수치를 다시 세지 않음.

AC#1·#2 충족. 일반 세션(모드 없음) 3회에서 기록된 target_sound 가 계획이 고른 키 f_as_p 를 3/3 되풀이했음. 오디오(pq13→pq13a)에 /f/ 가 한 자리도 없으므로 후보 블록의 조건절이 참일 수 없음 ⇒ 조건부 재사용이 아니라 구멍임. 코치가 지목한 것과 target_form 은 early 로 옳았고 어긋난 것은 target_sound 한 칸임.

⛔ 표에 없던 모양 둘을 회차가 새 행으로 적었음: ① 결정 82 의 어긋남 검사가 세 세션 모두 미표시로 남아 복습 시계가 전진했음(코치가 소리를 인용하지 않음 · sound_check_verdict 를 직접 돌려 None 확인) → TASK-116.3 으로 등록했음 ② ASR 이 오류 오디오를 정답 문장으로 전사했음.

⛔ AC#3 은 사용자 판단으로 올림 — 이 회차는 plan.py:320 만 고치면 사라진다를 지지하지 않음. 키가 프롬프트에 닿는 경로가 넷이고 후보 목록은 error_patterns 에서 오므로 계획을 지워도 남음.

비용 실측: Nova 4세션(판별 3 + 죽은 1 — 내가 --timeout 기본 30 으로 돌려 코칭 왕복을 못 담았음) · Claude 계획 호출 2회. 검증 전용 DB drop 완료 · dev DB 여섯 표 행 수가 회차 전후 같음.
<!-- SECTION:NOTES:END -->
