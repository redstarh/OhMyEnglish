"""음성 명령 tool 의 페이로드 검증 (`TASK-61.1` · 결정 102).

⛔ **발음 tool 과 규약이 하나 다르다** — 발음은 모르는 `outcome` 을 `unclear` 로 **강등**하지만
이쪽은 모르는 값을 만나면 **버린다**. 종료가 되돌릴 수 없는 명령이라, 모호한 페이로드로 세션을
닫는 것이 기록 하나를 잃는 것보다 나쁘다(결정 102 ③이 확인 절차를 둔 이유와 같다).
"""

from app.models.voice_command import (
    is_wake_command,
    parse_control_payload,
    requires_confirmation,
)


def test_a_report_command_payload_becomes_a_report() -> None:
    """둘째 조각의 명령은 「주간 리포트 보기」다 (`TASK-61.6` · 결정 107)."""
    report = parse_control_payload('{"command": "show_report", "stage": "requested"}')

    assert report is not None
    assert report.command == "show_report"
    assert report.stage == "requested"


def test_a_next_question_command_payload_becomes_a_report() -> None:
    """셋째 조각의 명령은 「다음 문제」다 (`TASK-61.7` · 결정 108)."""
    report = parse_control_payload('{"command": "next_question", "stage": "requested"}')

    assert report is not None
    assert report.command == "next_question"
    assert report.stage == "requested"


def test_only_a_command_that_cannot_be_undone_needs_confirmation() -> None:
    """⛔ 확인 필요 여부를 **앱이** 판정한다 — 모델의 규율에 맡기면 조회에도 확인을 묻거나
    종료를 확인 없이 부른다. PRD:85 는 「결과가 큰 명령」에만 확인을 요구한다(결정 107 ③).

    ⚠️ **명령을 더할 때 이 목록을 함께 늘린다** — 새 명령이 어느 쪽인지 정하지 않고 넘어가면
    확인 없이 도는 것이 기본값이 된다(결정 108 ① 이 「다음 문제」를 그렇게 판정했다).
    """
    assert requires_confirmation("end") is True
    assert requires_confirmation("show_report") is False
    assert requires_confirmation("next_question") is False


def test_a_confirmed_end_payload_becomes_a_report() -> None:
    report = parse_control_payload('{"command": "end", "stage": "confirmed"}')

    assert report is not None
    assert report.command == "end"
    assert report.stage == "confirmed"


def test_an_unknown_command_is_dropped_instead_of_guessed() -> None:
    assert parse_control_payload('{"command": "delete_everything", "stage": "confirmed"}') is None


def test_an_unknown_stage_is_dropped_instead_of_demoted() -> None:
    """⛔ 발음 tool 처럼 강등하지 않는다 — 모호한 단계로 세션을 닫지 않는다."""
    assert parse_control_payload('{"command": "end", "stage": "maybe"}') is None


def test_a_payload_that_is_not_json_is_dropped() -> None:
    assert parse_control_payload("종료해 주세요") is None


def test_the_wake_phrase_marks_an_utterance_as_a_command() -> None:
    assert is_wake_command('Oh My English, end the session.') is True


def test_the_korean_wake_phrase_is_accepted() -> None:
    """결정 102 ④ — 첫 조각이 한국어와 영어를 둘 다 받는다."""
    assert is_wake_command("오 마이 잉글리시, 학습 종료할게.") is True


def test_speech_without_the_wake_phrase_is_not_a_command() -> None:
    """⛔ 이것이 AC#3 의 판별력이다 — 학습 발화가 명령으로 실행되면 안 된다."""
    assert is_wake_command("I want to end the meeting early tomorrow.") is False


def test_my_english_alone_is_not_the_wake_phrase() -> None:
    """학습자가 자기 영어를 말하는 문장이 가장 흔한 오인식 후보다."""
    assert is_wake_command("My English is not good enough for meetings.") is False


def test_the_marker_must_be_at_the_front_not_anywhere_in_the_sentence() -> None:
    """⛔ 포함 검사로 바꾸면 이 발화가 명령이 된다 — 무력화로 확인한 자리다.

    학습자가 문장 가운데서 앱 이름을 말하는 것은 학습 발화이고, 그것을 명령으로 실행하면
    대화 도중에 세션이 닫힌다.
    """
    assert is_wake_command("I told my friend oh my english is improving.") is False


def test_the_korean_transcription_variant_is_accepted() -> None:
    """한글 표기가 「잉글리시」·「잉글리쉬」로 갈린다 — 둘 다 받는다.

    ⚠️ 실물 ASR 이 어느 쪽으로 적는지는 `TASK-61.3` 회차가 관측한다. 여기서는 두 표기를 받는 것만
    못 박는다 — 한 표기만 받으면 다른 표기가 조용히 학습 발화로 저장된다.
    """
    assert is_wake_command("오마이 잉글리쉬, 종료.") is True
