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
from app.models.plan import PlanQuestion, SessionInstruction
from app.models.pronunciation import (
    PRONUNCIATION_TOOL_NAME,
    PRONUNCIATION_TOOL_SCHEMA_JSON,
    parse_tool_payload,
)
from app.models.scenario import SessionScenario

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
# 가리켜야 모델이 어느 절이 덮이는지 안다.
#
# 값이 두 곳(이 상수 + 규칙 1 본문)에 있는 이유는 `SYSTEM_PROMPT`를 **f-string으로 만들지
# 않기 때문**이다 — 만들면 보간은 되지만 프롬프트 본문의 중괄호가 해석되고, 지시문 전문을
# 그대로 grep·읽는 것이 나빠진다. 프롬프트는 평문으로 두는 쪽이 낫다는 판단이고, 두 값이
# 갈라지는 것은 `test_the_base_level_range_constant_matches_the_fixed_prompt`가 막는다.
_BASE_LEVEL_RANGE = "A2-B1"

# 무대 블록 제목. 계획 블록의 마지막 줄이 이것을 **되짚으므로**(아래 `_FOCUS_BEATS_SETTING`)
# 두 문구가 같은 낱말(`today's setting`)로 서로를 가리켜야 모델이 어느 블록을 말하는지 안다.
_SETTING_HEADER = "Today's setting:"

# 드릴 지시. **문구가 지표와 맞물려 있다** — 설계 2판은 *"ask it / (답) / ask one follow-up /
# say it again"*이라는 고정 4단계를 열거했는데 그중 코치 턴은 **3개**였고 기대값은
# `drill_turns_min = 4`를 곱했다. 즉 **모델이 지시를 글자 그대로 완벽히 지켜도 드릴마다 1턴
# 미달**이고 매 세션 경고가 떴다(H-4). 캡틴 결정 10이 *"집계된 미달을 지시문 수정의 입력으로
# 쓴다"*이므로 그 오차는 **지시문을 잘못 고치도록 유도**한다. → 고정 단계를 열거하지 않고
# 「exchange 최소 N회」로 말해 문구와 지표가 같은 단위를 센다.
# ⚠️ **`turns`라는 낱말을 쓰지 않는다.** exchange 1회 = **코치 발화 뒤에 오는 사용자 발화 1건**이다
# — 아래 문구의 *"you say something, the learner answers"*가 정의한 그대로이고, 결과 조회가 세는
# 단위와 같다(설계서 §2.3의 `speaker = 'user' and prev = 'agent'`).
# ⛔ **방향을 뒤집지 마라.** 「사용자 발화 뒤에 오는 코치 발화」로 세면 세션이 학습자 발화로
# 끝나는 정상 종료 모양에서 **12 라운드를 정확히 채운 완전 순응 세션이 11로 세어지고** 매 세션
# 경고가 뜬다 — H-4가 이름 붙인 실패와 같은 부류다(문구와 지표의 단위가 갈린다). 그 방향 정정은
# 설계 4판이 했고 SQL 은 Batch C 가 소유한다. **이 문구가 정의의 정본이다.**
# ⚠️ f-string 이 아니라 `.format`인 이유는 `SYSTEM_PROMPT`를 평문으로 두는 것과 같다 — 모듈
# 상수는 런타임 값을 보간할 수 없다. 다른 중괄호가 없으므로 `.format`이 안전하다.
_DRILL_INSTRUCTION = """\
- Work through these questions one at a time, and stay on each one for at least {turns}
  exchanges. An exchange is one round: you say something, the learner answers. To fill
  them, follow up on what the learner just said and have them say it again a different
  way. That repeat is practice, not a correction — it does not count against the
  one-correction-per-turn limit in rule 4."""

# 결정 9의 예외 — *"시나리오 문구가 패턴을 지정하는 경우만"* 계획이 이긴다. 무대 문구가 짧아
# 실제로 드물지만, 프롬프트에 적어 두는 것이 «드물기를 바라는 것»보다 낫다.
_FOCUS_BEATS_SETTING = (
    "- If today's setting suggests a different pattern than the focus above, follow the focus."
)


