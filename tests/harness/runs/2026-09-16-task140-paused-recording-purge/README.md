# 회차 — `TASK-140`: 025 가 넓힌 「살아 있는 상태」를 녹음 층이 아는가

세션 `ohmyenglish-43` · 2026-09-16 KST · 기준 커밋 `0945a66` · 드라이버 `p_paused_recording.py`

> 무엇을 재는가: **정지 중인 세션의 쉐도잉 녹음이 「끝난 세션」으로 취급되는가.**
> 025(결정 117)가 `learning_sessions.status` 에 `paused` 를 더해 살아 있는 상태가 둘이 됐고
> (`services/sessions.py` `_LIVE_SESSION_STATUSES`), 녹음 층은 「진행 중」을 `status = 'active'`
> 하나로 판정한다.
>
> ⛔ **이 회차는 Nova 를 부르지 않는다.** 물음이 DB 상태와 삭제 스윕이라 음성 레그가 판별력을
> 더하지 못한다 — 앱의 함수(`load_recording` · `purge_expired_recordings`)를 그대로 부른다.

---

## 0. 스택과 격리

| 무엇 | 값 |
|---|---|
| DB | 검증 전용 `ohmyenglish_t140`(소유자 `ohmy` · `schema_migrations` **23**) |
| 녹음 뿌리 | `/tmp/t140-audio` — ⛔ **실물 `assets/audio` 를 쓰지 않는다**(삭제를 재는 회차다) |
| 워커 | 돌리지 않음 — 스윕 함수를 직접 부른다 |
| 팔 | `paused`(물음) · `active`(살아야 함) · `completed`(지워져야 함) |

심은 값: 학습자 타임존 `Asia/Seoul` · 녹음 시각 **2026-09-15 22:00 KST** ·
경계(`day_start_for`) **2026-09-16 00:00 KST** — 즉 **자정을 넘겨 정지 중인 세션**이다.

## 1. 관측 — 팔 셋 (드라이버 출력 그대로)

```
now=2026-09-16T15:04:05.168438+09:00 경계=2026-09-15T15:00:00+00:00 녹음시각=2026-09-15T13:00:00+00:00

[1] 스윕 전 — load_recording
  paused    load_recording=None
  active    load_recording=바이트 320
  completed load_recording=None

[2] purge_expired_recordings → 2건

[3] 스윕 뒤 — 포인터와 파일
  paused    선택됨=True  audio_url=null 파일=없음
  active    선택됨=False audio_url=있음 파일=있음
  completed 선택됨=True  audio_url=null 파일=없음
```

| 팔 | 조회(스윕 전) | 스윕이 골랐나 | 포인터 | 바이트 |
|---|---|---|---|---|
| `paused` | **None** | **예** | **null** | **삭제됨** |
| `active` | 바이트 320 | 아니오 | 있음 | 있음 |
| `completed` | None | 예 | null | 삭제됨 |

⇒ **`paused` 가 `completed` 와 한 글자도 다르지 않게 처리됐다.** 살아 있는 세션의 학습자 음성이
되돌릴 수 없이 지워졌다.

## 2. 판정 — 어긋난 자리 셋

설계서 §5.4 의 예외는 **「자정을 넘기며 진행되는 세션의 녹음을 학습자가 지금 비교한다」** 이고,
정지는 **바로 그 상황**이다(자리를 비웠다가 돌아온다 — 결정 117 이 그 뜻으로 만들었다).
그 예외를 표현한 세 자리가 값역이 넓어진 것을 모른다.

| 자리 | 지금 | 뜻 |
|---|---|---|
| `_SELECT_PURGE_USERS_SQL` | `s.status <> 'active'` | 정지 세션을 가진 학습자가 스윕 목록에 든다 |
| `_SELECT_EXPIRED_RECORDINGS_SQL` | `s.status <> 'active'` | 그 세션의 녹음이 만료 대상이 된다 |
| `load_recording` | `row["status"] != "active"` | 스윕 전에도 조회가 닫힌다 |

⚠️ **`end_session` 은 이미 넓다** — `_END_SESSION_SQL` 이 `status in ('active','paused')` 다
(025 가 함께 고쳤다). 즉 **025 는 세션 층만 넓히고 녹음 층을 지나쳤다.**
⚠️ `_SET_SESSION_MODE_SQL` 도 `status = 'active'` 로 남았지만 **이 결함이 아니다** — 그 UPDATE 의
호출자(`_record_session_mode_or_continue`)는 세션을 연 직후에만 돌아 정지 중에 닿지 않는다.

## 3. 도달 가능성 — 좁지 않다

