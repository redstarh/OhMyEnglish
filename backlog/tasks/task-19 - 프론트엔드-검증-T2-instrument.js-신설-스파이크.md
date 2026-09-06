---
id: TASK-19
title: '프론트엔드 검증 T2: instrument.js 신설 + 스파이크'
status: Done
assignee: []
created_date: '2026-09-06 00:13'
updated_date: '2026-09-06 03:29'
labels: []
dependencies:
  - TASK-29
ordinal: 19000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
계획서 T2. 계측 스크립트를 만들고 자기검사를 넣는다. 계측이 조용히 퇴화하면 시끄럽게 죽인다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 반환값이 instrumented가 아니면 즉시 ERROR로 끝낸다
- [x] #2 후킹 대상 부재를 일부러 만들어 throw하는지 확인
- [x] #3 createBufferSource를 어느 프로토타입에서 단정해야 하는지 실측 확정
- [x] #4 계측 없이 클릭했을 때의 대조를 실측한다 — sent가 0이면 FAIL이 아니라 BLOCKED로 보고
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
T2 스파이크 완료 — 회차 기록 tests/harness/runs/2026-09-06-t2-instrument-spike.md. 검증 에이전트로 3회차 돌렸다(throw 확인 / 정상 관통 / 무음 대조+타이밍).

실측으로 닫힌 미결 2건: ③ startOwner=AudioBufferSourceNode · createBufferSourceOwner=BaseAudioContext (계획서 예측대로 AudioContext.prototype 에서는 undefined 다) · ④ browser_leg §11-4 의 답은 '쓸 수 없다' — 무음 대조가 원리적으로 0 을 낼 수 없다.

⚠️ ④는 PASS 가 아니다. A1-7 은 측정도 대조도 성립하지 않는다: 스텁 세션이 23ms 에 자기종료해(DB ended_at-started_at=23.001ms) 캡처 프레임 1건(512샘플@16kHz=32ms)이 만들어지기 전에 끝나고, 학습 종료 버튼에 도달하지 못해 end_session 도 0 이다. 무음 대조는 lib/audio.ts 워클렛 process() 에 무음 게이트가 없어 프레임 수·바이트 길이가 유음과 완전히 같다(팀리드가 코드로 직접 확인 — 146 프레임 / 199,728 바이트 동일).

팀리드가 직접 확인한 것 4건 · 확인하지 못한 것(브라우저 관측 전부)은 회차 기록 §5 가 가른다. ⚠️ 팀리드가 DB 수치를 사후 조회로 대조해 '어긋난다'고 오판했다 — teardown 이 걷어간 값이라 사후에는 볼 수 없었고 에이전트의 3열 기록이 옳았다.

드러낸 결함 10건은 TASK-31 이 소유한다(TASK-21 의 선행으로 걸었다). 이미 고친 것: browser_leg P5(로그 pid 대조 — 로그가 종료된 pid 15648 것이고 실행은 41641 이었다) · §8-②(재계산 → baseline 복원. 캡틴의 pronunciation_an_as_a 를 0/NULL 로 덮었다) · §8-③(발음 패턴 보호) · pitfalls H-AB·H-AC.

── 2026-09-06 추가: 외부 감사 2회차 지적을 받아 팀리드가 브라우저로 직접 재현했다 ──
지적: AC#1~#3 의 근거가 에이전트 보고 단독이고 기록 스스로 '확인하지 못했다'고 적었다 — 재현되지 않은 주장 위에 Done 이 올라갔다. 지적이 옳다.

재현 결과(세션을 시작하지 않아 DB 무접촉, 전후 7·92·34·1·1·7 동일 · baseline drift 0):
- ③ 전건 일치. Chrome/152.0.0.0 · createBufferSource 는 AudioContext.prototype 에서 undefined 이고 소유자는 BaseAudioContext · startOwner=AudioBufferSourceNode · start 는 두 프로토타입에 모두 own 이고 stop 은 AudioScheduledSourceNode 에만 있다(§4-3 우려가 stop 에서 실현된다)
- ① 반환값이 문자열 instrumented. Promise 아님
- ② delete WebSocket.prototype.send → 체인 탐색 null → '계측 대상 부재: WebSocket 체인에 send 가 없다' throw → 복원 확인. 에이전트 보고 문구와 축자 일치

⚠️ 재현의 한계: 평가한 것은 instrument.js 의 가드·반환 경로이고 파일 전문이 아니다. 후킹 설치·계수·inject·probeColor 는 여전히 에이전트 보고가 근거다. 회차 기록 §7 이 그 선을 가른다.
<!-- SECTION:NOTES:END -->
