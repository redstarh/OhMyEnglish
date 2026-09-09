---
id: TASK-78
title: '결함/재개: 결정 49 의 사실 전제 둘이 반증됐다 — 앱 프롬프트에서 tool 이 오고 코칭 발화와 동시에 온다'
status: In Progress
assignee: []
created_date: '2026-09-09 16:28'
updated_date: '2026-09-09 22:32'
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
2026-09-10 AC#1·AC#2 완료. 정본 둘: tests/harness/runs/2026-09-10-task78-app-path.md (앱 경로·원인) · 2026-09-10-task78-coaching-implies-tool.md (판별).

⛔ 수치 정정 — 동료 세션이 어긋남을 지적해 발견했다. 내가 「15/15」와 「코칭 4 · tool 5」로 적었고 둘 다 틀렸다. 원인은 회차 수와 tool 이벤트 수를 같은 열에 섞은 것이다. 원자료를 기계로 다시 세었다: 기반 프롬프트 팔은 11회 · 코칭 3회 · tool 이 온 회차 3 · tool 이벤트 4건. 관계는 회차 단위로 센다 → 11/11 회차. target_sound 는 이벤트 4건 전부(동료 2건 합쳐 6건 전부).

⛔ 그리고 더 큰 정정 — 우리가 「앱 프롬프트」라 부른 --app-prompt 는 기반 프롬프트(2,339자)이고 앱이 실제로 보내는 것은 계획·무대가 붙은 4,545자다. 동료 세션이 그 사실을 독립 확인했다(SYSTEM_PROMPT 길이와 import 경로).

AC#1 — 앱 경로 2회(브라우저 레그 · nova 재기동 · 세션 18e64d1d·ad61c8ea): 전사문 둘 다 영어로 복원 · 코칭 0건 · pronunciation_attempts 델타 0. 통제 대조로 원인을 확정했다: 조립 프롬프트 전문을 --prompt-file 로 실어 같은 오디오 3회 → 코칭 0 · toolUse 0 이고 발화가 앱 경로와 거의 글자까지 같다. 변수를 하나만 바꿨다. 계획 블록이 초점을 article_missing_before_noun 등으로, 무대를 주말 계획으로, 힌트 시점을 관사·동사 누락으로 고정한다.

AC#2 — 코칭 여부가 축이다. 문장이 축이라는 앞선 판정은 같은 팔을 셋 더 돌려 반증했다. 코칭 자체가 흔들리는 원인은 미확정이고 후보 셋(샘플링 비결정성 · 규칙 9 의 mild 경계 · TASK-65 의 첫 발화 고정 기전) 중 배제된 것이 없다.

AC#3 미착수 — 워커를 켜지 않았고(H-AT) tool 이 오는 앱 회차를 얻지 못해 종단을 시작할 입력이 없었다.

AC#4 미착수 — 사용자 재결정. ⛔ 단순화의 순서가 바뀌었다: 지금 걷어내면 tool 도 우회로도 0 이 된다. ① 계획이 발음에 자리를 내주게 고침 → ② tool 도착률 재측정 → ③ 기준 넘으면 걷어냄. 동료 세션이 그 순서를 결정 50 에 적었다.

정리: 7개 표가 기준선과 정확히 일치(13|120|4|9|24|15|49) · 보존 세션 여섯 생존 · 백엔드 기준선 복원(pid 58241).
<!-- SECTION:NOTES:END -->
