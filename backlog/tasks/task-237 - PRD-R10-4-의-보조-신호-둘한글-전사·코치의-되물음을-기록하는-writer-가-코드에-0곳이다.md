---
id: TASK-237
title: PRD R10-4 의 보조 신호 둘(한글 전사·코치의 되물음)을 기록하는 writer 가 코드에 0곳이다
status: To Do
assignee: []
created_date: '2026-09-19 07:41'
labels: []
dependencies: []
ordinal: 301000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
배치 B6 회차(2026-09-19 · HEAD a34a143)가 mode=pronunciation 실물 세션에서 두 조건을 «둘 다 실제로» 만들었는데 기록이 0행이었음. 어느 쪽이 정본인지 사람이 정해야 하는 자리임 — PRD 와 캡틴 결정이 갈려 있음.

## 재현 (3단계)

1. 백엔드를 VOICE_ADAPTER=nova 로 띄운다.
2. mode=pronunciation 세션에 강한 한국어 억양 픽스처(p2k.wav)를 첫 발화로 흘린다.
3. 그 세션의 pronunciation_attempts 에서 signal_source in ('korean_transcript','agent_reprompt') 를 센다.

## 기대 (PRD §10.2 R10-4 · AC10-3)

판정 보조 신호 2개를 관측·기록한다 — ① 전사문에 한국어가 섞인 경우 ② Agent 가 재요청을 발화한 경우.

## 실제 — 조건은 둘 다 발생했고 기록은 0행

- ① 전사문에 한글: 일어났음. utterances seq 1 의 transcript 가 「아이피니시트더리포트엔쉐어드더리절치위드마이팀」 임.
- ② 코치의 되물음: 일어났음. agent 발화에 「Please repeat: I finished the report and shared the results with my team.」 이 있음.
- 그 세션의 signal_source in ('korean_transcript','agent_reprompt') 는 0행.

## 왜 0행인가 — 둘 다 «결정으로» 만들지 않기로 한 자리임

- korean_transcript: writer 를 지웠음. services/pronunciation.py 머리말이 근거를 적음 — 「보조 신호 경로를 지웠다(TASK-78.1 · 결정 120 · 결정 50 ③). 한글 전사 감지기(note_transcript)와 그 writer(record_signal)가 있던 자리다 — 51세션에서 입력을 한 번도 받지 못했고(0/51)」. ⚠️ 읽는 쪽과 값역은 남아 있어 CHECK 에는 여전히 그 값이 있음.
- agent_reprompt: 값역에만 두고 만들지 않음. models/pronunciation.py:32 · db/migrations/003_pronunciation_echo.sql:39 · services/review.py:256 이 「TASK-24 는 agent_reprompt 를 만들지 않는다로 2026-09-09 에 …」 를 적음.
- ⇒ 리포 전체에서 두 값을 «쓰는» 코드가 0곳임(읽는 경로와 CHECK 값역만 실재함).

## 갈림의 형태

PRD R10-4·AC10-3 은 지금도 그 기록을 요구함. 그런데 결정 120 과 TASK-24 가 각각 그 writer 를 없앴음. 시나리오 AC 문면은 PRD 를 따랐으므로 AC 쪽 잘못이 아니고, 구현도 결정을 따랐으므로 구현 쪽 잘못이 아님 — 문서 둘이 갈려 있음.
⚠️ 결정 120 의 근거는 「51세션에서 입력이 0건」이었는데 이 회차는 같은 조건에서 한글 전사가 **1건 실제로 발생**했음. 그 근거가 지금도 유효한지 다시 볼 자리임 — 다만 이 회차는 강한 억양 TTS 픽스처를 «일부러» 썼으므로 실사용 빈도의 근거는 되지 못함.

## 증거

tests/agent/runs/2026-09-19-b6/result.md §7-3 · evidence/12-r3-pronunciation-frames.json · evidence/13-r3-post-db.txt

HEAD: a34a143
시나리오: TS-34 (AC#3) — 테스트 원장(tests/agent) 의 ID 임

## 제안 (직접 고치지 않았음)

세 갈래 가운데 사람이 하나를 골라야 함.
1. PRD R10-4·AC10-3 을 개정해 보조 신호 요구를 걷는다 — 결정 120 과 TASK-24 를 정본으로 인정하는 안. 그때 CHECK 값역에 남은 두 값의 처리(과거 행 3건이 실재하므로 좁히지 않는다)를 함께 적어야 함.
2. writer 를 되살린다 — 결정 120 을 뒤집는 것이므로 결정 기록이 먼저 있어야 하고, 결정 59 의 「보조 신호는 복습 단계를 전진시키지 않는다」 는 유지해야 함.
3. 「기록은 하지 않지만 다음 세션 계획이 볼 수 있게 한다」 를 다른 수단으로 만든다 — R10-4 의 목적문이 그것임.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 PRD R10-4·AC10-3 과 구현이 한 방향으로 정리되었다 — PRD 를 개정했거나, writer 를 되살린 결정이 docs/design 에 기록되었다
<!-- AC:END -->
