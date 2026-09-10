---
id: TASK-70
title: Phase 1 최종 코드 리뷰를 돌려 Approve 판정을 기록한다 (완료 선언 항목 6)
status: In Progress
assignee: []
created_date: '2026-09-09 14:22'
updated_date: '2026-09-10 01:14'
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
- [x] #1 Phase 1 범위의 코드 리뷰를 돌려 판정을 받는다 — 리뷰어와 범위를 기록에 남긴다
- [x] #2 CRITICAL·HIGH 가 나오면 고치고 재리뷰한다. Approve 전에 이 태스크를 Done 으로 올리지 않는다
- [ ] #3 판정을 docs/design/2026-08-25-first-slice-acceptance-criteria.md 「선언 자리」 표의 항목 6 에 반영한다 — 원장에 상태를 두 벌 쓰지 않는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-09 1차 리뷰 · 2026-09-10 재리뷰. ⛔ 아직 Approve 가 아니므로 이 태스크는 열려 있음 — AC2 가 「Approve 전에 Done 으로 올리지 않는다」를 요구함.

AC1 — 리뷰를 두 번 돌렸음. 리뷰어는 codex-cli 0.153.4(`codex exec review`)이고 범위는 Phase 1 소유 모듈의 **현재 상태**임(과거 diff 가 아님 — 그 파일들이 이후 슬라이스로 바뀌었으므로). 판정 기준은 rules/common/code-review.md 임.
AC2 — 1차의 HIGH 3건을 고치고 재리뷰했음. 재리뷰가 그 셋을 해소로 인정했음: 「어댑터 오류 수정과 원자성 테스트 삭제는 현재 설계에 부합하지만」. 세 번째(폴링 상한)만 불충분으로 봤음.

1차 판정 (2026-09-09): Not Approve · HIGH 3건.
① 실행 중 어댑터 오류를 completed 로 기록 → 고쳤음(red 먼저 관측). ② 전사문·job 원자성 → 프레이밍 정정 + 공허한 테스트 삭제 + AC 문면 수정(TASK-76). ③ 종단 이벤트 없는 소켓 종료 → 결과 화면의 재확인으로 고쳤음(TASK-77).

재리뷰 판정 (2026-09-10): **Not Approve · 새 지적 둘.** 1차의 셋은 재지적되지 않았음.
- P1 — no_utterances 재확인 상한(3회 × 2초 ≈ 6초)이 워커 지연을 못 버팀. 종료 flush 가 실패한 동안 단일 워커가 다른 Claude 작업을 처리하면 스윕이 6초를 넘게 지연될 수 있고, 그러면 네 번째 판독에서 멈춰 교정을 영구히 못 보여줌. ⚠️ 지금 계측이 지연 시나리오를 못 잡는다는 지적도 함께 왔음. → TASK-79. ⛔ 지적이 맞음 — TASK-77 이 그 값을 「스윕 시점을 보장하는 계약이 없다」고 표시했는데 계약이 없으면 어떤 상수도 맞을 수 없음. 상수를 키우는 것으로 닫히지 않음.
- P2 — SigV4 자격증명 쌍이 원자적으로 선택되지 않음. 환경에 access key 만 남고 설정에 다른 쌍과 bearer 가 있으면 섞인 쌍을 완전한 SigV4 로 판단해 bearer 까지 지움 — 동작하던 인증이 잘못된 서명이 됨. → TASK-80.

⚠️ 리뷰 비용이 큼 — 사용자가 「리뷰가 너무 길어지는 것 같아」를 지적했음(2026-09-10). 다음 재리뷰는 **범위를 좁혀** 돌릴 것: 전체 Phase 1 모듈이 아니라 TASK-79·TASK-80 이 건드린 자리와 그 이웃만. 1·2차 판정이 이미 나머지를 덮었음.

게이트(마감 시점 직접 측정): pytest 884 passed · ruff check exit 0 · format unformatted 0 · ty check All checks passed · 게이트 밖 ruff All checks passed · format unformatted 0 · 프론트 tsc·eslint exit 0.
남은 것: TASK-79·TASK-80 을 닫고 **범위를 좁혀** 재리뷰. Approve 를 받으면 AC 문서 「선언 자리」 표의 항목 6 을 갱신함.

2026-09-10 재리뷰 2라운드 — 판정 미수신 상태로 남긴다.

1차(좁힌 범위 · TASK-79·TASK-80 이 건드린 자리와 이웃): HIGH 1건 · TASK-79 는 지적 없음. 그래서 approve 가 아니다.
- HIGH: config.py 의 prepare_bedrock_credentials 가 환경에 세션 토큰만 잔류한 상태에서 .env 의 영구 키 쌍을 올려 섞인 삼중값을 만들고 bearer 를 지운다. 내가 직접 재현했다.
- TASK-79: 리뷰어가 awaiting_analysis 판정 논증을 재구성해 반례를 찾았고 없었다. 프론트 영구 폴링 회귀도 없고 응답 키 추가가 기존 소비자를 깨지 않는다.

2차(재확인 요청 · f31ce3c · 범위를 config.py 와 test_config.py 로 더 좁힘): ⛔ **미수신이다.** 두 번 물었고 그 에이전트는 idle 이다.

⛔ 그래서 AC#3 을 체크하지 않고 이 태스크를 Done 으로 올리지 않는다. 「HIGH 를 고쳤다」는 Approve 가 아니고, idle 은 「끝났다」가 아니다.

다음 세션이 할 것: 같은 범위로 재확인을 다시 돌린다. ⛔ 전체 Phase 1 재리뷰로 넓히지 않는다 — 1·2차 판정이 나머지를 덮었고 전체 범위는 너무 길다. 물을 것 셋을 그대로 쓰면 된다.
1. 잔류 AWS_SESSION_TOKEN 만 있는 상태에서 SigV4 를 포기하고 bearer 로 가는 것이 「동작하던 인증을 깨지 않는다」는 기준에 맞는가.
2. 환경에 AWS_SESSION_TOKEN 과 AWS_ACCESS_KEY_ID 만 있고 secret 이 없는 조합에서 새 게이트가 막지 못하는 자리가 남았는가.
3. 세 키가 환경에 하나도 없다는 게이트의 보장이 대입으로 바꾼 세 줄에 실제로 성립하는가.

⚠️ AC 문서 「선언 자리」 표의 판정 문장을 이 상태에 맞춰 이미 고쳤다 — 남은 미충족이 항목 6 하나이고 그것이 재확인 미수신 때문이라고 적었다. 그 문서를 다시 쓰지 않아도 된다.
<!-- SECTION:NOTES:END -->
