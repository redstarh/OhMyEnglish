---
id: TASK-165
title: '구현 ④: api/videos.py — 엔드포인트 여섯과 라우터 등록'
status: Done
assignee: []
created_date: '2026-09-17 17:16'
updated_date: '2026-09-17 17:40'
labels: []
dependencies:
  - TASK-163
  - TASK-164
ordinal: 226000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
설계서 §3 을 이행한다. api/shadowing.py 의 계보를 베낀다. 값역은 서버가 소유하고 실패는 422·404 로 낸다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 APIRouter(prefix=/api/videos) 로 엔드포인트 여섯을 만들었다
- [x] #2 create_app() 에 include_router 를 더했다
- [x] #3 video_id·item_id 를 UUID 로 받는다 (경로 탈출 방어)
- [x] #4 값역을 서버가 검사한다 (url 파싱 · 제목 200자 · 문장 1000자 · 구간 90초 · 0<=start<end)
- [x] #5 구간 초를 서버가 소수 둘째 자리로 반올림한다
- [x] #6 GET /api/videos/{id} 가 영상과 문장 목록을 함께 준다 (왕복을 하나로)
- [x] #7 tests/integration/test_videos_api.py 를 쓰고 통과한다 — ⛔ 외부 호출이 0건이다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 이행 (2026-09-18)

- `app/backend/app/api/videos.py` — 엔드포인트 여섯.
- `app/backend/app/models/video.py` — 요청 검증 모델 둘과 상한 상수 셋.
- `app/backend/app/api/main.py` — 라우터 등록 **과 CORS 확장**.
- `tests/integration/test_videos_api.py` — 단정 **11개**. red 를 먼저 확인했음(10 failed).
- `tests/unit/test_schema.py` — 구간 상한 대조 단정 하나를 더했음.

### ⛔ 이 태스크에서 가장 값 있는 발견 — 테스트로는 잡히지 않는 실패

**리포에 POST·DELETE 엔드포인트가 하나도 없었음**(기존 일곱은 전부 `GET` 이고 쓰기는 WebSocket
으로만 일어났음). 그래서 `create_app()` 의 CORS 가 이랬음:

```python
app.add_middleware(CORSMiddleware, allow_origins=[FRONTEND_ORIGIN], allow_methods=["GET"])
```

⛔ **그 값을 그대로 두면 이 파일의 다른 단정 열 개가 전부 통과하는데 브라우저에서만 담기·지우기가
막힘.** `api_client` 는 ASGI 로 앱에 직접 붙어 **preflight 를 거치지 않기 때문**임.
⇒ `allow_methods=["GET", "POST", "DELETE"]` 로 넓히고 `allow_headers=["Content-Type"]` 을 더했음.
⇒ 그리고 **preflight 를 직접 보내는 단정**을 뒀음
(`test_the_browser_is_allowed_to_send_the_write_methods`).

### ⛔ 그 단정의 판별력을 무력화해서 재 봤음

「통과했다」만으로는 그 단정이 살아 있는지 알 수 없으므로 `allow_methods` 를 `["GET"]` 으로
되돌리고 돌렸음:

```
무력화 상태 exit=1
FAILED tests/integration/test_videos_api.py::test_the_browser_is_allowed_to_send_the_write_methods
1 failed, 10 deselected
```

복원 후 `11 passed`. ⇒ **그 단정은 반증력을 가짐.**

### 값역을 어디가 갖는가

| 검사 | 자리 | 응답 |
|---|---|---|
| URL 에서 videoId 를 못 뽑음 | 라우터가 `parse_youtube_id` 결과를 봄 | `422` |
| 제목·채널 공백·200자 초과 | `VideoCreateRequest` | `422` |
| 문장 공백·1000자 초과 | `PhraseCreateRequest` | `422` |
| 구간 순서·90초 초과·음수 | `PhraseCreateRequest` 의 `model_validator` | `422` |
| 경로 id 형태 | FastAPI 의 `UUID` 형 | `422` |
| 없는 영상·문장 | 서비스의 `None`·`False` | `404` |

⚠️ **구간 상한 90 이 스키마와 파이썬 양쪽에 있음.** 그래서
`test_clip_span_limit_matches_the_python_constant` 가 `pg_get_constraintdef` 에서 숫자를 뽑아
파이썬 상수와 **대조함** — 갈라지면 red 가 됨. 기존
`test_error_category_check_matches_the_python_value_domain` 과 같은 정신임.

### 함정 하나 — 설계가 의도한 실패가 테스트에서 먼저 드러났음

`add_phrase` 가 `level` 을 `users.current_level` 에서 읽으므로 **사용자가 없으면 NOT NULL 위반**임.
`clean_videos` 픽스처가 고정 사용자를 세우지 않아 3건이 그것으로 실패했음.
⇒ 픽스처가 사용자를 `on conflict do nothing` 으로 세우고, ⛔ **내가 만든 경우에만** 지움 — 무조건
지우면 `users` cascade 로 남의 테스트 데이터를 걷음.

### 설계와 다르게 한 것 하나

요청 필드 이름을 `start_sec`·`end_sec` 가 아니라 **`clip_start_sec`·`clip_end_sec`** 로 뒀음.
근거는 선례임 — 프런트가 쉐도잉에서 이미 그 이름을 받고 있음(`ShadowingTurns.as_event_payload`).
요청과 응답에서 다른 이름을 쓰면 화면이 같은 값을 두 이름으로 다룸.

### 게이트 (이 턴에 직접 돌린 출력)

`pytest` **1336 passed** · `ruff` 0 · `ruff format` **280 files** · `ty` 0 · `tsc` 0 · `eslint` 0.
<!-- SECTION:NOTES:END -->
