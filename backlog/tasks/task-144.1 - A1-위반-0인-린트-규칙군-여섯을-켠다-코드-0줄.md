---
id: TASK-144.1
title: 'A1: 위반 0인 린트 규칙군 여섯을 켠다 (코드 0줄)'
status: Done
assignee: []
created_date: '2026-09-16 15:22'
updated_date: '2026-09-16 15:25'
labels: []
dependencies: []
parent_task_id: TASK-144
ordinal: 199000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
pyproject.toml 만 고친다. BLE·DTZ·PTH·S310·SLF001·N803 은 켜도 위반 0건임을 착수 전에 확인했다. noqa: BLE001 6건이 살아난다 — 지우지 않는다.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## A1 완료 (2026-09-17 · 코드 0줄)

켠 것: BLE · DTZ · PTH · SLF (그룹 전체 위반 0건) + S310 · N803 (규칙 단위).
⚠️ S 그룹 전체는 17건 · N 그룹은 2건이라 그룹으로 넓히지 않고 규칙만 골랐음 — 넓히려면 그 수를 먼저 손봐야 함.

게이트(직접 돌림 · 파이프 없이 종료 코드 확인): ruff exit 0 · format exit 0 ·
수집 1273(기준선과 같음) · pytest 1273 passed exit 0.

실측 하나: BLE 를 켠 뒤 noqa: BLE001 6건 중 **5건이 실제로 위반을 막고 있음**. 남은 1건
(audio_gateway/nova.py:1191)은 ruff 가 logger.exception 핸들러를 BLE001 에서 면제하므로 불필요해졌음
— ⛔ 지우지 않았음(그 표식의 문면이 「기록 실패가 세션 종료를 막지 않는다」는 근거를 담고 있고
RUF100 은 이 리포에서 켜지 않았음).

⚠️ 검증에서 오탐 하나를 밟았음: ruff --select RUF100 은 기존 select 를 «대체»해서 BLE001 을
non-enabled 로 보고했음. --extend-select 로 다시 확인해 정정했음.
<!-- SECTION:NOTES:END -->
