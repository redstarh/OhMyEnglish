-- 004_pronunciation_attempt_seq.sql
-- 발음 시도의 **삽입 순서**를 DB가 강제한다 (003 후속).
--
-- 왜 필요한가: 003은 `created_at timestamptz not null default now()`만 가졌다. `now()`는
-- 트랜잭션 시각이라 **한 트랜잭션에서 만든 두 행이 같은 값을 갖는다**. 그런데 시도
-- 생명주기(설계서 §3.2)는 판정이 올 때 "같은 세션의 **최신** pending"을 골라야 한다 —
-- 동값이면 그 조회가 흔들린다. 실측: created_at 정렬로는 두 pending 중 오래된 쪽을
-- 3회 중 1회 골랐다(`tests/integration/test_pronunciation_service.py` ④번 케이스).
--
-- 왜 앱 코드에서 clock_timestamp()를 쓰지 않는가: 그러면 불변조건이 함수 하나의 규약이
-- 되고 표를 직접 쓰는 다른 writer(테스트 픽스처·시더·백필)가 그 규약을 모른 채 정렬 불가능한
-- 행을 만든다. 게다가 벽시계는 순서의 **대리**일 뿐이라 동값 tie-break가 `gen_random_uuid()`로
-- 떨어지고, 그러면 50% 확률로 잘못된 시도를 닫는다 — 재현 불가한 조용한 오염이다.
-- `services/utterances.py:151`이 같은 함정을 만나 정렬 키 끝을 단조값으로 만든 전례를 따른다.
--
-- 왜 created_at의 DEFAULT를 바꾸지 않는가: `created_at`은 학습 코치의 시간창 조회
-- (설계서 §6.2, 003의 `created_at desc` 인덱스)가 쓴다. 거기서는 트랜잭션 고정 시각이 오히려
-- 옳다. 한 컬럼에 "언제"와 "누가 먼저"를 겸하게 하는 것이 문제의 뿌리였다 — 둘을 나눈다.
--
-- ⚠️ attempt_seq는 **표 전역** 삽입 순서다. `utterances.sequence_no`(세션 안에서 1,2,3…)와
--    다르다. 롤백된 트랜잭션이 시퀀스를 전진시켜 번호에 구멍이 나므로 학습자에게 보이는
--    순번으로 쓰지 않는다. 쓰임은 "최신 하나 고르기" 하나뿐이다.

alter table pronunciation_attempts
  add column attempt_seq bigint not null generated always as identity;

-- 생명주기 조회는 (session_id, outcome)으로 좁힌 뒤 최신 하나를 고른다. 003의
-- pronunciation_attempts_session_outcome_idx가 앞의 두 등치 조건을 이미 담당하고, 좁혀진
-- 집합이 세션당 몇 건이라 정렬은 메모리에서 끝난다 — 인덱스를 새로 만들지 않는다.
