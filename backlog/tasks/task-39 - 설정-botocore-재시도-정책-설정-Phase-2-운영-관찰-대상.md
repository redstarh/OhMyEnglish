---
id: TASK-39
title: '설정: botocore 재시도 정책 설정 (Phase 2 운영 관찰 대상)'
status: To Do
assignee: []
created_date: '2026-09-07 17:50'
updated_date: '2026-09-12 00:53'
labels: []
dependencies: []
ordinal: 42000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASKS.md E절에서 이관. botocore 재시도 미설정 상태라 스로틀 시 중복 과금 위험이 있다. Phase 2 운영 관찰 시점에 설정한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 botocore 재시도 정책(최대 재시도·backoff)을 설정한다
- [ ] #2 스로틀 재현 또는 관찰로 중복 과금이 사라지는지 확인한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-12 세션 ohmyenglish-f4 (TASK-60 AC#3 에서 넘어옴). 실측 botocore 1.43.78 기본값: connect_timeout 60 · read_timeout 60 · retries None(= legacy 모드 기본이라 스로틀에 재시도가 «이미» 일어남). ⚠️ TASK-60 노트가 인용한 「기본 10분」은 이 리포의 값이 아님 — 참고 프로젝트 수치이고 여기서는 60초임. 그 문장을 그대로 옮기지 않음.

⛔ 이 태스크가 알아야 할 새 사실: 재시도가 SDK «안에서» 나므로 방금 만든 llm_calls 는 재시도분을 못 봄 — invoke_model 이 한 번 돌아오고 그 응답의 usage 만 적힘. 즉 중복 과금이 나도 이 표에는 1건으로 보임. ⇒ AC#2(중복 과금이 사라지는지 확인)를 이 표로 잴 수 없음. 재는 방법을 그 AC 설계에서 먼저 정해야 함(후보: botocore 이벤트 훅으로 시도 수를 세거나, retries 를 명시 설정해 max_attempts 를 알고 있는 값으로 고정).
<!-- SECTION:NOTES:END -->
