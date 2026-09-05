"""Nova 2 Sonic 양방향 스트림 어댑터 — 포트의 실물 구현 (설계서 §5.3·§7).

프로토콜은 **추측하지 않았다.** `tests/harness/spike_nova_protocol.py`(N-1 PASS)로
실제 음성 왕복을 확인한 시퀀스와 `tests/harness/runs/2026-08-26-N1/`의 원자료가
이 파일의 근거다. 그 실측에서 나온, 문서만 읽고는 알 수 없었던 것 넷:

1. **`await_output()`은 초기화 이벤트를 보내기 전에 반환하지 않는다.** HTTP 응답 헤더
   자체가 오지 않기 때문이다(먼저 기다리면 20초 타임아웃). 그래서 `start()`는 수신
   태스크를 **먼저 띄우고** 초기화 이벤트를 보낸다 — 순서를 뒤집으면 연결이 매달린다.
2. **문서에 없는 이벤트가 온다** — `userSpeechStart`/`userSpeechEnd`. 파서는 모르는
   이벤트를 로그만 남기고 넘긴다. 다음 필드 추가가 세션을 끊어선 안 된다.
3. **사용자 ASR은 `generationStage: FINAL` 한 블록으로만 온다.** 사용자 부분 전사문이
   없다 — 화면의 "듣고 있어요"는 `userSpeechStart`~`End` 구간이 근거다.
4. **오디오 출력은 헤더 없는 raw LPCM이다**(앞 4바이트가 `RIFF`가 아니었다). 포트가
   `bytes`만 약속하므로 포맷 변환은 클라이언트의 몫이다.
5. **tool use가 동작한다** — 2026-08-27 스파이크(`runs/2026-08-27-P-tooluse-spike/`).
   `promptStart.toolConfiguration`이 받아들여지고 `contentStart(type=TOOL, role=TOOL)` →
   `toolUse` → `contentEnd(stopReason=TOOL_USE)` 순서로 온다. `inputSchema.json`은
   **JSON 문자열**이다(객체가 아니다). TOOL 블록은 ASSISTANT 텍스트보다 **앞**에 오고,
   Nova는 재발화 **전에** tool을 부른다(`outcome: "pending"`) — 그래서 tool 호출 1건이
   판정된 시도 1건이 아니다(설계서 F3). `toolResult`는 **돌려보내지 않는다**: 안 보내도
   `END_TURN`으로 정상 종료했다(캡틴 결정 2026-08-28). 그 관측은 1회뿐이라 다중 턴
   거동은 5차수 관측 대상이다.

**무음 프레임은 만들지 않는다.** 스파이크는 WAV가 끝나면 프레임이 끊겨 endpointing을
유도할 무음을 넣어야 했지만, 실제 마이크는 사용자가 말을 멈춘 뒤에도 계속 흐른다.
다만 사용자가 **종료를 누르면** 프레임이 끊겨 endpointing이 발동하지 않을 수 있어,
`close()`가 `contentEnd`로 오디오 content를 명시적으로 닫는다.

자격증명은 `app.config` 하나에서만 온다 (F5) — 이 모듈은 키를 직접 읽지 않는다.
어떤 구현이 붙는지 세션 러너는 모르고(G3), 선택은 `factory.create_voice_adapter`에만 있다.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import logging
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from typing import Any

from app.audio_gateway.port import (
    AdapterEvent,
    InterruptionEvent,
    PronunciationEvent,
    Speaker,
    SpeechBoundaryEvent,
    TranscriptEvent,
)
from app.config import Settings, prepare_bedrock_credentials
from app.models.plan import SessionInstruction
from app.models.pronunciation import (
    PRONUNCIATION_TOOL_NAME,
    PRONUNCIATION_TOOL_SCHEMA_JSON,
    parse_tool_payload,
)

logger = logging.getLogger(__name__)

# 공식 문서(nova2-userguide/sonic-input-events.html) 값 = N-1 실측 값.
SAMPLE_RATE_HZ = 16_000
SAMPLE_SIZE_BITS = 16
CHANNEL_COUNT = 1
BYTES_PER_SAMPLE = SAMPLE_SIZE_BITS // 8
# 문서: "audio frames (approximately 32ms each) … maintaining the natural microphone
# sampling cadence". 16kHz·16bit·mono에서 32ms = 512샘플 = 1024바이트.
FRAME_MS = 32
FRAME_BYTES = SAMPLE_RATE_HZ * BYTES_PER_SAMPLE * CHANNEL_COUNT * FRAME_MS // 1000

# SDK docstring: "The response is returned in a stream that remains open for 8 minutes."
# 세션 롤오버는 이번 범위가 아니다 — 상한에 닿으면 조용히 매달리지 않고 스트림을 끝내
# 세션이 닫히게 한다(닫히지 않으면 세션이 영원히 `active` 고아로 남는다).
STREAM_LIMIT_SECONDS = 8 * 60.0

# 스트림 정리 상한. 정리가 늦는 것 때문에 세션 종료 기록이 막히면 안 된다.
CLOSE_TIMEOUT_SECONDS = 5.0

# 스파이크에서 실증된 추론 설정. 근거 문서가 정한 값이 아니라 스파이크 발명값이다.
_INFERENCE_CONFIGURATION = {"maxTokens": 1024, "topP": 0.9, "temperature": 0.7}

_SPECULATIVE_STAGE = "SPECULATIVE"
_INTERRUPTED_STOP_REASON = "INTERRUPTED"
# 턴 경계 신호. 실물 계측(2026-09-03)에서 `completionEnd`는 한 번도 오지 않았고 이것만 왔다.
_END_TURN_STOP_REASON = "END_TURN"
_ROLE_TO_SPEAKER: dict[str, Speaker] = {"USER": "user", "ASSISTANT": "agent"}
# TOOL content는 발화가 아니다. 이 role만 명시적으로 걸러야 하는 이유는 `_on_text_output`의
# `.get(role, "user")` 폴백이다 — 그냥 두면 tool JSON이 학습자 발화로 저장되고 분석 job까지
# 등록된다. 다른 모르는 role은 계속 user로 떨어뜨린다(USER가 이름을 바꿔도 전사문을 잃지
# 않는 쪽이 낫다는 기존 판단을 뒤집지 않는다).
_TOOL_ROLE = "TOOL"

# 대화 규칙의 정본은 `docs/agent-system-prompt.md`다. 여기에는 **Nova가 실제로 할 수 있는
# 부분만** 옮긴다: 오류 메모리 JSON 산출은 Claude 워커의 일이다(§5.2). 그대로 넣으면 모델이
# JSON을 소리로 읽는다. 학습자 수준·목표는 h-doc 프로필과 같다.
#
# 규칙 8~11(발음)은 2026-08-27 스파이크가 실효를 본 문구를 기준으로 한다 — 4차수에서 Nova가
# 발음을 지적하지 않은 것은 **능력 부재가 아니라 지시 부재였다**(설계서 §2). 규칙 11이
# 규칙 4의 상한을 다시 못박는 이유는 교정 예산이 코드로 강제되지 않기 때문이다(설계서 D5-1).
#
# 규칙 7(65% 발화 목표)은 `docs/PRD.md:59`·R10-8이 요구하는데 **지시문에 없었다**(2026-09-04
# 점검: `65%` 0건). 발음 절 **앞**에 넣어 발음 규칙이 8~11로 밀렸다 — 규칙 11이 번호로
# 가리키는 규칙 4는 밀리지 않으므로 그 상호 참조는 그대로 산다.
#
# ⚠️ 음성 명령 규칙은 여전히 빼 둔다. tool 호출은 이제 되지만 발음 보고용 tool 하나뿐이고,
# 명령 실행 경로(`voice_command` 발화)는 이 어댑터에 없다.
SYSTEM_PROMPT = """\
You are OhMyEnglish, a warm, practical English speaking coach for a Korean learner.

