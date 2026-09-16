---
id: TASK-148
title: '갈라냄: api/ws.py 의 도메인 정책 셋을 경계 밖으로 옮긴다 (고도 리뷰)'
status: In Progress
assignee: []
created_date: '2026-09-16 15:36'
updated_date: '2026-09-16 23:36'
labels: []
dependencies: []
ordinal: 209000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
R4(고도) 리뷰 발견 셋. ① _pronunciation_candidates(180-216)가 순수 도메인 정책인데 「이 파일은 얇다」고 선언한 전송 계층에 있다 → services/pronunciation.py ② session_socket(336-513)에 WebSocket 프로토콜과 모드 셋의 도메인 정책이 누적됐고 그 자리에서 결정 67→72 반전 이력이 있다(범위가 넓어 쪼개야 한다) ③ 세션 mode 값역만 models/ 에 Literal 정본이 없다 — 다른 모든 CHECK 기반 값역은 그 관례를 따른다. ⛔ 정리 회차에서 갈라낸 이유: ②는 범위가 크고 ③은 타입 신설이라 둘 다 형태 정리를 넘는다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 셋 중 어느 것을 언제 할지 사용자가 정한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 방향 확정 (2026-09-17 · 결정 122)

사용자가 「기능을 쪼개」로 정했음 — 즉 이 태스크는 「할지 말지」가 아니라 「어떻게 쪼개는가」만 남았음.
착수하지 않았으므로 상태를 To Do 로 되돌림(진행 중이 아님).

쪼갤 것 넷(고도 리뷰 R4 의 발견 + FIXED_USER_ID):
① _pronunciation_candidates(180-216) → services/pronunciation.py (순수 함수라 위험 낮음)
② session_socket(336-513) 의 모드별 정책 → services 쪽 표·전략 (범위가 커서 다시 쪼개야 함)
③ 세션 mode 값역 → models/ 에 Literal 신설 (001 CHECK 와 짝을 맞춤)
④ FIXED_USER_ID 를 ws.py 밖으로 (지금 형제 라우터 둘이 옆으로 참조함)

⛔ 착수 순서 권고: ③ → ① → ④ → ②. ②가 가장 크고 나머지 셋이 그 준비가 됨.

## 진행 (2026-09-17) — ③ ① ④ 를 닫았음. 남은 것은 ②

**③ 세션 mode 값역의 파이썬 정본**: `app/models/session.py` 신설 — `SessionMode` 리터럴 ·
`SESSION_MODES`(`get_args` 로 유도) · 실제로 쓰는 상수 넷. `review` 는 값역에 있고 상수는 없다
(진입점이 없어 부를 자리가 없음 — `models/usage.py` 가 세운 규약).
- `api/ws.py` 의 지역 상수 셋과 `services/sessions.py` 의 하나가 그 모듈을 받아쓰게 바꿨음.
- ⛔ **「값역」과 「소켓이 받는 진입 모드」를 갈랐음** — `?mode=review` 는 여전히 경고를 내고 말하기로
  진행함. 그래서 `ws.py` 에 `ENTRY_MODES` 를 남겼고 멤버십이 이전 네 값과 같아 동작이 변하지 않음.
- `tests/unit/test_schema.py` 의 CHECK 단정이 `SESSION_MODES` 를 함께 잼. ⛔ 하드코딩 목록을
  `SESSION_MODES` 로 «대체»하지 않았음 — 그러면 양쪽에서 같은 값을 지울 때 통과함(판별력 상실).
  판별력을 실측함: 리터럴에서 `review` 를 빼니 그 테스트가 FAIL 했고 복원했음.

**① 순수 함수 이동**: `_pronunciation_candidates` → `services/pronunciation.pronunciation_candidates`
(`load_known_sounds` 바로 아래 — 두 출처 중 하나를 그 함수가 읽음). 호출부의 지역 변수를
`sound_candidates` 로 바꿨음: 이름이 같으면 import 가 섀도잉돼 `UnboundLocalError` 가 됨.
⚠️ 팩토리 인자 한 자리가 함수 객체를 넘기고 있었고 타입 검사가 그것을 잡았음.
`tests/unit/test_ws_mode.py` 의 import 를 옮겼고 파일 이름은 그대로 둠(재는 대상이 진입 규칙임).

**④ `FIXED_USER_ID` 이동**: `app/models/user.py` 신설. 옆으로 참조하던 여덟 자리를 정본으로 돌렸음
(`api/results.py` · `api/daily.py` · 통합 테스트 넷 · 하네스 스크립트 셋).
⛔ **시드와의 복제를 단정으로 갚았음** — `test_the_fixed_user_matches_the_seed` 가
`migrate.USER_ID` 와 대조함. 그 단정이 없으면 어긋남이 「시드를 안 돌렸다」와 구별되지 않음.

**게이트**: `pytest` 1279 passed(새 단정 1건 추가) · `ruff` exit 0 · `ruff format` exit 0 ·
`ty` exit 0. ⚠️ `tests` 트리의 E501 17건은 그대로임 — `TASK-151` 의 범위임(파일별 개수까지 대조함).

**남은 ②**: `session_socket` 의 모드별 정책을 services 쪽 표로 옮기는 것. ③ 이 그 준비였음.
<!-- SECTION:NOTES:END -->
