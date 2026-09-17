---
id: TASK-166
title: '구현 ⑤: 쉐도잉 배선 — 사용자가 문장을 지정해 연습하는 경로를 연다'
status: Done
assignee: []
created_date: '2026-09-17 17:16'
updated_date: '2026-09-17 17:45'
labels: []
dependencies:
  - TASK-162
ordinal: 227000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
설계서 §6 을 이행한다. 지금 클립 선택은 자동이고 사용자가 고를 경로가 없다. coalesce 맨 앞 항을 더해 지정 클립을 받는다. 없는 id 는 조용히 자동 선택으로 떨어진다(기존 관례).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 _ATTACH_SHADOWING_CLIP_SQL 의 coalesce 맨 앞에 지정 id 항을 더했다
- [x] #2 start_shadowing_session 에 item_id 인자를 더했다
- [x] #3 api/ws.py 가 query_params 의 item 을 UUID 로 파싱하고 실패하면 None 으로 둔다 (오류로 만들지 않는다)
- [x] #4 lib/config.ts 의 SessionEntry 에 itemId 를 더하고 sessionSocketUrl 이 item 질의로 싣는다
- [x] #5 tests/integration/test_ws.py 에 두 경우를 더했다 — 지정 id 로 열면 그 문장이 붙고, 없는 id 면 자동 선택으로 떨어진다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 이행 (2026-09-18)

- `app/backend/app/services/sessions.py` — `_ATTACH_SHADOWING_CLIP_SQL` 의 `coalesce` **맨 앞**에
  지정 항을 더하고 `start_shadowing_session` 에 `item_id` 인자를 더했음.
- `app/backend/app/api/ws.py` — 헬퍼 `_requested_item_or_none` 과 `?item=` 배선.
- `app/frontend/lib/config.ts` — `SessionEntry.itemId` 와 `sessionSocketUrl` 의 `item` 질의.
- `tests/integration/test_ws.py` — 픽스처 `two_committed_clips` 와 단정 **3개**.

### ⛔ 이 태스크에서 가장 중요한 것 — 판별력을 위해 클립을 **둘** 만들었음

클립이 하나면 자동 선택도 그것을 고르므로 「지정한 클립이 붙었다」는 단정이 **아무것도 가리지 못함.**
⇒ `two_committed_clips` 가 `created_at` 을 1시간 벌려 둘을 만들고, 자동 선택이 고르는 것(이른 것)과
**다른 것**(나중 것)을 지정함.

red 를 확인한 출력:

```
FAILED test_ws_opens_the_shadowing_session_on_the_requested_clip
  + The earlier one.          ← 자동 선택이 붙었다
1 failed, 2 passed
```

⇒ 지정 경로가 없으면 정확히 그 단정만 실패하고 폴백 단정 둘은 그때도 통과함. 즉 셋이 **서로 다른
것**을 잼.

### 없는 id 를 조용히 흘리는 판단과 그 자리

`coalesce` 의 첫 항이 `(select i.id from shadowing_items i where i.id = $3)` 이므로 **없는 id 는
0행이 되어 다음 항으로 감.** 예외를 던지지 않는 것이 `api/ws.py` 의 `_load_*_or_none` 들과 같은
관례임 — 사용자가 방금 지운 문장을 다시 눌렀을 때 학습 자체가 막히면 안 됨.

⚠️ **존재 판정을 `ws.py` 에서 미리 조회하지 않은 이유**: 한 문장 안에서 판정하면 그 사이에 지워지는
창이 없음. 두 왕복으로 나누면 그 창이 생김.

### 단정 셋이 각각 무엇을 막나

| 단정 | 막는 것 |
|---|---|
| `..._on_the_requested_clip` | 지정이 무시되고 자동 선택이 붙는 것 |
| `..._falls_back_to_the_automatic_choice_when_the_requested_clip_is_unknown` | 지운 문장을 눌러 학습이 막히는 것 |
| `..._ignores_an_item_that_is_not_a_uuid` | 형태 오류가 연결 실패가 되는 것 |

### 함정 하나 — 부분 실행에서 `asyncio_mode` 가 꺼졌음

`test_ws.py` 의 테스트들은 `@pytest.mark.asyncio` 마커 없이 `asyncio_mode="auto"` 에 의존하는데,
부분 실행에서 그 설정이 적용되지 않아 **기존 테스트 2건이 「async 를 지원하지 않는다」로 실패**했음.
⇒ 내 변경 때문이 아니었고 `-o asyncio_mode=auto` 를 붙여 해결했음(handoff 착수 조건 1항이 이미
적어 둔 함정임).

### 게이트 (이 턴에 직접 돌린 출력)

`pytest` **1339 passed**(앞 차수 1336 + 새 3) · `ruff` 0 · `ruff format` **280 files** · `ty` 0 ·
`tsc` 0 · `eslint` 0. `test_ws.py` 단독은 **39 passed**(기존 36 + 새 3).
<!-- SECTION:NOTES:END -->
