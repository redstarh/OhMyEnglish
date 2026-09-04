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

You decide what the weakness really is, which situations to practise it in, and the difficulty.
The lists below are **facts**, already computed. Do not recompute them and do not drop any of them.
"""

# 발음은 시도 수 기준, 문법은 발생 수 기준이라 계산 근거가 다르다(§4.4 주의 2) — 한 정렬에
# 섞으면 발음이 부당하게 위/아래로 간다. 그래서 별도 절로 두고 그 사실을 문장으로도 알린다.
_PRONUNCIATION_NOTE = """\
Pronunciation attempts (separate list — counted per attempt, not per error occurrence, so do not
rank these against the grammar counts above):
"""

# 키 이름은 Task 5(`app.models.plan.PlanOutput`, `extra="forbid"`)와 글자 그대로 같아야 한다 —
# 하나만 어긋나면 실물 모델 응답이 검증 단계에서 전부 거부된다. 초점 1~2개·질문 3~5개는
# PRD.md:188(R11-2)의 문서 근거가 있는 값이고, 그 외 임계값은 넣지 않는다(발명하지 않는다).
# ⚠️ 지시문 크기 상한도 넣지 않는다 — 설계서 §3.4가 그 수치는 실측 후에 정한다고 했다.
_OUTPUT_SPEC = """\
Return one JSON object and nothing else. Keys:
- focus: one or two patterns, each {pattern_id, pattern_key, target_form}. Pick from the lists
  above.
- questions: three to five items, each {prompt, context}. Same target form, different
  situations.
- target_level: one CEFR code. It must equal level.target_level.
- reason: one short sentence **in Korean**, addressed to the learner, saying why today's practice
  is this. Never leave it empty.
- instruction: {target_level, focus:[{pattern_key, target_form}], sentence_length, hint_timing,
  contexts} — sentence_length and hint_timing are short English phrases that will be spliced into
  the tutor's instructions. contexts is the list of situations for today.
- level: {action: keep|up|down, target_level, reason}. Move at most one CEFR step from the current
  level, in either direction. Going down is allowed and is better than staying too hard.
- notes: observations worth keeping that numbers cannot hold — for example "adds articles in short
  sentences but drops them once the sentence gets longer". Empty list is fine.
"""


def _format_due_reviews(due_reviews: list[DueReview]) -> str:
    """설계서 §4.1 — 오늘 다뤄야 하는 목록. 판정을 다시 하지 않고 그대로 나열한다."""
    if not due_reviews:
        return "(none due today)"
    return "\n".join(
        f'- {review.pattern_key} ({review.category}): target form "{review.target_form}", '
        f"due since {review.next_review_at.isoformat()}, mastery {review.mastery_score}"
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
    모델이 한다 — 여기서 "만성이다"라고 선언하지 않는다."""
    if not chronic:
        return "(no chronic metrics yet)"
    lines: list[str] = []
    for metric in chronic:
        line = (
            f"- {metric.pattern_key} ({metric.category}): frequency {metric.frequency}, "
            f"seen in {metric.recurring_sessions} sessions across {metric.recurring_days} days, "
            f"span {metric.span}, longest gap {metric.max_gap}"
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
