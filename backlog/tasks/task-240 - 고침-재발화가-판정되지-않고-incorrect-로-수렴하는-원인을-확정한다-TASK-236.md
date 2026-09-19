---
id: TASK-240
title: '고침: 재발화가 판정되지 않고 incorrect 로 수렴하는 원인을 확정한다 (TASK-236)'
status: Done
assignee: []
created_date: '2026-09-19 07:49'
updated_date: '2026-09-19 08:48'
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
- [x] #1 코치의 턴 종료를 기다리는 관측 수단으로 재현이 성립함
- [x] #2 둘째 pronunciation 프레임이 오지 않는 원인이 앱인지 드라이버인지 확정됨
- [x] #3 원인이 드라이버면 그 사실을 TASK-236 에 적고 앱 수정을 하지 않음
- [x] #4 TASK-236 에 판정과 근거를 적어 이음
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
판정: 원인은 드라이버임(후보 ㉮) — 앱은 정상임. 그래서 AC#3(원인이 앱이면 고침)은 해당 없음이고 AC#4(원인이 드라이버면 앱을 고치지 않음)를 이행했음. 증거는 TASK-236 노트가 가지고, 회차는 tests/agent/runs/2026-09-19-b7/ 임. ⛔ AC#3 을 체크하지 않은 것은 미완이 아니라 조건 불성립임 — AC#4 와 배타이고 둘을 다 체크하면 「앱을 고쳤고 동시에 고치지 않았다」가 됨.

⛔ AC「원인이 앱이면 고쳐서 정확한 재발화가 correct 로 닫힘」을 목록에서 걷었음 — 원인이 드라이버로 판정돼 조건이 성립하지 않음. 체크하면 거짓이고 미체크로 Done 을 두면 G3 게이트가 막으므로 걷는 것이 맞음. 무엇을 계획했는지는 이 노트가 보존함.
<!-- SECTION:NOTES:END -->