def build_system_prompt(
    known_sounds: Sequence[str],
    plan: SessionInstruction | None,
    questions: Sequence[PlanQuestion],
    scenario: SessionScenario | None,
    *,
    drill_count: int,
    drill_turns_min: int,
) -> str:
    """세션용 지시문 = 기본 문구 + 놓친 소리 목록 + **오늘의 무대** + **오늘의 계획** (G-3).

    **블록 순서: `SYSTEM_PROMPT` → 놓친 소리 → `Today's setting:` → `Today's plan:`**
    (설계서 §2.2). 무대가 목표보다 **먼저** 읽혀야 하고, 계획 블록의 마지막 줄이 앞의 setting을
    **되짚어** 우선순위를 말할 수 있다. 뒤집으면 그 줄이 아직 나오지 않은 블록을 가리킨다.

    넷 중 아무것도 없으면 결과는 `SYSTEM_PROMPT` **그 자체**다 — 계획 없이 시작하는
    경로(AS4)에는 이 함수가 아무것도 덧붙이지 않는다. ⚠️ `SYSTEM_PROMPT` **자체는 이
    태스크에서 바뀌었다**(규칙 7 신설 + 발음 번호 8~11) — 2026-09-03 마이크 검증이 확인한
    문구와 같지 않다.

    **인자에 기본값을 두지 않는다** (설계서 §2.1의 C-1). 두면 호출부가 재료를 빠뜨려도 조용히
    통과해 **「질문이 안 실린 세션」·「무대 없는 세션」이 정상처럼 보인다** — 이 설계가 메우려는
    공백이 정확히 그 모양이다(데이터는 DB에 있었고 읽는 쪽이 없었다).

    ⚠️ **왜 드릴 설정값도 인자인가** (캡틴 판정 2026-09-08). 캡틴 결정 15의 「인자 4개」는
    **조립 재료**(놓친 소리 · 계획 · 질문 · 무대)를 센 것이고 그 결정이 답한 질문은 *"`questions`가
    실릴 자리가 있나"*였다 — **설정값의 전달 경로는 그 결정이 다루지 않았다.** 그래서 `drill_count`·
    `drill_turns_min`을 인자로 받는 것은 결정 15 위반이 아니다. 근거는 둘이다:

    1. **이 함수는 순수 함수로 남는다.** 여기서 `get_settings()`를 부르면 같은 인자가 프로세스
       환경에 따라 **다른 프롬프트**를 낸다 — 조립된 문구가 `.env`에 조용히 묶인다.
    2. **테스트가 값을 주입할 자리가 남는다.** 설계서 §6이 요구한 「기대값 경계 4건」과 H-5
       tripwire가 값 주입에 의존하므로, 전역에서 읽으면 그 판별력이 통째로 사라진다.

    ⛔ **G-3를 근거로 들지 않는다** — 그것은 내가 한 번 잘못 적었던 다리다. 이 모듈은 이미
    `from app.config import Settings, prepare_bedrock_credentials`를 하므로 `get_settings()`가
    **새 의존 간선을 만들지 않는다.** 그리고 `factory.py`의 G-3는 *"**소켓**이 조립하면 이음매가
    사라진다"*라서 nova가 설정을 읽는 것과 무관하다. 값의 소유자는 `Settings` 하나이고
    `factory.create_voice_adapter`가 옮긴다.

    **놓친 소리 목록**: 문법 워커에만 있던 §5.6 재사용 규약을 발음 경로에도 만든다. 목록만
    보여주는 것으로는 부족하다 — **그 키를 다시 쓰라는 지시**가 없으면 Nova가 같은 소리에
    새 키를 지어내고 (`th_as_s` vs `theta_to_s`) 반복 오류가 서로 다른 패턴으로
    흩어진다(설계서 §10 미결 3). ⚠️ 여기 실리는 키는 **Nova에게만 보이는 값**이다. 학습자
    화면에는 나가지 않는다 (설계서 §10 미결 4 — 결과 응답에서 이미 뺐다).

    **오늘의 계획**(§5.2 가변부): 계획을 문장으로 바꾸는 것은 **읽는 쪽의 일이다** —
    `session_plans.instruction`은 구조로 저장되고(jsonb) 여기서 문장이 된다. 설계서가 이
    변환을 정하지 않아 계획서 Task 10이 정했다.

    ⚠️ **고정 규칙과 같은 축을 말하는 줄은 대체한다는 것을 블록 안에 문장으로 적는다.**
    적지 않으면 두 지시가 함께 실려 모순된다. **대체하는 축은 아래 목록에서 둘뿐이다 —
    「힌트 시점」과 「목표 수준」.** 나머지는 전부 비대체이고 축마다 근거가 다르다.
    ⚠️ **"같은 축이다"가 곧 "계획이 이긴다"는 뜻이 아니다.**

    ⚠️ **후보의 개수를 세지 않는다.** 이 문장은 한때 *"같은 축으로 보이는 후보는 **셋**이고 그중
    둘만 대체한다"*였는데, 이 배치가 축을 셋 더하면서(무대 · 질문↔규칙2 · 질문↔규칙3 · 드릴 반복 ·
    우선순위) **그 수를 안 고쳐** 리뷰 2라운드에 걸렸다 — 블록이 늘 때마다 함께 밀리는 수라서
    구조적으로 낡는다. **대체하는 쪽은 세어도 안전하다**: 늘어나려면 고정 규칙을 덮는다는 판단이
    새로 필요하고 그것은 캡틴 결정을 요구한다. 그리고 명시한 두 이름이 있으므로 읽는 사람이
    목록에서 `대체한다`를 훑어 **직접 검산할 수 있다.**
    ⛔ **축을 더할 때 이 문단을 함께 읽어라** — 새 축이 대체 쪽이면 위 두 이름을 고쳐야 한다.

    * **힌트 시점** ↔ 규칙 2·5("긴 침묵 뒤에만 시작 힌트") — **대체한다.**
    * **목표 수준** ↔ 규칙 1의 `A2-B1 level` — **대체한다.** `models/plan.py`의 validator가
      `instruction.target_level`을 "대화 상대가 실제로 말하는 수준"으로 정의하고, 학습자
      프로필(h-doc)이 현재 수준의 패턴에 **고착시키지 말고 확장형을 조금씩 얹으라**고
      규정한다. ⚠️ 규칙 1의 **턴 길이** 부분(`Keep each of your turns to …`)은 대체 대상이
      **아니다** — 코치 자신의 턴 길이는 그대로다. 대체 범위를 넓히지 않는다.
    * **오늘의 상황** ↔ 규칙 3("일상 화제에서 시작해 몸이 풀리면 업무로 옮긴다") —
      **대체하지 않는다.** 규칙 3의 **순서 자체가** 프로필의 난이도 상향 경로(일상 → 업무
      협업 → 프로젝트 리딩 → AWS 보고)에서 왔고, 프로필은 "목표 수준을 현재 수준으로
      착각하면 첫 세션에서 얼어붙는다"를 흔한 실수로 이름 붙여 경계한다. 계획이 그 순서를
      덮으면 **프로필이 이름 붙인 실패를 코드로 허용**하는 것이 된다. 비용이 비대칭이다:
      규칙 3이 이기면 비용은 "오늘 상황 목록이 재정렬된다"뿐이고, `contexts`가 이기면
      첫 세션을 잃는다 — 되돌릴 수 없는 쪽이 한쪽에만 있다. 그래서 `- Situations to use
      today:`는 **대체 문장을 달지 않는다**(규칙 3 아래에서 고를 후보 목록으로 읽힌다).
      ⚠️ 이 판단을 테스트로 못박지 않는다 — 아무 코드도 만들지 않는 문구의 **부재**를
      단정하는 것이라 지킬 회귀가 없고, 규칙마다 tripwire를 늘리는 방향은 확장되지 않는다.
      **이 축은 이 docstring이 소유한다.**
    * **오늘의 무대** ↔ 규칙 3("일상 화제에서 시작해 몸이 풀리면 업무로 옮긴다") —
      **대체하지 않는다.** 캡틴 결정 9가 시나리오를 *"「오늘의 상황」과 같은 축"*으로 정했고,
      그 축의 비대체 근거는 위 `contexts` 항목과 **같은 것**이다(비용 비대칭 + h-doc이 이름 붙인
      실패). ⚠️ 그래서 setting 블록에도 대체 문장을 달지 않는다.
    * **질문 목록** ↔ 규칙 2("하나씩 묻고 멈춘다") — **대체하지 않는다. 강화한다.** 같은
      방향이라 `one at a time`이 규칙 2를 되짚는다.
    * **질문 목록** ↔ 규칙 3 — **대체하지 않는다.** `contexts`와 같은 처리다. ⛔ 그래서 문구에
      **`in this order`를 넣지 않는다** — 순서를 지정하면 규칙 3의 순서와 부딪히고, 결정 9가
      세운 「계획 = 목표, 무대·순서는 안 덮는다」 틀을 벗어난다.
    * **드릴 반복** ↔ 규칙 4(교정 1건/턴) — **명시적으로 갈라낸다.** 규칙 11이 *"발음 교정도
      교정이다"*로 상한을 못박은 **선례의 반대 방향**이다. 적지 않으면 모델이 드릴 반복을
      교정으로 세어 **드릴이 1턴에 끝난다**.
    * **우선순위 문장**(`_FOCUS_BEATS_SETTING`) ↔ 결정 9의 예외 — **계획이 이긴다.** 무대 문구가
      패턴을 지정하는 경우만이고, 그 판정을 프롬프트에 문장으로 적어 둔다.

    ⚠️ **`title`은 지시문에 싣지 않는다.** 규칙 6이 *"Never read JSON, lists, or metadata out
    loud"*이고 제목은 **화면용 라벨**이다. `prompt_template` 하나로 무대가 성립한다. ⚠️ 이 방어는
    시드 교체 **전에는 공허했다** — `title`과 `prompt_template`이 바이트 동일이라 제목을 빼도 같은
    문자열이 들어갔다(설계서 §2.2). 캡틴 결정 14의 시드 교체가 두 값을 갈라놓아 실질을 갖는다.

    ⚠️ **`sentence_length`의 주어는 학습자다** (`services/plan.py`의 프롬프트가 "as **the
    learner** is ready"로 그렇게 정의한다). 조립문에서 주어를 빼면 규칙 1의 `your turns`와
    섞여 코치 자신의 턴 길이 지시로 읽힌다.

    **값이 없는 줄은 아예 넣지 않는다** — 소리 기록 0건(지금 dev DB의 상태)·`contexts` 빈 목록·
    무대 부재·질문 빈 목록이 모두 같은 처리를 받는다. 빈 목록에 제목만 남기면 Nova가 "목록이
    비었다"를 지시로 오해할 여지가 생긴다. `focus`는 최소 1개가 보장되므로(`SessionInstruction`)
    그 처리가 필요 없다.

    ⛔ **열거하는 질문은 `questions[:drill_count]`다** (H-5). 전부 열거하고 기대값만 깎으면
    `drill_count`가 **대화를 바꾸지 않고 통과 문턱만 바꾸는 노브**가 된다 — 캡틴 결정 1은 드릴
    횟수를 *"설정값에 두고 **읽는다**"*이고, 읽어서 대화를 바꿔야 그 결정이 지켜진다. 기대값은
    `services/sessions.record_drill_turns_expected`가 **같은 슬라이스**로 센다.
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
    if scenario is not None:
        prompt = f"{prompt}\n\n{_SETTING_HEADER}\n{scenario.prompt_template}"
    if plan is None:
        # 계획이 없으면 `questions`도 무시한다 — 드릴 줄은 계획 블록 **안**에 있다.
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
    drilled = questions[:drill_count]
    if drilled:
        lines.append(_DRILL_INSTRUCTION.format(turns=drill_turns_min))
        lines.extend(
            f"    {number}. {question.prompt} ({question.context})"
            for number, question in enumerate(drilled, start=1)
        )
    if scenario is not None:
        # 무대가 없으면 이 줄은 아직 나오지 않은 블록을 가리킨다 — 그래서 넣지 않는다.
        lines.append(_FOCUS_BEATS_SETTING)
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
