"""음성 어댑터 구현 선택 — 픽스처 대역 import가 허용되는 **유일한** 지점 (G3).

세션 러너와 소켓 계층은 포트(`port.VoiceAdapter`)만 안다. 어떤 구현을 붙일지는
설정(`Settings.voice_adapter`)이 정하고 그 분기는 이 함수에만 있다 — Nova 어댑터를
추가할 때 고칠 자리가 한 곳으로 남고, 게이트웨이 코드는 손대지 않는다.

`-> VoiceAdapter` 반환 타입이 구현의 포트 준수를 정적으로 검사하는 이음매다:
구현이 포트에서 벗어나면 여기서 타입 오류로 걸린다.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.audio_gateway.nova import NovaVoiceAdapter, build_system_prompt
from app.audio_gateway.port import VoiceAdapter
from app.audio_gateway.stub import StubVoiceAdapter
from app.config import Settings
from app.models.plan import SessionInstruction

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
) -> VoiceAdapter:
    """`known_sounds`와 `plan`은 **데이터**다 — 조립된 지시문이 아니다 (G-3).

    호출자(소켓 계층)가 프롬프트를 조립하면 `nova`를 import해야 하고, 그러면 "어떤 구현이
    붙는지 소켓은 모른다"는 이음매가 사라진다(G3 — 이 모듈이 유일한 분기점인 이유). 그래서
    학습자의 소리 목록과 오늘의 계획만 받아 **여기서** 지시문을 만든다.

    **스텁에도 지시문을 넘긴다**(계획서 Task 10). 스텁은 값을 **보관만** 하고 발화에 쓰지
    않지만, 조립 지점에서 어댑터까지 지시문이 실제로 도달했는지 판정할 수단이 그것뿐이다
    (설계서 AS6). 생성 후 대입이 아니라 **생성자 인자**로 넘기는 것이 계약이다 — 스텁의
    `instructions`는 setter 없는 property다.
    """
    instructions = build_system_prompt(known_sounds, plan)
    if settings.voice_adapter == STUB_ADAPTER:
        return StubVoiceAdapter("fixture", instructions=instructions)
    if settings.voice_adapter == STUB_UNRESPONSIVE_ADAPTER:
        return StubVoiceAdapter("unresponsive", instructions=instructions)
    if settings.voice_adapter == NOVA_ADAPTER:
        return NovaVoiceAdapter(settings, instructions=instructions)
    # 오타를 조용히 스텁으로 흘려보내면 "실물이라 믿었던 세션이 픽스처였다"가 된다.
    raise ValueError(f"알 수 없는 voice_adapter 설정: {settings.voice_adapter!r}")
