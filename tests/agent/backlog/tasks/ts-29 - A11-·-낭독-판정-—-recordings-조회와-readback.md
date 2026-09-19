---
id: TS-29
title: A11 · 낭독 판정 — recordings 조회와 readback
status: Blocked
assignee: []
created_date: '2026-09-19 05:18'
updated_date: '2026-09-19 07:43'
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
- [x] #1 녹음이 저장된 뒤 판정 요청이 성공 갈래를 냄
- [x] #2 audio_url 이 없으면 판정이 404 이고 화면이 「지금은 낭독 판정을 쓸 수 없어요.」 를 냄
- [ ] #3 판정 결과가 성공·실패·판정 불가 가운데 하나로 기록됨 (PRD §10)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
⚠️ 전제 정정 (2026-09-19 · 영역 조사 대조): 낭독 판정은 스텁 어댑터면 라우터의 transcriber_available() 가드가 nova 만 허용해 **503** 을 냄. 그러므로 「쓸 수 없어요」 화면 갈래는 실물 없이 스텁으로도 관측됨 — 실물이 필요한 것은 **성공 갈래 하나**임. H-CG 는 audio_url 을 null 로 지워 404 를 만드는 우회를 적었는데, 503 으로도 같은 ok:false 화면에 닿으므로 그쪽이 더 싸다.

## B6 회차 (2026-09-19 · HEAD a34a143) — 차단됨 (AC 2/3)

수단: /tmp/b6_rb2.py (사본 runs/2026-09-19-b6/evidence/driver-b6_rb2.py). p_readback_leg.py 의 JS 상수·도우미를 import 해 한 세션에서 낭독을 두 번 태워 성공 갈래와 404 갈래를 함께 봤음.
세션 4ec9240c-5ae2-4c0a-9b8f-12ef498a3e07 · mode=shadowing · 07:25:22~07:26:08 UTC. 클립은 00000000-...-0201(45낱말)이고 픽스처 readback.wav 와 같은 글임.

- AC#1 ✅ 성공 갈래: POST .../recordings/df3aa791-.../readback 이 200 · 낱말 45개(match 44 · missing 1 = coffee.). 화면도 같게 렌더 — coffee. 하나만 line-through + rgb(255,138,138) 이고 범례가 함께 떴음. utterances.readback_transcript 에 전사가 남았음. 빠진 낱말 하나는 설계서 §6-1 이 ASR 한계로 이미 귀속해 둔 자리라 결함으로 올리지 않았음.
- AC#2 ✅ 실패 갈래: 같은 세션의 둘째 낭독(72983775-...)의 audio_url 을 null 로 지운 뒤 판정 → 화면 「지금은 낭독 판정을 쓸 수 없어요.」 · 같은 주소에 curl 로 다시 물어 404 {"detail":"readback not found"}. 전사가 있으면 load_recording 을 부르지 않으므로 이 갈래는 전사 없는 «다른» 발화로만 성립함.
- AC#3 ❌ 체크하지 않음 — AC 문면이 설계 계약과 어긋남. 설계서 2026-09-18-read-aloud-judgment-design.md §5 가 「연결하지 않음. v1 유예가 아니라 결론임」(TASK-211)으로 확정했고 실제 값역은 낱말마다 match·missing·different 셋임. 그 세션의 pronunciation_attempts 는 0행. ⇒ 결함 TASK-235 (작업 원장 ID).

⚠️ 본문의 전제 정정 노트 절반이 반증됐음 — 스텁으로는 쉐도잉 «화면»에 닿을 수 없음. 스텁 세션이 0.021~0.023초에 끝나 패널이 뜨기 전에 결과 화면으로 넘어감(3회 재현 · evidence/01-stub-round-note.md). 503 은 HTTP 로만 관측됨(회차 끝 evidence/17-backend-restored-stub.txt).

결과: tests/agent/runs/2026-09-19-b6/result.md §6
<!-- SECTION:NOTES:END -->
