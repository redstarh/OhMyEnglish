---
id: TASK-26.4
title: '구현 4: 모델 판단 — 프롬프트·파서·process_weekly·워커 분기'
status: To Do
assignee: []
created_date: '2026-09-13 23:36'
labels: []
dependencies:
  - TASK-26.2
  - TASK-26.3
parent_task_id: TASK-26
ordinal: 163000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
계획서 Task 4. 모델 호출은 트랜잭션 밖이고 저장은 한 트랜잭션 + complete 임(process_summary 의 규약). ⛔ 워커 분기를 빼면 else 가 process_analysis 로 보내 영구 failed 가 된다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 단정 여섯이 통과한다 — 한국어 요구 · 점수 금지를 두 축으로(금지 문장과 출력 규격) · 0건 주는 모델 미호출 · 저장 멱등 · computed_at · 토큰 기록이 «행으로» 남는지
- [ ] #2 워커 분기를 지워 red 를 보고 되돌린다
- [ ] #3 개선 패턴에 줄 사실을 정한다 — ⛔ mastery_score 를 쓰지 않는다(전부 0.00)
<!-- AC:END -->
