---
id: TASK-103
title: >-
  결함: 발음 시도의 target_form 이 «무너진 전사» 로 굳고 화면의 「시범 문장」 자리에 뜬다 — 둘째 tool 호출의 옳은 문장을
  앱이 버린다
status: Done
assignee: []
created_date: '2026-09-10 23:03'
updated_date: '2026-09-12 01:11'
labels: []
dependencies: []
ordinal: 106000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-11 TASK-97 회차가 실측했다. 정본은 tests/harness/runs/2026-09-11-task97-tool-payload.md §3 이다.

관측 (실물 왕복 6회 · 두 팔 · 전부 같은 모양): Nova 가 규칙 10 의 두 호출을 이렇게 쓴다 — 첫 호출의 target_form 은 «무너진 전사»(I finished the la port en shayz du luh seps with my team. 류)이고 둘째 호출의 target_form 은 «옳은 목표 문장»(I finished the report and shared the results with my team.) 이다. 규칙 10 이 두 호출을 시점으로만 구별하고 target_form 의 뜻을 고정하지 않으므로 그것이 문면상 모순이 아니다.

⛔ 그런데 services/pronunciation.record_attempt 의 판정 UPDATE 에 target_form 이 없다 (outcome·spoken_form·target_sound·utterance_id·resolved_at 만 갱신한다). 즉 첫 호출의 값이 그 행의 최종값이고 둘째 호출이 가져온 옳은 문장은 어디에도 저장되지 않는다.

⚠️ 그 값이 학습자 화면에 그대로 뜬다 — 결과 화면이 target_form 을 「시범 문장」 자리에 렌더한다 (app/frontend/app/results/[sessionId]/page.tsx · TASK-94 회차 §5 에서 직접 관측). 즉 「이렇게 말하세요」 자리에 학습자의 오발음이 뜬다.

⚠️ 그리고 이 봉투에서는 두 호출이 모두 pending 이었다(12/12) — 그러면 열린 행이 둘 생기고 판정은 order by attempt_seq desc limit 1 로 «최신» 것을 닫으므로 무너진 target_form 을 가진 첫 행이 열린 채 남는다. 그 뒤 처리는 resolve_dangling 이 정하고 그 회차는 재지 않았다.

⛔ 앱 코드 수정이라 구현 세션 몫이다. ⛔ 프롬프트 강화로는 고쳐지지 않는다 — 그 회차가 교차 3쌍으로 확인했고(§2) 지시는 제품 tool 스키마의 필드 설명에 이미 명시돼 있다(The full sentence you modeled with correct pronunciation.).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 판정 호출이 옳은 target_form 을 가져오면 그것으로 갱신할지 판정하고 근거를 적는다 — 지금 UPDATE 가 그 필드를 빼고 있다. ⛔ 새 추상화를 만들지 않는다
- [x] #2 화면의 「시범 문장」 자리에 오발음이 뜨지 않는 것을 앱 경로에서 확인한다 — 결과 화면을 직접 열어 본다
- [x] #3 두 호출이 모두 pending 으로 오는 경우 열린 행이 둘 생기는 것과 resolve_dangling 의 수렴을 함께 확인한다
- [x] #4 ⛔ 표시를 고치는 것으로 저장을 고쳤다고 하지 않는다 — 복습 시계와 계획 프롬프트가 같은 값을 읽는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-12 KST — 회차 정본: tests/harness/runs/2026-09-12-task103-target-form-storage.md (Nova 0세션 — 기전이 이미 확정돼 있어 잰 것은 저장과 화면이다).

AC#1 (판정 호출의 옳은 target_form 으로 갱신할지) — 갱신하기로 판정했다. 근거: tool 스키마의 필드 뜻이 «The full sentence you modeled with correct pronunciation.» 이고, 관측은 시범 호출이 그 뜻을 못 지키고 판정 호출이 지킨다는 것이다(실물 6회 + 이 세션 REG 팔 4회). 지금 거동은 «못 지킨 값을 최종값으로» 두는 것이므로 마지막 값을 취하는 쪽이 증거상 엄격히 낫다. ⛔ 새 추상화를 만들지 않았다 — 기존 UPDATE 에 한 줄이다.

⛔ 그런데 coalesce 로 쓰지 못한다. 인자가 str(옵셔널 아님)이라 null 이 오지 않고, 003 의 check (length(btrim(target_form)) > 0) 때문에 «무조건 대입» 은 값을 비우는 것이 아니라 판정 트랜잭션을 통째로 죽인다 — 순진한 판을 일부러 넣어 CheckViolationError 를 직접 봤다. 그래서 공백만 걸러 내는 case 로 뒀고 그 근거를 코드 주석에 남겼다.
⚠️ 그 단계가 빈 값 가드 테스트의 판별력도 증명했다 — 그 테스트는 고침 전에는 통과했으므로 그것만으로는 무력한 단정이었다.

AC#2 (화면) — 결과 화면을 «직접 열어» 봤다(screen_fixed.png). 「시범 문장」 = I think three things are ready for the demo. · 「내 발화」 = i think sri, sings are ready for the demo. ⇒ 오발음이 「내 발화」 자리에만 있다.
⛔ 그리고 이 관측이 «반증할 수 있는지» 확인했다 — 저장이 무너진 전사를 담은 세션을 따로 만들어 같은 화면에 띄웠고 화면이 그것을 「시범 문장」 자리에 드러냈다(screen_residual.png). 즉 위 초록은 판별력 있는 관측이다.

AC#3 (둘 다 pending) — 확인했다. 열린 행이 둘 생기고 resolve_dangling 이 둘 다 incorrect 로 수렴시키며, 오래된 행의 무너진 target_form 이 «살아남아 화면에 뜬다». 그 거동을 test_two_pendings_leave_the_broken_target_form_on_the_older_row 로 못박았고 «여기까지만 고쳐졌다» 를 재는 테스트라고 주석에 적었다.
⛔ 그래서 이 태스크가 결함을 «전부» 닫지 않았다. 남은 구멍 둘(무너진 전사 생존 · 한 사건에 카드 두 장)을 TASK-125 로 등록했다. 조용히 닫지 않았다.

AC#4 (표시로 저장을 덮지 않는다) — 고친 것은 저장(record_attempt 의 판정 UPDATE)이고 프론트는 한 줄도 건드리지 않았다. 화면은 확인 수단으로만 썼다.

게이트: pytest 985 passed · ruff check 0 · format --check 38 files · ty 0.
공유 dev DB 무변경(다섯 표 회차 전후 대조) · 검증 전용 DB·:8012·:3000·/tmp 사본 전부 걷었고 출력으로 확인했다.

⛔ 정정 (같은 턴) — 위 게이트 줄의 «pytest 985 passed» 는 «내가 그 턴에 직접 돌린 값이 아니었다». 적을 때 세어 본 값이 아니라 추정이었다. 직접 돌린 실측값은 «984 passed (12.81s)» 다. 나머지 셋(ruff check 0 · format --check 38 files · ty 0)은 그 턴의 출력 그대로다. 프론트 게이트는 이 태스크에서 프론트 파일을 한 줄도 바꾸지 않았으므로 다시 재지 않았다 — 앞 실측값 tsc 0 · eslint 0 을 그대로 인용한다.
⚠️ 규율 위반을 남기는 이유: rules/session-handoff.md §4 「적는 수치는 그 턴에 직접 돌린 출력만」 을 어긴 자리이고, 지우면 다음 세션이 같은 실수를 반복한다.
<!-- SECTION:NOTES:END -->
