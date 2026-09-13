-- 022_shadowing_clip_audio.sql
-- 합성한 쉐도잉 클립 오디오의 자리 — 파일명 컬럼 + 예외 경계 CHECK 둘
-- 설계: docs/design/2026-09-14-shadowing-clip-audio-design.md §3
-- 계획: docs/design/2026-09-14-shadowing-clip-audio-plan.md Task 1
-- 캡틴 결정: 47(쓴다·미리 만들어 저장 · R10-7 예외를 이 하나로 엶) · 90(리포 추적 · 접근 A) ·
--            88(시드의 시간 창은 실측 16.64)
-- 소유 태스크: TASK-66 · TASK-66.1
--
-- 번호: `ls db/migrations/` 실측 최대가 021 이므로 022 다(2026-09-14 에 쓰는 턴에 다시 조회했다).
-- ⛔ 번호를 미리 예약하지 않는다(결정 27) — 적용 직전에 한 번 더 확인한다.
-- ⛔ 소비자와 같은 커밋 흐름으로 나간다 — 011 이 세운 data-first 규약이고, 결정 90 이 그것을
--    유예하는 안("스키마와 엔드포인트만 내고 화면은 다음")을 기각했다.

alter table shadowing_items
  add column audio_filename text;

-- 파일명은 **id 로 결정된다.** 뿌리는 설정값(`shadowing_clip_audio_root`)이고 이 컬럼은 파일명만
-- 담는다 — 경로를 담으면 배포 자리가 바뀔 때 DB 값이 조용히 낡는다.
-- ⛔ **이 CHECK 가 경로 구분자를 원리적으로 배제한다** — 값역이 경로 이탈 방어의 첫 겹이고,
--    서비스가 경로를 `item_id` 로 조립하는 것이 둘째 겹이다(설계서 §5).
-- ⚠️ 포맷을 바꾸려면 이 제약을 고쳐야 한다. **그것이 의도다** — 값역이 계약이고, 011 이
--    `utterance_type` 값역으로 같은 일을 했다.
alter table shadowing_items
  add constraint shadowing_items_audio_filename_matches_id
  check (audio_filename is null or audio_filename = id::text || '.wav');

-- R10-7 예외의 경계. 결정 47 이 연 것은 「합성한 쉐도잉 클립 오디오」 하나이고, 출처 링크가 있는
-- 클립은 외부 저작물이라 PRD §5(*"저작물 전체를 저장하지 않는다"*)가 막는다.
-- ⛔ 011 의 `utterances_audio_only_for_shadowing` 주석이 적은 의도를 이 표에서 잇는다:
--    **다른 오디오가 조용히 쌓이는 길을 스키마가 막는다.** docstring 은 그 파일을 읽을 이유가
--    없는 사람을 구속하지 못하지만 스키마는 한다.
alter table shadowing_items
  add constraint shadowing_items_audio_only_for_synthetic
  check (audio_filename is null or source_url is null);

-- ⛔⛔ **적용 절차 — 이 파일을 돌리기 전에 읽어라** (011 이 세운 5단계를 그대로 쓴다)
--   ① `pg_dump -n public` 으로 백업한다. ⚠️ `-n public` 을 빼면 공유 인스턴스의 다른 스키마에서
--      `permission denied` 로 막힌다.
--   ② 표별 행 수를 기록한다(적용 후 대조용).
--   ③ 적용한다. ⚠️ `migrate.py` 는 이미 적용된 파일에 **아무 것도 출력하지 않는다** — 반드시
--      `schema_migrations` 를 조회해 확인한다.
--   ④ 재조회로 대조하고 출력을 태스크 노트에 남긴다.
--   ⑤ 어긋나면 **멈추고 사용자에게 올린다.** 스스로 고치지 않는다.
-- ⚠️ 2026-09-14 기준 dev DB 는 019 까지 적용돼 있고 **020·021 이 미적용이다** — 이 파일의 적용은
--    그 둘의 순서와 소유가 함께 걸리므로 승인 사안이다(`TASK-66.9`).
--
-- 되돌리기: `alter table shadowing_items drop column audio_filename;` 하나다. **값역 축소가
-- 아니라서 011 과 달리 안전하다** — 잃는 것은 파일명 문자열이고 파일은 git 이 추적하므로 남는다.
