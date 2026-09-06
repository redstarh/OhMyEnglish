---
id: TASK-15
title: '실행: 마이그레이션 007을 개발 DB에 적용'
status: Done
assignee: []
created_date: '2026-09-06 00:13'
updated_date: '2026-09-06 01:35'
labels:
  - caps-req
dependencies: []
ordinal: 15000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
캡틴 노트 항목 15. 007은 session_plans·learner_notes 표를 만들고 analysis_jobs의 CHECK 제약 2개를 drop/add한다(79줄). 되돌리기 스크립트가 0건이다. 항목 16(실물 계획 생성)의 선행 조건이다 — 계획을 저장할 자리가 없으면 실물 호출 결과를 받을 수 없다. 캡틴이 '007이 무엇인지 모르겠다'고 했으므로 설명을 회신 문서 §2에 담았고, 적용 결정은 아직 받지 않았다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 적용 전 개발 DB를 백업하거나 되돌릴 수단을 확보한다(rollback 스크립트가 없다)
- [x] #2 적용 후 표 2개 실재와 analysis_jobs 제약 변경을 직접 조회로 확인
- [x] #3 적용 전후 기존 데이터 행 수를 대조해 손실 0건을 확인
<!-- AC:END -->
