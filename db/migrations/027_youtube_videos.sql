-- 027_youtube_videos.sql
-- 영상으로 배우기 — 담아 둔 YouTube 영상 표와, 그 영상에서 담은 문장을 잇는 컬럼
-- 설계: docs/design/2026-09-18-video-learning-design.md §2
-- 스토리보드: docs/design/2026-09-18-video-learning-storyboard.md
-- 캡틴 결정: 125(PRD 범위를 넓히는 것이 아니다 — §10 이 이미 요구했다) ·
--            126(자막을 못 쓰는 제약을 설계의 축으로 삼는다 · 딕테이션)
-- 소유 태스크: TASK-162
--
-- 번호: `ls db/migrations/` 실측 최대가 026 이므로 027 이다(2026-09-18 에 쓰는 턴에 다시 조회했고
--       `schema_migrations` 의 마지막 적용도 026_dedicated_schema.sql 이었다).
-- ⛔ 번호를 미리 예약하지 않는다(결정 27).
--
-- 되돌리기:
--   alter table shadowing_items drop constraint shadowing_items_video_requires_source_url;
--   drop index shadowing_items_youtube_video_id_idx;
--   alter table shadowing_items drop column youtube_video_id;
--   drop table youtube_videos;
-- ⚠️ 되돌려도 담은 문장은 `shadowing_items` 에 남는다 — 사라지는 것은 「어느 영상에서 왔는지」뿐이고
--    `source_url` 이 그것을 대체한다.

-- ⛔ **`user_id` 를 두지 않는다.** `shadowing_items`·`learning_scenarios` 가 둘 다 그 컬럼을 갖지
--    않고 단일 사용자 전제를 따른다(2026-09-18 직접 조회). 여기서 혼자 다르게 하면 다중 사용자를
--    도입할 때 **한 표만 먼저 갈라져** 마이그레이션이 두 벌이 된다.
-- ⛔ **`thumbnail_url` 을 두지 않는다.** `https://i.ytimg.com/vi/<youtube_id>/hqdefault.jpg` 로
--    조립한다(실측 2026-09-18: 영상 둘 × 두 크기 넷 다 HTTP 200 · 없는 id 는 404). 얻는 것은
--    컬럼 하나가 줄고 **YouTube 정책의 30일 보관 대상이 둘로 줄어드는 것**이다.
--    ⚠️ 잃는 것: 그 URL 형태는 oEmbed 응답과 달리 문서화된 계약이 아니다. 패턴이 바뀌면
--    **썸네일이 안 보이고** 학습은 그대로 된다 — 화면이 이미지 실패에 대체 표시를 둔다.
create table youtube_videos (
  id uuid primary key default gen_random_uuid(),
  youtube_id text not null unique,
  title text not null,
  channel_name text not null,
  -- ⚠️ 제목·채널은 **YouTube 에서 온 값**이고 Developer Policies III.E.4.c·d 가 보관을 30일로
  --    제한한다. 그래서 받은 시각을 함께 남긴다 — 서버가 이 값으로 `metadata_stale` 을 계산하고
  --    화면이 다시 담을 때 `POST /api/videos` 가 갱신한다(설계서 §1 질문 2).
  -- ⛔ 시각 판정을 프론트에 두지 않는다 — 두 곳에 두면 갈라진다.
  metadata_fetched_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  -- ⛔ **형태를 스키마가 가두는 이유**: 이 값이 URL 조립에 쓰인다. 파싱이 뚫려 임의 문자열이
  --    들어오면 화면이 만드는 URL 이 우리 통제 밖으로 나간다. 값역이 첫 겹이고
  --    `services/video_url.parse_youtube_id` 가 둘째 겹이다 — 한 겹이 뚫려도 다른 겹이 막는다.
  constraint youtube_videos_youtube_id_shape check (youtube_id ~ '^[A-Za-z0-9_-]{11}$'),
  -- `shadowing_items_source_title_check` 와 같은 형태다 — 공백만인 라벨을 만들지 않는다.
  constraint youtube_videos_title_not_blank check (length(btrim(title)) > 0),
  constraint youtube_videos_channel_name_not_blank check (length(btrim(channel_name)) > 0)
);

comment on table youtube_videos is
  '사용자가 담아 둔 YouTube 영상. 메타데이터·링크만 보관한다(PRD 10). 오디오·영상은 저장하지 않는다.';

-- ⛔ **`on delete set null` 은 선례다** — `learning_sessions_shadowing_item_id_fkey` 가 이미 같은
--    동작이다(2026-09-18 직접 조회). 문장은 사용자가 만든 학습 자산이고 `review_tasks`·
--    `error_patterns`·`utterances` 가 그것에 매여 있으므로, 영상 한 개를 지우는 동작이 복습 이력을
--    지우면 그 동작이 되돌릴 수 없어진다(설계서 §1 질문 1).
alter table shadowing_items
  add column youtube_video_id uuid references youtube_videos(id) on delete set null;

-- FK 는 자동으로 인덱스를 만들지 않는다. 이 컬럼으로 「그 영상의 문장 목록」과 「영상별 문장 수」를
-- 조회하므로 인덱스를 함께 둔다.
create index shadowing_items_youtube_video_id_idx
  on shadowing_items (youtube_video_id)
  where youtube_video_id is not null;

-- ⚠️ **이 CHECK 의 값은 자기가 막는 것보다 「그 위에 서는 것」에 있다.** 영상에서 담은 문장이 반드시
--    `source_url` 을 가지면, 기존 `shadowing_items_audio_only_for_synthetic`
--    (`audio_filename is null or source_url is null`)이 **오디오 저장을 자동으로 막는다** —
--    YouTube Developer Policies III.E.1(오디오·영상 콘텐츠 저장 금지)을 **새 방어가 아니라 기존
--    방어가** 지킨다. 그래서 이 마이그레이션은 정책 방어를 새로 만들지 않는다.
alter table shadowing_items
  add constraint shadowing_items_video_requires_source_url
  check (youtube_video_id is null or source_url is not null);
