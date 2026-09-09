---
id: TASK-78
title: '결함/재개: 결정 49 의 사실 전제 둘이 반증됐다 — 앱 프롬프트에서 tool 이 오고 코칭 발화와 동시에 온다'
status: In Progress
assignee: []
created_date: '2026-09-09 16:28'
updated_date: '2026-09-09 22:03'
labels: []
dependencies: []
ordinal: 81000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-65 회차가 찾았다. 정본은 tests/harness/runs/2026-09-09-task65-session-context.md §4 다. 결정 49 는 ① 「앱 프롬프트로는 report_pronunciation_coaching 이 한 번도 불리지 않는다」 ② 「지금 구조에서는 턴마다 코칭 발화와 tool 호출 중 하나만 얻는다」를 근거로 toolChoice 강제를 기각하고 발음 판정을 보조 신호로 축소했다. 그 대가로 「복습 시계 도달 불가」를 받아들였다. ⛔ 둘 다 반증됐다. 앱 프롬프트(--app-prompt)로 toolChoice 강제 없이 다중 턴 세션을 돌리면 toolUse 가 오고(4건 중 3건) audioOutput 이 118·174·203 으로 코칭 발화가 함께 온다. payload 에 target_sound 가 실린다(th_as_t · th_as_s · sh_sound) — 복습 SQL 의 게이트를 통과할 재료다. 규칙 9 의 name the sound 까지 이행한 회차가 있다(Focus on the sh sound at the start). ⛔ 빠진 변수는 다중 턴 세션이다 — TASK-67 의 팔 열 개가 전부 단일 발화였고 앱은 다중 턴으로 돈다. ⚠️ 4건 중 1건(p1m→p1k)은 0이었고 그 이유는 미확정이다. 그리고 앱 경로(브라우저 캡처 → 게이트웨이)에서도 같은지는 확인하지 않았다 — 전부 스파이크 직결이다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 앱 경로에서 다중 턴으로 tool 이 오는지 확인한다 — 스파이크 직결에서만 관측했다. 브라우저 레그가 필요하고 백엔드를 VOICE_ADAPTER=nova 로 재기동해야 한다
- [x] #2 다중 턴에서 tool 이 오는 조건과 오지 않는 조건을 가른다 — 4건 중 1건이 0이었다. 표본을 늘려 발음 오류의 심각도·순서·턴 수 중 무엇이 정하는지 좁힌다
- [ ] #3 target_sound 가 실린 tool 이 실제로 pronunciation_attempts 행과 error_patterns 패턴과 next_review_at 을 만드는지 종단으로 확인한다 — 재료가 있다는 것과 복습 시계가 돈다는 것은 다르다
- [ ] #4 결과를 사용자에게 올려 결정 49 를 유지할지 뒤집을지 받는다 — 제품 요구사항 판단이라 팀리드가 정하지 않는다. ⛔ 받기 전에 toolChoice 강제를 제품 경로에 넣지 않는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-10 판별분. 정본은 tests/harness/runs/2026-09-10-task78-coaching-implies-tool.md 다. 앞선 표본 정정은 2026-09-09-task65-session-context.md §4.1 이 소유한다.

⛔ 판별 결과: 코칭 ⟺ tool 이 15회 전부 성립한다. 코칭한 회차는 전부 toolUse 가 왔고 코칭하지 않은 회차는 전부 오지 않았다. 반대 방향 사례 0건이다. tool 이 온 회차는 전부 target_sound 를 실었다(동료 세션 2회 합쳐 5/5).

즉 문제가 tool 배선이 아니다. 흔들리는 것은 Nova 가 발음을 다룰지 판단하는 것이고, 같은 바이트·같은 프롬프트에서 갈렸다 — p2a→p2k 다섯 회차 중 둘은 「I heard you say shared with a slight accent … Focus on the sh sound」였고 셋은 「Thank you for repeating. Your sentence is very clear.」였다.

사용자 물음(제대로 보내주는지 확인되면 우회로를 걷어내고 단순화)에 대한 답: tool 은 제대로 보낸다. 걷어낼 근거가 된다. 그리고 걷어내도 잃는 것이 없다 — 보조 신호는 여태 0행이고 TASK-65 가 그 이유를 확정했다(세션 첫 발화가 ASR 언어를 고정하므로 첫 마디부터 심하게 틀려야 한글 전사가 나온다).
⛔ 대가는 숨기지 않는다: 판정 빈도가 「Nova 가 그 턴에 코칭하기로 하는가」에 걸리고 그것이 같은 입력에서도 갈린다. 놓침이 있다. 다만 그 놓침은 우회로가 메워 주던 것이 아니다.

⛔ AC#2 를 다시 좁혔다 — 앞서 「문장이 축으로 보인다」고 적었으나 p2a→p2k 를 셋 더 돌리자 그 팔에서도 0 이 나왔다. 문장은 축이 아니고(또는 유일한 축이 아니고) 축은 「코칭 여부」다.

⚠️ 원인 미확정 후보 셋: 샘플링 비결정성(temperature 0.7 고정) · 규칙 9 의 never for a mild accent 판단이 경계에 걸림 · TASK-65 의 첫 발화 고정 기전이 발음 판단에도 걸림. 어느 것도 배제하지 못했다.

⛔ p2a+p2k 를 더 돌리는 것으로는 닫히지 않는다. 남은 걸음은 판별이고 셋을 회차 기록 §5 에 적었다. AC#1(앱 경로)을 먼저 하는 것을 권한다 — 나머지가 무엇을 얻어도 앱 경로에서 재현되지 않으면 쓸 수 없다.
<!-- SECTION:NOTES:END -->
