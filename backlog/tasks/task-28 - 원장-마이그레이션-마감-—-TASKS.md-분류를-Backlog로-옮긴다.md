---
id: TASK-28
title: 원장 마이그레이션 마감 — TASKS.md 분류를 Backlog로 옮긴다
status: In Progress
assignee: []
created_date: '2026-09-06 01:37'
updated_date: '2026-09-07 22:56'
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
- [ ] #1 TASKS.md 의 각 절이 태스크인지 영구 지식인지 분류한다 — 지시 문서의 분류 결정을 따른다
- [ ] #2 태스크인 것만 Backlog로 옮기고 나머지는 docs/design 또는 docs/ops/pitfalls.md 로 보낸다
- [x] #3 TASKS.md 를 지우지 않는다 — 다른 문서가 절 제목으로 인용한다. 옮긴 뒤 남는 것이 무엇인지 적는다
- [ ] #4 완료 후 지시 문서를 보관소로 보낸다(그때는 보관 기준 3개가 충족된다)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
handoff 줄 수 정리는 2026-09-06에 선행 처리했다 — 475줄 → 137줄(72% 감소). 이전 판은 handoff/backup/2026-09-06/HANDOFF-full-475lines.md 가 소유한다(지우지 않고 옮겼다). 이 태스크의 남은 범위는 TASKS.md 분류를 Backlog 로 옮기는 것이다 — handoff 는 이미 정리됐다.

2026-09-08 실행 결과 — 실행한 것: ① F절(전역 규약 정리, ~/.claude 범위) 삭제 ② B절(캡틴 결정 B-1~B-10) 전문을 docs/design/2026-08-30-captain-decisions-phase1.md 로 이관, TASKS.md 는 포인터만 남김 ③ H-3 실측값을 docs/ops/shared-database-guide.md §4.2-1 로 이관, H절을 포인터로 축약(비밀번호 노출 캡틴결정 TASK-42 로 이관) ④ 관련 문서 지도 를 README.md 로 이관 ⑤ I-3(awscrt teardown)을 docs/ops/pitfalls.md H-AK 로 이관 ⑥ 열린 항목 6건을 신규 백로그 태스크로 등록: TASK-37(하네스 5차수)·38(AWS 키 로테이션)·39(botocore 재시도)·40(추적 체크리스트 HTML)·41(public→전용 스키마 검토)·42(DB 비밀번호 노출 결정대기). 실행하지 않은 것 — A·C·D·E(잔여)·G·I(잔여)·J 절은 TASKS.md 에 그대로 둔다: 2026-09-05 이후 작성된 여러 설계 문서(2026-09-05-frontend-test-agent-plan.md·2026-09-05-slice2-execution-log.md 등)가 'TASKS.md C절/J절이 소유한다' 형태로 이 섹션들을 현재도 살아있는 정본으로 인용한다(grep 확인) — 지시 문서(2026-08-30 작성, 당시 TASKS.md 92행)는 이 성장을 예견하지 못했다. 이 섹션들을 옮기거나 비우면 그 인용들이 끊긴다. 이것은 지시 문서가 답하지 않은 자리라 캡틴 확인이 필요하다(최종 응답 참조) — 그래서 AC#1·#2·#4 는 미체크로 남긴다. 이 리포에는 없는 게이트(pytest 등)는 돌리지 않았다 — 앱 코드 변경 0, 문서·원장만 변경.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-09-07 22:56
---
캡틴 결정 32(2026-09-08): 「지금 마감해」 — 착수한다. ⚠️ 파일을 지우지 않는다(그 AC 는 이미 충족 — 다른 설계 문서가 절 제목으로 지금도 인용한다). 남은 것의 약 40%는 태스크가 아니라 결정 기록·판정 근거·사후 기록이므로 docs/design/** 또는 docs/ops/pitfalls.md 로 보낸다 (~/.claude/rules/task-management.md §4 가 경계를 소유한다).
---
<!-- COMMENTS:END -->
