"""`services/video_url.parse_youtube_id` — 붙여넣은 링크에서 영상 식별자를 뽑는다 (`TASK-163`).

설계: `docs/design/2026-09-18-video-learning-design.md` §4.

⛔ **이 모듈이 왜 서버에 있는가**: 프런트에는 테스트 러너가 없다(`TASK-159` 6항). 파싱은 형태 넷을
가르는 **논리**이므로 단위 테스트로 덮을 수 있는 쪽에 둔다. 프런트는 URL 을 그대로 넘기고 뽑지
않는다 — 규칙이 두 곳에 갈리지 않게 하는 것이 그 배치의 목적이다.

⚠️ **11자 검사가 여기와 스키마 양쪽에 있는 것은 중복이 아니다** — 027 의
`youtube_videos_youtube_id_shape` 가 값역의 겹이고 이 함수가 입구의 겹이다. 이 값이 URL 조립에
쓰이므로(`i.ytimg.com/vi/<id>/...` · `watch?v=<id>`) 한 겹이 뚫려도 다른 겹이 막아야 한다.
"""

from __future__ import annotations

from app.services.video_url import parse_youtube_id

_ID = "dQw4w9WgXcQ"


def test_it_reads_the_watch_form() -> None:
    assert parse_youtube_id(f"https://www.youtube.com/watch?v={_ID}") == _ID


def test_it_reads_the_short_link_form() -> None:
    assert parse_youtube_id(f"https://youtu.be/{_ID}") == _ID


def test_it_reads_the_shorts_form() -> None:
    assert parse_youtube_id(f"https://www.youtube.com/shorts/{_ID}") == _ID


def test_it_reads_the_embed_form() -> None:
    assert parse_youtube_id(f"https://www.youtube.com/embed/{_ID}") == _ID


def test_it_ignores_extra_query_parameters() -> None:
    """사용자가 「현재 시각부터」로 복사하면 `&t=` 가 붙는다 — 그것 때문에 실패하지 않는다."""
    assert parse_youtube_id(f"https://www.youtube.com/watch?v={_ID}&t=42s") == _ID
    assert parse_youtube_id(f"https://youtu.be/{_ID}?t=42") == _ID
    assert parse_youtube_id(f"https://www.youtube.com/watch?list=PLxxxx&v={_ID}") == _ID


def test_it_accepts_the_mobile_host_and_a_missing_scheme() -> None:
    """사용자가 손으로 옮겨 적으면 스킴이 빠진다. 모바일 호스트도 같은 영상이다."""
    assert parse_youtube_id(f"https://m.youtube.com/watch?v={_ID}") == _ID
    assert parse_youtube_id(f"www.youtube.com/watch?v={_ID}") == _ID
    assert parse_youtube_id(f"youtu.be/{_ID}") == _ID


def test_it_tolerates_surrounding_whitespace() -> None:
    assert parse_youtube_id(f"  https://youtu.be/{_ID}  ") == _ID


def test_it_rejects_an_id_that_is_not_eleven_characters() -> None:
    assert parse_youtube_id("https://www.youtube.com/watch?v=dQw4w9WgXc") is None
    assert parse_youtube_id("https://www.youtube.com/watch?v=dQw4w9WgXcQQ") is None
    assert parse_youtube_id("https://youtu.be/dQw4w9WgXc") is None


def test_it_rejects_characters_outside_the_identifier_alphabet() -> None:
    assert parse_youtube_id("https://www.youtube.com/watch?v=dQw4w9WgXc!") is None
    assert parse_youtube_id("https://www.youtube.com/watch?v=dQw4w9WgX.Q") is None


def test_it_rejects_hosts_that_are_not_youtube() -> None:
    """⛔ 이 단정이 이 함수의 값을 정한다 — 아무 URL 에서 11자 조각을 뽑지 않는다.

    ⚠️ 첫째 줄이 특히 중요하다: 호스트를 부분 문자열로 검사하면
    `youtube.com.attacker.test` 가 통과한다.
    """
    assert parse_youtube_id(f"https://youtube.com.attacker.test/watch?v={_ID}") is None
    assert parse_youtube_id(f"https://vimeo.com/watch?v={_ID}") is None
    assert parse_youtube_id(f"https://example.test/{_ID}") is None


def test_it_rejects_a_youtube_url_without_a_video() -> None:
    assert parse_youtube_id("https://www.youtube.com/") is None
    assert parse_youtube_id("https://www.youtube.com/watch") is None
    assert parse_youtube_id("https://www.youtube.com/results?search_query=hello") is None
    assert parse_youtube_id("https://youtu.be/") is None


def test_it_rejects_empty_and_blank_input() -> None:
    assert parse_youtube_id("") is None
    assert parse_youtube_id("   ") is None


def test_it_rejects_a_bare_identifier_without_a_url() -> None:
    """⚠️ 관대하게 받으면 「검색어를 붙여넣었다」와 구분되지 않는다 — 링크를 요구한다."""
    assert parse_youtube_id(_ID) is None
