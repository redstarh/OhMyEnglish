---
id: TASK-229.3
title: '종합 분석: 결함을 심각도로 분류하고 수정 태스크를 도출'
status: Done
assignee: []
created_date: '2026-09-19 05:11'
updated_date: '2026-09-19 07:51'
labels: []
dependencies:
  - TASK-229.2
parent_task_id: TASK-229
ordinal: 293000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
회차가 끝난 뒤에만 착수함. 결함을 rules/common/code-review.md 의 4단계(CRITICAL·HIGH·MEDIUM·LOW)로 분류하고 중복·같은 뿌리를 묶어 수정 태스크를 세움.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 결함 전부에 심각도가 붙음
- [x] #2 같은 뿌리를 가진 결함이 묶여 중복 태스크가 없음
- [x] #3 수정 태스크가 우선순위 순으로 작업 원장에 등록됨
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
종합 분석 (2026-09-19 · 결함 9건 본문을 직접 읽어 가름).

심각도와 종류:
- HIGH 앱결함 TASK-232 → 수정 TASK-239 (무대 후보가 수준 1행으로 좁혀져 같은 무대 반복 · 회전 규약 깨짐)
- HIGH 앱결함 TASK-236 → 수정 TASK-240 (재발화가 판정되지 않고 incorrect 로 수렴 · ⛔ 원인 미확정 — 관측 수단 한계가 확인됐으므로 재현이 선행)
- HIGH 기능부재 TASK-233 → 수정 TASK-241 (자주 틀리는 패턴에서 즉시 드릴 경로가 0곳 · PRD:70 이 글자로 요구)
- MEDIUM 앱결함 TASK-234 → 수정 TASK-242 (음성 명령 진입이 started_via 로 갈리지 않음)
- MEDIUM 테스트자산 TASK-230 → 수정 TASK-243 (회귀 기준선이 공유 DB 의 살아 있는 행에 매여 낡음)
- MEDIUM 문서 TASK-238 → 수정 TASK-244 (완료 선언문의 발음 미동작 서술이 낡아 반대 전제를 전파 · 이 회차 지시가 실제로 오독했음)
- LOW 테스트AC TASK-235 → 수정 TASK-245 (TS-29 AC 문면이 확정 계약과 갈림)
- 해소됨 TASK-231 (AC 문면 둘을 회차 도중 고쳤음 · 커밋 754a69a)
- 제품판단 TASK-237 → 결정대기 TASK-246 (PRD R10-4 와 결정 120 이 갈림 · 사람이 골라야 함)

뿌리 묶음 넷: A 발음·낭독(236·237·238·235) · B 진입·기록(233·234) · C 무대 회전(232) · D 테스트 기준선(230).
중복 없음 — 9건이 서로 다른 자리이고 A 묶음의 넷도 층이 다름(동작·요구사항·문서·AC).

⚠️ 이 회차가 내 전제를 둘 반증했음: ① 표면을 OpenAPI 로만 세어 WebSocket 안의 mode·source 분기 넷을 빠뜨렸음 ② 낡은 완료 선언문을 인용해 발음 영역을 「미동작」으로 계획했으나 실제로는 동작했음(TASK-238).
<!-- SECTION:NOTES:END -->
