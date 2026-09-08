#!/usr/bin/env python3
"""N-1 프로토콜 스파이크 — Nova 2 Sonic에 실제 음성을 넣어 전사문을 받아온다.

`scripts/spike_nova_bidirectional.py`는 **자격증명이 이 연산에 통하는가**만 판정한다
(스트림이 열리고 4xx가 없으면 PASS). 이 스파이크는 그 다음 질문에 답한다 —
**전체 초기화 시퀀스를 보내면 Nova가 우리 음성을 알아듣고 이벤트를 돌려주는가.**
어댑터를 쓰기 전에 반드시 답이 있어야 하는 것들:

1. 사용자 발화 ASR이 어떤 이벤트로 오는가 (`role`·`generationStage`·`stopReason`)
2. **우리 포트의 `partial` 전사문에 대응하는 것이 실제로 존재하는가**
   (문서상 사용자 ASR은 `generationStage=FINAL`이고 `SPECULATIVE`는 ASSISTANT 텍스트다 —
   그렇다면 AC U1의 "부분 전사문 회색 표시"는 대응 데이터가 없을 수 있다)
3. `audioOutput`이 정말 헤더 없는 raw LPCM인가 (프론트 재생 경로에 직결)
4. 32ms 프레임 케이던스가 실제로 요구되는가

자격증명 해석·진단 장치는 기존 스파이크에서 **재사용한다** — 경로가 둘이면
"스파이크는 통과했는데 앱은 실패한다"를 만든다.

입력은 `tests/harness/fixtures/voice/u1.wav`(16kHz·16bit·mono, `say`로 합성)다.
기대 전사문을 미리 알고 있으므로 ASR 정확도를 사람이 눈으로 판정할 수 있다.

실행:
    cd app/backend && .venv/bin/python ../../tests/harness/spike_nova_protocol.py
    cd app/backend && .venv/bin/python ../../tests/harness/spike_nova_protocol.py --wav u3.wav
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import contextlib
import json
import sys
import uuid
import wave
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "app" / "backend"
SCRIPTS_DIR = REPO_ROOT / "scripts"
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "voice"
HARNESS = REPO_ROOT / ".harness"
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))

from spike_nova_bidirectional import (  # noqa: E402
    NOVA_MODEL_ID,
    DiagnosticTransport,
    _install_swallowed_exception_reporter,
    _open_stream,
    _quiet_close,
    _report,
)

from app.config import Settings, prepare_bedrock_credentials  # noqa: E402

# 공식 문서(nova2-userguide/sonic-input-events.html) 값. 픽스처가 16kHz라 그대로 맞춘다.
SAMPLE_RATE_HZ = 16_000
SAMPLE_SIZE_BITS = 16
CHANNEL_COUNT = 1
# 문서: "audio frames (approximately 32ms each) … maintaining the natural microphone
# sampling cadence". 16kHz·16bit·mono에서 32ms = 512샘플 = 1024바이트.
FRAME_MS = 32
FRAME_BYTES = SAMPLE_RATE_HZ * (SAMPLE_SIZE_BITS // 8) * CHANNEL_COUNT * FRAME_MS // 1000

OPEN_TIMEOUT_S = 20.0
# 마지막 오디오 프레임 이후 이벤트를 더 기다리는 상한. Nova는 사용자가 말을 멈춘 것을
# 감지한 뒤에 응답하므로 여유가 필요하다.
DRAIN_TIMEOUT_S = 30.0

SYSTEM_PROMPT = "You are an English speaking coach. Keep replies to one short sentence."

# ── 발음 교정 스파이크 (`--tools`) ────────────────────────────────────────────
# 묻는 것 하나: **Nova 2 Sonic이 `promptStart.toolConfiguration`을 받고 `toolUse`를
# 내보내는가.** PRD v1.1 §10(발음 시범·재발화)이 "재발화 결과를 기록한다"를 요구하는데,
# Nova의 판정을 DB로 가져오는 수단이 tool 호출뿐이다. `nova.py:73-76`은 "도구 호출이
# 없어 음성 명령 규칙은 지킬 수 없다"고만 적어 두었고 실제로 시도한 기록이 없다.
#
# 답이 "된다"면 설계는 구조화 이벤트로 간다. "안 된다"면 보조 신호(한글 전사·재요청)만으로
# 축소해야 한다 — 설계의 모양이 이 한 번의 왕복에 달려 있어서 먼저 확인한다.
# ⚠️ **이름과 스키마를 여기서 다시 적지 않는다 — 앱 상수를 그대로 보낸다** (A-3, 2026-09-09).
# 왜 바꿨나: 2026-08-27 스파이크는 **자기 스키마**(3필드 · 전부 required · `outcome` enum 에
# `pending` 없음)를 보냈고, 그래서 실증된 것은 **봉투 모양까지**였다 —
# `toolConfiguration`→`tools`→`toolSpec`→`inputSchema.json` 이 문자열이라는 것. 앱이 실제로
# 보내는 것은 **4필드**(`+target_sound`) · **required 2개** · **`outcome` 에 `pending` 포함**
# 이고 그 모양은 실물 왕복을 거친 적이 없었다. 스파이크가 앱과 다른 것을 보내는 동안은
# 「스파이크는 통과했는데 앱은 실패한다」를 만들 수 있다 (이 파일 머리주석의 같은 경고).
# 실증본 원자료는 `runs/2026-08-27-P-tooluse-spike/P-tooluse-nova-protocol.json` 이 보존한다.
# 대조표는 `docs/design/2026-09-08-tasks-md-archive.md` §A-3 이 소유한다.
# ── `--app-prompt` — 프롬프트를 원인에서 배제하거나 지목하기 위한 통제 대조 ─────────────
# 왜 필요한가 (2026-09-09 실측): 같은 `p1m.wav` 로 **스파이크 프롬프트**는 `toolUse` 를 받았고
# **앱 경로**(실물 세션 2건)는 `pronunciation` 프레임 0건이었다. 오디오·스키마·모델이 같으므로
# 남은 차이는 시스템 프롬프트인데, 그것을 **말로 추론하지 않고 재려면** 이 스파이크가 앱
# 프롬프트를 실어 같은 오디오를 한 번 더 보내면 된다. 그러면 앱 경로의 나머지(브라우저 캡처 ·
# 게이트웨이 릴레이)가 변수에서 빠진다.
# ⛔ `build_system_prompt` 를 쓰지 않고 **기반 프롬프트만** 가져온다 — 그 함수는 조립 재료 4개 +
#    드릴 설정값 2개를 요구하고(캡틴 결정 19), 계획·무대를 끼우면 **무엇이 원인인지 다시 흐려진다.**
#    규칙 8~11(발음)은 기반 프롬프트에 **무조건** 들어 있다(직접 확인).
from app.audio_gateway.nova import SYSTEM_PROMPT as APP_SYSTEM_PROMPT  # noqa: E402
from app.models.pronunciation import (  # noqa: E402
    PRONUNCIATION_TOOL_NAME,
    PRONUNCIATION_TOOL_SCHEMA_JSON,
)

TOOL_SYSTEM_PROMPT = (
    "You are an English pronunciation coach for a Korean learner. "
    "When the learner mispronounces a sound, say the whole sentence back with correct "
    "pronunciation and ask them to repeat it. "
    f"Then you MUST call the {PRONUNCIATION_TOOL_NAME} tool to report what you heard. "
    "Keep spoken replies to one or two short sentences."
)


def _tool_configuration() -> dict[str, Any]:
    """앱의 `nova._pronunciation_tool_configuration()` 과 같은 봉투를 만든다.

    ⛔ 이 함수를 앱과 다르게 고치지 않는다 — 그러면 이 스파이크가 관측하는 것이 앱의
    거동이 아니게 되고 A-3 이 다시 열린다. `description` 문구만 스파이크 쪽이 짧다
    (앱은 `for later practice.` 가 붙는다 — 그 차이는 Nova 의 수락 여부에 영향이 없다).
    """
    return {
        "tools": [
            {
                "toolSpec": {
                    "name": PRONUNCIATION_TOOL_NAME,
                    "description": (
                        "Report a pronunciation coaching attempt so the app can store it."
                    ),
                    "inputSchema": {"json": PRONUNCIATION_TOOL_SCHEMA_JSON},
                }
            }
        ]
    }


def build_events(
    prompt_name: str,
    audio_content: str,
    text_content: str,
    with_tools: bool = False,
    system_prompt: str | None = None,
) -> dict[str, Any]:
    """초기화·종료 이벤트를 한곳에 모아 둔다 (공식 문서 스키마 그대로).

    `system_prompt` 를 주면 그것을 쓴다 — `--app-prompt` 가 앱 프롬프트를 실어 통제 대조를
    만드는 경로다. 주지 않으면 기존 거동(`--tools` 면 `TOOL_SYSTEM_PROMPT`, 아니면
    `SYSTEM_PROMPT`)을 그대로 유지한다.
    """
    return {
        "session_start": {
            "event": {
                "sessionStart": {
                    "inferenceConfiguration": {
                        "maxTokens": 1024,
                        "topP": 0.9,
                        "temperature": 0.7,
                    },
                    # Nova 2에서 추가된 필드 — barge-in(AC2) 민감도가 여기서 정해진다.
                    "turnDetectionConfiguration": {"endpointingSensitivity": "MEDIUM"},
                }
            }
        },
        "prompt_start": {
            "event": {
                "promptStart": {
                    "promptName": prompt_name,
                    "textOutputConfiguration": {"mediaType": "text/plain"},
                    "audioOutputConfiguration": {
                        "mediaType": "audio/lpcm",
                        "sampleRateHertz": SAMPLE_RATE_HZ,
                        "sampleSizeBits": SAMPLE_SIZE_BITS,
                        "channelCount": CHANNEL_COUNT,
                        "voiceId": "matthew",
                        "encoding": "base64",
                        "audioType": "SPEECH",
                    },
                    # `--tools`일 때만 실린다 — 없을 때의 기존 거동을 바꾸지 않는다.
                    **({"toolConfiguration": _tool_configuration()} if with_tools else {}),
                }
            }
        },
        "system_start": {
            "event": {
                "contentStart": {
                    "promptName": prompt_name,
                    "contentName": text_content,
                    "type": "TEXT",
                    "interactive": False,
                    "role": "SYSTEM",
                    "textInputConfiguration": {"mediaType": "text/plain"},
                }
            }
        },
        "system_text": {
            "event": {
                "textInput": {
                    "promptName": prompt_name,
                    "contentName": text_content,
                    "content": system_prompt
                    or (TOOL_SYSTEM_PROMPT if with_tools else SYSTEM_PROMPT),
                }
            }
        },
        "system_end": {
            "event": {"contentEnd": {"promptName": prompt_name, "contentName": text_content}}
        },
        "audio_start": {
            "event": {
                "contentStart": {
                    "promptName": prompt_name,
                    "contentName": audio_content,
                    "type": "AUDIO",
                    "interactive": True,
                    "role": "USER",
                    "audioInputConfiguration": {
                        "mediaType": "audio/lpcm",
                        "sampleRateHertz": SAMPLE_RATE_HZ,
                        "sampleSizeBits": SAMPLE_SIZE_BITS,
                        "channelCount": CHANNEL_COUNT,
                        "audioType": "SPEECH",
                        "encoding": "base64",
                    },
                }
            }
        },
        "audio_end": {
            "event": {"contentEnd": {"promptName": prompt_name, "contentName": audio_content}}
        },
        "prompt_end": {"event": {"promptEnd": {"promptName": prompt_name}}},
        "session_end": {"event": {"sessionEnd": {}}},
    }


def read_lpcm(path: Path) -> bytes:
    """WAV 헤더를 벗겨 raw LPCM만 돌려준다 — Nova가 받는 것은 컨테이너가 아니다."""
    with wave.open(str(path)) as wav:
        if (wav.getframerate(), wav.getsampwidth() * 8, wav.getnchannels()) != (
            SAMPLE_RATE_HZ,
            SAMPLE_SIZE_BITS,
            CHANNEL_COUNT,
        ):
            raise SystemExit(
                f"{path.name}이 {SAMPLE_RATE_HZ}Hz/{SAMPLE_SIZE_BITS}bit/mono가 아니다: "
                f"{wav.getframerate()}Hz/{wav.getsampwidth() * 8}bit/{wav.getnchannels()}ch"
            )
        return wav.readframes(wav.getnframes())


async def send_event(stream: Any, payload: dict[str, Any]) -> None:
    from aws_sdk_bedrock_runtime.models import (
        BidirectionalInputPayloadPart,
        InvokeModelWithBidirectionalStreamInputChunk,
    )

    await stream.input_stream.send(
        InvokeModelWithBidirectionalStreamInputChunk(
            value=BidirectionalInputPayloadPart(bytes_=json.dumps(payload).encode())
        )
    )


async def pump_output(receiver: Any, observed: list[dict[str, Any]]) -> None:
    """출력 이벤트를 계속 읽어 분류해 출력한다. 스트림이 끝나면 반환한다."""
    stage: dict[str, str] = {}  # contentId -> "role/generationStage"
    while True:
        chunk = await receiver.receive()
        if chunk is None:
            return
        raw = getattr(getattr(chunk, "value", None), "bytes_", None)
        if not raw:
            continue
        try:
            event = json.loads(raw)["event"]
        except (ValueError, KeyError):
            print(f"  [?] 해석할 수 없는 출력: {raw[:120]!r}")
            continue
        name, body = next(iter(event.items()))
        observed.append({name: body})

        if name == "contentStart":
            extra = body.get("additionalModelFields") or ""
            label = f"{body.get('role')}/{extra}"
            stage[body.get("contentId", "")] = label
            print(f"  [contentStart] type={body.get('type')} {label}")
        elif name == "textOutput":
            label = stage.get(body.get("contentId", ""), "?")
            print(f"  [textOutput]   {label}  {body.get('content')!r}")
        elif name == "audioOutput":
            audio = base64.b64decode(body.get("content", ""))
            head = audio[:4]
            print(
                f"  [audioOutput]  {len(audio)}B  앞 4바이트={head!r} "
                f"(RIFF면 컨테이너, 아니면 raw LPCM)"
            )
        elif name == "contentEnd":
            print(f"  [contentEnd]   type={body.get('type')} stopReason={body.get('stopReason')}")
        elif name == "completionEnd":
            print(f"  [completionEnd] stopReason={body.get('stopReason')}")
        elif name == "usageEvent":
            pass  # 소음
        else:
            print(f"  [{name}] {json.dumps(body, ensure_ascii=False)[:140]}")


async def run(
    wav_name: str,
    realtime: bool,
    silence_ms: int,
    with_tools: bool = False,
    app_prompt: bool = False,
) -> int:
    swallowed: list[BaseException] = []
    _install_swallowed_exception_reporter(swallowed)
    settings = Settings()  # ty: ignore[missing-argument]

    print("[1/6] 자격증명 준비 (앱과 같은 이음새)")
    prepare_bedrock_credentials(settings)

    wav_path = FIXTURE_DIR / wav_name
    lpcm = read_lpcm(wav_path)
    frames = [lpcm[i : i + FRAME_BYTES] for i in range(0, len(lpcm), FRAME_BYTES)]
    print(
        f"[2/6] 입력 준비: {wav_path.name} → raw LPCM {len(lpcm)}B, "
        f"{len(frames)}프레임 × {FRAME_BYTES}B({FRAME_MS}ms), "
        f"{len(lpcm) / (SAMPLE_RATE_HZ * 2):.2f}초"
    )

    from aws_sdk_bedrock_runtime.client import AsyncBedrockRuntimeClient
    from aws_sdk_bedrock_runtime.config import AsyncBedrockRuntimeConfig

    print(f"[3/6] 클라이언트 생성 (region={settings.aws_region})")
    sdk_config = await AsyncBedrockRuntimeConfig.resolve(region=settings.aws_region)
    transport = DiagnosticTransport(sdk_config.transport)
    sdk_config.transport = transport
    client = AsyncBedrockRuntimeClient(config=sdk_config)

    print(f"[4/6] 스트림 열기 ({NOVA_MODEL_ID})")
    stream = await _open_stream(client, NOVA_MODEL_ID, OPEN_TIMEOUT_S)

    prompt_name = str(uuid.uuid4())
    events = build_events(
        prompt_name,
        f"audio-{uuid.uuid4()}",
        f"text-{uuid.uuid4()}",
        with_tools=with_tools,
        system_prompt=APP_SYSTEM_PROMPT if app_prompt else None,
    )
    if app_prompt:
        print(
            f"    시스템 프롬프트 = **앱의 `nova.SYSTEM_PROMPT`** ({len(APP_SYSTEM_PROMPT)}자) — "
            "통제 대조. 스파이크 전용 프롬프트를 쓰지 않는다"
        )
    if with_tools:
        schema = json.loads(PRONUNCIATION_TOOL_SCHEMA_JSON)
        print(
            f"    toolConfiguration 포함 — tool={PRONUNCIATION_TOOL_NAME} "
            f"(앱 상수: 필드 {len(schema['properties'])}개 · "
            f"required {len(schema['required'])}개 · "
            f"outcome enum={schema['properties']['outcome']['enum']})"
        )
    observed: list[dict[str, Any]] = []
    pump: asyncio.Task[None] | None = None

    async def await_and_pump() -> None:
        """`await_output()`은 **서비스가 응답을 시작하기 전까지 반환하지 않는다** —
        HTTP 응답 헤더 자체가 아직 오지 않았기 때문이다(실측: 초기화 이벤트를 보내지
        않고 기다리면 20초 타임아웃). 그래서 수신을 전송과 **동시에** 시작한다."""
        _, receiver = await stream.await_output()
        await pump_output(receiver, observed)

    try:
        pump = asyncio.create_task(await_and_pump(), name="nova-output")

        print("[5/6] 초기화 시퀀스 + 오디오 전송")
        for key in (
            "session_start",
            "prompt_start",
            "system_start",
            "system_text",
            "system_end",
            "audio_start",
        ):
            await send_event(stream, events[key])
        audio_content = events["audio_start"]["event"]["contentStart"]["contentName"]

        async def push(frame: bytes) -> None:
            await send_event(
                stream,
                {
                    "event": {
                        "audioInput": {
                            "promptName": prompt_name,
                            "contentName": audio_content,
                            "content": base64.b64encode(frame).decode("ascii"),
                        }
                    }
                },
            )
            if realtime:
                await asyncio.sleep(FRAME_MS / 1000)

        for index, frame in enumerate(frames):
            await push(frame)
            if index and index % 20 == 0:
                print(f"    … {index}/{len(frames)} 프레임")
        print(f"    발화 {len(frames)}프레임 전송 완료")

        # **무음을 이어 보낸다.** 프레임이 끊기면 endpointing(발화 종료 감지)이 발동할
        # 근거가 없다 — 실측: 프레임 직후 곧바로 contentEnd/sessionEnd를 보내면
        # userSpeechStart만 오고 전사문이 오지 않았다. 마이크는 사람이 말을 멈춘 뒤에도
        # 무음을 계속 흘리므로, 그 조건을 재현해야 한다.
        silence_frames = silence_ms // FRAME_MS
        for _ in range(silence_frames):
            await push(b"\x00" * FRAME_BYTES)
        print(f"    무음 {silence_frames}프레임({silence_ms}ms) 전송 — endpointing 유도")

        print(f"[6/6] 출력 대기 (최대 {DRAIN_TIMEOUT_S:.0f}s) — 세션은 아직 닫지 않는다")
        deadline = asyncio.get_running_loop().time() + DRAIN_TIMEOUT_S
        while asyncio.get_running_loop().time() < deadline:
            if any("completionEnd" in item for item in observed):
                print("    completionEnd 도착 — 대기 종료")
                break
            await asyncio.sleep(0.5)

        print("    종료 시퀀스 전송 (contentEnd → promptEnd → sessionEnd)")
        for key in ("audio_end", "prompt_end", "session_end"):
            await send_event(stream, events[key])
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(asyncio.shield(pump), 10.0)
    finally:
        if pump is not None and not pump.done():
            pump.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await pump
        await _quiet_close(stream)

    # `--tools`는 별도 파일에 쓴다 — N1(3차수 프로토콜 실증) 원자료를 덮지 않는다.
    # ⛔ `--app-prompt`도 또 다른 파일에 쓴다 — 그 둘은 **통제 대조의 두 팔**이라 한쪽이 다른
    #    쪽을 덮으면 대조 자체가 사라진다(2026-09-09).
    if with_tools:
        name = (
            "P-tooluse-appprompt-nova-protocol.json"
            if app_prompt
            else "P-tooluse-nova-protocol.json"
        )
    else:
        name = "N1-nova-protocol.json"
    out = HARNESS / "evidence" / name
    out.write_text(json.dumps(observed, ensure_ascii=False, indent=1))

    kinds: dict[str, int] = {}
    for item in observed:
        for key in item:
            kinds[key] = kinds.get(key, 0) + 1
    user_texts = [b["content"] for i in observed for k, b in i.items() if k == "textOutput"]
    print(f"\n관측 이벤트: {kinds or '없음'}")
    print(f"전사문/텍스트 {len(user_texts)}건: {user_texts}")
    print(f"raw -> {out}")

    if with_tools:
        # 스파이크의 유일한 질문에 대한 답. 이름이 정확히 무엇으로 오는지 모르므로
        # 'tool'이 들어간 이벤트를 전부 훑는다.
        tool_events = {k: v for k in kinds for v in [kinds[k]] if "tool" in k.lower()}
        print(f"\n[tool use 판정] tool 관련 이벤트: {tool_events or '없음'}")
        if tool_events:
            for item in observed:
                for k, b in item.items():
                    if "tool" in k.lower():
                        print(f"  [{k}] {json.dumps(b, ensure_ascii=False)[:400]}")
            print("→ Nova가 toolConfiguration을 받아들이고 tool 이벤트를 냈다.")
        else:
            print(
                "→ tool 이벤트가 오지 않았다. promptStart는 거부되지 않았으나(오류 없음)\n"
                "  Nova가 tool을 호출하지 않았다. 프롬프트 강제력·스키마 형태·모델 지원\n"
                "  세 가능성이 남는다 — 설계는 보조 신호 축소안으로 가야 한다."
            )

    if transport.saw_error_status or swallowed:
        _report(transport, swallowed)
        print("\nFAIL: 오류 응답 또는 삼켜진 예외가 있다.", file=sys.stderr)
        return 1
    if not user_texts:
        print(
            "\nFAIL: 텍스트 출력이 하나도 오지 않았다 — 초기화 시퀀스나 오디오 포맷을 다시 본다.",
            file=sys.stderr,
        )
        return 1
    print("\nPASS: Nova가 초기화 시퀀스를 받아들이고 텍스트 이벤트를 돌려줬다.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wav", default="u1.wav")
    ap.add_argument(
        "--silence-ms", type=int, default=1600, help="발화 뒤에 붙일 무음 길이 — endpointing 유도용"
    )
    ap.add_argument(
        "--no-realtime",
        action="store_true",
        help="32ms 케이던스 없이 최대 속도로 보낸다 (케이던스 요구 여부 확인용)",
    )
    ap.add_argument(
        "--tools",
        action="store_true",
        help="promptStart에 toolConfiguration을 실어 Nova의 tool use 지원을 확인한다 "
        "(PRD v1.1 §10 발음 교정 설계의 선행 검증). 발음 픽스처와 함께 쓴다: "
        "--wav p1m.wav --tools",
    )
    ap.add_argument(
        "--app-prompt",
        action="store_true",
        help="스파이크 전용 프롬프트 대신 앱의 nova.SYSTEM_PROMPT 를 실어 보낸다 — "
        "「앱 경로에서 발음 tool 이 불리지 않는 것이 프롬프트 탓인가」를 재는 통제 대조. "
        "같은 오디오로 --tools 단독과 대조한다: --wav p1m.wav --tools --app-prompt",
    )
    args = ap.parse_args()
    return asyncio.run(
        run(
            args.wav,
            realtime=not args.no_realtime,
            silence_ms=args.silence_ms,
            with_tools=args.tools,
            app_prompt=args.app_prompt,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
