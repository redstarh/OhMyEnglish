---
id: TASK-81.1
title: '하네스: p_app_path.py 가 픽스처 둘을 순서대로 흘리게 확장한다 (TASK-81 AC#4 의 전건)'
status: Done
assignee: []
created_date: '2026-09-14 15:24'
updated_date: '2026-09-14 15:32'
labels: []
dependencies: []
parent_task_id: TASK-81
ordinal: 170000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
회차 2026-09-15 (tests/harness/runs/2026-09-15-task81-app-leg) 가 이것을 요구했다. 드라이버가 픽스처 «하나»만 첫 발화로 흘려 왕복이 1회뿐이고, 같은 계획·같은 오디오의 WS 레그(TASK-129 회차)에서 코칭이 난 자리는 코치의 둘째 턴이었다. 즉 브라우저 레그가 코칭을 잴 조건 자체를 못 만든다. 사용자가 2026-09-15 에 드라이버 확장을 승인했다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 픽스처 둘을 쉼표로 받아 순서대로 흘린다 — ws_session.py 의 --wav 계약과 같은 모양으로 맞춘다
- [x] #2 둘째 픽스처가 코치의 첫 턴 «뒤»에 도착하게 한다 — 한꺼번에 흘리면 두 발화가 같은 턴에 묶여 왕복이 안 생긴다
- [x] #3 instrument.js 를 고치지 않는다 — 계측 sha256 대조가 깨지지 않는 것을 확인한다
- [x] #4 확장한 드라이버로 회차를 다시 돌려 코칭 발생을 판정하고 TASK-81 AC#4 를 닫거나 그 근거로 열어 둔다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-15 — 확장 완료. --wav 가 쉼표 목록을 받고 둘째부터는 「코치 오디오가 온 적 있고 그 뒤 --quiet-ms 동안 안 옴」을 문턱으로 흘림. 실측 문턱 관측: heardAgentAudio=true · waitedMs=10348 · plays[1] 이 10.5초에 시작. instrument.js 를 고치지 않아 sha256 대조가 그대로 통과했음. 그 드라이버로 ARM-3 을 돌려 TASK-81 AC#4 를 닫았음.
<!-- SECTION:NOTES:END -->
