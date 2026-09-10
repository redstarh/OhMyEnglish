---
id: TASK-1
title: '신규 요구사항: 일일 오류 패턴 분석 Summary Table'
status: Awaiting Decision
assignee: []
created_date: '2026-09-06 00:11'
updated_date: '2026-09-10 22:24'
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-11 brainstorming 진행 중 — 접근 셋을 제시하고 사용자 승인 대기임. 정본 절차는 docs/ops/data-first-design-convention.md 이고 그 6단계 중 1~2 를 마쳤음.

받은 결정 둘: ⑴ 소비자는 «학습자 화면 — 오늘 무엇을 틀렸는지» ⑵ 범위는 «설계 + 구현까지».

⛔ 조사로 확정한 것 (직접 조회):
- 표 18개에 «일일 단위 표가 없음» — 규약 1단계 완료
- error_occurrences 를 users.timezone(Asia/Seoul) 으로 날짜 집계하면 「그날 무엇을 분석했는지」가 «이미 나옴» (2026-09-09 6건/2패턴 · 09-03 9건/5패턴)
- learner_notes(window_from·window_to·note jsonb)가 기간 요약을 이미 담고 계획 프롬프트가 읽음(plan.py:102 저장 · plan_input.py 소비). 다만 일일 단위가 아님
- 소비 지점이 실재함 — api/results.py 가 결과 응답을 소유하고 corrections·drill·awaiting_analysis 키 규약이 있음
- 마이그레이션 다음 빈 번호는 012 (008 이 비었으나 규약이 되살리지 말라 함)

제시한 접근 셋:
A(권장) 새 표 없이 읽을 때 집계 + 결과 화면에 절 추가. 마이그레이션 0건이라 공유 DB 쓰기 승인이 필요 없음. ⛔ AC#3(표 스키마·마이그레이션 번호 지정)과 어긋나므로 고르면 AC#3 을 「표가 필요 없다는 판정과 근거」로 바꿔야 함. ⚠️ 한계: 패턴이 나중에 병합·삭제되면 과거 날짜 집계가 달라짐.
B 새 표 daily_error_summary(012) + 화면. AC#3 문면에 맞고 과거가 고정됨. ⚠️ 마이그레이션을 공유 개발 DB 에 적용해야 하고 그것은 결정 40 이 묻게 한 항목임. 그리고 「오늘만 본다」면 스냅샷 값어치가 아직 없어 이 리포가 네 번 낸 「reader 0곳」 형태에 가까움.
C learner_notes 재사용. ⚠️ 한 표에 두 계약이 생겨 권장하지 않음.

규약 §3 표를 A 로 채운 것도 제시했음 — 저장 0 · 읽는 쪽은 api/results.py + 프론트 결과 화면(이 태스크가 만듦) · 소유자 공백 없음.
<!-- SECTION:NOTES:END -->
