---
id: TASK-38
title: '정리: AWS access key 로테이션 (대화 기록 경유 노출)'
status: Done
assignee: []
created_date: '2026-09-07 17:50'
updated_date: '2026-09-08 22:19'
labels: []
dependencies: []
ordinal: 41000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASKS.md E절에서 이관. 키가 대화 기록을 경유해 노출됐다. 참조: docs/ops/iam-setup-nova-sigv4.md §6.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 키를 로테이션한다
- [x] #2 docs/ops/iam-setup-nova-sigv4.md §6 절차를 따라 반영을 확인한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-09 캡틴 결정 41 — 로테이션 면제. 미루는 것이 아니라 하지 않기로 결정된 것임.

확인한 것(팀리드 직접): 이 저장소 추적 파일에 키가 0건임 — git grep -nE 'AKIA[0-9A-Z]{16}|aws_secret_access_key\s*=\s*[A-Za-z0-9/+=]{40}' 이 빈 출력임. 즉 노출 경로는 리포 밖(대화 기록)이고 리포에서 지울 것이 없었음. iam-setup-nova-sigv4.md §6 첫째 수칙(실키를 문서에 적지 않는다)은 지켜져 있었음.

AC#1(키를 로테이션한다) — ⛔ 하지 않음. 캡틴 결정 41 이 면제했음. 그 문서 §6 둘째 수칙(「유출 의심 시 즉시 Deactivate」)의 명시적 예외이므로 조용히 두지 않고 그 문서에 예외로 적었음.

AC#2(§6 절차를 따라 반영을 확인한다) — 로테이션이 없으므로 반영할 것이 없음. 대신 §6 에 면제 사실·확인 결과(추적 0건)·잔여 위험을 적어 절차 문서를 실제와 맞췄음.

⚠️ 받아들이는 잔여 위험: 그 키는 계속 유효하고 노출 기록은 회수할 수 없음. 권한이 Bedrock invoke 로 좁혀진 것이 피해 범위를 제한하는 유일한 방어임. 비용 청구를 관측하면 즉시 이 결정을 다시 봄 — 그것이 이 예외의 유효 조건임.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-09-07 22:27
---
연관 감사(2026-09-08 팀리드): To Do → Awaiting Decision. 캡틴 결정 21 제약 5 가 이 태스크를 명시적으로 지목한다 — 「TASK-38(AWS access key 로테이션)도 같은 종류의 미결이다. 함께 보라 — 그것 역시 살아 있는 자격증명이고 실행은 캡틴 몫이다.」 실행 주체가 캡틴이므로 To Do 로 두면 브리핑이 「착수 가능」으로 올려 작업세션이 손댈 수 없는 일을 매번 다시 집어 든다. TASK-42(DB 비밀번호 회전)와 한 묶음으로 본다.
---

created: 2026-09-07 22:56
---
캡틴 결정 29(2026-09-08): 「별도 지시 있을때까지 하지마」. ⚠️ 결정 21 제약 5 가 이것을 「살아 있는 자격증명」으로 지목한 판정은 유지된다 — 미루는 것이지 무해하다고 판정한 것이 아니다. Awaiting Decision 유지.
---
<!-- COMMENTS:END -->
