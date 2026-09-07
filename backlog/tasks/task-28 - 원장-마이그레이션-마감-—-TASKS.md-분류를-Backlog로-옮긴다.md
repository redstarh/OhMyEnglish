---
id: TASK-28
title: 원장 마이그레이션 마감 — TASKS.md 분류를 Backlog로 옮긴다
status: Done
assignee: []
created_date: '2026-09-06 01:37'
updated_date: '2026-09-07 23:12'
labels:
  - caps-req
dependencies: []
ordinal: 28000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
문서 정리 점검(2026-09-06)에서 발견. docs/design/2026-08-30-tasks-md-migration-spec.md 가 '분류는 캡틴이 확정했고 실행만 남았다'고 적은 미실행 작업 지시인데 태스크로 등록돼 있지 않았다 — 보관 후보로 훑다가 잡았다. 2026-09-06에 캡틴 회신 후속을 Backlog에 새로 등록했지만 그것은 이 지시의 실행이 아니다. ⚠️ 이 문서는 폐기 대상이 아니다 — 인용 0곳이지만 대체 문서가 없고 실행이 남았다(보관 판정 기준 3개 중 1번 미충족).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 TASKS.md 의 각 절이 태스크인지 영구 지식인지 분류한다 — 지시 문서의 분류 결정을 따른다
- [x] #2 태스크인 것만 Backlog로 옮기고 나머지는 docs/design 또는 docs/ops/pitfalls.md 로 보낸다
- [x] #3 TASKS.md 를 지우지 않는다 — 다른 문서가 절 제목으로 인용한다. 옮긴 뒤 남는 것이 무엇인지 적는다
- [x] #4 완료 후 지시 문서를 보관소로 보낸다(그때는 보관 기준 3개가 충족된다)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
handoff 줄 수 정리는 2026-09-06 에 선행 처리했다 — 475줄 → 137줄. 이전 판은 handoff/backup/2026-09-06/HANDOFF-full-475lines.md 가 소유한다(지우지 않고 옮겼다).

■ 1차 시도 (2026-09-08 오전, 부분 실행 후 멈춤) — 기록으로 남긴다. F절 삭제 · B절 → docs/design/2026-08-30-captain-decisions-phase1.md · H-3 실측값 → docs/ops/shared-database-guide.md §4.2-1 · 관련 문서 지도 → README.md · I-3 → docs/ops/pitfalls.md H-AK · 열린 항목 6건을 TASK-37~42 로 등록했다. 그리고 A·C·D·E·G·I·J 절은 손대지 않고 멈췄다 — 근거는 '2026-09-05 이후 설계 문서들이 그 절들을 살아 있는 정본으로 인용하므로 옮기면 인용이 끊긴다' 였다. 지시 문서(2026-08-30 작성, 당시 TASKS.md 315줄·표 92행)가 그 성장을 예견하지 못한 자리라 캡틴 확인을 요청했다.

■ 2차 실행 (2026-09-08, 캡틴 결정 32 「지금 마감해」) — 마감했다. ⚠️ 1차의 '옮기면 인용이 끊긴다' 는 전제가 절반만 맞았다: 인용은 절 **제목**을 가리키므로 **제목을 남기고 본문만 옮기면 끊기지 않는다.** 그래서 TASKS.md 를 1499줄 → 209줄로 줄이면서 인용되는 절 제목 26개를 전부 보존했다(직접 대조 확인). 옮긴 원문의 정본은 docs/design/2026-09-08-tasks-md-archive.md 한 장이고, 그 문서가 '무엇이 어디로 갔나' 표와 '원장에 등록하지 않은 이연' 표를 갖는다. 「상태 기호」 절은 삭제했다(도구의 statuses 가 소유).

■ 이 실행에서 새로 등록한 태스크 2건: TASK-47(G-6 Phase 1 완료 선언 6항목 대조 — 실행 증거는 있고 선언이 없었다) · TASK-48(S2-12 문서 마감 + AS11 신설 — 설계서에 AS11·AC11-5 리터럴이 각 0건임을 확인). TASK-37 에 O-1(agent 전사문 선행 개행)을 AC 로 더했다. 중복 대조는 backlog task list --plain 전수 + AS11/S2-12/G-5/G-6 grep 으로 했다.

■ 함께 고친 낡은 서술 4곳 (본문을 고치고 설명을 안 고치는 실패를 막는다): README.md('값이 다르면 TASKS.md 가 맞다' → 원장) · docs/ops/status-report-convention.md §4 2번('원장 근거 = TASKS.md 절' → Backlog 태스크 ID) · docs/templates/status-report-template.html 2곳('상태의 정본 TASKS.md' → Backlog.md) · docs/design/2026-08-30-captain-decisions-phase1.md:4(보관된 지시서 경로).

■ 새 함정 1건: docs/ops/pitfalls.md H-AO — 이 리포에는 .github/ 도 git remote 도 없어서 [skip ci] 가 동작상 무의미하다(둘 다 이 턴에 직접 확인). 여러 계획서가 그것을 CI 분 절감으로 말한다.

■ 앱 코드 변경 0. pytest 를 돌리지 않았다 — 팀리드가 같은 워킹트리에서 구현 작업 중이고 동시 실행은 테스트 DB 를 파괴한다(H-X). 게이트 실측값은 팀리드가 확보한 732 passed · ruff·ty exit 0 을 인용한다.

■ 남은 stale 1건(내가 고치지 않았다): handoff/HANDOFF.md:53 이 이 태스크를 'TASKS.md 140k 잔여 분류' 로 적는다. handoff 는 팀리드 소유라 건드리지 않았다.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-09-07 22:56
---
캡틴 결정 32(2026-09-08): 「지금 마감해」 — 착수한다. ⚠️ 파일을 지우지 않는다(그 AC 는 이미 충족 — 다른 설계 문서가 절 제목으로 지금도 인용한다). 남은 것의 약 40%는 태스크가 아니라 결정 기록·판정 근거·사후 기록이므로 docs/design/** 또는 docs/ops/pitfalls.md 로 보낸다 (~/.claude/rules/task-management.md §4 가 경계를 소유한다).
---
<!-- COMMENTS:END -->
