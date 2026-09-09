---
id: TASK-70
title: Phase 1 최종 코드 리뷰를 돌려 Approve 판정을 기록한다 (완료 선언 항목 6)
status: In Progress
assignee: []
created_date: '2026-09-09 14:22'
updated_date: '2026-09-09 16:27'
labels: []
dependencies: []
ordinal: 73000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-09 TASK-47 의 6항목 대조에서 증거 부재로 드러났음. 근거는 docs/design/2026-09-09-phase1-completion-audit.md §6 임.

찾은 것: 태스크별 리뷰와 고침 라운드는 실재함 — Phase 1 창 커밋 본문에 「Task 9 fix round 1 — 리뷰 Important 5건」·「리뷰 fix round 1 — Important 5건 + Minor 1건」·「리뷰 Important 3건 (fix round 2)」가 있음.

못 찾은 것: Phase 1 전체에 대한 Approve 판정 기록임. 계획 문서가 남은 단계를 「re-review → W-live → E2E-S → /simplify+최종 리뷰」로 적었는데 그 「최종 리뷰」의 판정이 없음. 리포에 있는 Approve 기록은 전부 다른 범위임 — 2026-09-04 것은 학습 코치 슬라이스 1(006·review_tasks)이고 S2-* 는 슬라이스 2 이며 .superpowers/sdd/ 의 보고서 셋도 슬라이스 2·시나리오·쉐도잉 범위임.

⛔ 이것은 항목 4(red→green)와 달리 사후에 돌려도 같은 판정을 냄 — 그래서 결정 사안이 아니라 작업임.

범위: Phase 1 의 F·W·R·G·U 산출물임. 심각도·승인 기준은 ~/.claude/rules/common/code-review.md 가 소유함(Approve = CRITICAL·HIGH 0건).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Phase 1 범위의 코드 리뷰를 돌려 판정을 받는다 — 리뷰어와 범위를 기록에 남긴다
- [ ] #2 CRITICAL·HIGH 가 나오면 고치고 재리뷰한다. Approve 전에 이 태스크를 Done 으로 올리지 않는다
- [ ] #3 판정을 docs/design/2026-08-25-first-slice-acceptance-criteria.md 「선언 자리」 표의 항목 6 에 반영한다 — 원장에 상태를 두 벌 쓰지 않는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-09 리뷰를 돌렸음 — 판정 Not Approve · HIGH 3건. ⛔ AC2 가 「Approve 전에 Done 으로 올리지 않는다」를 요구하므로 이 태스크는 열려 있음.

범위 결정: Phase 1 소유 모듈의 **현재 상태**를 봤음. 과거 커밋 diff 가 아님 — Phase 1 은 2026-08-25~26 구현이고 그 뒤 슬라이스 2·발음·쉐도잉이 같은 파일들을 고쳤으므로 그때의 diff 를 보면 지금 없는 코드를 봄. 리뷰어에게 그 사실을 프롬프트에 명시했음.

리뷰어: codex-cli 0.153.4 (`codex exec review`). 판정 기준은 rules/common/code-review.md (Approve = CRITICAL 0 · HIGH 0).

지적 셋과 내 검증:
① 실행 중 어댑터 오류를 completed 로 기록함 (audio_gateway/session.py) — ✅ 맞음. finally 가 무조건 completed 를 기록해 결과 조회의 R2 우선순위가 connection_failed 에 걸리지 못하고 final·no_utterances 로 떨어짐. 학습자가 장애를 성공으로 봄. ✅ 고쳤음 — 실패하는 테스트를 먼저 써서 red 를 관측했고(assert 'completed' == 'failed') 고친 뒤 885 passed 이며 다른 테스트가 깨지지 않았음. ⚠️ 원래 의도(active 고아 방지)는 그대로 둠 — 닫는 것은 닫고 상태만 사실에 맞췄음. flush 실패는 이 경로에 오지 않음(_flush_analysis 가 예외를 삼킴)을 주석과 테스트로 갈랐음.
② 전사문 저장과 job 등록의 원자성 — ⚠️ 프레이밍을 정정했음. codex 가 든 「전사문만 남고 job 이 없다」는 리퍼+스윕이 덮음(flush_ended_sessions + reap_orphan_sessions · services/utterances.py:238~252 가 그 짝을 이미 적어 뒀음). ✅ 그러나 codex 의 **테스트 지적은 맞음** — tests/unit/test_utterances.py:117 이 호출자 트랜잭션을 열어 두 호출을 감싸는데 프로덕션은 그 패턴을 금지함(_flush_analysis docstring). 즉 AC W1 의 원자성이 프로덕션 경로에서 검증된 적이 없음. TASK-76 으로 등록했고 TASK-47 의 판정 문서에 정정을 남겼음.
③ 종단 이벤트 없는 소켓 종료를 성공으로 처리함 (frontend/app/page.tsx) — ✅ 맞음. onClose 가 session_ended 수신을 보지 않아 이른 종단 상태 읽기가 폴링을 영구히 멈춤. TASK-77 로 등록했음. ⛔ 해결 방향을 발명하지 않았음 — 선택지 셋을 그 태스크에 적었음.

게이트 직접 쟀음: pytest 885 passed(884 → 885 는 이 리뷰가 만든 회귀 테스트 1건) · ruff check exit 0 · format unformatted 0 · ty check All checks passed · 게이트 밖 ruff All checks passed · format unformatted 0 · 프론트 tsc·eslint exit 0.

⚠️ 리뷰어가 리뷰 중에 자기 판단으로 pytest 를 돌렸음 — H-X 대로 다른 세션에 알렸음.
남은 것: TASK-76·TASK-77 이 닫힌 뒤 재리뷰. Approve 를 받으면 AC 문서 「선언 자리」 표의 항목 6 을 갱신함.
<!-- SECTION:NOTES:END -->
