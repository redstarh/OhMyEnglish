---
id: TASK-14
title: '문서: AC11-5 실물 테스트 범위를 정리해 캡틴에게 올린다'
status: Done
assignee: []
created_date: '2026-09-06 00:13'
updated_date: '2026-09-07 17:45'
labels:
  - caps-req
dependencies: []
ordinal: 14000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
캡틴 노트 항목 20(미결정 6 결정됨) + 항목 4 답변. AC11-5(두 세션 연속 틀린 패턴에서 대화가 구별된다)는 자동 판정이 불가능하다 — 실물 음성 응대가 달라지는 것을 요구하고 대역은 정해진 발화만 낸다. 캡틴 지시: 실제 테스트해야 하는 것 전체를 정리해 따로 진행 요청한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 마이크 2회 연속 세션 시나리오를 하네스 시나리오 문서로 쓴다(1회차 의도적 반복 오류 → 계획 생성 대기 → 2회차 지시문·대화 확인)
- [x] #2 무엇을 자동으로 재고 무엇을 사람이 판정하는지 나눈다
- [x] #3 소요 시간·비용·필요한 준비물을 적는다
- [x] #4 캡틴에게 올릴 요청서 형태로 마감한다 — 승인 없이 실행하지 않는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-08 요청서 작성 완료. 산출물 docs/design/2026-09-08-ac11-5-live-test-request.md.

내용: §0 psql 직접 조회(패턴 8건·최다빈도 article_missing_before_noun freq 7·복습기한 지남) → §2
마이크 2세션 시나리오(mic-1·mic-2·live-plan-1 절차 재사용, 새 수단 0개) → §3 자동/사람 판정 분리
(DB·API 4건 자동, 지시문 의미 확인·대화 유발 여부 2건 사람) → §4 시간(~25~30분)·비용(호출 횟수,
금전 미추정) · 준비물(캡틴 실물 마이크 필수) → §5 캡틴에게 물을 것 6건 → §6 승인 전 미실행 확정.

범위 밖 발견 1건(고치지 않고 여기 적는다): TASK-25 Implementation Notes(2026-09-07)가 이미 적어 둔
사실이지만 이 태스크의 요청서 설계에 직접 영향을 준다 — session_plans.questions(질문 3~5개)가
지시문 조립에 아직 실리지 않는다(sessions.py:108-115가 id·reason·instruction 세 컬럼만 고른다).
TASK-25.2가 그 배선을 진행 중이다. 요청서 §5-3에서 "지금 상태로 돌릴지 TASK-25.2 완료를 기다릴지"를
캡틴 결정 항목으로 올렸다 — 이 태스크가 그 배선을 대신 만들지 않았다.

pytest 미실행(DB 공유 함정 H-X, 지시 규약대로). DB 쓰기 0건 — 읽기 전용 psql 조회 3건만 실행.
<!-- SECTION:NOTES:END -->
