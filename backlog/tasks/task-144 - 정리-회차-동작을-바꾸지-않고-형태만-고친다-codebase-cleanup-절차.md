---
id: TASK-144
title: '정리 회차: 동작을 바꾸지 않고 형태만 고친다 (codebase-cleanup 절차)'
status: Done
assignee: []
created_date: '2026-09-16 15:22'
updated_date: '2026-09-16 15:46'
labels: []
dependencies: []
ordinal: 198000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
절차 정본은 ~/.claude/skills/codebase-cleanup/SKILL.md 이고 이 리포 배선은 docs/design/2026-09-16-codebase-cleanup-plan.md 다. 기준선(2026-09-17 착수 시점 직접 측정): HEAD 920dee0 · 테스트 수집 1273 · 통과 1273 · ruff/format/ty 통과 · tsc/eslint exit 0. ⛔ 동작변경=예 는 적용하지 않고 태스크로 갈라낸다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 리뷰 다섯 갈래를 읽기 전용으로 돌리고 발견을 신뢰도 순으로 통합한다
- [x] #2 적용 묶음을 파일 겹침 0으로 돌린다 — A5(프로토콜 축)는 단독
- [x] #3 최종 게이트를 리드가 직접 돌려 수집 개수가 기준선 이상임을 보인다
- [x] #4 동작변경 발견을 태스크로 갈라내고 번호를 보고에 적는다
- [x] #5 실사용 게이트가 필요한지 판단하고 근거를 보고에 적는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 마감 (2026-09-17)

정본은 docs/design/2026-09-16-codebase-cleanup-plan.md §8~§12 임.

기준선 대조: 수집 1273 → 1274 · 통과 1273 → 1274 · ruff·format·ty·tsc·eslint 전부 exit 0 ·
문면 정본 검사 7 passed(전·후 같음). 실사용 게이트를 돌렸음(A5 를 건드렸으므로) — 검증 전용 DB +
:8014 백엔드로 명령 픽스처를 흘려 voice_command 저장과 completed 종료를 확인했고, 로그의 Traceback
1건은 Nova 의 55초 간격 거동(H-BF)이라 정리 탓이 아님.

적용: A1(린트 여섯 · 코드 0줄) · A5(상태 헬퍼 + 새 단정) · A7(집계 층) · daily 축.
적용 없음: A2·A3·A4(형태 수준 발견 0건) · A6 는 부분(analyzed 판정 이관만).
갈라냄 여섯: TASK-145 ~ TASK-150.

절차 판정 둘: ① 묶음 배정은 리뷰 «뒤에» 확정해야 함(R3 이 지목한 세 파일이 묶음에 없어 A7 신설)
② 적용 에이전트에게 게이트를 전부 열거해야 함(AA 가 ty 를 안 돌려 타입 검사가 깨진 채 보고했음).
위험 하나: AB 가 git stash 를 썼음 — 손실 0건을 확인했으나 금지 목록에 넣어야 함.
<!-- SECTION:NOTES:END -->
