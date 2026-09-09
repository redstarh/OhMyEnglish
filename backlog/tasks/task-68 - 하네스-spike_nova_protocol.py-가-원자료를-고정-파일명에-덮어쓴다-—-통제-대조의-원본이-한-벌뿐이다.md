---
id: TASK-68
title: '하네스: spike_nova_protocol.py 가 원자료를 고정 파일명에 덮어쓴다 — 통제 대조의 원본이 한 벌뿐이다'
status: To Do
assignee: []
created_date: '2026-09-09 14:22'
labels: []
dependencies: []
ordinal: 71000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
test Agent 회차가 찾았고 팀리드가 실제로 덮어써서 확인했다. 이 스크립트는 결과를 .harness/evidence/ 의 고정 3개 파일명(N1-nova-protocol.json · P-tooluse-nova-protocol.json · P-tooluse-appprompt-nova-protocol.json)에 쓴다. 즉 회차를 한 번 더 돌리면 앞 회차의 원자료가 사라지고, 그 경로는 git 추적 밖이라 복구할 수 없다. 5차수 통제 대조 두 팔의 원본이 단 한 벌이었고 agent 가 착수 직후 .harness/evidence/run5-preserved/ 로 살렸다 — 그 뒤 agent 9회와 팀리드 2회가 실제로 덮었다. ⛔ 즉 이것은 가설이 아니라 이미 한 번 일어난 일이다. TASK-59 회차에서 팀리드도 같은 문제를 손으로 우회했다(회차마다 cp 로 복사).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 --out 인자 또는 타임스탬프 파일명으로 회차가 서로를 덮지 않게 한다 — 어느 쪽을 골랐는지와 이유를 적는다
- [ ] #2 기존 호출부가 깨지지 않는지 확인한다 — 기본값을 두어 인자 없이 돌리는 절차 문서를 무효로 만들지 않는다
- [ ] #3 --help exit 0 을 확인한다 — 수치가 0 인 것이 스크립트가 도는 증거가 아니다(H-AV 계열)
- [ ] #4 게이트를 다시 잰다 — tests/ 아래 .py 를 건드리면 ty check 대상이고 pytest 는 수집하지 않아 그 틈에서 게이트가 조용히 깨진다(H-AV)
<!-- AC:END -->