1. **정지 중에는 소켓이 살아 있다**(결정 117). 그래서 그 세션은 워커의 `live_sessions` 에 들고
   고아 리퍼가 **걷지 않는다**(`_REAP_ORPHAN_SESSIONS_SQL` 의 `not (s.id = any($1))`).
   ⇒ 정지 상태가 자정을 넘겨 유지될 수 있다.
2. **정지 중에는 학습 발화가 저장되지 않는다**(결정 117). 리퍼의 유휴 기준이
   `max(utterances.created_at)` 이라 그 값도 자라지 않는다 — 소켓이 살아 있는 한 1번이 계속 참이다.
3. **스윕은 유휴 사이클마다 돈다**(`analysis_worker.sweep_recordings` — 큐가 빌 때). 경계를 넘긴
   뒤 첫 유휴 사이클에 지워진다. 워커를 내려도 `load_recording` 이 같은 경계를 다시 계산해
   **조회는 그 즉시 닫힌다**(§6.4 의 장치).

⚠️ **`WORKER_ENABLED=false` 인 이 리포의 dev 환경에서는 바이트가 남는다** — 그래서 이 회차가
검증 전용 DB 에서 스윕을 직접 불렀다. 운영에서 워커가 돌면 3번이 삭제까지 간다.

## 4. 단정이 왜 안 잡았나

`tests/unit/test_recordings.py` 는 세션 상태를 **`active` 와 `completed` 두 값으로만** 밟는다
(`_new_shadowing_session(status=...)` 의 호출 전수). `paused` 를 밟는 단정이 이 파일에 없고,
025 가 값역을 넓힐 때 이 파일을 함께 보지 않았다.
⇒ 고치는 결정이 나면 **`paused` 팔을 단정으로 박는 것이 그 고침의 일부**다.

## 5. 재현 절차

```bash
cd ~/MyProject/OhMyEnglish
/opt/homebrew/opt/postgresql@17/bin/psql "postgresql://ohmy:ohmy@localhost:5432/postgres" \
  -c "create database ohmyenglish_t140 owner ohmy"
DATABASE_URL="postgresql://ohmy:ohmy@localhost:5432/ohmyenglish_t140" \
  app/backend/.venv/bin/python scripts/migrate.py
DATABASE_URL="postgresql://ohmy:ohmy@localhost:5432/ohmyenglish_t140" \
  app/backend/.venv/bin/python \
  tests/harness/runs/2026-09-16-task140-paused-recording-purge/p_paused_recording.py /tmp/t140-audio
# 끝나면 정리한다
/opt/homebrew/opt/postgresql@17/bin/psql "postgresql://ohmy:ohmy@localhost:5432/postgres" \
  -c "drop database ohmyenglish_t140"
rm -rf /tmp/t140-audio
```

⚠️ **뿌리를 인자로 준다** — 기본값을 쓰면 실물 `assets/audio` 를 지운다.

## 6. 마감 — 고침과 단정 (결정 119)

사용자가 **「세 자리 함께 + 단정 추가」**를 골랐고 **이 세션이 TDD 로 구현**했다(결정 119).

- **정본을 하나로** 뒀다: `services/sessions.py` 의 `LIVE_SESSION_STATUSES` 튜플이 값역이고
  `LIVE_SESSION_STATUSES_SQL` 이 그것에서 **유도**된다 — 문자열을 두 곳에 적지 않는다.
- **고친 세 자리**: `_SELECT_PURGE_USERS_SQL` · `_SELECT_EXPIRED_RECORDINGS_SQL` ·
  `load_recording`. 앞의 둘은 `not in {LIVE_SESSION_STATUSES_SQL}`, 마지막은 파이썬 쪽 검사다.
- **박은 단정 셋**(RED 를 먼저 봤다 — 셋 다 기대한 이유로 실패했다):
  `test_load_still_serves_a_past_day_recording_while_the_session_is_paused` ·
  `test_purge_spares_a_paused_session` ·
  `test_purge_spares_the_paused_session_of_a_learner_who_also_has_a_finished_one`.
  ⛔ **셋째가 없으면 대상 조회 쪽이 지켜지지 않는다** — 끝난 세션이 학습자를 목록에 올리므로
  둘째 단정만으로는 그 자리를 지우고도 통과한다(진행 중 세션의 같은 짝이 그 근거다).

게이트(고친 뒤 직접 돌린 출력): `pytest` **1266 passed**(14.95s · 앞 판 1263 + 단정 3) ·
`ruff check` 통과 · `ruff format --check` **49 files** · `ty check` 통과 ·
`npx tsc --noEmit` **exit 0** · `npx eslint .` **exit 0**.
