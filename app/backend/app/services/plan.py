"""`plan_next_session` job 처리 — Task 4~7이 이 모듈을 채운다.

지금은 워커가 job 종류로 분기할 수 있게 계약만 고정한다 (계획서 Task 3).

`build_plan_prompt`(Task 6)는 `PlanInput`(Task 4)을 Claude에게 보낼 프롬프트 문자열로
조립하는 **순수 함수**다 — DB에 닿지 않는다. 설계서 §4의 3계층 순서를 그대로 따른다:
① 오늘 다뤄야 하는 목록(due) → ② 최근 창(recent) → ③ 만성 사실(chronic) →
④ 발음 시도(별도 절) → ⑤ 출력 규격. 목록은 이미 계산된 **사실**이라 프롬프트가 그것을
다시 계산하라고 요구하지 않고, 무엇이 오늘의 약점이고 난이도를 어떻게 조절할지는 모델이
판단한다(§3.2의 승인된 경계).

발음 절을 문법 절과 분리하는 이유(§4.4 주의 2): 발음의 빈도는 **시도 수** 기준이고 문법은
**발생 수** 기준이라 계산 근거가 다르다. 한 정렬에 섞으면 발음이 부당하게 위/아래로 간다.

출력 규격(`_OUTPUT_SPEC`)의 키 이름은 Task 5의 검증 계약(`app.models.plan.PlanOutput`)과
**글자 그대로 같아야** 한다 — `extra="forbid"`라서 하나만 어긋나도 실물 모델 응답이 전부
거부된다. 지시문 크기 상한은 넣지 않는다 — 설계서 §3.4가 "구체 수치는 Nova 초기화 시간을
실측해 정한다"고 했고, 그 실측은 아직 하지 않았다(발명하지 않는다).

**리뷰 라운드 1 (2026-09-05)에서 잡힌 것 — 다시 만들지 말 것**:
* **Critical-1**: 복습·만성 목록에 `pattern_id`가 없으면 모델이 UUID를 지어낸다. 지어낸
  값이 형식만 맞으면 `focus_pattern_ids uuid[]`에 **FK가 없어서** 조용히 저장되고 복습·초점
  조회가 영구히 어긋난다 — 대역 테스트로는 안 드러난다. 그래서 각 줄에 `pattern_id`를 싣고
  `_OUTPUT_SPEC`이 "목록의 id를 그대로 복사하라, 지어내지 마라"를 명시한다. 짧은 번호로
  되매핑하는 대안은 기각했다 — 대응표라는 새 층이 새 실패 모드(목록 밖 번호)를 만든다.
* **Important-1**: 키 이름이 맞아도 **제약**(세 `target_level`의 일치, CEFR 값역,
  `instruction.focus`도 1~2개, 빈 문자열 금지)을 프롬프트가 말하지 않으면 Task 5가 응답을
  거부한다. `_OUTPUT_SPEC`에 그 제약을 문장으로 적어 넣었다.
  ⚠️ **고침 중에 필드 단위로 다시 대조해 2건을 더 찾았다**: ① `PlanOutput` 계열 전부가
  `extra="forbid"`라서 **모르는 키 하나가 응답 전체를 죽인다** — "Return one JSON object and
  nothing else"는 JSON **밖**의 산문만 막고 키는 막지 않는다 ② 열거한 셋(`sentence_length`·
  `hint_timing`·`level.reason`) 밖에도 `questions.prompt`·`context`·`contexts` 항목·`notes`
  항목이 `min_length=1`이다. 출력의 **모든** 문자열이 그 제약을 받으므로 한 문장으로 적었다.
"""

from __future__ import annotations

import logging
from uuid import UUID

import asyncpg

from app.services.chronic import ChronicMetric
from app.services.jobs import ClaimedJob, report_failure
from app.services.plan_input import PlanInput, PronunciationTally, RecentUtterance
from app.services.review import DueReview
from app.workers.claude_client import ClaudeClient

logger = logging.getLogger(__name__)

# Task 7이 저장까지 채우기 전까지 정상 대상 job이 수렴하는 사유. `raise`가 아니라
# 이 문구로 report_failure를 부르는 이유(리뷰 라운드 1, I4): `raise`는 워커의 바깥
# `except`로 새서 이 job을 `running`에 lease가 풀리지 않은 채 남기고(complete도
# fail_or_retry도 안 불린다), lease 만료(5분×5회)까지 걸리며, 기록되는 사유도
# "lease expired without report"라는 거짓 진단이 된다. `report_failure`는 큐를
# 정상 백오프로 재큐하고 참인 사유를 남긴다 — 가시성은 아래 `logger.warning`으로
# 옮긴다(이 리포는 지정된 실행에서 INFO가 안 보이는 함정 H-Z가 있어 WARNING 이상이어야 한다).
PLAN_NOT_IMPLEMENTED = "plan generation is not implemented yet (Task 7)"

