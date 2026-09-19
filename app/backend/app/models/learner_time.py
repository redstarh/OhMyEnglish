"""학습자의 「오늘」 — 경계 계산과 naive 거부의 정본 (`TASK-226`).

⛔ **이 모듈이 있는 이유는 중복이 아니라 「경계의 정본」이다** — `services/user_timezone.py` 가
타임존 «조회»에 대해 같은 자리를 차지한다. 같은 계산이 두 서비스에 갈라져 있었다:
`services/recordings.day_start_for`(절대 시각)와 `services/daily_summary._today_in`(날짜). 그리고
naive `now` 를 거부하는 **같은 문면**이 네 자리에 복제돼 있었다(`jobs` · `recordings` 둘 ·
`daily_summary`). 갈라지면 「학습자의 하루가 언제 시작하는가」가 두 값으로 존재하게 되고, 그 갈림은
자정 앞뒤에서만 드러나므로 아무것도 알려 주지 않는다.

⛔ **순수 모듈이다** — DB·Settings·로거를 보지 않는다. 그래서 `services` 와 `workers` 양쪽이 층
규칙을 거스르지 않고 가져갈 수 있다(`models/recording.py` 가 규격 상수에 대해 같은 자리다).

⚠️ **타임존 값의 정본은 `users.timezone` 컬럼이다** — 이 모듈은 그 값을 **받기만** 한다. 호스트
시간도 세션 기본값도 아니고, 조회는 `services/user_timezone.timezone_of` 가 소유한다.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

# ⛔ **문면을 한 자리에 둔다.** 네 자리에 복제돼 있었고, 그중 하나만 바꿔도 「호출자의 버그」와
# 「타임존 값 문제」를 문면으로 가르던 자리가 조용히 깨진다(`recordings._has_expired` 의 경고가
# 그 갈림을 실제로 겪은 기록이다).
_NAIVE_NOW = "`now` must be timezone-aware (naive datetime is not allowed)"


def require_aware(value: datetime | None) -> datetime | None:
    """naive datetime 을 경계에서 거부한다. `None` 은 그대로 통과시킨다.

    이 시스템의 모든 시각은 `timestamptz`/aware 이고, naive 를 조용히 바인딩하면 **서버 오프셋만큼
    시각이 밀린다.** `None` 을 허용하는 것은 SQL 로 넘기는 「값을 주지 않았다」를 뜻하는 호출자
    (`services/jobs`)가 있기 때문이다 — 그 호출자에게는 기본값을 여기서 정해 줄 수 없다(기본값이
    DB 의 `clock_timestamp()` 다).
    """
    if value is not None and value.tzinfo is None:
        raise ValueError(_NAIVE_NOW)
    return value


def resolve_now(now: datetime | None) -> datetime:
    """`now` 를 확정하고 **aware 를 보장한다.** 주지 않으면 앱 시계(UTC)를 쓴다.

    ⚠️ 앱 시계를 쓰는 것이 판단이다 — 경계 계산이 Python 이므로 시계도 같은 쪽에 둔다. DB 시계
    (`clock_timestamp()`)를 쓰려면 왕복이 한 번 더 늘고, 두 시계는 같은 호스트다.
    ⛔ **검사를 `day_start_for`·`local_date` 에만 맡기지 않는다** — 그쪽의 `ZoneInfo` 실패와
    naive 입력이 **같은 `ValueError`** 라, 호출자가 타임존 값 문제만 잡으려고 둔 `except` 에
    호출자 자신의 버그가 걸려 「멀쩡한 타임존을 지목하는 경고」가 난다(2026-09-09 리뷰가 런타임으로
    관측한 자리다). 먼저 터뜨리면 그 `except` 가 타임존 값 문제로만 좁혀진다.
    """
    resolved = now if now is not None else datetime.now(UTC)
    if resolved.tzinfo is None:
        raise ValueError(_NAIVE_NOW)
    return resolved


def local_date(tz_name: str, *, now: datetime) -> date:
    """학습자 타임존의 **오늘 날짜**.

    ⛔ **`current_date` 를 쓰지 않는다** — UTC 자정~09:00(KST) 구간에 그 값이 학습자의 날짜보다
    하루 이르다(설계 세션이 공유 DB 에서 직접 관측했다: `current_date`=2026-09-07 인데
    `(now() at time zone 'Asia/Seoul')`=2026-09-08). 복습 일정·일일 예산·학습 계획이 그 한 칸에
    걸린다.
    """
    return resolve_now(now).astimezone(ZoneInfo(tz_name)).date()


def day_start_for(tz_name: str, *, now: datetime) -> datetime:
    """학습자의 「오늘」이 시작한 **절대 시각**. 녹음 삭제는 이 값보다 이전이 대상이다(§5.2).

    **SQL 의 `AT TIME ZONE` 이 아니라 Python 에서 구하는 이유 셋** (§5.2 — 전역 규약은 둘 다
    허용한다): ① 잘못된 타임존 값이 **한 사람만** 막는다(집합 UPDATE 안에서 터지면 한 사람의
    값이 전체 삭제를 막는다 · `users.timezone` 에 CHECK 가 없다) ② `created_at < $1` 이 011 의
    부분 인덱스를 탄다(`(created_at at time zone …)::date` 는 못 탄다) ③ 되돌릴 수 없는 삭제의
    경계라 DB 없이 경계값을 값싸게 재야 한다.

    ⚠️ **`replace(hour=0, …)` 를 쓰지 않는다.** 2026-09-09 리뷰가 이 서술의 이전 판을 정정했다 —
    위험은 「존재하지 않는 자정」이 아니라 **자정이 두 번 오는 날**이다(자정에 DST 가 끝나는 지역).
    `replace` 는 입력 시각의 `fold` 를 물려받아 **두 번째** 자정을 고르고, 그러면 경계가 한 시간
    늦어져 그 사이 녹음이 「어제」로 분류돼 하루 일찍 삭제된다. 날짜와 tzinfo 로 다시 조립하면
    `fold=0`, 즉 **첫 번째** 자정이 되고 그것이 「오늘이 시작한 시각」이다.
    실측(`America/Havana`, `2026-11-01 05:30Z`): 조립 → `04:00Z` · `replace` → `05:00Z`.
    ⚠️ **`America/New_York` 로는 이 차이가 드러나지 않는다** — 그 지역은 자정이 아니라 02:00 에
    바뀌어 두 방식이 같은 값을 낸다.

    ⚠️ **날짜와 시각을 같은 모듈이 갖는 것이 이 자리의 값이다** — 스윕과 서빙이 **같은 함수 하나**를
    부르는 §6.4 의 규약이 이제 일일 요약까지 덮는다.
    """
    zone = ZoneInfo(tz_name)
    today_local = local_date(tz_name, now=now)
    return datetime.combine(today_local, time.min, tzinfo=zone).astimezone(UTC)


__all__ = ["day_start_for", "local_date", "require_aware", "resolve_now"]
