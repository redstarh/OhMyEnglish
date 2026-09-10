---
id: TASK-79
title: '결함: no_utterances 재확인 상한이 워커 지연을 못 버틴다 — 회복 전에 폴링이 끝남'
status: In Progress
assignee: []
created_date: '2026-09-09 22:55'
updated_date: '2026-09-10 00:29'
labels: []
dependencies: []
ordinal: 82000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-10 TASK-70 재리뷰가 P1 로 지적했음. 근거: app/frontend/app/results/[sessionId]/page.tsx 의 NO_UTTERANCES_RECHECKS = 3.

TASK-77 이 「분석 대상 없음」을 상한 안에서 다시 보게 고쳤음. 그 상한이 3회 × 2초 = 약 6초임. 리뷰 지적: 종료 flush 가 실패한 동안 **단일 워커가 다른 Claude 작업을 처리하면 스윕이 6초를 넘게 지연될 수 있음.** 그러면 네 번째 판독에서 폴링이 멈추고, 이후 스윕과 분석이 끝나도 화면이 교정을 영구히 표시하지 않음.

⛔ 지적이 맞음. TASK-77 이 그 값을 「설계 발명값 — 스윕이 언제 도는지 보장하는 계약이 없다」고 주석에 표시했는데, 계약이 없으면 **어떤 상수도 맞을 수 없음**. 즉 상수를 키우는 것으로는 닫히지 않음.

⚠️ 리뷰가 함께 지적한 것: 지금 계측은 재확인 횟수 변경만 잡고 **지연 시나리오는 잡지 못함.** 상한을 늘려도 그 계측은 여전히 PASS 를 냄.

⛔ 해결 방향을 발명하지 않음 — 선택지가 여럿임: ① 워커가 스윕으로 job 을 건 뒤 그 사실을 결과 API 가 드러내 화면이 종단 판정을 바꿀 근거를 갖게 함(계약을 만드는 쪽) ② 결과 API 가 「아직 회복 대상일 수 있음」을 상태로 구별해 R2 에 자리를 줌 ③ 상한을 시간이 아니라 「스윕이 최소 한 번 돌았음」에 걸음.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 상수 대신 계약으로 닫는다 — 「스윕이 돌았다」를 화면이 알 수 있는 근거를 만든다
- [ ] #2 지연 시나리오를 계측이 잡게 한다 — 스윕을 늦춰도 화면이 교정을 놓치지 않는 것을 관측한다
- [x] #3 다른 종단 상태의 즉시 정지를 깨지 않는다 (TASK-56·TASK-77 의 음성 대조를 유지한다)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-10 구현 — 상수를 없애고 응답 필드로 닫았다.

무엇을 했는가: 결과 API 응답에 awaiting_analysis(bool)를 더했다. 분석 대상 발화(speaker=user · utterance_type=learning)가 있는데 analyze_utterance job 이 0건이면 참이다. 프론트는 NO_UTTERANCES_RECHECKS 상수를 없애고 그 값으로 폴링 여부를 정한다.

⛔ AC#1 의 문면과 다른 점을 밝힌다. AC 는 「스윕이 돌았다」를 화면이 알 근거를 만들라고 했는데 나는 「걸릴 대상이 남아 있는가」를 근거로 썼다. 문면을 따르지 않은 이유는 다른 세션이 코드로 확인해 넘긴 사실 둘이다. ⑴ 워커는 큐가 빌 때만 스윕을 부른다(analysis_worker 의 if job is None 블록) — 즉 분석이 밀리는 동안에는 스윕이 돌지 않으므로 「스윕이 돌았다」가 이 태스크가 다루는 지연 시나리오에서 영구히 거짓일 수 있다. ⑵ analysis_jobs 에 출처를 구별하는 컬럼이 없어(직접 확인) 「스윕이 걸었다」와 「정상 경로가 걸었다」를 가릴 값이 없다 — 그 방향은 마이그레이션이 선행된다. AC#1 의 핵심(상수 대신 계약)은 충족했고 계약의 재료만 바꿨다.

⛔ 처음 고른 안을 버렸다. no_utterances 를 「발화 0건」으로 좁히고 발화가 있는데 job 이 0건이면 analyzing 을 내려 했는데, 직접 센 결과 보존 세션 d127dece 가 발화 6 · user 3 · job 0 이었다 — 그 표본이 바로 flush 실패 재현본이고, 그 안을 쓰면 그 세션 status 가 바뀌어 「분석 대상 없음」 표본이 리포에서 사라진다(보존 세션 중 발화 0건은 76d9ef31 하나이고 그것은 failed 라 규칙 1 이 먼저 잡는다). 그래서 status 를 건드리지 않고 키만 더하는 쪽으로 바꿨다.

AC#3 근거: 변경은 no_utterances 분기 하나이고 TERMINAL_STATUSES 판정과 다른 네 상태 처리는 그대로다. 그리고 발화가 0건인 세션은 처음부터 거짓이라 첫 판독에 멈춘다 — 이전 판(3회 재확인)보다 오히려 빠르다.

게이트: pytest 892 passed · ruff check exit 0 · format 34 files already formatted · ty check 통과 · 게이트 밖 ruff 0건 · format 100 files · 프론트 tsc exit 0 · eslint exit 0.

⚠️ AC#2 를 열어 둔다. 프론트에 단위 테스트 도구가 없다(package.json 에 test 스크립트가 없음) — TASK-77 의 계측도 브라우저 레그였다. 그래서 지연 시나리오 계측은 브라우저 레그가 필요하고 :8002 를 다른 세션이 쓰는 동안에는 착수하지 않는다.
<!-- SECTION:NOTES:END -->
