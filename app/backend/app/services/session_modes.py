"""진입 모드 하나가 세션을 어떻게 여는지 — 소켓이 읽어 그대로 따르는 표 (`TASK-148` ② · 결정 122).

⚠️ **`api/ws.py` 에서 이리로 옮겼다.** 그 파일은 「얇다」고 선언한 전송 계층인데 모드 셋의 도메인
정책이 그 안에 누적됐고, 그 자리에서 결정 67 → 72 의 반전 이력이 있다. 누적의 값은 「모드를 하나
더 붙이려면 소켓의 다섯 자리를 고쳐야 한다」였다 — 지금은 이 표에 한 줄을 더한다.

⛔ **이 표는 값역이 아니다.** 값역은 018 의 `learning_sessions_mode_check` 이고 파이썬 이름은
`models/session` 이 갖는다. 여기 담는 것은 그중 **진입점이 있는 것만**이다 — `review` 는 값역 안인데
여기 없고, 그래서 `policy_for` 가 `None` 을 돌려주고 소켓이 경고한 뒤 말하기로 진행한다.

⛔ **여기에 조회·전송을 넣지 않는다.** 이 모듈은 순수 데이터다: 어떤 조회를 할지는 소켓이, 무엇을
지시문에 실을지는 조립기가 갖는다. 그 경계가 무너지면 이 표가 다시 「정책 반, 배선 반」이 된다.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.session import (
    PRONUNCIATION_MODE,
    SCENARIO_INTAKE_MODE,
    SHADOWING_MODE,
    SPEAKING_MODE,
    SessionMode,
)


@dataclass(frozen=True)
class SessionModePolicy:
    """한 진입 모드의 정책. 필드 이름은 **소켓이 하는 일**이고 모드 이름이 아니다."""

    mode: SessionMode
    """세션 행에 적히는 값. `writes_mode_to_row` 가 참일 때만 실제로 적힌다."""

    opens_shadowing_session: bool = False
    """`start_shadowing_session` 으로 열고 클립을 함께 읽는다 (`TASK-45` · 결정 35)."""

    writes_mode_to_row: bool = False
    """세션 행의 `mode` 를 뒤에 적는다. ⛔ **대가가 모드마다 다르다** — 아래 표의 주석이 갖는다."""

    records_drill_turns: bool = True
    """기대 exchange 수를 남긴다 (캡틴 결정 16). 질문이 실리지 않는 모드에서는 성립하지 않는다."""

    pronunciation_prompt: bool = False
    """발음 전용 지시문을 요청하고 소리 후보를 재료로 넘긴다 (`TASK-10.1` · 결정 72)."""

    scenario_intake_prompt: bool = False
    """조립기에 질문 5개 블록을 요청하고, 드릴 질문과 무대는 넘기지 않는다 (`TASK-5` Task 6)."""


# ⚠️ 명시적 선택이라 경고하지 않는다 — `?mode=speaking` 은 「알 수 없는 값」이 아니다
# (2026-09-09 리뷰 지적). 세션 행의 `mode` 는 001 의 기본값이 이미 이 값이라 다시 적지 않는다.
_SPEAKING = SessionModePolicy(mode=SPEAKING_MODE)

# `TASK-45` · 결정 35 — 쉐도잉은 **세션을 만드는 방식부터** 다르다(클립 1개가 붙는다).
# ⛔ 기대 exchange 수를 쓰지 않는다 (캡틴 결정 37): 그 값은 말하기 관측 지표이고 `TASK-36` 이
# 읽으므로, 쉐도잉에 쓰면 아직 돌리지도 않은 관측이 오염된 데이터를 본다. null 이 「관측 대상
# 아님」을 뜻하는 것은 결정 16 이 세운 계약이다.
_SHADOWING = SessionModePolicy(
    mode=SHADOWING_MODE,
    opens_shadowing_session=True,
    records_drill_turns=False,
)

# `TASK-10.1` — 바꾸는 것은 **지시문**이고, `TASK-112`(결정 67 · 마이그레이션 014) 이후로는
# 세션 행의 `mode` 도 같은 값으로 적힌다.
# ⚠️ **그 서술은 한 번 뒤집혔고 그 사실을 남긴다** — 처음에는 *"세션 행의 mode 를 바꾸지 않는다
# (001 값역 밖이고 값역을 늘리는 것은 이 태스크 범위 밖이다)"* 였다. 그 대가(결과 화면·집계가 발음
# 세션을 말하기로 세는 것)를 사용자가 결정 67 로 갚기로 정했다.
# ⛔ **적는 조건이 결정 72 로 「요청받았는가」가 됐다.** 이전 판은 「소리가 정해졌는가」였고 근거는
# **폴백의 존재**였다 — 폴백으로 말하기가 된 세션까지 발음으로 집계하면 결정 67 이 닫으려던 결함의
# 반대 방향 변종이 된다. 폴백이 사라졌으므로 요청한 세션은 실제로 발음 세션이다.
# ⛔ 기대 exchange 수를 쓰지 않는다 — 근거가 쉐도잉과 **같다**(결정 37): 이 모드의 지시문에는
# 질문이 실리지 않으므로 그 값이 애초에 성립하지 않는다.
_PRONUNCIATION = SessionModePolicy(
    mode=PRONUNCIATION_MODE,
    writes_mode_to_row=True,
    records_drill_turns=False,
    pronunciation_prompt=True,
)

# `TASK-5` Task 6 · 사용자 결정 79 (마이그레이션 018 이 값역을 열었다).
# ⛔ **`?source=additional` 로는 이 진입을 가릴 수 없다** — 추가 학습 메뉴 여섯 가운데 다섯이 그
# 값이고 그중 셋(자유 대화 · 약점 패턴 집중 · 질문 답변 5개)이 `mode` 를 갖지 않아 서로 구별되지
# 않는다(그 설계서 §5 가 코드로 확인한 목록을 갖는다). 그 값으로 가르면 **자유 대화 세션에 질문
# 5개 지시가 샌다.**
# ⛔ **세션 행의 `mode` 를 반드시 적는다** — 발음 모드와 달리 이 값은 지시문만 바꾸는 것이 아니다.
# 종료 경로가 `mode` 를 읽어 `generate_scenario` job 을 걸므로(설계서 §5 흐름 3) 적지 못하면
# **질문은 했는데 무대가 만들어지지 않는다.** 그래서 쓰는 값과 읽는 값이 같은 이름이어야 하고
# (`services/sessions.end_session` 이 `SCENARIO_INTAKE_MODE` 로 판정한다) 둘 다 `models/session` 을
# 받아쓴다. 리터럴이 두 곳에 있으면 세션은 정상으로 열리고 **job 만 안 걸리며 게이트는 침묵한다.**
# ⚠️ 기대 exchange 수는 **쓴다** — 이 세션에도 질문이 실리므로(다섯 축) 결정 16 의 관측이 성립한다.
_SCENARIO_INTAKE = SessionModePolicy(
    mode=SCENARIO_INTAKE_MODE,
    writes_mode_to_row=True,
    scenario_intake_prompt=True,
)

_POLICIES: dict[str, SessionModePolicy] = {
    policy.mode: policy for policy in (_SPEAKING, _SHADOWING, _PRONUNCIATION, _SCENARIO_INTAKE)
}

DEFAULT_POLICY = _SPEAKING
"""모드를 주지 않은 연결이 받는 정책 — 001 의 기본값과 같은 말하기 세션이다."""


def policy_for(requested_mode: str | None) -> SessionModePolicy | None:
    """`?mode=` 값의 정책. **진입점이 없는 값이면 `None`** 이다.

    ⛔ **여기서 경고하지 않는다.** 「알 수 없는 값」은 오타 난 링크·낡은 화면이라는 전송 쪽
    사건이고, 그 로그는 소켓이 남긴다 — 이 모듈은 정책만 답한다. 값역 안이지만 진입점이 없는
    `review` 도 같은 `None` 으로 떨어지고, 그것이 의도다(값역을 이 표에 복제하지 않는다).

    ⚠️ 모드를 주지 않은 연결(`None`)은 오류가 아니라 **기본**이므로 `DEFAULT_POLICY` 를 돌려준다.
    """
    if requested_mode is None:
        return DEFAULT_POLICY
    return _POLICIES.get(requested_mode)
