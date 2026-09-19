---
id: TS-29
title: A11 · 낭독 판정 — recordings 조회와 readback
status: To Do
assignee: []
created_date: '2026-09-19 05:18'
updated_date: '2026-09-19 05:22'
labels: []
dependencies:
  - TS-21
ordinal: 29000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
영역 A11. 대상: GET /api/sessions/{id}/recordings/{utterance_id} · POST .../readback. ⛔ 스텁 둘로는 관측 불가함(H-CG) — A3 의 실물 회차와 같은 세션으로 잼. 실패 갈래는 audio_url 을 null 로 지워 404 를 만들어 관측함.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 녹음이 저장된 뒤 판정 요청이 성공 갈래를 냄
- [ ] #2 audio_url 이 없으면 판정이 404 이고 화면이 「지금은 낭독 판정을 쓸 수 없어요.」 를 냄
- [ ] #3 판정 결과가 성공·실패·판정 불가 가운데 하나로 기록됨 (PRD §10)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
⚠️ 전제 정정 (2026-09-19 · 영역 조사 대조): 낭독 판정은 스텁 어댑터면 라우터의 transcriber_available() 가드가 nova 만 허용해 **503** 을 냄. 그러므로 「쓸 수 없어요」 화면 갈래는 실물 없이 스텁으로도 관측됨 — 실물이 필요한 것은 **성공 갈래 하나**임. H-CG 는 audio_url 을 null 로 지워 404 를 만드는 우회를 적었는데, 503 으로도 같은 ok:false 화면에 닿으므로 그쪽이 더 싸다.
<!-- SECTION:NOTES:END -->
