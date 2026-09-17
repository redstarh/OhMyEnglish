---
id: TASK-163
title: '구현 ②: services/video_url.py — YouTube URL 에서 videoId 를 뽑는 순수 함수'
status: Done
assignee: []
created_date: '2026-09-17 17:16'
updated_date: '2026-09-17 17:26'
labels: []
dependencies: []
ordinal: 224000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
설계서 §4 의 parse_youtube_id 를 만든다. DB 를 쓰지 않으므로 ① 과 병행할 수 있다. 형태 넷을 다루고 도메인을 확인한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 parse_youtube_id(url) -> str | None 을 만들었다
- [x] #2 형태 넷(watch?v= · youtu.be/ · shorts/ · embed/)을 다 뽑는다
- [x] #3 질의 문자열이 붙어도 뽑는다 (&t=42s)
- [x] #4 11자 형태가 아니면 None 을 준다
- [x] #5 ⛔ YouTube 도메인이 아니면 None 을 준다 — 아무 URL 에서 조각을 뽑지 않는다
- [x] #6 tests/unit/test_video_url.py 를 쓰고 통과한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 이행 (2026-09-18)

- `app/backend/app/services/video_url.py` — `parse_youtube_id(url) -> str | None` 하나.
- `tests/unit/test_video_url.py` — 단정 **13개**. red 를 먼저 확인했음(`ModuleNotFoundError`).

### 받는 것과 거부하는 것

| 받음 | 거부함 |
|---|---|
| `watch?v=` · `youtu.be/` · `shorts/` · `embed/` | 11자가 아닌 것(10자·12자) |
| 질의가 더 붙어도 됨 (`&t=42s` · `?t=42` · `list=` 가 앞에 와도) | 알파벳 밖 문자(`!` · `.`) |
| `m.youtube.com` · 스킴이 없는 형태 | ⛔ YouTube 아닌 호스트 |
| 앞뒤 공백 | YouTube 인데 영상이 없는 URL(`/` · `/watch` · `/results?...`) |
| | 빈 문자열·공백만 |
| | ⛔ 맨 식별자만 준 것(`dQw4w9WgXcQ`) |

### ⛔ 이 함수의 값을 정하는 단정 하나

`test_it_rejects_hosts_that_are_not_youtube` 의 첫 줄 —
`https://youtube.com.attacker.test/watch?v=<id>` 가 **`None`** 이어야 함.
호스트를 부분 문자열로 검사하면 그것이 통과하고, 그 순간 이 함수가 「아무 URL 에서 11자 조각을 뽑는
함수」가 됨. 그래서 `_ALLOWED_HOSTS` 를 **정확히 일치**로 봄.

### 설계와 다르게 한 것 하나와 그 근거

설계서 §4 의 표에 없던 것을 둘 받아들였음: **`m.youtube.com`** 과 **스킴이 없는 형태**.
근거는 사용자 경험임 — 손으로 옮겨 적으면 스킴이 빠지고, 그것을 거부하면 사용자가 이유를 알 수 없음.
⛔ **관대함이 호스트 검사를 무르게 하지 않음** — 스킴을 붙여 파싱하되 호스트 검사는 그대로 거침.
그것을 `test_it_accepts_the_mobile_host_and_a_missing_scheme` 와 위의 공격 URL 단정이 함께 못 박음.

### 게이트 (이 턴에 직접 돌린 출력)

`pytest` **1314 passed**(앞 차수 1301 + 새 13) · `ruff` 0 · `ruff format` **275 files** · `ty` 0.

⚠️ **`H-BW` 를 다시 밟았음** — 한글 주석의 `E501` 은 문자 수가 아니라 **표시 폭**이라 3곳이 걸렸고
줄을 나눠 고쳤음. 한글 주석을 쓴 직후 `ruff check` 를 돌리는 규율이 그것을 잡았음.
<!-- SECTION:NOTES:END -->
