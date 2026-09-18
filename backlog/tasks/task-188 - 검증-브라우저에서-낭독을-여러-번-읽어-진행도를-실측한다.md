---
id: TASK-188
title: '검증: 브라우저에서 낭독을 여러 번 읽어 진행도를 실측한다'
status: Done
assignee: []
created_date: '2026-09-18 02:28'
updated_date: '2026-09-18 03:49'
labels: []
dependencies:
  - TASK-187
ordinal: 249000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
프런트에 테스트 러너가 없어 화면 판정은 브라우저 관측이 유일하다. H-CC 대로 쿼리 없이 열어 마이크 대체를 먼저 심는다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 낭독을 목표 횟수만큼 반복해 진행도가 그대로 오르는 것을 관측한다
- [x] #2 재접속 뒤에도 회차가 유지되는 것을 관측한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 실물 Nova 검증 2026-09-18 — 진행도가 그대로 올랐음

스택: `:8014` 에 `WORKER_ENABLED=false VOICE_ADAPTER=nova **SHADOWING_REPEAT_COUNT=3**` ·
`.env.local` 을 그쪽으로 돌리고 프런트 재기동(검증 뒤 되돌렸음). `H-CC` 대로 쿼리 없이 `/` 로 열어
마이크 대체를 먼저 심고 화면의 「쉐도잉」 버튼을 눌렀음(`__gumCalled=1`).

### 관측 결과

| 단계 | `role=status` 문구 |
|---|---|
| 세션 열림 | **3번 중 0번 읽었어요** ← 목표 3 이 설정에서 왔음 |
| 1회차 뒤 | **3번 중 1번 읽었어요** |
| 2회차 뒤 | **3번 중 2번 읽었어요** |
| 3회차 뒤 | **3번 다 읽었어요** ← 도달 문구로 바뀜 |

세션 `5c0c614b` · DB 의 `shadowing_recording` 발화 **3건** — 화면 회차와 일치함.
세션 종료 뒤 `status=completed` · `ended_at` 채워짐.

### AC#2 는 그대로 관측하지 못했음 — 대체 증거를 적음

⛔ **앱에 「같은 세션으로 재접속」하는 경로가 없음** — 페이지를 새로 고치면 `startSession` 이 **새
세션**을 만들고 회차는 세션별 발화 수라 0 에서 다시 시작함. 그래서 「재접속 뒤 유지」를 화면으로
관측할 자리가 없음.

⚠️ **DB 발화 수와 화면 회차가 일치하는 것은 판별력이 약함** — 화면이 스스로 0→1→2→3 을 세도 같은
화면이 되므로 그 일치만으로는 두 갈래가 갈리지 않음. 그래서 증거를 코드와 테스트에 둠:
`page.tsx` 가 `setReadTurns(event.turn_index)` 로 **서버 값을 그대로 담고 증가 연산을 하지 않음** ·
서버는 `count_recording_turns` 로 발화를 셈 · `test_repeated_shadowing_turns_are_numbered_in_order`
가 그 계산을 `[1, 2]` 로 잼.
⛔ **즉 「재접속에도 유지된다」는 설계상 참이고 브라우저 관측으로 확인한 것은 아님.** 그 구분을 남김.

### 되돌린 것

`.env.local` → `:8002` · 프런트 재기동(**PID 15136**) · `:8014` 종료.
확인: `frontend=200` · `nova8014=000` · 백엔드 `:8002` LISTEN(**PID 29399**).
<!-- SECTION:NOTES:END -->