# h-doc 학습자 프로필이 문구를 지배한다: 단문·단일 절 기준 · 일상 → 업무 협업 순서 ·
# 목표 수준(AWS 보고 문형)으로 예문을 만들지 않는다. 아래 목록은 이미 계산된 사실이라
# 모델에게 다시 계산하라고 요구하지 않는다 — 무엇이 약점이고 얼마나 어려운지는 모델이 정한다.
_PROMPT_HEADER = """\
You plan the next English speaking session for one Korean learner.

Learner profile: can handle greetings, small talk, and simple daily-life sentences; mostly uses
short patterns such as "I want to...", "I need to...", "I'd like to...". Long-term goal is to
join business meetings and report project status. Start from daily life and move toward work
topics — do not write examples at the long-term goal level.

Sentence length: default to short, single-clause sentences built on patterns like the ones above.
Extend length and clause count gradually as the learner is ready — never jump straight to the
long-term goal level. This applies to instruction.sentence_length and to the example questions.

You decide what the weakness really is, which situations to practise it in, and the difficulty.
The lists below are **facts**, already computed. Do not recompute them and do not drop any of them.
"""

# 발음은 시도 수 기준, 문법은 발생 수 기준이라 계산 근거가 다르다(§4.4 주의 2) — 한 정렬에
# 섞으면 발음이 부당하게 위/아래로 간다. 그래서 별도 절로 두고 그 사실을 문장으로도 알린다.
# ⚠️ 닫는 `"""`를 새 줄에 두지 않는다(리뷰 M2) — 그러면 이 문자열이 `\n`으로 끝나
# `build_plan_prompt`의 `"\n".join`이 개행을 하나 더 얹는다. 다른 절 제목(예: "Chronic
# metrics ...:")은 한 줄 문자열이라 그 문제가 없다 — 발음 절만 제목과 목록 사이에
# 빈 줄이 하나 더 생겼었다.
_PRONUNCIATION_NOTE = """\
Pronunciation attempts (separate list — counted per attempt, not per error occurrence, so do not
rank these against the grammar counts above):"""

# 키 이름은 Task 5(`app.models.plan.PlanOutput`, `extra="forbid"`)와 글자 그대로 같아야 한다 —
# 하나만 어긋나면 실물 모델 응답이 검증 단계에서 전부 거부된다. 초점 1~2개·질문 3~5개는
# PRD.md:188(R11-2)의 문서 근거가 있는 값이고, 그 외 임계값은 넣지 않는다(발명하지 않는다).
# ⚠️ 지시문 크기 상한도 넣지 않는다 — 설계서 §3.4가 그 수치는 실측 후에 정한다고 했다.
_OUTPUT_SPEC = """\
Return one JSON object and nothing else. Keys:
- focus: one or two patterns, each {pattern_id, pattern_key, target_form}. Pick from the lists
  above and copy pattern_id exactly as given there — never invent one.
- questions: three to five items, each {prompt, context}. Same target form, different
  situations.
- target_level: one CEFR code (A1|A2|B1|B2|C1|C2). It must equal level.target_level and
  instruction.target_level — all three must match.
- reason: one short sentence **in Korean**, addressed to the learner, saying why today's practice
  is this. Never leave it empty.
- instruction: {target_level, focus:[{pattern_key, target_form}], sentence_length, hint_timing,
  contexts}. instruction.target_level must equal the top-level target_level. instruction.focus
  also has one or two items (pattern_key and target_form only — no pattern_id here).
  sentence_length and hint_timing are short English phrases spliced into the tutor's
  instructions and must not be empty. contexts is the list of situations for today.
- level: {action: keep|up|down, target_level, reason}. Move at most one CEFR step from the current
  level, in either direction. Going down is allowed and is better than staying too hard. reason
  must not be empty.
- notes: observations worth keeping that numbers cannot hold — for example "adds articles in short
  sentences but drops them once the sentence gets longer". Empty list is fine.

Do not add any key that is not listed above — one unknown key makes the whole response invalid.
Every string anywhere in the object must be non-empty.
"""


# 목록이 0건이면 제목은 유지하고 명시적 placeholder(예: "(none due today)")를 넣는다 —
# `audio_gateway/nova.py`(§10 R10-2 계열)의 선례("0건이면 블록을 아예 넣지 않는다. 제목만
# 남으면 빈 목록 자체를 지시로 오해할 여지가 있다")와 **일부러 다르다**: 여기 5개 절은
# 항상 같은 순서로 고정돼야 모델이 "이 절이 왜 통째로 없지?"를 궁금해하지 않는다 —
# "없다"고 명시적으로 말하는 쪽이 이 자리에서는 모호성이 더 적다(리뷰 M1).


def _format_due_reviews(due_reviews: list[DueReview]) -> str:
    """설계서 §4.1 — 오늘 다뤄야 하는 목록. 판정을 다시 하지 않고 그대로 나열한다.

    `pattern_id`를 반드시 싣는다(리뷰 Critical-1) — 안 실으면 모델이 UUID를 지어내고,
    형식만 맞은 가짜 id가 FK 없는 `focus_pattern_ids`에 조용히 저장돼 복습 조회가 어긋난다.
    """
    if not due_reviews:
        return "(none due today)"
    return "\n".join(
        f"- {review.pattern_key} [pattern_id: {review.pattern_id}] ({review.category}): "
        f'target form "{review.target_form}", due since {review.next_review_at.isoformat()}, '
        f"mastery {review.mastery_score}"
        for review in due_reviews
    )


