---
id: TS-22
title: A4 · 세션 결과 화면과 API — 여섯 상태와 오류 경계
status: Done
assignee: []
created_date: '2026-09-19 05:18'
updated_date: '2026-09-19 05:33'
labels: []
dependencies: []
ordinal: 22000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
영역 A4. 대상: GET /api/sessions/{id}/results · 화면 /results/[sessionId]. TS-2·TS-4·TS-5 의 회귀 확인을 포함함. 실물 외부 호출 없음.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 여섯 세션 상태가 규약대로 응답함 (TS-4 회귀)
- [x] #2 없는 uuid 와 형식이 잘못된 uuid 의 오류 경계가 사용자에게 구분돼 나옴 (TS-5 회귀)
- [x] #3 화면이 상태 하나를 사람이 읽을 수 있는 문구로 냄 (TS-2 회귀)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
판정: PASS (AC 3/3). 회차 2026-09-19-b1 · HEAD 74fb5c0 · 공유 인스턴스. 실물 외부 호출 0회.
AC#1 결과 조회의 R2 규칙 다섯이 전부 규약대로 응답함. TS-4 의 보존 세션 6건을 다시 조회해 상태 6모양을 받았고, corrections 키 규약이 모든 갈래에서 성립함 — connection_failed·no_utterances·analyzing 은 키 부재 · partial_failure 는 빈 배열 · final 은 1건과 2건.
⚠️ 그 가운데 2건은 TS-4 의 기록과 어긋났음: 210233be 는 analyzing → partial_failure · d127dece 는 no_utterances → final. analysis_jobs 를 직접 조회해 **API 결함이 아니라 픽스처 데이터가 바뀐 것**임을 가렸음(210233be 의 job 3건이 failed 로 종단 · d127dece 의 job 3건이 2026-09-18 03:56:57 에 새로 등록돼 done — 함정 H-CD 의 그 사건). 결함 TASK-230 으로 등록함.
⚠️ 그 결과 analyzing 과 no_utterances 를 낼 세션이 dev DB 에 0건이라, 격리 사용자 b1000000-0000-4000-8000-000000000001 로 세션 3건을 심어 두 상태를 직접 관측함 — no_utterances 의 두 뜻을 awaiting_analysis 로 가르는 계약까지 확인함(발화 0건이면 false · 발화는 있고 job 0건이면 true). 심은 행은 관측 직후 전부 지웠고 잔존 0건을 확인했음(그 세션 재조회가 404). 다른 사용자로 격리했으므로 FIXED_USER_ID 의 히스토리·일일·주간 집계는 건드리지 않았음.
AC#2 없는 uuid 는 404 {"detail":"session not found"} · 형식이 틀린 uuid 는 422 uuid_parsing 임. 화면에서도 갈림을 확인했음 — 404 는 「그 학습 결과를 찾을 수 없습니다.」 · 422 는 「그 학습 결과를 열 수 없습니다.」 로 **서로 다른 한국어 문구**가 나오고 상태 코드나 영어 예외가 새지 않았음.
AC#3 /results/6225ddaf-... 화면이 status final 을 「확정」으로 냄. 하이드레이션 13/13 · 기계 키 노출 0건 · 교정 원문과 교정문이 한국어 설명과 함께 렌더됨.
연결된 결함: TASK-230 (작업 원장).
증거: runs/2026-09-19-b1/evidence/TS-22-*.
<!-- SECTION:NOTES:END -->
