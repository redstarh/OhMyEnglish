---
id: TASK-54
title: '결함: ty.toml 주석에 tests 아래 새 파일이 ty 게이트 대상이라는 경고를 더한다'
status: Done
assignee: []
created_date: '2026-09-09 08:15'
updated_date: '2026-09-09 08:20'
labels: []
dependencies: []
ordinal: 57000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-09 테스트 회차에서 관측. 커밋 057ceef 에서 ty check 가 exit 1 · 진단 4건이었고 전부 tests/harness/c5_pronunciation_badge.py 였다. 원인은 루트 ty.toml 의 [src] include = [app/backend/app, tests] 가 tests 를 게이트 범위에 넣는 것이다. 회귀 자체는 a982577 에서 해소됐다(직접 재측정해 exit 0 확인). 남은 결함은 문서다 — ty.toml 주석은 app/backend/pyproject.toml 에 [tool.ty] 를 추가하지 말라는 경고만 담고, tests 아래 파일을 추가하면 그것도 게이트 대상이 된다는 사실을 말하지 않는다. 그 사실을 몰라 두 커밋(7bbc415·057ceef) 동안 게이트가 깨진 채였다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ty.toml 주석이 tests 아래 새 파일도 ty 게이트 대상임을 말한다
- [x] #2 docs/ops/pitfalls.md 에 같은 함정을 등록한다 — 하네스 파일 추가 시 ty 를 다시 잰다
- [x] #3 고친 뒤 ty check exit 0 을 직접 돌려 확인한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-09 완료. 읽는 자리 셋에 넣었다.

① ty.toml 머리주석 — [src] include 가 tests 를 담으므로 tests/ 아래 새 파일도 게이트 대상임을 못박고, pytest 가 test_*.py 만 수집해서 실행체(c1_*.py·c5_*.py)가 그 틈에 있다는 것을 함께 적었다.
② docs/ops/pitfalls.md 에 H-AV 로 등록했다. 대응은 「tests/ 에 .py 를 건드렸으면 게이트 넷을 모두 다시 잰다」이고, 앞의 셋만 재고 닫는 것이 실제 발생 경로였음을 적었다. 진단 내용의 함정(isinstance 만으로 좁히면 dict[Unknown, Unknown] 이 되어 str 키를 거부하고 4건이 종류만 바뀜)도 담았다.
③ handoff 착수 전 필수 7번 함정 목록 맨 앞에 H-AV 를 넣었다.

AC#3 검증 — 호출자가 직접 돌렸다: ty check exit 0 (All checks passed!) · 게이트 밖 ruff·format exit 0.

⚠️ 이 결함은 다른 세션의 테스트 회차가 찾았고 내가 스스로 못 잡았다. 그 사실을 H-AV 본문에 적었다.
<!-- SECTION:NOTES:END -->
