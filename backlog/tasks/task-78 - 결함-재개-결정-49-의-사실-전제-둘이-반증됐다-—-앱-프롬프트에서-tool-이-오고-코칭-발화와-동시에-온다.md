---
id: TASK-78
title: '결함/재개: 결정 49 의 사실 전제 둘이 반증됐다 — 앱 프롬프트에서 tool 이 오고 코칭 발화와 동시에 온다'
status: In Progress
assignee: []
created_date: '2026-09-09 16:28'
updated_date: '2026-09-09 22:19'
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
- [x] #1 앱 경로에서 다중 턴으로 tool 이 오는지 확인한다 — 스파이크 직결에서만 관측했다. 브라우저 레그가 필요하고 백엔드를 VOICE_ADAPTER=nova 로 재기동해야 한다
- [x] #2 다중 턴에서 tool 이 오는 조건과 오지 않는 조건을 가른다 — 4건 중 1건이 0이었다. 표본을 늘려 발음 오류의 심각도·순서·턴 수 중 무엇이 정하는지 좁힌다
- [ ] #3 target_sound 가 실린 tool 이 실제로 pronunciation_attempts 행과 error_patterns 패턴과 next_review_at 을 만드는지 종단으로 확인한다 — 재료가 있다는 것과 복습 시계가 돈다는 것은 다르다
- [ ] #4 결과를 사용자에게 올려 결정 49 를 유지할지 뒤집을지 받는다 — 제품 요구사항 판단이라 팀리드가 정하지 않는다. ⛔ 받기 전에 toolChoice 강제를 제품 경로에 넣지 않는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-10 AC#1 완료. 정본은 tests/harness/runs/2026-09-10-task78-app-path.md 다. 판별 회차는 2026-09-10-task78-coaching-implies-tool.md, 표본 정정은 2026-09-09-task65-session-context.md §4.1 이 소유한다.

앱 경로 실측: 백엔드를 VOICE_ADAPTER=nova 로 재기동해 브라우저 레그로 2회 돌렸다(세션 18e64d1d·ad61c8ea). 두 회차 모두 전사문이 영어로 복원되고 발음 코칭 0건이며 pronunciation_attempts 델타 0 이다. agent 가 곧바로 주말 계획으로 넘어갔다.

⛔ 원인을 통제 대조로 확정했다 — 계획 블록이다. 지금까지 우리가 「앱 프롬프트」라 부른 --app-prompt 는 기반 프롬프트만 싣는 팔이고, 앱이 실제로 보내는 것은 계획·무대가 붙은 4,545자다. factory.py:63 과 같은 재료로 조립해(known_sounds=['an_as_a'] · plan 있음 · questions 5 · scenario 있음) --prompt-file 로 실어 같은 오디오로 3회 돌리자 코칭 0회·toolUse 0 이었고 발화가 앱 경로와 거의 글자까지 같았다. 변수를 하나만 바꿨고 결과가 뒤집혔다.

계획 블록이 초점을 article_missing_before_noun 과 business_expression_verb_noun_collocation 로, 무대를 주말 계획으로, 힌트 시점을 관사·동사 누락으로 고정한다. 규칙 9 가 이미 Grammar first 인데 계획이 그 방향을 한 번 더 못박는다.

⛔ 단순화 판단에 미치는 것: tool 배선은 문제가 아니다(코칭 ⟺ tool 15/15 · target_sound 5/5 그대로 참). 그러나 지금 앱 설정에서는 코칭 자체가 일어나지 않으므로, 우회로를 걷어내고 tool 에만 의존하면 그 신호를 앱 자신의 프롬프트가 막는다. 전제가 하나 늘었다 — 계획이 발음에 자리를 내줘야 한다. 후보 셋을 회차 기록 §5 에 적었고 어느 것도 시험하지 않았다.

⚠️ AC#3(복습 시계 종단)은 못 닫았다 — 워커를 켜지 않았다(H-AT). 그리고 tool 이 오는 회차를 앱 경로에서 얻지 못했으므로 종단을 시작할 입력 자체가 없었다.

정리: 7개 표가 기준선과 정확히 일치한다(13|120|4|9|24|15|49). 보존 세션 여섯 전건 생존. 백엔드를 기준선(stub_unresponsive · 워커 꺼짐 · pid 58241)으로 복원했다.
<!-- SECTION:NOTES:END -->
