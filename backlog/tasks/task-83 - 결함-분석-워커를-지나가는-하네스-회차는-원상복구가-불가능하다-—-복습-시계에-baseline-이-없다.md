---
id: TASK-83
title: '결함: 분석 워커를 지나가는 하네스 회차는 원상복구가 불가능하다 — 복습 시계에 baseline 이 없다'
status: Done
assignee: []
created_date: '2026-09-10 00:21'
updated_date: '2026-09-10 13:57'
labels: []
dependencies: []
ordinal: 86000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-82 AC#3·AC#4 회차에서 실측했다. teardown 이 8개 표를 기준선으로 되돌렸고 harness_pattern_baseline drift 도 0 이었으나, 학습자의 복습 시계는 움직인 채 남았다: error_patterns 9→10 · review_tasks 15→17 · 기존 review_task ede30660 이 pending→done(completed_at 이 회차 발화 시각) · 기존 패턴 verb_tense_past_simple_for_past_events 의 next_review_at 이 2026-09-12 23:59:37 로 다시 쓰임. 원인은 스냅샷 스키마의 공백이다 — harness_pattern_baseline 은 id·pattern_key·frequency·last_seen_at 넷만 담고 next_review_at·mastery_score 가 없으며 review_tasks 에는 baseline 표가 아예 없다. 그래서 「drift 0」이 「되돌아왔다」를 뜻하지 않는다. 정본은 tests/harness/runs/2026-09-10-task82-p5-p6.md §6-2 다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 회차 전에 error_patterns 의 next_review_at·mastery_score 와 review_tasks 전체를 파일로 뜨는 절차를 하네스 문서에 못박는다 — 표 스키마를 고치는 것보다 먼저 한다
- [x] #2 harness_pattern_baseline 에 next_review_at·mastery_score 를 넣을지, review_tasks baseline 표를 만들지 판정한다 — 마이그레이션이므로 별도 승인이 필요하다
- [x] #3 「drift 0 이 되돌아왔다를 뜻하지 않는다」를 함정으로 등록한다
- [x] #4 이번에 남은 잔여(패턴 1건·review_tasks 2건·기존 행 2건의 변경)를 어떻게 처리했는지 결론과 근거를 기록한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
잔여 처리 완료 2026-09-10 (AC#4). 사용자 판정 「측정 근거가 있는 것까지 되돌림」에 따라 팀리드가 직접 실행했음. 되돌리기 전 상태를 파일로 떴음 — tests/harness/runs/2026-09-10-task82-p5-p6/error-patterns-before-revert.json(10행) · review-tasks-before-revert.json(17행).

단계별 실행과 출력(한 명령에 묶지 않았음): ⑴ review_tasks.f89095cd 삭제 → DELETE 1 ⑵ error_patterns.45961bc2(business_expression_unclear_work_noun) 삭제 → DELETE 1 · cascade 로 62841eb4 가 0건이 된 것 확인 ⑶ review_tasks.ede30660 을 status pending · completed_at NULL 로 → UPDATE 1.

되돌린 뒤 직접 잰 값: error_patterns 9 · review_tasks 15 · error_occurrences 24 — 셋 다 기준선 일치. ede30660 이 review_stage 1 · pending · completed_at NULL 임.

⛔ 되돌리지 않은 것 하나: verb_tense_past_simple_for_past_events 의 next_review_at 은 2026-09-12 23:59:37.666124+00 그대로임. 회차 전 값을 아무도 스냅샷하지 않았고, 동료 세션이 대화로 2026-09-09 19:54 를 말했으나 그 세션이 마감해 대조할 상대가 사라졌으며 어느 기록에도 그 값이 없음. last_seen_at + 1일 규칙에서 유도하면 같은 값이 나오지만 그것은 계산이지 측정이므로 판정 문면과 browser_leg.md §8-② 가 둘 다 금지함.

⚠️ 그래서 불일치가 남았고 다음 회차가 전제로 삼아야 함 — ede30660(1단계)이 pending 인데 그 패턴의 next_review_at 은 2단계 간격만큼 밀려 있음. 복습 주기 시나리오(P9~P12)를 다시 돌리는 회차는 이 한 칸을 알고 시작해야 함. 남은 AC#1~#3 이 그 구조를 고침.

AC#1·#2·#3 완료 2026-09-10.

⛔ AC#2 의 전제가 틀렸음 — 내가 이 태스크를 만들 때 「마이그레이션이므로 별도 승인이 필요하다」로 적었는데 사실이 아님. harness_pattern_baseline 은 db/migrations/** 에 없고 browser_leg.md 가 create table as 로 만드는 하네스 표임(command grep 으로 확인). 그래서 컬럼을 늘리는 데 승인이 필요하지 않고, 판정은 「늘린다」로 확정해 그 자리에서 실행했음.

AC#1·#2 — browser_leg.md §8-0 을 고쳤음. harness_pattern_baseline 이 next_review_at·mastery_score 를 담고, harness_review_task_baseline 을 신설해 review_tasks 의 status·completed_at·due_at·review_stage·cycle_started_at 을 담음. drift 대조도 네 컬럼과 review_tasks 세 컬럼을 보게 바꿨음. 파일 스냅샷은 회차 디렉터리에 두고 커밋하도록 못박았음(/tmp 금지 — restore 가 죽은 회차에서 그것이 유일한 복원 근거였음). README.md 의 같은 SQL 블록에는 정본이 browser_leg.md §8-0 임을 가리키는 주석을 달았음 — 두 곳이 갈라지지 않게 함. ⚠️ 그 README 블록의 podman 명령이 낡은 것도 함께 표시했음(dev DB 는 homebrew :5432 임 — H-T). 고치지는 않았음(범위 밖).

⛔ 새 SQL 을 직접 돌려 확인했음. select 두 개는 정상(patterns 9행 · review_tasks 15행). 그런데 새 drift 쿼리를 기존 표에 걸면 ERROR: column b.next_review_at does not exist 가 남 — 기존 표 컬럼이 id,pattern_key,frequency,last_seen_at 넷뿐임(information_schema 로 확인). 즉 컬럼을 늘린 첫 회차는 drift 대조를 못 함. 그것을 「멈춤」으로 오독하지 않도록 전이 절차를 §8-0 에 적었음 — ① 옛 컬럼 둘로만 drift 를 보고 ② 0 이면 새 스키마로 재스냅샷하며 ③ 그 재스냅샷이 「지금 값을 새 기준선으로 삼는다」는 선언이므로 회차 기록에 남김.

AC#3 — 함정 H-AY 를 등록했음(docs/ops/pitfalls.md DB 절). 번호는 발급 직전에 grep 으로 그 순간 최대값을 확인했음. pitfalls 머리말의 「최종 갱신」도 함께 갱신했음 — 이 리포의 지배 실패 모드가 그 자리임.
<!-- SECTION:NOTES:END -->
