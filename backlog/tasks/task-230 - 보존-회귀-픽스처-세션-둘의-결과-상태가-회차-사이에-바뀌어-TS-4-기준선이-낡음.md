---
id: TASK-230
title: 보존 회귀 픽스처 세션 둘의 결과 상태가 회차 사이에 바뀌어 TS-4 기준선이 낡음
status: To Do
assignee: []
created_date: '2026-09-19 05:33'
labels: []
dependencies: []
ordinal: 294000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
재현: 1) GET /api/sessions/210233be-ecaa-4409-a1af-8b7016cfe7e9/results 2) GET /api/sessions/d127dece-d1d1-4329-802d-9b8fd1067388/results 3) TS-4 에 적힌 기대 상태와 대조함.

기대(TS-4 · 2026-09-09 기록): 210233be 는 analyzing 이고 corrections 키가 부재함 · d127dece 는 no_utterances 이고 corrections 키가 부재함.
실제(2026-09-19): 210233be 는 partial_failure 이고 corrections 가 빈 배열임 · d127dece 는 final 이고 corrections 1건임.

원인(DB 로 확정함): API 결함이 아니고 픽스처 데이터가 바뀐 것임. 210233be 의 analyze_utterance job 3건이 failed 로 종단해 R2 규칙 4 가 partial_failure 를 냄. d127dece 의 job 3건은 2026-09-18 03:56:57 에 새로 등록돼 done 으로 끝났고 R2 규칙 5 가 final 을 냄 — 그 등록은 docs/ops/pitfalls.md 의 H-CA 가 아니라 H-CD 가 적어 둔 「워커 기동이 끝난 세션의 미등록 발화를 찾아 job 을 새로 등록함」 그 사건임.

영향: 회귀 기준선이 공유 dev DB 의 살아 있는 행에 매여 있어 조용히 낡음. 이 회차는 두 건을 「새로 실패」로 올릴 뻔했고 analysis_jobs 를 직접 조회해서야 데이터 변화임을 가렸음. 다음 회차도 같은 오보 위험을 그대로 가짐.

제안(고치지 않고 적음 · 셋 중 하나): ⑴ 기준선에 세션→상태 대응을 적지 않고 R2 규칙 번호를 적어 규칙 단위로 회귀를 봄 ⑵ 상태별 픽스처를 회차마다 심어서 씀 — 이 회차가 그렇게 했고 격리 사용자 b1000000-0000-4000-8000-000000000001 로 세션 3건을 심어 analyzing·no_utterances 두 뜻을 관측한 뒤 전부 지웠음(검증 0건) ⑶ 보존 픽스처 세션을 워커의 미등록 발화 스윕 대상에서 빼 불변으로 만듦.

증거: tests/agent/runs/2026-09-19-b1/evidence/TS-22-ac1-six-states.txt · TS-22-ac1-seeded-two-states.txt / HEAD: 74fb5c0 / 시나리오: TS-22
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 210233be 와 d127dece 를 다시 조회했을 때 기준선과 어긋나지 않음 — 기준선을 규칙 단위로 바꾸거나 픽스처를 회차마다 심는 쪽으로 정리됨
<!-- AC:END -->
