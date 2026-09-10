---
id: TASK-103
title: >-
  결함: 발음 시도의 target_form 이 «무너진 전사» 로 굳고 화면의 「시범 문장」 자리에 뜬다 — 둘째 tool 호출의 옳은 문장을
  앱이 버린다
status: To Do
assignee: []
created_date: '2026-09-10 23:03'
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
- [ ] #1 판정 호출이 옳은 target_form 을 가져오면 그것으로 갱신할지 판정하고 근거를 적는다 — 지금 UPDATE 가 그 필드를 빼고 있다. ⛔ 새 추상화를 만들지 않는다
- [ ] #2 화면의 「시범 문장」 자리에 오발음이 뜨지 않는 것을 앱 경로에서 확인한다 — 결과 화면을 직접 열어 본다
- [ ] #3 두 호출이 모두 pending 으로 오는 경우 열린 행이 둘 생기는 것과 resolve_dangling 의 수렴을 함께 확인한다
- [ ] #4 ⛔ 표시를 고치는 것으로 저장을 고쳤다고 하지 않는다 — 복습 시계와 계획 프롬프트가 같은 값을 읽는다
<!-- AC:END -->
