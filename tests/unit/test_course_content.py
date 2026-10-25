"""문법 코스 콘텐츠 파일의 값역 (`TASK-286`).

정본 파일 `app/backend/app/content/grammar_basic.json` 이 `models.course.Course` 를 통과하는지와,
값역이 실제로 잘못된 파일을 거부하는지(판별력)를 함께 잰다.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.models.course import (
    CONTENT_PATH,
    SENTENCES_PER_UNIT,
    UNIT_COUNT,
    Course,
    load_course,
    sentence_key,
)


def test_content_file_covers_113_units_with_five_sentences_each() -> None:
    course = load_course()
    units = [unit for day in course.days for unit in day.units]
    assert len(course.days) == 6
    assert len(units) == UNIT_COUNT
    assert all(len(unit.sentences) == SENTENCES_PER_UNIT for unit in units)
    texts = [text for unit in units for text in unit.sentences]
    assert len(set(texts)) == len(texts), "같은 문장이 두 단원에 들어 있음"


def test_day_ranges_match_the_video_tables_of_contents() -> None:
    course = load_course()
    ranges = [(day.units[0].unit, day.units[-1].unit) for day in course.days]
    assert ranges == [(1, 21), (22, 41), (42, 62), (63, 82), (83, 100), (101, 113)]


def test_sentence_lookup_by_key() -> None:
    course = load_course()
    first = course.days[0].units[0]
    assert sentence_key(1, 0) == "u001-s1"
    assert course.sentence("u001-s1") == first.sentences[0]
    assert course.sentence("u113-s5") == course.days[-1].units[-1].sentences[4]
    assert course.sentence("u114-s1") is None
    assert course.sentence("u001-s6") is None
    assert course.sentence("nonsense") is None


def test_unit_at_follows_chapter_boundaries() -> None:
    day = load_course().days[0]
    second = day.units[1]
    assert day.unit_at(Decimal(0)).unit == 1
    assert day.unit_at(Decimal(second.start_sec)).unit == 2
    assert day.unit_at(Decimal(day.duration_sec + 100)).unit == day.units[-1].unit


def _raw() -> dict[str, object]:
    return json.loads(Path(CONTENT_PATH).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "break_it",
    [
        lambda raw: raw["days"][0]["units"][0]["sentences"].pop(),  # 문장 4개
        lambda raw: raw["days"][0]["units"].pop(3),  # 단원 번호 건너뜀
        lambda raw: raw["days"][1]["units"][0].update(end_sec=0),  # 끝이 시작보다 앞
        lambda raw: raw["days"].pop(),  # Day 5개
        lambda raw: raw["days"][0]["units"][0]["sentences"].__setitem__(0, "  "),  # 빈 문장
    ],
)
def test_validation_rejects_broken_content(break_it) -> None:  # type: ignore[no-untyped-def]
    raw = _raw()
    break_it(raw)
    with pytest.raises(ValueError):
        Course.model_validate(raw)
