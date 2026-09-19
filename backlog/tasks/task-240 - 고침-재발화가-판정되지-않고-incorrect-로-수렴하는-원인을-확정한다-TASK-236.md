---
id: TASK-240
title: '고침: 재발화가 판정되지 않고 incorrect 로 수렴하는 원인을 확정한다 (TASK-236)'
status: To Do
assignee: []
created_date: '2026-09-19 07:49'
labels: []
dependencies: []
ordinal: 304000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
심각도 HIGH · 앱 결함이나 ⛔ 원인 미확정 · 뿌리 그룹 A(발음·낭독). 결함 정본은 TASK-236 임. 현상: 학습자가 정확히 따라 말했는데 pronunciation_attempts 가 outcome=incorrect · spoken_form=null 로 남고 resolved_at 이 세션 종료 시각과 같음(resolve_dangling 의 수렴). 둘째 pronunciation 프레임이 오지 않았음. ⛔ 관측 수단의 한계가 확인됐음 — ws_session.py 는 「보내면서 받지 않는다」가 계약이라 코치의 턴이 끝나기를 기다리지 않고 모든 프레임의 t 가 뭉쳐 도착 시각을 잃음. ⇒ 고치기 전에 «코치의 턴을 기다리는» 드라이버로 재현해 원인을 먼저 가름. 실물 Nova 호출이 필요함.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 코치의 턴 종료를 기다리는 관측 수단으로 재현이 성립함
- [ ] #2 둘째 pronunciation 프레임이 오지 않는 원인이 앱인지 드라이버인지 확정됨
- [ ] #3 원인이 앱이면 고쳐서 정확한 재발화가 correct 로 닫힘
- [ ] #4 원인이 드라이버면 그 사실을 TASK-236 에 적고 앱 수정을 하지 않음
- [ ] #5 TASK-236 에 판정과 근거를 적어 이음
<!-- AC:END -->
