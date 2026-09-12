"""음성 어댑터 구현 선택 — 픽스처 대역 import가 허용되는 **유일한** 지점 (G3).

세션 러너와 소켓 계층은 포트(`port.VoiceAdapter`)만 안다. 어떤 구현을 붙일지는
설정(`Settings.voice_adapter`)이 정하고 그 분기는 이 함수에만 있다 — Nova 어댑터를
추가할 때 고칠 자리가 한 곳으로 남고, 게이트웨이 코드는 손대지 않는다.

`-> VoiceAdapter` 반환 타입이 구현의 포트 준수를 정적으로 검사하는 이음매다:
구현이 포트에서 벗어나면 여기서 타입 오류로 걸린다.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.audio_gateway.nova import (
    NovaVoiceAdapter,
    build_pronunciation_prompt,
    build_system_prompt,
)
from app.audio_gateway.port import VoiceAdapter
from app.audio_gateway.stub import StubVoiceAdapter
from app.config import Settings
from app.models.plan import PlanQuestion, SessionInstruction
from app.models.scenario import SessionScenario
from app.models.usage import UsageSink

STUB_ADAPTER = "stub"
# Nova 2 Sonic 실연동 (3차수). 어댑터 생성은 스트림을 열지 않는다 — 연결은 `start()`가
# 하고 그 상한은 세션 러너가 건다(`session.CONNECT_TIMEOUT`).
NOVA_ADAPTER = "nova"
# 연결 실패 시나리오(E2E-S 6)를 **코드 수정 없이** 재현하기 위한 설정값. 무응답은
# 예외가 아니라 "응답이 오지 않는 것"이라 실물로 만들기 어렵고, 서버를 이 모드로
# 띄우면 프론트엔드의 연결 실패 화면(U2)을 손으로 확인할 수 있다.
STUB_UNRESPONSIVE_ADAPTER = "stub_unresponsive"


def create_voice_adapter(
    settings: Settings,
    *,
    known_sounds: Sequence[str] = (),
    plan: SessionInstruction | None = None,
    questions: Sequence[PlanQuestion],
    scenario: SessionScenario | None,
    pronunciation_sound: str | None = None,
    usage_sink: UsageSink | None = None,
) -> VoiceAdapter:
    """넷 다 **데이터**다 — 조립된 지시문이 아니다 (G-3).

    호출자(소켓 계층)가 프롬프트를 조립하면 `nova`를 import해야 하고, 그러면 "어떤 구현이
    붙는지 소켓은 모른다"는 이음매가 사라진다(G3 — 이 모듈이 유일한 분기점인 이유). 그래서
    학습자의 소리 목록·오늘의 계획·질문 목록·오늘의 무대만 받아 **여기서** 지시문을 만든다.

    ⚠️ **`questions`는 `plan`과 나란히 데이터로 받는다** (설계서 §2.1). 두 가지를 하지 않은
    것이 계약이다: ① **`PreparedPlan`을 그대로 받지 않는다** — 그것은 `services`의 타입이고
    여기서 import하면 `models` ← `services` 의존 방향이 뒤집힌다. `list[PlanQuestion]`은 이미
    `models/plan.py`에 있으므로 방향을 깨지 않는다. ② **`SessionInstruction`에 넣지 않는다** —
    `extra="forbid"` + 필수 필드 증가는 **저장된 모든 행을 한꺼번에** 검증 실패시킨다
    (`services/sessions.load_prepared_plan`이 그 실패 모드에 이미 이름을 붙여 뒀다).

    ⚠️ **`questions`·`scenario`에 기본값을 두지 않는다.** 두면 호출자가 재료를 빠뜨려도 조용히
    통과해 「질문이 안 실린 세션」·「무대 없는 세션」이 정상처럼 보인다 — 이 설계가 메우는 공백이
    정확히 그 모양이다. 드릴 설정값 둘은 `Settings`에서 꺼내 조립기로 옮긴다: 조립기가 전역을
    읽으면 같은 입력이 프로세스 환경에 따라 다른 프롬프트를 낸다.

    **스텁에도 지시문을 넘긴다**(계획서 Task 10). 스텁은 값을 **보관만** 하고 발화에 쓰지
    않지만, 조립 지점에서 어댑터까지 지시문이 실제로 도달했는지 판정할 수단이 그것뿐이다
    (설계서 AS6). 생성 후 대입이 아니라 **생성자 인자**로 넘기는 것이 계약이다 — 스텁의
    `instructions`는 setter 없는 property다.

    `usage_sink`는 **Nova 에만** 전달된다 (`TASK-124` · 결정 68) — 스텁은 토큰을 쓰지 않으므로
    넘기면 「쓰지 않은 비용」을 발명한다. ⚠️ 이 인자를 빼면 Nova 의 토큰 기록이 **조용히**
    **꺼진다**:
    어댑터의 기본값이 `None`(기록 없음)이고, 그 기본값은 스트림 대역만으로 도는 단위 테스트를 위한
    것이다. 실물 배선은 소켓 계층 한 곳뿐이고 그 자리를 게이트 테스트가 못 박는다.
    """
    # `TASK-10.1` — 발음 전용 모드. **소리 키가 오면 그 모드다**: 계획·무대·질문·놓친 소리 목록을
    # 싣지 않고 규칙 1~7 도 없는 짧은 지시문을 쓴다. 형태의 근거는 `nova.PRONUNCIATION_MODE_PROMPT`
    # 위 주석이 소유한다(실측 4/4 대 일반 세션 규모 0/76).
    #
    # ⛔ **여기서 소리 키를 «고르지» 않는다** — 어느 소리를 오늘의 초점으로 삼을지는 제품 정책이고
    # 소켓 계층이 계획·놓친 소리 목록을 읽어 정한다. 이 모듈은 「소리가 주어졌으면 그 지시문」만
    # 안다. 고르는 규칙을 여기 두면 팩토리가 `services` 의 판단을 흡수해 G3 의 이음매가 흐려진다.
    # ⚠️ 소리 없이 이 모드로 붙는 경로는 만들지 않는다 — 소켓이 그때 말하기로 떨어뜨린다.
    instructions = (
        build_pronunciation_prompt(pronunciation_sound)
        if pronunciation_sound is not None
        else build_system_prompt(
            known_sounds,
            plan,
            questions,
            scenario,
            drill_count=settings.drill_count,
            drill_turns_min=settings.drill_turns_min,
        )
    )
    if settings.voice_adapter == STUB_ADAPTER:
        return StubVoiceAdapter("fixture", instructions=instructions)
    if settings.voice_adapter == STUB_UNRESPONSIVE_ADAPTER:
        return StubVoiceAdapter("unresponsive", instructions=instructions)
    if settings.voice_adapter == NOVA_ADAPTER:
        # `TASK-124`(결정 68) — 토큰 기록 sink 를 넘긴다. ⛔ **스텁에는 넘기지 않는다**: 스텁은
        # 토큰을 쓰지 않으므로 행을 만들면 「쓰지 않은 비용」을 발명한다.
        return NovaVoiceAdapter(settings, instructions=instructions, usage_sink=usage_sink)
    # 오타를 조용히 스텁으로 흘려보내면 "실물이라 믿었던 세션이 픽스처였다"가 된다.
    raise ValueError(f"알 수 없는 voice_adapter 설정: {settings.voice_adapter!r}")