The learner can handle greetings, small talk, and simple daily-life sentences, and mostly
speaks in short patterns such as "I want to...", "I need to...", and "I'd like to...".
Their goal is to join business meetings and report project status in English.

Rules:
1. Speak clear, natural English at A2-B1 level. Keep each of your turns to one or two
   short sentences.
2. Ask one question at a time, then stop and wait for the learner. A pause means they are
   thinking — do not fill it with another question, an example, or a rephrasing. Only after
   a long silence, offer one short sentence starter and then stop again.
3. Start from daily-life topics and move toward work updates once the learner is warmed up.
4. Do not correct every mistake. At most one correction per turn: quote what the learner
   said, give one natural correction, and ask them to say it again. Never pair a correction
   with a new question in the same turn — correct, ask for the repeat, and then stop.
5. If the learner is stuck, offer a short sentence starter instead of the full answer.
6. Never read JSON, lists, or metadata out loud.
7. Aim for the learner to speak at least 65% of the session. Keep your own turns short.

Pronunciation coaching:
8. You hear the learner's actual audio. The transcript does not show pronunciation
   errors, so you are the only one who can notice them.
9. Grammar first. On most turns, correct grammar and leave pronunciation alone. Take up
   pronunciation only when a sound is so far off that the sentence is hard to understand —
   never for a mild accent. When you do take it up, name the sound that was off, say the
   whole sentence back with correct pronunciation, and ask the learner to repeat it.
10. Call report_pronunciation_coaching twice: once with outcome "pending" right after you
    have modeled the sentence, and again with correct, incorrect, or unclear once you have
    heard the learner repeat it. Always include target_sound - a short reusable key for the
    sound that was off, such as th_as_s or f_as_p - so the app can group repeat offenders.
