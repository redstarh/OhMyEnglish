---
id: TASK-1
title: '신규 요구사항: 일일 오류 패턴 분석 Summary Table'
status: To Do
assignee: []
created_date: '2026-09-06 00:11'
updated_date: '2026-09-06 01:35'
labels:
  - caps-req
dependencies: []
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
캡틴 노트 항목 1. 매일의 오류 패턴 분석 내용을 별도 Summary Table에 기록한다. 지금은 error_patterns/error_occurrences에 누적만 되고 '그날 무엇을 분석했는지'를 담는 일일 단위 표가 없다. 근거: docs/design/2026-09-06-captain-response-to-status-report.md 항목 1.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 요구사항을 Given/When/Then으로 상세화해 docs/PRD.md 또는 요구사항 문서에 반영
- [ ] #2 일일 경계를 사용자 타임존으로 구하는 규약을 명시(current_date 금지)
- [ ] #3 표 스키마(컬럼·키·보존기간)를 설계서에 반영하고 마이그레이션 번호를 지정
- [ ] #4 읽는 화면 또는 소비자를 함께 정의(reader 0곳 재발 금지)
<!-- AC:END -->
