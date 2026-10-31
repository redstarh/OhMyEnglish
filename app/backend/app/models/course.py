"""문법 코스의 콘텐츠 값역과 요청 몸통 (`TASK-286`).

설계: `docs/design/2026-10-26-grammar-course-design.md` §5·§6.

⛔ **콘텐츠는 파일이 정본이다** (`app/content/grammar_basic.json`). 이 모듈이 그 파일을 읽을 때
값역을 가둔다 — 단원 113개 · 문장 5개씩 · 시각 단조 · 키 유일. 파일을 고친 사람이 실수하면 앱이
뜨지 않는 쪽이 맞다: 조용히 통과하면 학습자가 빈 카드나 엉뚱한 단원을 본다.
⛔ **문장은 영상·교재의 문장이 아니다** — 단원의 문법 패턴으로 새로 쓴 문장이다(설계서 §2 반목표).
"""

from __future__ import annotations

import json
import re
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

import pydantic

CONTENT_PATH = Path(__file__).resolve().parent.parent / "content" / "grammar_basic.json"
UNIT_COUNT = 113
DAY_COUNT = 6
SENTENCES_PER_UNIT = 5

# 따라 하기 녹음의 상한 — 30초 · 16kHz · 16bit · mono. 그보다 긴 문장은 이 코스에 없다.
MAX_ATTEMPT_PCM_BYTES = 30 * 16_000 * 2

_SENTENCE_KEY = re.compile(r"^u(\d{3})-s(\d)$")


def sentence_key(unit: int, index: int) -> str:
    """단원·순번(0부터)으로 문장 키를 만든다. 시도 기록이 이 키를 가리키므로 바뀌면 안 된다."""
    return f"u{unit:03d}-s{index + 1}"


class CourseUnit(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid", frozen=True)

    unit: int = pydantic.Field(ge=1, le=UNIT_COUNT)
    topic: str = pydantic.Field(min_length=1)
    start_sec: int = pydantic.Field(ge=0)
    end_sec: int = pydantic.Field(gt=0)
    sentences: tuple[str, ...] = pydantic.Field(
        min_length=SENTENCES_PER_UNIT, max_length=SENTENCES_PER_UNIT
    )

    @pydantic.model_validator(mode="after")
    def _span_is_ordered(self) -> CourseUnit:
        if self.end_sec <= self.start_sec:
            raise ValueError(f"unit {self.unit}: end_sec must be after start_sec")
        if any(not text.strip() for text in self.sentences):
            raise ValueError(f"unit {self.unit}: empty sentence")
        return self


class CourseDay(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid", frozen=True)

    day: int = pydantic.Field(ge=1, le=DAY_COUNT)
    youtube_id: str = pydantic.Field(pattern=r"^[A-Za-z0-9_-]{11}$")
    units: tuple[CourseUnit, ...] = pydantic.Field(min_length=1)

    @pydantic.model_validator(mode="after")
    def _units_are_contiguous(self) -> CourseDay:
        for before, after in zip(self.units, self.units[1:], strict=False):
            if after.unit != before.unit + 1:
                raise ValueError(f"day {self.day}: unit {after.unit} does not follow {before.unit}")
            if after.start_sec < before.end_sec:
                raise ValueError(
                    f"day {self.day}: unit {after.unit} starts before {before.unit} ends"
                )
        return self

    @property
    def duration_sec(self) -> int:
        return self.units[-1].end_sec

    def unit_at(self, position_sec: Decimal) -> CourseUnit:
        """재생 위치가 속한 단원. 마지막 단원 뒤는 마지막 단원으로 본다."""
        for item in self.units:
            if position_sec < item.end_sec:
                return item
        return self.units[-1]


class Course(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid", frozen=True)

    course: str
    days: tuple[CourseDay, ...] = pydantic.Field(min_length=DAY_COUNT, max_length=DAY_COUNT)

    @pydantic.model_validator(mode="after")
    def _covers_every_unit_once(self) -> Course:
        if [item.day for item in self.days] != list(range(1, DAY_COUNT + 1)):
            raise ValueError("days must be 1..6 in order")
        units = [unit.unit for day in self.days for unit in day.units]
        if units != list(range(1, UNIT_COUNT + 1)):
            raise ValueError("units must be 1..113 exactly once, in order")
        return self

    def day(self, number: int) -> CourseDay | None:
        return next((item for item in self.days if item.day == number), None)

    def sentence(self, key: str) -> str | None:
        """키가 가리키는 문장. 형식이 틀리거나 없는 단원이면 `None` — 라우터가 404 로 옮긴다."""
        match = _SENTENCE_KEY.match(key)
        if match is None:
            return None
        unit_number, index = int(match.group(1)), int(match.group(2)) - 1
        for day in self.days:
            for item in day.units:
                if item.unit == unit_number:
                    return item.sentences[index] if 0 <= index < len(item.sentences) else None
        return None


@lru_cache(maxsize=1)
def load_course(path: Path = CONTENT_PATH) -> Course:
    """콘텐츠 파일을 한 번 읽어 값역으로 가둔다. 실패하면 예외 — 조용히 빈 코스를 내지 않는다."""
    return Course.model_validate(json.loads(path.read_text(encoding="utf-8")))


class ProgressUpdate(pydantic.BaseModel):
    """학습 화면이 저장하는 진도.

    ⚠️ **`unit` 은 «문장 연습»의 단원이고 영상 위치에서 계산하지 않는다** — 학습자는 영상을 앞서
    들으면서 앞 단원의 문장을 따라 할 수 있다(설계서 §7).
    그 단원이 이 Day 에 속하는지는 서비스가 본다.
    """

    model_config = pydantic.ConfigDict(extra="forbid")

    position_sec: Decimal = pydantic.Field(ge=0, le=Decimal(24 * 3600))
    unit: int = pydantic.Field(ge=1, le=UNIT_COUNT)
    sentence_index: int = pydantic.Field(ge=0, lt=SENTENCES_PER_UNIT)
    completed: bool = False
    # 화면이 아는 완료 횟수 — 완료 전에 보낸 저장이 완료 뒤에 도착하면 서비스가 버린다(TASK-287).
    completed_count: int = pydantic.Field(default=0, ge=0)