11. A pronunciation correction is a correction. It counts against the one-per-turn limit
    in rule 4 — never add it on top of a grammar correction in the same turn."""

# 규칙 1이 말하는 기본 수준. 계획 블록이 "이 수준을 대체한다"고 말할 때 **같은 낱말**로
# 가리켜야 모델이 어느 절이 덮이는지 안다. `SYSTEM_PROMPT`는 평문 리터럴이라 여기서
# 보간할 수 없으므로 값이 두 곳에 있다 — 갈라지는 것은
# `test_the_base_level_range_constant_matches_the_fixed_prompt`가 막는다.
_BASE_LEVEL_RANGE = "A2-B1"


def build_system_prompt(known_sounds: Sequence[str], plan: SessionInstruction | None = None) -> str:
    """세션용 지시문 = 위 기본 문구 + 놓친 소리 목록 + **오늘의 계획** (G-3, 캡틴 결정 B-4).

    소리 목록도 계획도 없으면 결과는 `SYSTEM_PROMPT` **그 자체**다 — 계획 없이 시작하는
    경로(AS4)에는 이 함수가 아무것도 덧붙이지 않는다. ⚠️ `SYSTEM_PROMPT` **자체는 이
    태스크에서 바뀌었다**(규칙 7 신설 + 발음 번호 8~11) — 2026-09-03 마이크 검증이 확인한
    문구와 같지 않다.

    **놓친 소리 목록**: 문법 워커에만 있던 §5.6 재사용 규약을 발음 경로에도 만든다. 목록만
    보여주는 것으로는 부족하다 — **그 키를 다시 쓰라는 지시**가 없으면 Nova가 같은 소리에
    새 키를 지어내고 (`th_as_s` vs `theta_to_s`) 반복 오류가 서로 다른 패턴으로
    흩어진다(설계서 §10 미결 3). ⚠️ 여기 실리는 키는 **Nova에게만 보이는 값**이다. 학습자
    화면에는 나가지 않는다 (설계서 §10 미결 4 — 결과 응답에서 이미 뺐다).

    **오늘의 계획**(§5.2 가변부): 계획을 문장으로 바꾸는 것은 **읽는 쪽의 일이다** —
    `session_plans.instruction`은 구조로 저장되고(jsonb) 여기서 문장이 된다. 설계서가 이
    변환을 정하지 않아 계획서 Task 10이 정했다.

    ⚠️ **고정 규칙과 같은 축을 말하는 줄은 대체한다는 것을 블록 안에 문장으로 적는다.**
    적지 않으면 두 지시가 함께 실려 모순된다. 축은 **둘**이다(S2-10 리뷰가 잡았다 — 처음에는
    힌트 시점만 적었다):
    * **힌트 시점** ↔ 규칙 2·5("긴 침묵 뒤에만 시작 힌트")
    * **목표 수준** ↔ 규칙 1의 `A2-B1 level`. 계획이 이긴다: `models/plan.py`의 validator가
      `instruction.target_level`을 "대화 상대가 실제로 말하는 수준"으로 정의하고, 학습자
      프로필(h-doc)이 현재 수준에 고착시키지 말라고 규정한다. ⚠️ 규칙 1의 **턴 길이**
      부분(`Keep each of your turns to …`)은 대체 대상이 **아니다** — 코치 자신의 턴 길이는
      그대로다. 대체 범위를 넓히지 않는다.

    ⚠️ **`sentence_length`의 주어는 학습자다** (`services/plan.py`의 프롬프트가 "as **the
    learner** is ready"로 그렇게 정의한다). 조립문에서 주어를 빼면 규칙 1의 `your turns`와
    섞여 코치 자신의 턴 길이 지시로 읽힌다.

    **값이 없는 줄은 아예 넣지 않는다** — 소리 기록 0건(지금 dev DB의 상태)과 `contexts`
    빈 목록이 같은 처리를 받는다. 빈 목록에 제목만 남기면 Nova가 "목록이 비었다"를 지시로
    오해할 여지가 생긴다. `focus`는 최소 1개가 보장되므로(`SessionInstruction`) 그 처리가
    필요 없다.
    """
    prompt = SYSTEM_PROMPT
    if known_sounds:
        listed = ", ".join(known_sounds)
        prompt = (
            f"{prompt}\n\n"
            "Sounds this learner has missed before:\n"
            f"{listed}\n"
            "If one of them is off again, reuse that exact key as target_sound instead of\n"
            "inventing a new one — repeat offenders must group under one key."
        )
    if plan is None:
        return prompt
    forms = ", ".join(f"{item.pattern_key} ({item.target_form})" for item in plan.focus)
    lines = [
        "Today's plan:",
        f"- Target level for today, instead of the {_BASE_LEVEL_RANGE} level in rule 1: "
        f"{plan.target_level}",
        f"- Focus on: {forms}",
        f"- Aim for the learner's sentences to be this shape: {plan.sentence_length}",
    ]
    if plan.contexts:
        lines.append(f"- Situations to use today: {', '.join(plan.contexts)}")
    lines.append(
        f"- Hint timing for today, instead of the general hint rule above: {plan.hint_timing}"
    )
    return f"{prompt}\n\n" + "\n".join(lines)


def _pronunciation_tool_configuration() -> dict[str, Any]:
    """`promptStart.toolConfiguration`.

    ⚠️ **스파이크가 실측한 것은 봉투 모양까지다** — `toolConfiguration` → `tools` →
    `toolSpec` → `inputSchema.json`이 **문자열**이라는 것. **필드 구성은 실증되지 않았다**:
    스파이크는 3필드(전부 required, `outcome` enum에 `pending` 없음)를 보냈고 우리는
    4필드(required 2개, `pending` 포함)를 보낸다. 설계 §4.2를 따른 것이고 JSON Schema에서
    더 느슨한 방향이라 거부될 근거는 없지만, **실물 왕복으로 확인한 적이 없다**
    (그 차이는 `TASKS.md` A-3이 표로 기록한다).

    이름과 스키마의 소유자는 `app.models.pronunciation` 하나다. 여기서 문자열을 다시 적으면
    어댑터가 보내는 이름과 파서가 기다리는 이름이 갈라져 tool 이벤트가 조용히 버려진다.
    """
    return {
        "tools": [
            {
                "toolSpec": {
                    "name": PRONUNCIATION_TOOL_NAME,
                    "description": (
                        "Report a pronunciation coaching attempt so the app can store it "
                        "for later practice."
                    ),
                    # Sonic은 이 값을 **문자열**로 받는다 (객체가 아니다 — 스파이크 실측).
                    "inputSchema": {"json": PRONUNCIATION_TOOL_SCHEMA_JSON},
                }
            }
        ]
    }


def _generation_stage(body: dict[str, Any]) -> str | None:
    """`contentStart.additionalModelFields`에서 `generationStage`를 꺼낸다.

    실측에서 이 필드는 **JSON 문자열**로 온다(`'{"generationStage":"FINAL"}'`). 모양이
    바뀌어도 죽지 않아야 한다 — 못 읽으면 `None`이고, 그때 전사문은 확정으로 취급된다
    (사용자 발화를 잃는 쪽이 화면에 한 줄 더 뜨는 쪽보다 나쁘다).
    """
    fields = body.get("additionalModelFields")
    if isinstance(fields, str):
        try:
            fields = json.loads(fields)
        except ValueError:
            logger.debug("additionalModelFields를 해석할 수 없다: %r", fields[:80])
            return None
    if not isinstance(fields, dict):
        return None
    stage = fields.get("generationStage")
    return stage if isinstance(stage, str) else None


def _is_control_payload(text: str) -> bool:
    """전사문이 아니라 **제어 신호**인가 (I-5).

    실물에서 barge-in 때 `{ "interrupted" : true }`가 ASSISTANT `textOutput`으로 온다
    (마이크 2회 실측, 세션 `182e7d49` seq 9·15). 그것을 전사문으로 만들면 기계 문자열이
    학습 기록에 섞이고 agent 발화 수가 부풀어 "학습자 65% 발화" 지표가 왜곡된다.

    **문자열 상수로 박지 않는 이유**: Nova가 공백을 바꿔 보낸다. **포함 검사를 하지 않는
    이유**: 중괄호를 말하는 정상 발화("I said {like this}")를 잃는다. 그래서 **JSON 객체로
    파싱되는지**만 본다 — 사람 발화가 JSON 객체가 되는 경우는 없다.
    """
    stripped = text.strip()
    if not stripped.startswith("{"):
        return False
    try:
        return isinstance(json.loads(stripped), dict)
    except ValueError:
        # `json.JSONDecodeError`가 `ValueError`의 하위 클래스다 — 파싱 실패는 곧 사람 말이다.
        return False


def _offset_ms(body: dict[str, Any]) -> int | None:
    offset = body.get("inputAudioOffsetMs")
    return offset if isinstance(offset, int) else None


class NovaEventTranslator:
    """Nova 출력 이벤트 → 포트 이벤트. 순수 상태기계다(I/O·시계를 보지 않는다).

    상태를 갖는 이유는 두 가지다. ① `generationStage`는 `contentStart`에만 실려 오고
    `textOutput`에는 없으므로 `contentId`로 이어야 한다. ② ASSISTANT 텍스트가
    `SPECULATIVE`로만 오고 끝나는 턴이 있어(N-1 실측) 턴이 끝날 때 그 문장을 확정으로
    올려야 한다 — 올리지 않으면 agent 질문이 전사문에 한 행도 남지 않는다.
    """

    def __init__(self) -> None:
        self._stage_by_content: dict[str, str | None] = {}
        self._role_by_content: dict[str, str] = {}
        # 한 턴의 SPECULATIVE agent 청크들. **리스트인 이유**는 한 completion에 텍스트가
        # 여러 블록으로 오기 때문이다 — 문자열 하나로 두고 덮어쓰면 마지막 블록만 남아
        # 시범 문장("Say this after me: …")이 전사문에서 사라진다(발음 스파이크 실측).
        self._pending_agent_chunks: list[str] = []
        # 이번 턴에 **이미 한 행으로 올린** agent 청크들. Nova가 같은 텍스트를 FINAL로
        # 재전송하므로(I-6 실측) 그것을 알아보고 버리기 위한 기억이다.
        self._flushed_agent_chunks: set[str] = set()

    def translate(self, name: str, body: dict[str, Any]) -> list[AdapterEvent]:
        if not isinstance(body, dict):
            logger.warning("Nova 이벤트 %s의 본문이 객체가 아니다 — 넘긴다", name)
            return []
        if name == "contentStart":
            return self._on_content_start(body)
        if name == "textOutput":
            return self._on_text_output(body)
        if name == "audioOutput":
            return self._on_audio_output(body)
        if name == "toolUse":
            return self._on_tool_use(body)
        if name == "contentEnd":
            return self._on_content_end(body)
        if name == "userSpeechStart":
            return [SpeechBoundaryEvent(speaking=True, offset_ms=_offset_ms(body))]
        if name == "userSpeechEnd":
            return [SpeechBoundaryEvent(speaking=False, offset_ms=_offset_ms(body))]
        if name == "completionEnd":
            return self._flush_pending_agent_text()
        # `usageEvent`·`completionStart`, 그리고 아직 문서에 없는 이벤트가 여기로 온다.
        logger.debug("Nova 이벤트 %s를 흘려보냈다", name)
        return []

    def _on_content_start(self, body: dict[str, Any]) -> list[AdapterEvent]:
        content_id = body.get("contentId")
        if not isinstance(content_id, str):
            return []
        self._stage_by_content[content_id] = _generation_stage(body)
        role = body.get("role")
        if isinstance(role, str):
            self._role_by_content[content_id] = role
        return []

    def _on_text_output(self, body: dict[str, Any]) -> list[AdapterEvent]:
        text = body.get("content")
        if not isinstance(text, str) or not text.strip():
            # 빈 전사문은 세션이 어차피 버린다(`session._store_final`) — 여기서 끊는다.
            return []
        if _is_control_payload(text):
            logger.debug("제어 페이로드를 전사문으로 만들지 않았다 (I-5): %r", text[:40])
            return []
        raw_content_id = body.get("contentId")
        content_id = raw_content_id if isinstance(raw_content_id, str) else ""
        # 실측에서는 `textOutput`에도 role이 실려 온다 — 없으면 contentStart에서 이어 온다.
        raw_role = body.get("role")
        role = raw_role if isinstance(raw_role, str) else self._role_by_content.get(content_id, "")
        if role == _TOOL_ROLE:
            logger.debug("TOOL content의 textOutput을 전사문으로 만들지 않았다")
            return []
        speaker = _ROLE_TO_SPEAKER.get(role, "user")
        # `SPECULATIVE`만 예고다. 모르는 값·없는 값은 확정으로 취급한다(위 `_generation_stage`).
        stage = self._stage_by_content.get(content_id)
        kind = "partial" if stage == _SPECULATIVE_STAGE else "final"
        if speaker == "agent":
            if kind == "partial":
                self._pending_agent_chunks.append(text)
            elif text in self._flushed_agent_chunks:
                # **재전송이다** — 이 청크는 이미 이번 턴의 행에 실렸다 (I-6). 블록마다
                # 행을 만들면 한 턴이 N행으로 갈린다. 같은 청크가 또 오는 경우를 위해
                # 소비하며 지운다.
                self._flushed_agent_chunks.discard(text)
                return []
            else:
                # 아직 아무것도 올리지 않은 턴에서 온 FINAL이다 — 그것이 정본이므로
                # 쌓인 청크를 버린다. 안 버리면 같은 내용이 청크 + FINAL로 두 번 실린다.
                self._pending_agent_chunks.clear()
        return [TranscriptEvent(kind=kind, text=text, speaker=speaker)]

    def _on_tool_use(self, body: dict[str, Any]) -> list[AdapterEvent]:
        """발음 tool을 포트 이벤트로 바꾼다 (설계서 §4.2).

        **예외를 던지지 않는다.** 발음 기록 실패가 대화를 끊으면 안 된다 — 검증은
        `models.pronunciation.parse_tool_payload`가 하고 그것도 던지지 않는다(강등·폐기).
        모르는 tool은 조용히 넘긴다: 나중에 다른 tool이 생겨도 발음 경로가 오작동하지
        않아야 한다.
        """
        tool_name = body.get("toolName")
        if tool_name != PRONUNCIATION_TOOL_NAME:
            # **warning이다.** 선언한 tool이 하나뿐이라 오탐 비용이 0이고, 모델이 이름을
            # 줄여 부르면(`report_pronunciation`) 모든 발음 이벤트가 조용히 사라진다.
            # 설계서 §3.1은 놓침이 조용히 일어나선 안 된다고 요구한다 — 문서화된 기동이
            # `--log-level warning`이라 debug는 프로덕션에서 한 줄도 보이지 않는다.
            logger.warning("발음 tool이 아닌 %r을 무시했다", tool_name)
            return []
        raw = body.get("content")
        report = parse_tool_payload(raw if isinstance(raw, str) else "")
        if report is None:
            # `parse_tool_payload`가 이미 왜 버렸는지 경고를 남겼다.
            return []
        return [
            PronunciationEvent(
                target_form=report.target_form,
                outcome=report.outcome,
                spoken_form=report.spoken_form,
                target_sound=report.target_sound,
            )
        ]

    def _on_audio_output(self, body: dict[str, Any]) -> list[AdapterEvent]:
        content = body.get("content")
        if not isinstance(content, str):
            return []
        try:
            return [base64.b64decode(content, validate=True)]
        except ValueError:
            logger.warning("base64로 해석할 수 없는 audioOutput을 버렸다")
            return []

    def _on_content_end(self, body: dict[str, Any]) -> list[AdapterEvent]:
        content_id = body.get("contentId")
        if isinstance(content_id, str):
            self._stage_by_content.pop(content_id, None)
            self._role_by_content.pop(content_id, None)
        if body.get("stopReason") == _INTERRUPTED_STOP_REASON:
            return [InterruptionEvent()]
        if body.get("stopReason") == _END_TURN_STOP_REASON:
            # 턴이 끝났다 — 쌓인 청크를 **한 행으로** 올린다 (I-6). 이 신호는 FINAL
            # 재전송보다 **앞에** 오므로, 여기서 올려야 agent 행이 사용자 다음 발화보다
            # 먼저 들어가 `sequence_no` 순서가 보존된다. 쌓인 것이 없으면 no-op이다.
            return self._flush_pending_agent_text()
        return []

    def _flush_pending_agent_text(self) -> list[AdapterEvent]:
        """턴이 끝났다 — 예고로만 온 agent 청크들을 **이어붙여** 한 행으로 확정한다.

        끊긴 턴(barge-in)에서도 올린다: 사용자가 이미 그 질문의 일부를 들었으므로
        전사문에서 통째로 사라지는 편이 더 나쁘다.

        **왜 이어붙이는가.** 한 completion = 한 턴인데 Nova는 그 턴의 텍스트를 여러 블록으로
        보낸다(발음 스파이크 실측: SPECULATIVE 2블록, 사이에 AUDIO 블록, FINAL 재전송 없음).
        두 번째 블록이 선행 공백과 `\\n\\n`으로 시작하는 것이 별개 메시지가 아니라 **연속
        청크**라는 증거다. 청크마다 행을 만들면 전사문이 부풀고, 마지막 하나만 남기면 시범
        문장이 사라진다 — 그래서 이어붙여 한 행으로 만든다.
        """
        if not self._pending_agent_chunks:
            return []
        chunks = list(self._pending_agent_chunks)
        self._pending_agent_chunks.clear()
        text = "".join(chunks)
        if not text.strip():
            return []
        # 무엇을 올렸는지 기억한다 — Nova가 같은 청크를 FINAL로 재전송하면 알아보고 버린다.
        self._flushed_agent_chunks = {chunk for chunk in chunks if chunk.strip()}
        return [TranscriptEvent(kind="final", text=text, speaker="agent")]


StreamOpener = Callable[[], Awaitable[Any]]


async def _open_bedrock_stream(settings: Settings) -> Any:
    """실물 양방향 스트림을 연다. 자격증명 획득은 `app.config`에만 있다 (F5)."""
    from aws_sdk_bedrock_runtime.client import AsyncBedrockRuntimeClient
    from aws_sdk_bedrock_runtime.config import AsyncBedrockRuntimeConfig
    from aws_sdk_bedrock_runtime.models import (
        InvokeModelWithBidirectionalStreamOperationInput,
    )

    prepare_bedrock_credentials(settings)
    # 이 SDK는 config 직접 생성을 금지한다 — `resolve()`가 유일한 경로다.
    sdk_config = await AsyncBedrockRuntimeConfig.resolve(region=settings.aws_region)
    client = AsyncBedrockRuntimeClient(config=sdk_config)
    return await client.invoke_model_with_bidirectional_stream(
        InvokeModelWithBidirectionalStreamOperationInput(model_id=settings.nova_model_id)
    )


class NovaVoiceAdapter:
    """`port.VoiceAdapter`의 Nova 2 Sonic 구현.

    `open_stream`은 테스트 이음매다 — 가짜 스트림을 넣으면 실물 호출 없이 이벤트
    시퀀스·파싱·종료 순서를 전부 관측할 수 있다. 기본값은 실물이다.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        open_stream: StreamOpener | None = None,
        stream_limit_seconds: float = STREAM_LIMIT_SECONDS,
        instructions: str | None = None,
    ) -> None:
        # 세션마다 조립된 지시문(G-3). `None`이면 기본 문구 — 스텁·기존 차수 재현이
        # 흔들리지 않게 "주지 않으면 이전과 같다"를 기본값으로 둔다.
        self.instructions = instructions or SYSTEM_PROMPT
        self._settings = settings
        self._open_stream: StreamOpener = open_stream or (lambda: _open_bedrock_stream(settings))
        self._stream_limit_seconds = stream_limit_seconds
        self._prompt_name = str(uuid.uuid4())
        self._audio_content_name = f"audio-{uuid.uuid4()}"
        self._text_content_name = f"text-{uuid.uuid4()}"
        self._stream: Any | None = None
        self._pump: asyncio.Task[None] | None = None
        self._queue: asyncio.Queue[AdapterEvent | None] = asyncio.Queue()
        self._translator = NovaEventTranslator()
        self._audio_open = False
        self._closed = False

    # --- 포트 구현 ---

    async def start(self) -> None:
        self._stream = await self._open_stream()
        # **수신을 먼저 띄운다.** `await_output()`은 초기화 이벤트를 받기 전에 반환하지
        # 않으므로(실측), 순서를 뒤집으면 여기서 영원히 기다린다.
        self._pump = asyncio.create_task(self._pump_output(), name="nova-output")
        for payload in self._initialization_events():
            await self._send_event(payload)
        self._audio_open = True

    async def send_audio(self, frame: bytes) -> None:
        if not self._audio_open:
            logger.debug("오디오 경로가 닫혀 있어 프레임(%d바이트)을 버렸다", len(frame))
            return
        if not frame or len(frame) % BYTES_PER_SAMPLE:
            # 16bit raw LPCM이면 나올 수 없는 길이다 — 다른 포맷(webm/opus)이거나 잘린
            # 프레임이다. 그대로 보내면 Nova가 잡음을 전사하고 원인을 알 수 없다.
            logger.warning("샘플 경계에 맞지 않는 오디오 프레임(%d바이트)을 버렸다", len(frame))
            return
        try:
            await self._send_event(
                {
                    "event": {
                        "audioInput": {
                            "promptName": self._prompt_name,
                            "contentName": self._audio_content_name,
                            "content": base64.b64encode(frame).decode("ascii"),
                        }
                    }
                }
            )
        except Exception:
            # 프레임 하나가 대화를 끊지 않는다. 스트림이 정말 죽었으면 출력 펌프가 끝나며
            # 세션이 닫힌다 — 여기서 예외를 올리면 그 경로를 앞질러 릴레이가 터진다.
            logger.warning("오디오 프레임 전송이 실패해 오디오 경로를 닫는다", exc_info=True)
            self._audio_open = False

    async def events(self) -> AsyncIterator[AdapterEvent]:
        while True:
            event = await self._queue.get()
            if event is None:  # 출력 펌프가 끝났다 = 대화 종료
                return
            yield event

    async def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._audio_open = False
        if self._stream is not None:
            for payload in self._termination_events():
                # 이미 끊긴 스트림에 보내는 것은 오류가 아니다 — 종료를 막지 않는다.
                with contextlib.suppress(Exception):
                    await self._send_event(payload)
        if self._pump is not None and not self._pump.done():
            self._pump.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._pump
        if self._stream is not None:
            await self._quiet_close(self._stream)

    # --- 내부 ---

    async def _pump_output(self) -> None:
        """출력 이벤트를 큐로 옮긴다. 스트림이 끝나거나 상한에 닿으면 반환한다."""
        stream = self._stream
        try:
            if stream is None:
                return
            _, receiver = await stream.await_output()
            loop = asyncio.get_running_loop()
            deadline = loop.time() + self._stream_limit_seconds
            while True:
                remaining = deadline - loop.time()
                if remaining <= 0:
                    logger.warning(
                        "Nova 스트림 상한(%.0f초)에 닿았다 — 세션을 닫는다 "
                        "(롤오버는 아직 구현 범위가 아니다)",
                        self._stream_limit_seconds,
                    )
                    return
                try:
                    chunk = await asyncio.wait_for(receiver.receive(), remaining)
                except TimeoutError:
                    continue  # 다음 반복에서 상한을 판정한다
                if chunk is None:
                    return
                for event in self._translate_chunk(chunk):
                    self._queue.put_nowait(event)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Nova 출력 스트림이 예외로 끝났다 — 세션을 닫는다")
        finally:
            self._queue.put_nowait(None)

    def _translate_chunk(self, chunk: Any) -> list[AdapterEvent]:
        raw = getattr(getattr(chunk, "value", None), "bytes_", None)
        if not raw:
            return []
        try:
            event = json.loads(raw)["event"]
            name, body = next(iter(event.items()))
        except (AttributeError, KeyError, StopIteration, TypeError, ValueError):
            logger.warning("Nova 출력을 해석할 수 없다: %r", raw[:120])
            return []
        return self._translator.translate(name, body)

    async def _send_event(self, payload: dict[str, Any]) -> None:
        from aws_sdk_bedrock_runtime.models import (
            BidirectionalInputPayloadPart,
            InvokeModelWithBidirectionalStreamInputChunk,
        )

        stream = self._stream
        if stream is None:
            raise RuntimeError("Nova 스트림이 아직 열리지 않았다")
        await stream.input_stream.send(
            InvokeModelWithBidirectionalStreamInputChunk(
                value=BidirectionalInputPayloadPart(bytes_=json.dumps(payload).encode())
            )
        )

    async def _quiet_close(self, stream: Any) -> None:
        """정리 실패가 세션 종료 기록을 막지 않게 한다.

        `close()`는 내부적으로 `await_output()`을 다시 기다리므로, 이미 취소된 상태에서는
        `CancelledError`(BaseException 계열)가 올라온다 — 스파이크가 실측한 모양이다.
        """
        try:
            await asyncio.wait_for(stream.close(), CLOSE_TIMEOUT_SECONDS)
        except (Exception, asyncio.CancelledError):
            logger.debug("Nova 스트림 close를 조용히 넘겼다", exc_info=True)

    def _initialization_events(self) -> list[dict[str, Any]]:
        """실증된 초기화 시퀀스 (스파이크와 같은 순서·같은 필드)."""
        return [
            {
                "event": {
                    "sessionStart": {
                        "inferenceConfiguration": _INFERENCE_CONFIGURATION,
                        # Nova 2에서 추가된 필드 — barge-in(AC2) 민감도가 여기서 정해진다.
                        "turnDetectionConfiguration": {
                            "endpointingSensitivity": self._settings.nova_endpointing_sensitivity
                        },
                    }
                }
            },
            {
                "event": {
                    "promptStart": {
                        "promptName": self._prompt_name,
                        "textOutputConfiguration": {"mediaType": "text/plain"},
                        "audioOutputConfiguration": {
                            "mediaType": "audio/lpcm",
                            "sampleRateHertz": SAMPLE_RATE_HZ,
                            "sampleSizeBits": SAMPLE_SIZE_BITS,
                            "channelCount": CHANNEL_COUNT,
                            "voiceId": self._settings.nova_voice_id,
                            "encoding": "base64",
                            "audioType": "SPEECH",
                        },
                        # 발음 판정을 DB로 가져오는 **유일한** 수단이다 (설계서 §4.2) —
                        # 전사문에는 발음의 흔적이 0이다(4차수 P2 실측). 봉투 모양은
                        # 스파이크가 실측했고 필드 구성은 아직 실물 미검증이다(아래 함수).
                        "toolConfiguration": _pronunciation_tool_configuration(),
                    }
                }
            },
            {
                "event": {
                    "contentStart": {
                        "promptName": self._prompt_name,
                        "contentName": self._text_content_name,
                        "type": "TEXT",
                        "interactive": False,
                        "role": "SYSTEM",
                        "textInputConfiguration": {"mediaType": "text/plain"},
                    }
                }
            },
            {
                "event": {
                    "textInput": {
                        "promptName": self._prompt_name,
                        "contentName": self._text_content_name,
                        "content": self.instructions,
                    }
                }
            },
            {
                "event": {
                    "contentEnd": {
                        "promptName": self._prompt_name,
                        "contentName": self._text_content_name,
                    }
                }
            },
            {
                "event": {
                    "contentStart": {
                        "promptName": self._prompt_name,
                        "contentName": self._audio_content_name,
                        "type": "AUDIO",
                        # 대화 중 사용자가 끼어들 수 있어야 한다 (barge-in).
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
        ]

    def _termination_events(self) -> list[dict[str, Any]]:
        return [
            {
                "event": {
                    "contentEnd": {
                        "promptName": self._prompt_name,
                        "contentName": self._audio_content_name,
                    }
                }
            },
            {"event": {"promptEnd": {"promptName": self._prompt_name}}},
            {"event": {"sessionEnd": {}}},
        ]
