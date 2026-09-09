---
id: TASK-76
title: '결함: W1 원자성 테스트가 프로덕션에 없는 호출 패턴에서만 검증한다 (공허 통과)'
status: To Do
assignee: []
created_date: '2026-09-09 16:26'
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
- [ ] #1 프로덕션의 호출 패턴(호출자 트랜잭션 없음)으로 테스트를 다시 써서 실제로 보장되는 것만 단정한다
- [ ] #2 AC W1 의 문면과 I-1 이후의 설계(묶음 단위 job)가 어긋난 것을 판정하고 AC 문서를 갱신한다 — 문면을 그대로 두고 테스트만 고치지 않는다
- [ ] #3 리퍼+스윕이 덮는 범위를 테스트로 고정한다 — 「전사문만 남는 상태가 회복된다」를 관측한다
- [ ] #4 고친 테스트가 무력화에서 FAIL 하는 것을 확인한다 (결정 48 의 등가 증거)
<!-- AC:END -->
