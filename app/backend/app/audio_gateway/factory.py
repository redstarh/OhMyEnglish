"""음성 어댑터 구현 선택 — 픽스처 대역 import가 허용되는 **유일한** 지점 (G3).

세션 러너와 소켓 계층은 포트(`port.VoiceAdapter`)만 안다. 어떤 구현을 붙일지는
설정(`Settings.voice_adapter`)이 정하고 그 분기는 이 함수에만 있다 — Nova 어댑터를
추가할 때 고칠 자리가 한 곳으로 남고, 게이트웨이 코드는 손대지 않는다.

`-> VoiceAdapter` 반환 타입이 구현의 포트 준수를 정적으로 검사하는 이음매다:
구현이 포트에서 벗어나면 여기서 타입 오류로 걸린다.
"""

from __future__ import annotations

from app.audio_gateway.port import VoiceAdapter
from app.audio_gateway.stub import StubVoiceAdapter
from app.config import Settings

STUB_ADAPTER = "stub"


def create_voice_adapter(settings: Settings) -> VoiceAdapter:
    if settings.voice_adapter == STUB_ADAPTER:
        return StubVoiceAdapter()
    # 오타를 조용히 스텁으로 흘려보내면 "실물이라 믿었던 세션이 픽스처였다"가 된다.
    raise ValueError(f"알 수 없는 voice_adapter 설정: {settings.voice_adapter!r}")
