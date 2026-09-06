---
id: TASK-20
title: '프론트엔드 검증 T5a: CDP 프레임 주입 스파이크 (3종 + 창 확인)'
status: Done
assignee: []
created_date: '2026-09-06 00:14'
updated_date: '2026-09-06 04:00'
labels: []
dependencies:
  - TASK-19
ordinal: 20000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
계획서 T5a. 범위가 3종 + 창 확인으로 넓어졌다(지적 M-c·N-3 반영). C2가 partial+final 둘을 요구하므로 그 둘이 되는지 모르면 T3의 전제가 닫히지 않는다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 pronunciation 프레임 1건 주입 시 배지가 뜨는지
- [x] #2 partial 주입 시 접두 단락이 0에서 1로 늘어나는지
- [x] #3 final 주입 시 두 갈래를 각각 확인 — 첫 final은 새 줄이 되고, 같은 화자 연속 주입은 줄 수가 늘지 않는다
- [x] #4 주입 창이 실제로 먹는지 확정 — 무응답 대역 모드에서 연결 상한 10초 안에 측정이 끝나는가
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
T5a 완료 — 회차 기록 tests/harness/runs/2026-09-06-t5a-injection-spike.md. AC 4건 전건 PASS, 2회 독립 회차 일치.

닫힌 미결 4건(browser_leg §11): 5(CDP 주입이 되는가 — 된다. 3종 전부) · 6(주입 창 — 256ms = 창의 2.6%, 창 실측 10,023ms 로 CONNECT_TIMEOUT=10.0 과 일치) · 2(start 소유자 = AudioBufferSourceNode, createBufferSource = BaseAudioContext) · 3(AudioContext 는 제스처 안에서 생성하면 running. audio 계수 0 의 원인은 suspend 가 아니라 T2 의 23ms 자기종료였다). C5 폐기와 §7-6 직렬 큐 대안 둘 다 불필요해졌다.

inject() 의 recv 무오염이 설계 주장에서 관측으로 승격됐다(8프레임 주입 후 recv 불변, injected 0→8).

⚠️ finalLines 는 §11-7 의 답으로 채택하지 않는다. 이 회차는 여유가 9.7초일 때 동작한 것만 보였고, 에이전트가 실제 session_ended 경로를 밟지 않았으며 settle 을 넣어 문제 조건을 구조적으로 회피했다. T2 의 결함은 살아 있고 TASK-31 이 소유한다.

⚠️ 증거의 약점: 자동 저장 아티팩트로 AC ①②③을 재확인할 수 없다(캡처 시점이 창 밖이다 — D-1). 재현 경로가 payload 재실행뿐이다. §10 에 outerHTML 반환 규약을 박았고 다음 회차부터 적용한다.

browser_leg.md 결함 8건 중 7건을 반영했다(D-1 증거 모델 · D-3 한 eval · D-4 대기값 · D-5 §8-⑤ 예외 · D-6 console 스텁 · D-7 active 후 계수 · D-8 언마운트 근거 정정). D-2(§3 cwd 어긋남)는 TASK-31 로 넘겼다. 덤으로 P9 행이 표 밖에 떨어져 있던 것을 제자리로 넣었다 — 프리플라이트는 9건이다.

팀리드 직접 확인 7건: sha256 15289B 일치 · CONNECT_TIMEOUT 실재 · 임시서버 정리 · DB 7·34·92·7·1·1 drift 0 · eval 이 promise 를 await 한다(254ms — instrument.js docstring 의 거짓 근거를 정정했다) · console.txt 58B 스텁 · failed 에서 컨테이너 언마운트.
<!-- SECTION:NOTES:END -->
