"""음성 명령 tool 의 페이로드 검증 (`TASK-61.1` · 결정 102).

⛔ **발음 tool 과 규약이 하나 다르다** — 발음은 모르는 `outcome` 을 `unclear` 로 **강등**하지만
이쪽은 모르는 값을 만나면 **버린다**. 종료가 되돌릴 수 없는 명령이라, 모호한 페이로드로 세션을
닫는 것이 기록 하나를 잃는 것보다 나쁘다(결정 102 ③이 확인 절차를 둔 이유와 같다).
"""

from app.models.voice_command import (
    SURFACED_ON_MARKER_MISS,
    closes_session,
    is_wake_command,
    parse_control_payload,
    requires_confirmation,
)


def test_an_additional_learning_payload_carries_its_target() -> None:
    """넷째 조각의 명령은 「추가 학습」이고 **어느 학습인지**를 함께 받는다 (결정 110 ②)."""
    report = parse_control_payload(
        '{"command": "start_additional", "stage": "requested", "target": "shadowing"}'
    )

    assert report is not None
    assert report.command == "start_additional"
    assert report.target == "shadowing"


def test_an_additional_learning_payload_without_a_target_is_dropped() -> None:
    """⛔ 어느 학습을 열지 모르는 채 세션을 닫지 않는다 — 이 모듈의 「모르는 값은 버린다」 규약이
    가장 강하게 걸리는 자리다(세션이 닫히는 명령이다).
    """
    assert parse_control_payload('{"command": "start_additional", "stage": "requested"}') is None


def test_an_unknown_additional_target_is_dropped() -> None:
    assert (
        parse_control_payload(
            '{"command": "start_additional", "stage": "requested", "target": "karaoke"}'
        )
        is None
    )


def test_only_the_commands_that_close_the_session_do_so() -> None:
    """⛔ 「확인이 필요한가」와 「세션을 닫는가」를 **두 집합으로** 둔 이유가 이 단정이다
    (결정 110 ④) — 지금은 값이 같지만 개념이 다르고, 한 이름으로 쓰면 갈릴 때 조용히 틀린다.
    """
    assert closes_session("end") is True
    assert closes_session("start_additional") is True
    assert closes_session("show_report") is False
    assert closes_session("next_question") is False


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


def test_only_three_commands_are_surfaced_when_the_marker_is_missing() -> None:
    """결정 113 ② (`TASK-61.16`) — 버려짐을 화면에 알리는 명령은 셋이고 `next_question` 은 아니다.

    ⛔ **넓히면 알림이 잡음이 된다.** `next_question` 은 프레임이 버려져도 코치가 실제로 다음 질문을
    하므로 화면이 어긋나지 않는다 — 실측이 그것을 갈랐다
    (`tests/harness/runs/2026-09-16-task61-15-accepted-without-execution` §4 의 표).
    ⚠️ 이 집합은 「실행 여부」와 무관하다 — 실행하지 않는 것은 표지 검사가 정하고 그것은 결정 104 다.
    """
    assert SURFACED_ON_MARKER_MISS == {"end", "start_additional", "show_report"}
    assert "next_question" not in SURFACED_ON_MARKER_MISS


def test_the_short_wake_words_are_accepted() -> None:
    """결정 114 — 표지를 「헤이」·「헬로」 계열로 단순화했다 (`TASK-61.17`).

    ⛔ **바꾼 것은 표지의 «형태» 하나다** — 「표지를 앱이 판정한다」(결정 102 ①·104 D5)는 그대로다.
    근거: 앱 이름 표지가 영어에서 2회 중 1회 인식되지 않았고
    (`runs/2026-09-16-task61-15-accepted-without-execution` §3-①) 그 실패가 결함의 트리거였다.
    """
    assert is_wake_command("Hey, end the session.") is True
    assert is_wake_command("Hello, show my weekly report.") is True
    assert is_wake_command("헤이, 학습 종료할게.") is True
    assert is_wake_command("헬로, 다음 문제.") is True


def test_the_hello_variant_with_a_trailing_vowel_is_accepted() -> None:
    """ASR 이 「헬로우」로 적는 경우 — 앞자리 검사가 그것을 함께 받는다.

    ⚠️ `잉글리시`·`잉글리쉬` 를 둘 다 받은 것과 같은 이유다: 한 표기만 받으면 다른 표기가 조용히
    학습 발화로 저장된다.
    """
    assert is_wake_command("헬로우 학습 종료.") is True


def test_the_app_name_wake_phrase_still_works_after_the_simplification() -> None:
    """⛔ 단순화가 기존 표지를 깨지 않는다 (`TASK-61.17` AC#2).

    이미 만들어 둔 픽스처(`vc01`·`vc03` 계열)와 이전 회차의 관측이 앱 이름 표지에 걸려 있어,
    그것을 떨어뜨리면 **회귀를 회귀로 알아볼 수 없게 된다.**
    """
    assert is_wake_command("Oh My English, end the session.") is True
    assert is_wake_command("오 마이 잉글리시, 학습 종료할게.") is True


def test_a_short_wake_word_in_the_middle_is_still_not_a_marker() -> None:
    """⛔ 맨 앞 검사는 단순화 뒤에도 유지된다 — 이것이 이 값역의 판별력이다.

    「헤이」·「헬로」는 짧아서 문장 가운데 들어갈 확률이 앱 이름보다 훨씬 높다. 포함 검사로 바꾸면
    이 두 발화가 명령이 되고, 대화 도중에 세션이 닫힌다.
    """
    assert is_wake_command("I said hello to my boss this morning.") is False
    assert is_wake_command("친구에게 헬로라고 인사했어요.") is False


def test_a_greeting_now_counts_as_a_marker_and_that_cost_is_accepted() -> None:
    """⚠️ **결정 114 가 알고 받은 대가를 여기 못 박는다 — 숨기지 않는다.**

    「Hello」·「Hey」는 영어 학습자가 가장 자주 말하는 첫마디라 학습 발화가 표지를 얻는다. 표지만으로는
    아무것도 실행되지 않지만(모델이 tool 을 불러야 한다) 그 발화는 `voice_command` 로 저장되어
    **분석에서 빠진다**(`services/utterances.py` 가 `learning` 만 분석 대상으로 본다).
    ⇒ 이 단정이 깨지는 방향으로 값역을 좁히려면 **그 크기를 먼저 실물 회차로 재고** 결정 114 를
    다시 올린다(`TASK-61.17` AC#4).
    """
    assert is_wake_command("Hello, my name is Jin.") is True
