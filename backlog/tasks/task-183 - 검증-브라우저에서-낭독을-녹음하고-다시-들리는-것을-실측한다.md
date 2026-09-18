---
id: TASK-183
title: '검증: 브라우저에서 낭독을 녹음하고 다시 들리는 것을 실측한다'
status: Done
assignee: []
created_date: '2026-09-18 01:40'
updated_date: '2026-09-18 02:03'
labels: []
dependencies:
  - TASK-182
ordinal: 244000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
프런트에 테스트 러너가 없어 화면 판정은 브라우저 관측이 유일하다(handoff ③ 4항). localhost:3000 으로 열고(H-CA) 마이크는 AudioContext → MediaStreamDestination 으로 갈아 끼운다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 낭독 턴을 열고 닫아 shadowing_recording 발화가 새로 1건 늘어난다
- [x] #2 「내 낭독 듣기」 를 눌러 재생이 시작되는 것을 관측한다
- [x] #3 응답 Content-Type 이 audio/wav 이고 첫 4바이트가 RIFF 다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 실물 Nova 검증 2026-09-18 — 성공했음

세운 스택은 TASK-178 과 같음: `:8014` 에 `WORKER_ENABLED=false VOICE_ADAPTER=nova` · `.env.local` 의
`NEXT_PUBLIC_API_BASE` 만 그쪽으로 돌리고 프런트 재기동(검증 뒤 되돌렸음).

### 진입 경로가 TASK-178 과 달랐음 — 기록해 둘 함정

⛔ `?mode=shadowing&item=...` 로 열면 **페이지 로드 즉시** `getUserMedia` 가 불려 마이크 대체를
심을 틈이 없음. 권한 대화를 승인해도 실제 장치가 없어 「마이크 권한을 요청하는 중」에서 멈춤.
⇒ **쿼리 없이 `/` 로 열어 대체를 먼저 심고, 화면의 「쉐도잉」 버튼을 누름.** 같은 문서라 대체가 살아남음.

### 관측 결과

| 관측 | 값 |
|---|---|
| 세션 | `11a0098e` · `status=active` → 「학습 종료」로 `completed` · `ended_at` 채워짐 |
| 마이크 대체 | `__gumCalled=1` (AudioContext → MediaStreamDestination 220Hz) |
| 녹음 전 화면 | 버튼 셋 — 「클립 듣기」·「따라 읽기」·「학습 종료」. **「내 낭독 듣기」 없음** |
| 낭독 중 | 「클립 듣기」 `disabled=true` · 「읽기 끝」 토글 · `role=status` 안내가 새 문구 |
| 낭독 닫은 뒤 | **「내 낭독 듣기」 가 나타남** (서버 `shadowing_recording` 프레임을 받은 뒤) |
| 재생 | `duration=23.136` · `playing=true` · `error=null` ⇒ **WAV 헤더가 읽혔음** |
| 응답 | `HTTP 200` · `content-type: audio/wav` · 첫 바이트 `RIFF$L..WAVEfmt ` · 740,396 B |
| 디스크 원본 | 헤더 없는 PCM(`3782 a480…`) · 740,352 B ⇒ **차이가 정확히 44바이트(WAV 헤더)** |
| 발화 | `shadowing_recording` **2건** (앞 1건 + 이번 1건) |
| 두 소리 | 낭독 재생 중 「클립 듣기」를 누르니 낭독 `paused=true·currentTime=0` · 클립 `paused=false·currentTime=5.55` |
| 재생 끝 | 23.136초 뒤 라벨이 「내 낭독 듣기」로 되돌아감 (`ended` → `stop()`) |

### 판별력을 어떻게 뒀는가

⛔ **버튼 라벨만 보면 「디코드 실패」와 「재생 중」이 갈리지 않음** — `error` 가 나도 `stop()` 이 라벨을
되돌리므로 같은 화면이 됨. 그래서 `Audio` 생성자를 감싸 `loadedmetadata`·`playing`·`error` 를 따로
기록했음. raw PCM 이면 `duration=null`·`error` 가 나왔을 자리에 `23.136`·`null` 이 나왔음.
「두 소리가 겹치지 않는다」도 라벨로는 못 갈려서 **요소를 들고 `paused`·`currentTime` 을 읽었음.**

### 함께 관측한 것 — TASK-178 의 낭독 파일이 사라져 있었음

`assets/audio/` 가 비어 있고(리포 전체 `.pcm` 0건) DB `audio_url` 포인터만 남아 있었음 ⇒ 조회가 404.
설계가 정상으로 인정하는 「고아 포인터」 상태임(§4.5 의 ②). `assets/audio` mtime 이 **09-18 08:14** 로
이 세션 시작 전이라 **내 변경과 무관함.** ⛔ **원인은 확정하지 않음** — 워커 스윕은 `WORKER_ENABLED=false`
라 돌지 않았어야 하고, 지운 주체를 가릴 증거가 없음.

### 되돌린 것

`.env.local` → `:8002` · 프런트 재기동(**PID 52032**) · `:8014` 종료.
확인: `frontend=200` · 백엔드 `:8002` LISTEN(**PID 29399**) · `:8014` 응답 없음.
<!-- SECTION:NOTES:END -->
