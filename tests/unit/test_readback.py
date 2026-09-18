"""`services/readback.compare_readback` — 클립의 글과 낭독 전사문을 낱말 단위로 견준다 (`TASK-207`).

설계: `docs/design/2026-09-18-read-aloud-judgment-design.md` §4.

⛔ **이 판정에 모델을 부르지 않는다** — 「원본대로 읽었는가」는 낱말 일치로 답이 정해진다. 그래서
순수 함수이고, 같은 입력에 같은 답이 나는 것을 테스트가 고정한다(그 성질이 화면 안내의 근거다).

⚠️ **판정은 «기대한» 낱말마다 난다.** 학습자가 없는 낱말을 «더» 말한 경우는 v1 이 세지 않는다 —
셋(맞음·빠짐·다름) 밖의 넷째 갈래이고 화면에 낼 자리가 없다. 넣으려면 값역부터 넓힌다.
"""

from __future__ import annotations

from app.services.readback import compare_readback

_CLIP = "I usually go to the gym after work"


def _verdicts(expected: str, spoken: str) -> list[tuple[str, str]]:
    return [(v.word, v.verdict) for v in compare_readback(expected, spoken)]


def test_같은_문장을_읽으면_낱말마다_맞음이다() -> None:
    assert _verdicts(_CLIP, _CLIP) == [
        ("I", "match"),
        ("usually", "match"),
        ("go", "match"),
        ("to", "match"),
        ("the", "match"),
        ("gym", "match"),
        ("after", "match"),
        ("work", "match"),
    ]


def test_한_낱말을_빼면_그_낱말만_빠짐이다() -> None:
    spoken = "I usually go to gym after work"  # `the` 를 빼먹었다
    assert _verdicts(_CLIP, spoken) == [
        ("I", "match"),
        ("usually", "match"),
        ("go", "match"),
        ("to", "match"),
        ("the", "missing"),
        ("gym", "match"),
        ("after", "match"),
        ("work", "match"),
    ]


def test_한_낱말을_다르게_읽으면_다름이다() -> None:
    spoken = "I usually go to the jim after work"  # gym → jim
    assert _verdicts(_CLIP, spoken) == [
        ("I", "match"),
        ("usually", "match"),
        ("go", "match"),
        ("to", "match"),
        ("the", "match"),
        ("gym", "different"),
        ("after", "match"),
        ("work", "match"),
    ]


def test_대소문자_차이를_오류로_세지_않는다() -> None:
    assert _verdicts("Hello World", "hello world") == [
        ("Hello", "match"),
        ("World", "match"),
    ]


def test_문장부호_차이를_오류로_세지_않는다() -> None:
    assert _verdicts("Hello, world!", "hello world") == [
        ("Hello,", "match"),
        ("world!", "match"),
    ]


def test_부호만_있는_토큰은_판정하지_않는다() -> None:
    """클립 전사문에 줄표나 홑따옴표가 낱말처럼 떨어져 있어도 판정할 낱말이 아니다."""
    assert _verdicts("Hello — world", "hello world") == [
        ("Hello", "match"),
        ("world", "match"),
    ]


def test_낭독_전사가_비면_낱말마다_빠짐이다() -> None:
    assert _verdicts("Hello world", "") == [
        ("Hello", "missing"),
        ("world", "missing"),
    ]


def test_같은_입력에_같은_답이_난다() -> None:
    """⛔ 두 결과가 같은 것만 보면 빈 결과에서도 통과한다 — 내용까지 함께 고정한다."""
    spoken = "I usually go to the jim after"  # gym → jim · work 를 빼먹었다
    first = _verdicts(_CLIP, spoken)
    second = _verdicts(_CLIP, spoken)
    assert first == second
    assert first == [
        ("I", "match"),
        ("usually", "match"),
        ("go", "match"),
        ("to", "match"),
        ("the", "match"),
        ("gym", "different"),
        ("after", "match"),
        ("work", "missing"),
    ]


def test_긴_전사문에서_한_낱말을_빼먹어도_그_한_자리만_잡힌다() -> None:
    """⛔ `difflib` 의 `autojunk` 가 이 자리를 조용히 깨뜨린다 — 그것을 잡는 유일한 테스트다.

    `SequenceMatcher` 는 기본값에서 b 가 200 항목을 넘으면 「b 의 1% 를 넘게 나오는 항목」을 junk 로
    버린다. 자연스러운 영어에서는 기능어가 그 문턱을 쉽게 넘으므로 **긴 전사문의 정렬이 통째로
    뭉개진다**.
    ⚠️ **같은 열끼리는 `autojunk` 가 결과를 바꾸지 않는다**(2026-09-18 직접 관측) — 그래서
    「같은 문장을 읽었다」 형태로는 이 회귀를 볼 수 없고 반드시 «다른» 열이어야 한다.
    ⚠️ 되풀이가 심한 글(같은 문장 30번)로도 쓰지 않는다 — 똑같이 긴 정렬이 여럿 있어 `difflib` 이
    그 가운데 하나를 고르고 그것이 99낱말을 빠짐으로 만든다(직접 관측). 그것은 이 가드의 회귀가
    아니라 정렬 모호성이므로 **자연스러운 글**로 재야 한다.
    """
    sentence = "in the {0} we can see that a small {0}s changes the whole {0} quickly"
    nouns = (
        "garden river market temple bridge harbour meadow castle island valley"
        " forest station library concert kitchen"
    ).split()
    text = " ".join(sentence.format(noun) for noun in nouns)
    words = text.split()
    assert len(words) > 200
    dropped = words.index("castle")
    spoken = " ".join(words[:dropped] + words[dropped + 1 :])
    verdicts = compare_readback(text, spoken)
    assert [v.verdict for v in verdicts].count("missing") == 1
    assert verdicts[dropped].verdict == "missing"


def test_원본_낱말의_원래_모양을_그대로_돌려준다() -> None:
    """화면이 원본을 그대로 보여야 하므로 정규화한 형태를 돌려주지 않는다."""
    verdicts = compare_readback("Don't stop!", "dont stop")
    assert [v.word for v in verdicts] == ["Don't", "stop!"]
