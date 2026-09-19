---
id: TS-29
title: A11 · 낭독 판정 — recordings 조회와 readback
status: Done
assignee: []
created_date: '2026-09-19 05:18'
updated_date: '2026-09-19 08:09'
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
- [x] #3 판정 결과가 낱말마다 맞음·다름·빠짐 가운데 하나로 응답에 실리고 전사문이 utterances.readback_transcript 에 한 번만 저장됨 (설계서 §4 3번·§7 표)
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

AC 문면을 고쳤음 (2026-09-19 · TASK-245 · 결함 TASK-235).

원래 AC#3 은 「판정 결과가 성공·실패·판정 불가 가운데 하나로 기록됨 (PRD §10)」이었으나 그것이 틀렸음 — 낭독 판정의 값역이 아님.

근거 셋:
- 설계서 docs/design/2026-09-18-read-aloud-judgment-design.md 가 §5 에서 「판정 확정 (2026-09-18 · TASK-211): 연결하지 않음. v1 유예가 아니라 결론임」으로 적고, 같은 문서 §6-1 이 「지금 코드가 이미 그 판정에 맞음 — 낭독 판정은 utterances.readback_transcript 만 쓴다」로 잇고 있음.
- PRD §10 의 성공·실패·판정 불가는 R10-2 의 «재발화» 값역이고 낭독 판정의 값역이 아님. 두 값역을 같은 문면으로 묶은 것이 내 잘못이었음.
- 실측(회차 B6): 응답과 저장 형태가 낱말마다 match·missing·different 셋이고, 그 회차 관측은 match 44 · missing 1(coffee.) 이었으며 같은 세션의 pronunciation_attempts 는 0행이었음.

고친 AC#3: 「판정 결과가 낱말마다 맞음·다름·빠짐 가운데 하나로 응답에 실리고 전사문이 utterances.readback_transcript 에 한 번만 저장됨」. 「한 번만」을 넣은 것은 설계서 §4 3번이 「이미 있으면 전사를 건너뜀 — 한 번만 계산함」을 계약으로 적었고 §7 표가 재조회 0 을 요구하기 때문임.

⛔ 반대 방향을 고르지 않은 이유: 복습 경로에 잇겠다고 판단하면 TASK-211 의 확정과 결정 59(「소리를 지목하지 못하는 기록은 자격이 없다」)를 함께 뒤집는 일이므로 결정 기록이 먼저 있어야 함. 이 태스크의 범위가 아님.

⚠️ AC 를 지우고 다시 더했으므로 번호가 밀렸음.
<!-- SECTION:NOTES:END -->
