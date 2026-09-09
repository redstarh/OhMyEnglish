---
id: TASK-78
title: '결함/재개: 결정 49 의 사실 전제 둘이 반증됐다 — 앱 프롬프트에서 tool 이 오고 코칭 발화와 동시에 온다'
status: In Progress
assignee: []
created_date: '2026-09-09 16:28'
updated_date: '2026-09-09 16:37'
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
2026-09-09 AC#2 진행분. 정본은 tests/harness/runs/2026-09-09-task65-session-context.md §4·§4.1 이다.

표본을 넷에서 여덟로 늘렸다. ⛔ 먼저 적은 「4건 중 3건」이 과장이었다 — 그 넷에 p2a→p2k 회차가 둘 다 들어 있었다. 전수 8건에서 toolUse 가 온 것은 3건이다.

갈리는 축이 턴 수가 아니라 문장으로 보인다: p2 문장(업무 보고) 2/2 · p1 문장 1/5. p1m→p1k 의 0 은 반복에서도 0 이었다(간헐 아님). p1a→p1m·p1a→p1k 도 0 이다.

⚠️ 무엇이 정하는지는 미확정이다. 문장이 2종뿐이다. p2 의 치환(f→p·r→l·θ→s 가 finished the report and shared the results 에 걸린다)이 전사문을 실제로 왜곡시키는 것과(5차수 P2(p2m) FAIL 이 그 실측이다) 관련이 있어 보이나 재지 않았다. 문장을 늘리려면 새 픽스처가 필요하고 그것은 이 AC 범위를 넘는다.

⛔ 결정 49 의 두 전제는 반증된 채로 남는다 — 「한 번도 불리지 않는다」는 1건만 있어도 무너지고, 「코칭 발화와 tool 중 하나만 얻는다」도 세 회차 전부 audioOutput 이 0 이 아니라 무너진다. 바뀌는 것은 강도다: 「다중 턴이면 온다」가 아니라 「다중 턴에서 올 수 있다」다.

⛔ AC#1 의 부분 증거를 직접 쿼리해 확인했다 — 그리고 이것이 더 크다. pronunciation_attempts 4행 전부:
  bbfc3908|nova_tool|am_as_i_m|2026-08-31
  bbfc3908|nova_tool|w_as_vw|2026-08-31
  bbfc3908|nova_tool|an_as_a|2026-08-31
  7b43ce56|nova_tool|an_as_a|2026-09-03
두 세션 다 살아 있고 mode='speaking' 이다. 즉 앱 경로가 이미 tool 을 target_sound 와 함께 받은 적이 있고, 그 반례가 DB 에 처음부터 있었다. 다른 세션이 먼저 지목했고 내가 같은 쿼리로 확인했다.
⚠️ 단정하지 않는 것: 그 세션들의 시스템 프롬프트가 지금 것과 같은지는 확인하지 않았다. 규칙 8~11 이 2026-08-27 설계에서 왔으므로 그럴 법하나 build_system_prompt 가 그 뒤 바뀌었을 수 있다.

AC#1 은 체크하지 않는다 — 위 증거는 과거 기록이고 다중 턴 여부도 확인되지 않았다. 신규 관측에는 브라우저 레그와 백엔드 nova 재기동이 필요하다. AC#3 도 미착수다(워커 필요).
<!-- SECTION:NOTES:END -->
