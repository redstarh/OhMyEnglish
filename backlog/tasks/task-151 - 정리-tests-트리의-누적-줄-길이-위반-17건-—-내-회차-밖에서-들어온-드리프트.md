---
id: TASK-151
title: '정리: tests 트리의 누적 줄 길이 위반 17건 — 내 회차 밖에서 들어온 드리프트'
status: Done
assignee: []
created_date: '2026-09-16 22:45'
updated_date: '2026-09-17 00:01'
labels: []
dependencies: []
ordinal: 212000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-17 정리 회차에서 발견. tests 트리의 lint 기준선은 H-L 이 「0」으로 적어 뒀는데(2026-09-09 TASK-37 이 정리) 지금 E501 이 17건이다. 파일별: test_pronunciation_sound_check.py 6 · test_nova.py 6 · test_gateway.py 4 · test_pipeline.py 1. 전부 한국어 주석·docstring 이고 다른 세션들이 그 뒤에 넣은 것이다(내가 오늘 넣은 8건은 이 회차에서 고쳤다). ⛔ 남의 세션 문장을 임의로 줄이지 않고 별 태스크로 둔다 — 문면을 고치는 것이므로 그 문장을 쓴 갈래가 하는 것이 맞다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 17건을 줄 나눔으로 고치고 tests 트리 기준선을 0 으로 되돌린다
- [x] #2 H-L 항목의 「기준선 0」 서술이 다시 참이 되게 한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 처리 (2026-09-17)

**17건을 문단 재감기로 고쳤음** — 낱말은 하나도 고치지 않고 줄 위치만 다시 잡았음(남의 세션 문장을
고쳐 쓰지 않는다는 이 태스크의 제약). 파일 넷: `test_gateway.py` · `test_nova.py` ·
`test_pronunciation_sound_check.py` · `test_pipeline.py`. docstring 요약 줄 넷은 문단 대상이 아니라
따로 나눴음.

**⛔ 두 번 틀린 뒤에 원인을 잡았고 그것이 새 함정임 (`H-BW`)**: `ruff` 의 `E501` 은 문자 수가 아니라
**표시 폭**으로 잼 — 한글은 2열임. `Line too long (102 > 100)` 이라 지목된 줄의 파이썬 `len()` 이
**67** 이었음(UTF-8 바이트는 137). 그래서 `len()` 으로 자리를 잡은 첫 판은 엉뚱한 곳을 나눴고,
두 번째 판은 조건이 참이 되지 않아 **한 줄도 안 고치고 「0건」을 냈음**.
⚠️ 폭 계산이 맞는지 `ruff` 보고값과 한 줄로 대조하고 나서 고치는 것이 그 함정을 1분에 드러냄.

**⚠️ 이미 적혀 있던 함정도 밟았음 (`H-BN`)** — 리포 루트에서 `ruff check tests` 를 돌려 기본 규칙셋
(E501 이 기본 select 에 없음)으로 검사했고 「0건」을 얻었음. 먼저 읽었으면 한 회차를 아꼈음.

**낱말을 밀어내는 방식은 수렴하지 않았음** — 넘친 낱말을 다음 줄로 미니 그 줄이 넘치고, 6회차에도
1건이 남았음. 문단 단위로 다시 감으면 한 번에 끝남. 그 판정을 `H-BW` 에 적었음.

**AC#2 — 「기준선 0」을 규율이 아니라 게이트로 만들었음**: 기전이 규율 부족이 아니라 **게이트가 그
두 경로를 아예 보지 않는 것**이었음(`ruff check .` 은 cwd `app/backend` 범위임). 그래서
`docs/ops/local-run.md` 의 게이트 명령에 `../../tests ../../scripts` 를 넣었고, `H-L` 에 재발 사실과
그 기전을 적었음. 같은 문서의 낡은 베이스라인 서술(`6건`·`4 files`)도 지웠음.

**게이트 (새 명령으로 직접 돌림)**: `pytest` 1280 passed · `ruff check . ../../tests ../../scripts`
exit 0 · `ruff format --check` 같은 세 경로 exit 0 · `ty` exit 0.
<!-- SECTION:NOTES:END -->
