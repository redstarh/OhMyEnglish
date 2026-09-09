---
id: TASK-76
title: '결함: W1 원자성 테스트가 프로덕션에 없는 호출 패턴에서만 검증한다 (공허 통과)'
status: Done
assignee: []
created_date: '2026-09-09 16:26'
updated_date: '2026-09-09 22:14'
labels: []
dependencies: []
ordinal: 79000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-09 TASK-70 의 codex 리뷰가 HIGH 로 지적하고 팀리드가 코드로 확인했음.

tests/unit/test_utterances.py:117 의 test_transcript_and_job_roll_back_together_when_the_turn_fails 가 `async with db_conn.transaction():` 으로 호출자 트랜잭션을 열어 save_final_transcript 두 번과 flush_pending_analysis 를 함께 감싸고, 예외를 던져 둘이 함께 롤백되는 것을 단정함.

⛔ 프로덕션은 그 패턴을 쓰지 않고 금지함. app/backend/app/audio_gateway/session.py 의 _save_final 은 트랜잭션을 열지 않으며, _flush_analysis 의 docstring 이 「호출자의 트랜잭션 안에서 부르지 않는다 — SQL 오류가 나면 그 트랜잭션이 abort 되어 뒤따르는 종료 기록까지 함께 실패한다」를 명시함. 즉 테스트가 증명하는 성질을 프로덕션이 의도적으로 피함.

⚠️ 그래서 AC W1 의 「확정 전사문 저장과 analyze_utterance 등록이 한 트랜잭션이고」는 프로덕션 경로에서 검증된 적이 없음. TASK-47 의 6항목 대조가 W1 을 「테스트 실재」로 충족 판정했는데 그 근거가 이 테스트였음 — 판정을 정정했음(docs/design/2026-09-09-phase1-completion-audit.md).

⚠️ 다만 codex 가 든 실패 시나리오의 피해는 리퍼+스윕이 덮음. services/utterances.py:238 의 flush_ended_sessions 가 「끝난 세션에서 job 이 없는 묶음을 걷어 등록」하고, 종료 기록 전에 죽은 세션은 sessions.reap_orphan_sessions 가 failed 로 닫아 스윕 대상으로 만듦(워커가 리퍼 → 스윕 순서로 부름). 즉 「전사문만 남고 job 이 없다」는 영구 상태가 아님.

그래서 이 태스크의 내용은 원자성 구현이 아니라 **무엇이 참인지 테스트가 정직하게 말하게 하는 것**임. I-1 이 저장과 등록을 갈라 놓았으므로(job 은 묶음 단위로 agent 턴에 걸림) 1:1 원자성은 더 이상 설계가 아님 — AC W1 의 문면과 지금 설계가 어긋난 것도 함께 판정해야 함.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 프로덕션의 호출 패턴(호출자 트랜잭션 없음)으로 테스트를 다시 써서 실제로 보장되는 것만 단정한다
- [x] #2 AC W1 의 문면과 I-1 이후의 설계(묶음 단위 job)가 어긋난 것을 판정하고 AC 문서를 갱신한다 — 문면을 그대로 두고 테스트만 고치지 않는다
- [x] #3 리퍼+스윕이 덮는 범위를 테스트로 고정한다 — 「전사문만 남는 상태가 회복된다」를 관측한다
- [x] #4 고친 테스트가 무력화에서 FAIL 하는 것을 확인한다 (결정 48 의 등가 증거)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-09 완료. ⛔ 테스트를 고치지 않고 **지웠음** — 그 판단의 근거가 이 태스크의 내용임.

AC1 — 프로덕션 패턴에서 참인 것만 남겼음. 그런데 그것을 새로 쓸 필요가 없었음: 지금 참인 것을 이미 둘이 덮고 있었음. ① test_user_learning_transcript_is_saved_and_enqueued_when_the_turn_closes 가 「저장만으로는 job 이 걸리지 않는다 (I-1)」를 호출자 트랜잭션 없이 단정함 ② test_sweep_enqueues_an_unflushed_run_in_an_ended_session · test_sweep_covers_sessions_closed_as_failed 가 회복을 단정함. 같은 것을 세 번째로 쓰는 대신 거짓 신호를 없앴고, 지운 자리에 되살리지 말라는 이유를 주석으로 남겼음.

AC2 — 판정: 낡은 것은 테스트가 아니라 AC W1 의 문면임. 코드가 이미 그 사실을 적어 뒀음 — save_final_transcript docstring 의 「분석 job은 여기서 걸지 않는다」와 「I-1에서 enqueue가 빠지며 두 write의 원자성이라는 원래 목적은 사라졌다」임. AC 문서의 W1 에서 「확정 전사문 저장과 analyze_utterance 등록이 한 트랜잭션이고」를 지우고 지금 요구 셋으로 바꿨음 — 전사문 저장의 원자성·묶음의 마지막 발화에 job 1건·등록 실패 시 묶음을 잃지 않음(다음 flush → flush_ended_sessions → 리퍼+스윕).

AC3 — 리퍼+스윕이 덮는 범위는 이미 테스트가 고정하고 있었음(위 ②와 integration/test_worker.py 의 test_worker_reaps_an_orphan_session_and_then_recovers_its_run). 새로 쓰지 않고 그것을 근거로 인용했음.

AC4 — 무력화 둘을 걸어 FAIL 을 직접 관측했음(결정 48 의 등가 증거).
① flush 의 묶음 정렬을 뒤집음(`order by ... sequence_no` → `desc`): 884 → 882 passed · FAIL 2건 — test_merge_sql_keeps_its_explicit_ordering · test_agent_speech_between_finals_splits_the_run_in_two. 즉 「job 이 묶음의 마지막 발화에 걸린다」가 공허하지 않음.
② 회복 스윕이 failed 세션을 건너뛰게 뒤집음(ENDED_SESSION_STATUSES 를 completed 만으로): 882 passed · FAIL 2건 — test_sweep_covers_sessions_closed_as_failed · test_worker_reaps_an_orphan_session_and_then_recovers_its_run. 즉 리퍼→스윕 짝도 공허하지 않음.
⛔ 두 변이 모두 되돌렸고 `git diff --stat` 이 그 파일에 아무것도 내지 않는 것으로 확인했음.

게이트: pytest 884 passed(885 → 884 는 지운 테스트 1건 — 회귀가 아님) · ruff check exit 0 · format unformatted 0 · ty check All checks passed.
<!-- SECTION:NOTES:END -->
