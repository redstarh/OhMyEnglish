---
id: TASK-223
title: '결함: 고아 스윕이 정지 중 세션의 진행 중 녹음을 지운다'
status: Done
assignee: []
created_date: '2026-09-19 01:01'
updated_date: '2026-09-19 01:35'
labels: []
dependencies: []
ordinal: 284000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
정리 회차(TASK-222)의 리뷰 세 갈래가 독립적으로 같은 자리를 지목했음 — 단순화·고도·효율. services/recordings.py:557 의 2다리 고아 스윕만 살아 있는 세션을 리터럴 'active' 로 판정하고, 정본인 sessions.LIVE_SESSION_STATUSES 를 읽지 않는다. 같은 파일이 :107 · :124 · :396 세 자리에서는 그 상수를 읽는다. TASK-140 이 마이그레이션 025 의 paused 추가에 맞춰 세 자리를 고치면서 이 한 자리를 지나쳤다. 결과: 정지 중 쉐도잉 세션의 열린 .part 파일이 「.part 는 언제나 고아」 규칙(remove_orphan_recordings_in)으로 지워진다. 워커 유휴 사이클 1Hz 경로라 도달성이 높다. ⚠️ sessions.py:186 의 주석이 바로 이 형태의 누락을 막으려고 두 이름을 공개로 둔 것이라고 적어 두었다. ⚠️ 이 누락이 남은 이유가 테스트 공백이다 — test_recordings.py 에 load_recording(:429)·purge(:574·:593) 의 paused 사례는 있으나 스윕의 paused 사례가 없다. ⛔ 동작변경=예 이므로 정리 묶음에서 갈라냈다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 스윕이 LIVE_SESSION_STATUSES 를 읽는다
- [x] #2 정지 중 세션의 .part 가 남는 것을 테스트가 잡는다
- [x] #3 recordings.py:383·:470 의 낡은 서술 두 줄을 함께 고친다
- [x] #4 게이트 여덟이 통과하고 수집 개수가 줄지 않는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 고친 것 (2026-09-19)

`services/recordings.py` 의 2다리 스윕이 리터럴 `"active"` 대신 `sessions.LIVE_SESSION_STATUSES` 를 읽음. 서술 세 자리를 함께 고쳤음 — 1다리 독스트링의 `status = 'active'`(025 뒤로 낡았음) · `load_recording` 독스트링의 「스윕도 같은 이름을 읽는다」(그 단정이 실제로 거짓이었음을 기록) · 스윕 자신의 가드 서술(값역 정본을 이름으로 가리킴).

## 판별력 (먼저 실패시켰음)

새 단정 `test_orphan_sweep_does_not_touch_a_paused_session` 을 고치기 «전에» 돌려 `assert 1 == 0` 을 직접 봤음 — 정지 중 세션의 `.part` 가 실제로 지워졌음. 고친 뒤 통과함.

## 게이트 (이 회차에 직접 돌림)

`pytest` 수집·통과 **1401**(직전 1400 · 새 단정 1건만큼 늘었고 줄지 않았음) · `ruff` 0 · `ruff format` 305 files · `ty` 0. 프런트 셋은 소스를 건드리지 않아 세션 시작의 값이 유지됨(`tsc` 0 · `eslint` 0 errors/경고 1 기준선 · `next build` `/`=`○`).

## 같은 모양을 더 찾았고 0건이었음

`== 'active'` · `!= 'active'` · `<> 'active'` 를 `app`·`tests`·`scripts` 에 걸어 남은 제품 코드 자리를 찾았음. 하나가 걸렸으나(`_SET_SESSION_MODE_SQL` 과 그 독스트링) **낡은 것이 아니었음** — 그 SQL 은 `status = 'active'` 가 캡틴 결정(2026-09-03)이고 독스트링이 그것과 일치함. 나머지는 주석·테스트 문면임.
<!-- SECTION:NOTES:END -->
