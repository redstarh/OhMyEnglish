"""`learning_sessions.mode` 의 값역 — DB CHECK 와 짝을 맞춘 파이썬 정본.

⛔ **값역의 정본은 `db/migrations/018_scenario_source_and_generate_job.sql` 의
`learning_sessions_mode_check` 다.** 이 모듈은 그 값을 파이썬이 부르는 이름이고, 두 곳이 갈라지는
것은 `tests/unit/test_schema.py::test_session_mode_domain_includes_scenario_intake` 가 막는다 —
그 단정이 `SESSION_MODES` 와 `pg_get_constraintdef` 를 함께 잰다.

**왜 신설했는가** (`TASK-148` ③ · 결정 122): CHECK 기반 값역 가운데 **`mode` 만** `models/` 정본이
없었다. 문자열이 `api/ws.py` 의 지역 상수 셋과 `services/sessions.py` 의 하나로 흩어져 있었고,
`analysis.ErrorCategory` · `pronunciation.PronunciationOutcome` · `voice_command.ControlCommand` 는
모두 이 관례를 따른다.

⛔ **`review` 를 목록에서 빼지 않는다.** 진입점이 없어 쓰는 코드가 0곳이지만 018 의 CHECK 가 그 값을
갖는다. 018 이 `drop`+`add` 로 목록을 «대체»하므로 파이썬 쪽에서 빠뜨리면 그 값이 DB 에서 사라져도
대조 단정이 침묵한다.

⚠️ **「값역」과 「소켓이 받는 진입 모드」는 다르다.** `review` 는 값역 안이지만 진입점이 없어
`?mode=review` 는 알 수 없는 값으로 경고한다 — 그 목록은 `api/ws.py` 가 갖는다.
"""

from __future__ import annotations

from typing import Literal, get_args

SessionMode = Literal["speaking", "shadowing", "review", "pronunciation", "scenario_intake"]

# ⛔ **목록을 두 번 적지 않고 `get_args` 로 유도한다** — 손으로 옮겨 적으면 한쪽만 늘어난다.
SESSION_MODES: tuple[SessionMode, ...] = get_args(SessionMode)

# 코드가 부르는 이름 — **실제로 쓰는 값만** 둔다(`models/usage.py` 가 세운 같은 규약).
# 그래서 `review` 에는 상수가 없다: 진입점이 없어 부를 자리가 없다.
# ⚠️ 값을 다시 적는 것이 위 리터럴과 갈라질 위험은 **타입이 갚는다** — 주석의 `SessionMode` 가
# 리터럴 밖 값을 거부하므로 오타는 `ty` 에서 걸린다.
SPEAKING_MODE: SessionMode = "speaking"
SHADOWING_MODE: SessionMode = "shadowing"
PRONUNCIATION_MODE: SessionMode = "pronunciation"
SCENARIO_INTAKE_MODE: SessionMode = "scenario_intake"
