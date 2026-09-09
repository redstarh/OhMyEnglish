---
id: TASK-68
title: '하네스: spike_nova_protocol.py 가 원자료를 고정 파일명에 덮어쓴다 — 통제 대조의 원본이 한 벌뿐이다'
status: Done
assignee: []
created_date: '2026-09-09 14:22'
updated_date: '2026-09-09 14:30'
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
- [x] #1 --out 인자 또는 타임스탬프 파일명으로 회차가 서로를 덮지 않게 한다 — 어느 쪽을 골랐는지와 이유를 적는다
- [x] #2 기존 호출부가 깨지지 않는지 확인한다 — 기본값을 두어 인자 없이 돌리는 절차 문서를 무효로 만들지 않는다
- [x] #3 --help exit 0 을 확인한다 — 수치가 0 인 것이 스크립트가 도는 증거가 아니다(H-AV 계열)
- [x] #4 게이트를 다시 잰다 — tests/ 아래 .py 를 건드리면 ty check 대상이고 pytest 는 수집하지 않아 그 틈에서 게이트가 조용히 깨진다(H-AV)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-09 완료.

AC#1 — 둘을 다 넣었다. --out 인자(명시 경로)와 기본값 변경(.harness/evidence/<팔>-<픽스처>-<UTC시각>.json). ⛔ --out 만 넣지 않은 이유: 사람이 그것을 기억하는 것에 맡기면 안 막힌다 — 잊는 것이 바로 관측된 실패다(5차수 원본이 그렇게 덮였다). 그래서 기본값 자체를 회차마다 다르게 했다. 시각은 UTC다.

AC#2 — 고정 이름 파일을 「가장 최근」 포인터로 함께 갱신한다. 절차 문서와 기존 회차 기록이 그 이름을 가리키므로 없애면 인용이 끊긴다. ⚠️ 그 포인터는 덮인다 — 판정 근거로 인용할 것은 스크립트가 출력하는 raw -> 경로다. 그 사실을 코드 주석과 tests/harness/README.md 에 적었다.

AC#3 — --help exit 0 확인.

AC#4 — 게이트 넷을 직접 다시 쟀다: pytest 884 passed (다른 세션의 877 에서 늘어난 것은 그쪽 TASK-47 작업분이고 내 변경은 harness 파일이라 pytest 가 수집하지 않는다) · ruff check exit 0 · ruff format --check exit 0 · 게이트 밖 ruff check ../../tests ../../scripts All checks passed · ty check All checks passed. ⚠️ H-X 대로 pgrep 으로 동시 pytest 없음을 확인하고 다른 세션에 미리 알렸다.

⛔ exit 0 을 증거로 쓰지 않고 거동을 반증 가능하게 확인했다 — 같은 픽스처로 스파이크를 두 번 돌려 파일 둘이 따로 생기고 앞 회차(N1-nova-protocol-u1-20260909T142915Z.json · 74k)가 살아 있는 것을 확인했다. 포인터(N1-nova-protocol.json)만 80k 로 갱신됐다.
<!-- SECTION:NOTES:END -->
