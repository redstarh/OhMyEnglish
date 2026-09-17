---
id: TASK-147
title: '성능: review.py 의 순차 왕복을 배치화한다 — 최빈 쓰기 경로에서 발화당 5~24회'
status: Done
assignee: []
created_date: '2026-09-16 15:36'
updated_date: '2026-09-17 00:09'
labels: []
dependencies: []
ordinal: 208000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
R3(효율) 리뷰의 실측. recompute(497-552)가 category·history·apply·ladder(최대 3)·supersede·abandon 로 5~8회 순차 왕복하고, analysis 가 touched 패턴마다 그것을 부르므로 발화 하나 분석에 5~24회가 나간다. store_attempts(465-476)도 attempts 길이만큼 순차 INSERT 다. ⛔ 팀리드 판정으로 정리 회차에서 «갈라냈다»: ① SQL 을 unnest 로 바꾸는 것은 형태 정리가 아니라 성능 변경이고 ② store_attempts 의 건당 warning(패턴이 사라진 key 를 이름으로 남긴다)이 배치화하면 충실도가 떨어진다 — 이 리포는 로그 건수를 지표로 쓴다(함정 H-Z). ③ ladder upsert 를 한 문장으로 합치면 배치 안 중복 충돌 규칙(ON CONFLICT DO UPDATE 가 같은 행을 두 번 못 건드린다)이 새 조건으로 들어온다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 ladder upsert 배치화 전후로 recompute 의 왕복 수를 계측해 전·후 수치를 낸다
- [x] #2 store_attempts 배치화가 건당 warning 을 잃지 않는 형태인지 정한다
- [x] #3 test_review.py 의 멱등·순서 단정이 배치판에서도 통과하는 것을 보인다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 처리 (2026-09-17)

**AC#1 — 왕복 수를 계측했고 그 계측을 게이트로 남겼음.** 초를 재지 않고 **왕복 수**를 잼(결정적임).
`_CountingConnection` 대역이 `review.py` 가 쓰는 넷(`execute`·`fetch`·`fetchrow`·`fetchval`)만 넘기며 셈.

| 경로 | 전 | 후 |
|---|--:|--:|
| `recompute` (사다리 3칸) | **8** | **6** |
| `store_attempts` (재시도 3건) | **4** | **2** |

⚠️ **전 수치를 얻은 방법**: 후 수치로 단정을 먼저 걸고 돌렸음 — 실패 메시지가 전 수치를 그대로 줬고
(`assert 8 == 6` · `assert 4 == 2`) 그 실패가 곧 **판별력의 증거**임.
⛔ **상한이 아니라 등호로 잼** — 상한이면 5회 구현도 통과해 「무엇이 정상인가」를 더 이상 말하지 않음.
⚠️ `recompute` 는 사다리 길이에 **무관하게** 6 이 됨(전에는 5+L 이었음). `analysis` 가 touched 패턴마다
그것을 부르므로 그 증가가 곱해져 돌아오는 자리였음.

**구현 둘**:
- 사다리 upsert → `unnest($5::smallint[], $6::timestamptz[], $7::text[], $8::timestamptz[])` 한 문장.
  ⚠️ **배치가 안전한 근거를 주석에 적었음**: conflict target 이 `review_stage` 를 품고 `fold_stages` 가
  `1..L` 연속만 만들므로 한 문장 안에서 같은 행을 두 번 건드리지 않음. 그 성질이 깨지면 이 문장은
  런타임에 터지는데, **칸마다 보내던 판은 조용히 마지막 값으로 덮었음** — 배치가 오히려 더 시끄러움.
- `store_attempts` → `resolved`(left join) + `inserted`(데이터 변경 CTE) 한 문장.
  ⛔ **키 해석과 insert 를 두 문장으로 나누지 않았음**: 나누면 그 사이에 패턴이 사라져 외래키 위반으로
  **호출자 트랜잭션이 통째로 깨짐**(그 발화의 교정까지 잃음). 한 문장은 스냅샷이 하나라 그 창이 없음.
  ⚠️ 빈 목록이면 문장을 보내지 않음(왕복 1회 절약).

**AC#2 — 건당 warning 을 지키는 형태로 정했고, 그 경로에 단정을 세웠음.** 배치 문장이 입력 키 전부를
`pattern_id` 와 함께 돌려주고 파이썬이 `null` 인 키를 **이름으로** 찍음 — 문면은 이전과 글자까지 같음.
⛔ **그 경로에 테스트가 0건이었음**(`grep "pattern is gone" tests/` → 0). 배치화하면서 처음 세웠고,
경고 호출을 지워 보니 그 테스트만 FAIL 했음(복원 확인). 없으면 「경고를 잃었다」가 조용함 — 저장은
나머지 건으로 성공하고 왕복 수도 그대로라 어느 게이트도 울지 않음.

**AC#3 — 멱등·순서 단정이 배치판에서 통과함**: `test_recompute_is_idempotent` ·
`test_backfill_is_idempotent` 포함 `test_review.py` **33 passed**. 전체 게이트는 수집 1283 ·
`pytest` 1283 passed · `ruff` 0 · `ruff format` 0 · `ty` 0.

⚠️ **`_STORE_ATTEMPTS_SQL` 주석이 E501 로 두 번 걸렸음** — 한글은 2열이라(`H-BW`) 문면을 고칠 때마다
폭이 넘침. 문단을 다시 감아 해결했음.
<!-- SECTION:NOTES:END -->