def _format_recent(recent: list[RecentUtterance]) -> str:
    """설계서 §4.2 — 최근 창(14일) 안의 학습 발화와 그에 붙은 교정."""
    if not recent:
        return "(no learner utterances in this window)"
    lines: list[str] = []
    for utterance in recent:
        lines.append(f'- [{utterance.said_at.isoformat()}] "{utterance.transcript}"')
        for correction in utterance.corrections:
            lines.append(
                f"    correction: {correction.pattern_key} ({correction.category}) — "
                f'"{correction.original_span}" -> "{correction.correction}" '
                f"({correction.severity}, confidence {correction.confidence})"
            )
    return "\n".join(lines)


def _format_chronic(chronic: list[ChronicMetric], chronic_pattern_ids: set[UUID]) -> str:
    """설계서 §6.1/§6.2 — 만성 지표는 사실만 담는다. 판정 문구는 결정론적 신호 하나뿐이다:
    3단계(1·3·7일)를 완주한 뒤 재발한 패턴에 사실 문장을 덧붙인다. 만성 여부의 최종 판단은
    모델이 한다 — 여기서 "만성이다"라고 선언하지 않는다.

    `pattern_id`를 싣는 이유는 `_format_due_reviews`와 같다(리뷰 Critical-1). `span`·`max_gap`은
    `timedelta`를 `str()`로 새면 `"9 days, 0:00:00"`처럼 나와 `0:00:00`이 별개 필드로 읽힐 수
    있다(리뷰 Important-6) — 그래서 `.days` 정수만 낸다. `max_gap`은 발생이 1건뿐인 패턴이면
    `None`이다(`chronic.py`).
    """
    if not chronic:
        return "(no chronic metrics yet)"
    lines: list[str] = []
    for metric in chronic:
        max_gap_text = "n/a" if metric.max_gap is None else f"{metric.max_gap.days} days"
        line = (
            f"- {metric.pattern_key} [pattern_id: {metric.pattern_id}] ({metric.category}): "
            f"frequency {metric.frequency}, seen in {metric.recurring_sessions} sessions "
            f"across {metric.recurring_days} days, span {metric.span.days} days, "
            f"longest gap {max_gap_text}"
        )
        if metric.pattern_id in chronic_pattern_ids:
            line += "  [completed all three review stages before, then came back]"
        lines.append(line)
    return "\n".join(lines)


def _format_pronunciation(pronunciation: list[PronunciationTally]) -> str:
    """설계서 §4.4 — 발음 시도 집계. 점수·등급은 요구하지 않는다.

    하지 않는 것 목록: requirements-summary.md:120-121.
    """
    if not pronunciation:
        return "(no pronunciation attempts in this window)"
    return "\n".join(
        f"- {tally.target_sound}: {tally.outcome}, {tally.attempts} attempts, "
        f"last seen {tally.last_seen.isoformat()}"
        for tally in pronunciation
    )


def build_plan_prompt(data: PlanInput) -> str:
    """다음 세션 계획 프롬프트를 조립한다 (설계서 §4, 계획서 Task 6). 순수 함수 — DB 없음.

    절 순서는 §4의 3계층 그대로다: ① 오늘 다뤄야 하는 목록 → ② 최근 창 → ③ 만성 사실 →
    ④ 발음 시도(별도 절) → ⑤ 출력 규격. 출력 규격의 키 이름은 Task 5의 검증 계약과 같아야
    하고(모듈 docstring 참조), 지시문 크기 상한은 아직 넣지 않는다(§3.4).
    """
    sections = [
        _PROMPT_HEADER,
        "Due for review today (facts, already computed — do not recompute):",
        _format_due_reviews(data.due_reviews),
        "",
        f"Recent learner utterances ({data.window_from.isoformat()} to "
        f"{data.window_to.isoformat()}):",
        _format_recent(data.recent),
        "",
        "Chronic metrics (facts only — you decide whether a pattern counts as chronic):",
        _format_chronic(data.chronic, data.chronic_pattern_ids),
        "",
        _PRONUNCIATION_NOTE,
        _format_pronunciation(data.pronunciation),
        "",
        f"Current level: {data.current_level}",
        "",
        _OUTPUT_SPEC,
    ]
    return "\n".join(sections)


async def process_plan(pool: asyncpg.Pool, claude: ClaudeClient, job: ClaimedJob) -> None:
    """계획 생성 job 하나를 처리한다. Task 4~7이 이 함수의 안을 채운다.

    지금은 대상 검증만 한다 — 계약을 먼저 고정해 워커 분기가 이 태스크에서 완결되게 한다.
    """
    if job.session_id is None:
        await report_failure(pool, job, f"plan job {job.id} has no session target")
        return
    logger.warning("job %s: plan generation not implemented yet (Task 7)", job.id)
    await report_failure(pool, job, PLAN_NOT_IMPLEMENTED)
