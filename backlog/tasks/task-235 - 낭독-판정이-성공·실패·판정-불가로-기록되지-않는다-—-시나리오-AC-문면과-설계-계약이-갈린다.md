---
id: TASK-235
title: 낭독 판정이 성공·실패·판정 불가로 기록되지 않는다 — 시나리오 AC 문면과 설계 계약이 갈린다
status: Done
assignee: []
created_date: '2026-09-19 07:40'
updated_date: '2026-09-19 08:09'
labels: []
dependencies: []
ordinal: 299000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
배치 B6 회차(2026-09-19 · HEAD a34a143)가 TS-29 AC#3 에서 AC 문면과 문서화된 계약의 갈림을 만났음. 제품이 기대와 다르게 동작한 것이 아니고 어느 쪽이 정본인지 사람이 정해야 하는 자리임. 그래서 시나리오 AC 를 체크하지 않고 이 태스크로 넘김. 같은 갈래의 전례가 TASK-231 임.

## 갈림 — TS-29 AC#3 과 낭독 판정의 기록 형태

- 재현: 쉐도잉 세션에서 낭독을 저장한 뒤 POST /api/sessions/{sid}/recordings/{uid}/readback (실물 nova 어댑터)
- 기대(AC 문면): 「판정 결과가 성공·실패·판정 불가 가운데 하나로 기록됨 (PRD §10)」
- 실제: 응답과 저장 형태가 낱말마다 match·missing·different 셋임. 이 회차 관측은 match 44 · missing 1(coffee.) 이고 그 세션의 pronunciation_attempts 는 0행이었음.
- 연결하지 않는 것이 확정된 계약임 — docs/design/2026-09-18-read-aloud-judgment-design.md §5 가 「판정 확정 (2026-09-18 · TASK-211): 연결하지 않음. v1 유예가 아니라 결론임」 으로 적고 근거 셋을 가짐(review.py 의 허용 목록 필터 · 결정 59 의 「소리를 지목하지 못하는 기록은 자격이 없다」 · 전사기 기원의 거짓 양성 실측).
- PRD 와도 어긋나지 않음 — PRD §10 의 성공·실패·판정 불가는 R10-2 의 «재발화» 값역이고 낭독 판정의 값역이 아님.

## 증거

tests/agent/runs/2026-09-19-b6/result.md §6 과 그 회차의 evidence/06-r1-leg1-judgment.json · evidence/07-r1-post-db.txt

HEAD: a34a143
시나리오: TS-29 (AC#3) — 테스트 원장(tests/agent) 의 ID 임

## 제안 (직접 고치지 않았음)

⛔ 코드가 아니라 AC 문면을 계약에 맞추는 쪽이 옳아 보임.
- TS-29 AC#3 → 「판정 결과가 낱말마다 맞음·다름·빠짐 가운데 하나로 응답에 실리고 전사문이 utterances.readback_transcript 에 한 번만 저장된다」 로 고치는 안.
⚠️ 반대로 복습 경로에 잇겠다고 판단한다면 그것은 TASK-211 의 확정과 결정 59 를 함께 뒤집는 일이므로 결정 기록이 먼저 있어야 함.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 TS-29 AC#3 의 문면이 낭독 판정의 문서화된 계약과 일치하도록 고쳐졌거나, 구현을 바꾸기로 한 결정이 docs/design 에 기록되었다
<!-- AC:END -->
