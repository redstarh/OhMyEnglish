---
id: TASK-238
title: Phase 1 완료 선언문이 「발음 코칭이 어떤 프롬프트 조건에서도 일어나지 않는다」를 그대로 두어 낡은 전제가 전파된다
status: To Do
assignee: []
created_date: '2026-09-19 07:42'
labels: []
dependencies: []
ordinal: 302000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
배치 B6 회차(2026-09-19 · HEAD a34a143)가 실측으로 그 문장을 반증했음. 문서 결함이고 실제로 잘못된 전제를 전파했음 — 이 배치의 착수 지시가 그 문장을 근거로 TASK-75 를 미해결로 인용했음.

## 재현 (2단계)

1. docs/design/2026-08-25-first-slice-acceptance-criteria.md:169 를 읽는다.
2. 백엔드를 VOICE_ADAPTER=nova 로 띄우고 mode=pronunciation 세션에 강한 억양 픽스처(p2k.wav)를 흘린 뒤 pronunciation 프레임과 pronunciation_attempts 를 센다.

## 기대

문서의 서술과 실측이 같은 방향이어야 함.

## 실제 — 반대 방향

- 문서: 「Phase 1 AC 충족」과 「발음 기능 동작」은 다른 축이고 후자는 아직 아니다. 발음 코칭이 지금 어떤 프롬프트 조건에서도 일어나지 않는다(실물 왕복 28회 · 조건 넷 전부 0). 원인은 SYSTEM_PROMPT 규칙 9·11 이고 그것을 푸는 작업은 TASK-75 가 소유한다.
- 실측(2026-09-19): mode=pronunciation 세션 1회에서 pronunciation 프레임이 1/1 도착하고, 코치가 소리를 지목해 문장 전체를 다시 읽고 따라 말하기를 요청했으며, pronunciation_attempts 1행(signal_source=nova_tool · target_sound=th_as_t · sound_check=matched)과 error_patterns 1행(pronunciation_th_as_t)이 생겼음.
- TASK-75 는 Done 임(2026-09-10 04:30 UTC). 그 태스크가 규칙 9·11 문제를 발음 전용 모드 신설로 풀었고 설계 정본이 docs/design/2026-09-12-pronunciation-mode-design.md 임.

## 왜 결함인가

그 문장은 「이 구별 없이 이 선언을 인용하면 「선언했는데 발음이 안 된다」가 된다」 라고 스스로 인용 주의를 붙였음. 지금은 그 문장 자체가 낡아 반대 방향의 오독을 만듦 — 실제로 이 배치의 착수 지시가 「발음 기능은 미동작」·「TASK-75 가 미해결」로 인용했고, 그 결과 이 시나리오는 실패를 예상하는 자리로 계획됐음.
⚠️ 문서가 28회 왕복으로 세운 관측 자체는 그 시점에 참이었음 — 지우는 것이 아니라 «그 뒤에 무엇이 바뀌었는지»를 함께 적어야 함.

## 증거

tests/agent/runs/2026-09-19-b6/result.md §1(전제 ①) · §7-1 · §7-4 · evidence/12-r3-pronunciation-frames.json · evidence/13-r3-post-db.txt

HEAD: a34a143
시나리오: TS-34 — 테스트 원장(tests/agent) 의 ID 임
관련: TASK-75 (Done)

## 제안 (직접 고치지 않았음)

docs/design/2026-08-25-first-slice-acceptance-criteria.md 의 그 절에 뒤집힘을 «덧붙여» 적는 안 — 원문을 지우지 않고 「2026-09-10 에 TASK-75 가 닫혔고 2026-09-12 에 발음 전용 모드가 들어와, 2026-09-19 실측에서 그 모드의 tool 도착이 1/1 이었음. 그러므로 위 문장은 일반 세션(SYSTEM_PROMPT 규칙 9·11 경로)에 한정해 읽어야 함」 을 붙이는 형태. 되돌린 판단의 역사를 남기는 것이 이 리포의 규율임.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 그 문서의 해당 절이 2026-09-10 이후의 변화를 함께 담아, 인용해도 낡은 전제가 전파되지 않는다
<!-- AC:END -->
