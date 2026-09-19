# 영상으로 배우기 — 설계 (`TASK-161`)

> **선행**: 스토리보드 `docs/design/2026-09-18-video-learning-storyboard.md` 가 화면과 사용자 동작을
> 정했음. 이 문서는 그것을 **표·API·타입·테스트**로 옮기고, 스토리보드가 넘긴 질문 다섯에 답함.
>
> **근거의 정본**: `TASK-157`(langflix 분해) · `TASK-158`(정책·API 제약) · `TASK-159`(코드 구조).
> ⛔ 그 노트를 여기 옮겨 적지 않고 필요한 자리에서 태스크 ID 로 가리킴.
>
> **사용자 부재 상태에서 씀**(사용자가 *"나 자러간다 … 나에게 물어보지 말고, 너의 권고대로 일단
> 진행해 … 기능은 심플하고 너무 복잡하지 않게해"* 로 판단을 위임했음). 그래서 **모든 갈림길에서
> 권고를 고르고, 되돌리는 비용을 함께 적음.**

## §0. 이 설계가 만드는 것 — 전체 목록

| 층 | 새로 만드는 것 | 기존 것을 고치는 것 |
|---|---|---|
| DB | `027` — 표 `youtube_videos` + `shadowing_items.youtube_video_id` | 없음(기존 컬럼·CHECK 를 바꾸지 않음) |
| 백엔드 | `api/videos.py` · `services/videos.py` · `models/video.py` | `services/sessions.py` 의 클립 부착 SQL 한 줄 · `api/ws.py` 의 파라미터 한 줄 |
| 프론트 | `app/videos/page.tsx` · `app/videos/[videoId]/page.tsx` · `lib/youtube.ts` | `app/page.tsx` 의 `ADDITIONAL_LEARNING` 한 원소 · `lib/config.ts` 의 타입 하나 · `lib/api.ts` 에 조회 함수 |
| 테스트 | `tests/unit/test_video_url.py` · `tests/unit/test_videos_service.py` · `tests/integration/test_videos_api.py` | `tests/unit/test_schema.py` 에 값역 단정 · `tests/integration/test_ws.py` 에 지정 클립 경우 |

⛔ **새 세션 모드를 만들지 않음** · **새 job 종류를 만들지 않음** · **백엔드 런타임 의존성을 늘리지
않음**. 셋의 근거는 `TASK-159` 의 「새로 만들지 않는 것 셋」임.

## §1. 스토리보드가 넘긴 질문 다섯 — 답과 근거

### 질문 1. 영상을 지울 때 담은 문장을 함께 지우나

**답: 문장을 남김.** `shadowing_items.youtube_video_id` 를 **`on delete set null`** 로 둠.

- 근거: 문장은 사용자가 만든 학습 자산이고 `review_tasks`·`error_patterns`·`utterances` 가 그것에
  매여 있음. 영상 한 개를 지우는 동작이 복습 이력을 지우면 그 동작이 되돌릴 수 없게 됨.
- ⚠️ 대가: 「출처 영상이 사라진 문장」이 생김. 다만 **`source_url` 이 그대로 남으므로 출처를 완전히
  잃지 않음** — 화면이 그 문장을 `쉐도잉` 목록에서 계속 보여주고 영상 링크는 외부로 엶.
- 되돌리는 비용: `on delete cascade` 로 바꾸려면 마이그레이션 한 줄임. 반대 방향(cascade 로 지운
  뒤 되살리기)은 **불가능**하므로 보수적인 쪽을 고름.

### 질문 2. 제목·채널의 30일 보관 제한을 어떻게 지키나

**답: 저장하되 `metadata_fetched_at` 을 함께 두고, 30일이 지난 것은 서버가 `stale` 로 표시함.
갱신은 별도 엔드포인트 없이 `POST /api/videos` 가 겸함(같은 요청이 담기와 갱신을 함).**

- 근거: 저장하지 않으면 목록 화면이 영상 수만큼 외부 호출을 함 — 느리고 한 개만 실패해도 목록이
  깨짐. 저장하고 신선도를 기록하면 **갱신이 필요한 것만** 다시 부름.
- ⛔ **엔드포인트를 늘리지 않는 것이 이 답의 핵심임** — 담기와 갱신이 같은 입력(`url` + 제목·채널)을
  받으므로 하나로 둠. 중복은 오류가 아니라 **갱신**이고, 응답의 `created` 불린이 화면 문구를 가름.
- **썸네일은 저장하지 않음** — videoId 에서 조립함(§2 의 실측 근거).
- ⚠️ **남은 위험을 적어 둠**: `shadowing_items.source_title` 은 기존 계약(NOT NULL)이라 담을 때의
  제목을 그대로 보관하고 갱신 대상이 아님. 그 값은 **사용자가 담은 학습 항목의 라벨**로 위치를
  정하고, 영상 메타데이터의 정본은 `youtube_videos` 에 둠. ⛔ 나는 법률 판단을 하지 않음 — 이 설계가
  한 것은 「갱신 경로를 두고 정본을 한 곳에 모은 것」이고 그것으로 충분하다고 단정하지 않음.

### 질문 3. 담은 문장의 `level` 을 무엇으로 채우나

**답: 서버가 `users.current_level` 을 읽어 채움.** 사용자에게 묻지 않음.

- 근거: 기존 클립 선택(`_ATTACH_SHADOWING_CLIP_SQL`)이 이미 그 값을 기준으로 하므로 **같은 기준을
  쓰면 담은 문장이 그 선택에도 자연히 들어옴.** 화면에 선택지가 늘지 않음(사용자 지시 「심플하게」).
- ⚠️ 대가: 실제 영상이 사용자 수준보다 어려워도 그 수준으로 적힘. 담은 문장은 사용자가 **직접
  지정해 연습**하므로 자동 선택의 정확도에 의존하지 않아 그 대가가 작음.

### 질문 4. 구간 시각의 정밀도

**답: 소수 둘째 자리. ⛔ 접기를 «값역 층»이 하고 검증은 «접힌 값»을 봄** (`TASK-170` 이 정정함).

- 근거: 기존 시드 행이 `0.00`~`17.36` 으로 둘째 자리임 — 발명이 아니라 선례를 따름.
- 플레이어의 `getCurrentTime()` 이 부동소수를 주므로 **서버가 받아 접음**(값역을 서버가 소유하는 관례).
- ⚠️ **이 답의 첫 판은 「서비스가 저장 직전에 반올림한다」였고 그것이 결함을 만들었음** — 검증이
  **원본 값**으로 순서를 보면 `5.0 → 5.001` 처럼 원본은 순서가 맞는데 접으면 같아지는 구간이 값역을
  통과해 스키마 CHECK 에서 터지고 사용자는 **`500`** 을 봄. 통합 테스트가 그것을 재현했음(`TASK-170`).
  ⇒ `PhraseCreateRequest` 의 필드 검증이 먼저 접고 모델 검증이 그 값으로 판정함. 정밀도의 정본은
  `models/video.CLIP_PRECISION` 이고 서비스의 접기는 **라우터 없이 불릴 때를 위한 이중 방어**로 남음.
- ⚠️ **화면도 접힌 값으로 비교함** — 그러지 않으면 화면이 통과시킨 요청을 서버가 거부해 사용자가
  「구간 끝이 시작보다 뒤여야 해요」 대신 일반 실패 문구를 봄. 그 정밀도는 응답의
  `clip_precision_sec` 로 내려보내므로 **화면에 사본을 두지 않음.**

### 질문 5. `ADDITIONAL_LEARNING` 자료구조를 어떻게 넓히나

**답: 원소에 `href?: string` 을 더함.** 세 상태가 됨.

| 원소의 모양 | 거동 |
|---|---|
| `entry` 가 있음 | 세션 소켓을 엶 (기존 다섯) |
| `href` 가 있음 | 그 경로로 이동함 (**새 일곱째**) |
| 둘 다 없고 `note` 가 있음 | 비활성 + 안내 (`업무 역할극`) |

- ⛔ **`업무 역할극` 의 빈 칸이 이 변경에 휩쓸리지 않음** — 지금 렌더 조건이 `item.entry === null`
  하나인데 그것을 `item.entry === null && item.href === undefined` 로 좁힘. 그 칸의 `note` 와
  비활성은 그대로임.
- ⚠️ 음성 명령 매핑(`entryForTarget()`)은 `entry` 를 전제하므로 **일곱째 항목에 음성 명령을 붙이지
  않음.** 붙이려면 `AdditionalTarget` 값역과 백엔드 `ADDITIONAL_TARGETS` 를 함께 열어야 하고, 그것은
  이 갈래의 요구가 아님(사용자 지시 「심플하게」).

## §2. 데이터 모델 — `027`

⚠️ **번호는 파일을 쓰는 턴에 최대값을 다시 확인해 받음**(결정 27). 이 문서를 쓴 시점의 실측은
`db/migrations/` 최대 `026_dedicated_schema.sql` 이고 `schema_migrations` 마지막 적용도 같은 파일임.

### 새 표 `youtube_videos`

| 컬럼 | 형 | null | 무엇인가 |
|---|---|---|---|
| `id` | `uuid` (`gen_random_uuid()`) | NO | 우리 식별자. API 경로가 이것을 씀 |
| `youtube_id` | `text` **unique** | NO | 영상의 YouTube 식별자 11자 |
| `title` | `text` | NO | oEmbed 가 준 제목 (30일 갱신 대상) |
| `channel_name` | `text` | NO | oEmbed 가 준 채널명 (30일 갱신 대상) |
| `metadata_fetched_at` | `timestamptz` (`now()`) | NO | 제목·채널을 받은 시각 |
| `created_at` | `timestamptz` (`now()`) | NO | 담은 시각 |

CHECK 넷:

| 제약 | 문장 | 무엇을 막는가 |
|---|---|---|
| `youtube_videos_youtube_id_shape` | `youtube_id ~ '^[A-Za-z0-9_-]{11}$'` | 파싱이 뚫려도 임의 문자열이 못 들어옴. **URL 조립에 쓰이는 값이라 형태를 스키마가 가둠** |
| `youtube_videos_title_not_blank` | `length(btrim(title)) > 0` | `shadowing_items_source_title_check` 와 같은 형태 |
| `youtube_videos_channel_name_not_blank` | `length(btrim(channel_name)) > 0` | 같음 |
| `youtube_videos_youtube_id_key` | `unique (youtube_id)` | 같은 영상이 두 행이 되지 않음 — `POST` 가 upsert 인 근거 |

⛔ **`user_id` 를 두지 않음.** `shadowing_items`·`learning_scenarios` 가 둘 다 그 컬럼을 갖지 않고
단일 사용자 전제를 따름(직접 조회로 확인). 여기서 혼자 다르게 하면 다중 사용자 도입 때 **한 표만
먼저 갈라져** 마이그레이션이 두 벌이 됨.

⛔ **`thumbnail_url` 을 두지 않음.** `https://i.ytimg.com/vi/<youtube_id>/hqdefault.jpg` 로 조립함.

- 실측(2026-09-18): 영상 둘 × `hqdefault`·`mqdefault` 넷 다 **HTTP 200** · 없는 id 는 **404**.
- 얻는 것: 컬럼 하나가 줄고 **30일 보관 대상이 둘로 줄어듦**.
- ⚠️ **잃는 것과 그 크기**: 이 URL 형태는 oEmbed 응답과 달리 문서화된 계약이 아님. 패턴이 바뀌면
  **썸네일이 안 보임**이고 학습은 그대로 됨 — 화면이 이미지 실패에 대체 표시를 둠. 되돌리려면
  컬럼을 더하는 마이그레이션 하나임.

### 기존 표에 더하는 컬럼 하나

```
alter table shadowing_items
  add column youtube_video_id uuid references youtube_videos(id) on delete set null;
```

- ⛔ **`on delete set null` 은 선례임** — `learning_sessions_shadowing_item_id_fkey` 가 이미 같은
  동작임(직접 조회로 확인). 질문 1 의 답이 이 선례와 같은 방향임.
- CHECK 하나를 함께 더함: `youtube_video_id is null or source_url is not null`.
  ⇒ 영상에서 담은 문장은 **반드시 출처 링크를 가짐.** 그러면 기존
  `shadowing_items_audio_only_for_synthetic`(`audio_filename is null or source_url is null`)이
  **오디오 저장을 자동으로 막음** — 정책 III.E.1 을 새 방어가 아니라 **기존 방어가** 지킴.
- ⛔ **기존 컬럼·CHECK 를 하나도 바꾸지 않음.** 값역 확장(`drop`+`add`)이 필요한 자리가 없음 —
  새 세션 모드를 만들지 않기 때문임.

### 되돌리기

```
alter table shadowing_items drop constraint shadowing_items_video_requires_source_url;
alter table shadowing_items drop column youtube_video_id;
drop table youtube_videos;
```

⚠️ **담은 문장은 `shadowing_items` 에 남음** — 되돌려도 학습 자산이 사라지지 않음. 사라지는 것은
「어느 영상에서 왔는지」뿐이고 `source_url` 이 그것을 대체함.

## §3. API — `api/videos.py`

`APIRouter(prefix="/api/videos", tags=["videos"])`. `api/shadowing.py` 의 계보를 그대로 베낌.
`create_app()` 에 `include_router` 한 줄을 더함.

| # | 메서드·경로 | 몸통 | 응답 | 화면 동작 |
|--:|---|---|---|---|
| 1 | `GET /api/videos` | — | 영상 목록 (각 항목에 `phrase_count`·`metadata_stale`) | S2 목록 |
| 2 | `POST /api/videos` | `{url, title, channel_name}` | `{id, youtube_id, title, channel_name, created}` | S2 담기·갱신 |
| 3 | `DELETE /api/videos/{video_id}` | — | `204` | S2 지우기 |
| 4 | `GET /api/videos/{video_id}` | — | 영상 하나 + **담은 문장 목록** + `clip_max_span_sec`·`clip_precision_sec` | S3 진입 |
| 5 | `POST /api/videos/{video_id}/phrases` | `{transcript, clip_start_sec, clip_end_sec}` | 담은 문장 하나 | S3 문장 담기 |
| 6 | `DELETE /api/videos/{video_id}/phrases/{item_id}` | — | `204` | S3 문장 지우기 |

**여섯인 이유**: 화면 동작 하나에 하나씩임. ⛔ 4 가 영상과 문장 목록을 **함께** 주는 것이 요청을
하나로 줄이는 자리임 — 갈라 두면 S3 이 열릴 때마다 왕복이 둘이 됨.

**값역은 서버가 소유함** (관례):

| 입력 | 검사 | 실패 응답 |
|---|---|---|
| `url` | videoId 를 뽑지 못하면 거부 | `422` |
| `title`·`channel_name` | 공백만이면 거부 · 상한 200자 | `422` |
| `clip_start_sec`·`clip_end_sec` | **둘째 자리로 먼저 접고** 그 값으로 `0 <= start < end` · `end - start <= 90` | `422` |
| `transcript` | 공백만이면 거부 · 상한 1000자 | `422` |
| `video_id`·`item_id` | 경로에서 `UUID` 로 받음 | `422` (FastAPI 가 함) |

⛔ **`item_id` 를 `UUID` 로 받는 것이 경로 탈출 방어임** — `api/shadowing.py` 의
`get_clip_audio(item_id: UUID, ...)` 가 같은 근거로 그 형을 씀.

⚠️ **`metadata_stale` 은 서버가 계산함**: `metadata_fetched_at < now() - interval '30 days'`.
프론트가 날짜를 비교하지 않음 — 시각 판정을 두 곳에 두지 않음.

⚠️ **6 이 `{video_id}` 를 경로에 요구하는 이유**: 문장은 영상의 하위 자원이고, 그 영상에 속하지 않는
문장 id 를 주면 `404` 임. 그렇게 두면 **다른 영상의 문장을 지우는 요청이 성립하지 않음.**

## §4. 서비스 계층

관례를 따름: **raw SQL** · `conn` 을 **첫 인자**로 · 트랜잭션 경계는 호출자 소유 · 공용 헬퍼 금지
(정본은 `services/__init__.py` docstring).

### `services/video_url.py` — 순수 함수 하나

```
def parse_youtube_id(url: str) -> str | None
```

⛔ **모듈을 따로 두는 이유**: `conn` 을 받지 않는 유일한 함수이고, 테스트 배치 관례가
`tests/unit/test_<모듈>.py` 1:1 이므로 `test_video_url.py` 와 짝이 맞음. `services/videos.py` 에
섞으면 그 파일의 테스트가 「DB 를 쓰는 것」과 「안 쓰는 것」을 함께 담음.

다루는 형태 넷과 실패:

| 입력 | 결과 |
|---|---|
| `https://www.youtube.com/watch?v=<id>` | `<id>` |
| `https://youtu.be/<id>` | `<id>` |
| `https://www.youtube.com/shorts/<id>` | `<id>` |
| `https://www.youtube.com/embed/<id>` | `<id>` |
| 위 형태에 `&t=42s` 등이 붙음 | `<id>` (질의 문자열을 무시함) |
| 11자 형태가 아님 · YouTube 도메인이 아님 · 빈 문자열 | `None` |

⛔ **11자 형태 검사를 이 함수가 함** — 스키마 CHECK 와 **겹으로** 둠. 한 겹이 뚫려도 다른 겹이
막아야 함(`api/shadowing.py` 가 경로 조립에서 같은 방식을 씀).
⚠️ 도메인을 확인함 — 아무 URL 에서 11자 조각을 뽑지 않음. 허용 호스트는 `youtube.com`(+`www.`·`m.`)
과 `youtu.be` 임.

### `services/videos.py` — 여섯 함수

| 함수 | 하는 일 | 없을 때 |
|---|---|---|
| `list_videos(conn)` | 영상 목록 + 문장 수 + `metadata_stale` | 빈 리스트 |
| `upsert_video(conn, *, youtube_id, title, channel_name)` | 담기·갱신. `(행, created)` 를 줌 | — |
| `delete_video(conn, video_id)` | 영상만 지움 | `False` |
| `load_video_with_phrases(conn, video_id)` | 영상 하나 + 문장 목록 | `None` |
| `add_phrase(conn, video_id, *, transcript, start_sec, end_sec)` | `shadowing_items` 에 행을 넣음 | `None` (영상이 없음) |
| `delete_phrase(conn, video_id, item_id)` | 그 영상의 문장만 지움 | `False` |

**`upsert_video` 의 SQL 형태** — `on conflict` 로 한 문장에 담음:

```
insert into youtube_videos (youtube_id, title, channel_name)
values ($1, $2, $3)
on conflict (youtube_id) do update
   set title = excluded.title,
       channel_name = excluded.channel_name,
       metadata_fetched_at = now()
returning id, youtube_id, title, channel_name, metadata_fetched_at,
          (xmax = 0) as created
```

⚠️ **`xmax = 0` 이 「새로 만들었는가」를 줌** — upsert 에서 삽입과 갱신을 가르는 표준 수법임. 이 값이
화면 문구(「담았어요」 vs 「이미 담아 둔 영상이에요」)를 가름.
⛔ **`metadata_fetched_at` 을 갱신 때만 `now()` 로 미룸** — 삽입은 컬럼 기본값이 이미 그 값임.

**`add_phrase` 가 `level` 을 얻는 방법**: 같은 INSERT 안에서 `users` 를 읽음 —
`(select current_level from users where id = $5)`. ⇒ 왕복이 하나로 끝나고, 사용자가 없으면
NOT NULL 위반으로 실패함(조용히 기본값을 만들지 않음).

**`add_phrase` 가 채우는 컬럼**: `source_title` ← 영상 제목 · `source_url` ←
`https://www.youtube.com/watch?v=<youtube_id>` · `transcript` · `clip_start_sec` · `clip_end_sec` ·
`level` · `youtube_video_id`.
⛔ **`source_url` 을 정규화된 한 형태로 저장함** — 사용자가 `youtu.be` 로 넣어도 저장은 `watch?v=`
형태임. 그래야 나중에 문자열로 비교할 수 있음.

## §5. 프론트엔드

⚠️ **프론트에 테스트 러너가 없음**(`TASK-159` 6항). 그래서 **논리를 프론트에 두지 않는 것**이 이
절의 규율임 — 프론트가 하는 것은 전송·표시·플레이어 제어뿐임.

### `lib/youtube.ts` — 새 모듈

| 내보내는 것 | 하는 일 |
|---|---|
| `fetchVideoMeta(url)` | oEmbed 를 부름. 실패면 `null` (⚠️ 없는 영상이 **400** 임) |
| `thumbnailUrl(youtubeId)` | `https://i.ytimg.com/vi/<id>/hqdefault.jpg` 를 조립함 |
| `loadPlayerApi()` | IFrame Player API 스크립트를 한 번만 싣고 준비를 기다림 |

⛔ **`fetchVideoMeta` 가 videoId 를 뽑지 않음** — 그것은 서버의 일임(§4). 프론트는 URL 을 그대로
oEmbed 와 서버에 넘김. ⇒ 파싱 규칙이 두 곳에 갈리지 않음.

### `app/VideoPlayer.tsx` — 새 컴포넌트

`app/` 에 나란히 두는 관례를 따름(`ShadowingPanel.tsx`·`WeeklyReportPanel.tsx` 가 그 자리임).

- `new YT.Player(...)` 로 플레이어를 만들고 `onStateChange`·`onError` 를 받음.
- 부모에게 주는 것: `getCurrentTime()` 값을 읽는 함수 · 구간 반복을 켜는 함수 · 오류 코드.
- **구간 반복**은 `onStateChange` 에서 끝(`0`)을 받거나 `getCurrentTime()` 이 끝점을 넘으면
  `seekTo(시작점)` 함. ⚠️ IFrame API 에 반복 기능이 없어 우리가 만드는 유일한 자리임(`TASK-158` 7항).
- ⛔ **플레이어 컨트롤을 가리지 않음**(정책 III.I.6).

### 화면 둘

| 파일 | 화면 | 상태 |
|---|---|---|
| `app/videos/page.tsx` | S2 목록 | `videos` · `draft`(URL 입력) · `preview`(oEmbed 결과) · `error` |
| `app/videos/[videoId]/page.tsx` | S3 학습 | `video` · `phrases` · `span`(시작·끝) · `transcript` · `error` |

상태 관리 라이브러리를 쓰지 않음 — `useState`·`useRef` 만 씀(기존 관례).
조회는 `lib/api.ts` 의 `fetch`(`cache: "no-store"`)를 씀.

### `app/page.tsx` 의 변경 — 원소 하나와 조건 하나

```
{ label: "영상으로 배우기", entry: null, href: "/videos" }
```

렌더 조건을 `item.entry === null` 에서 `item.entry === null && item.href === undefined` 로 좁힘
(질문 5). ⛔ `업무 역할극` 의 `note` 와 비활성이 그대로임.

## §6. 쉐도잉 배선 — 기존 코드를 고치는 유일한 자리

지금 클립 선택은 자동임. **사용자가 문장을 지정하는 경로를 엶.**

`_ATTACH_SHADOWING_CLIP_SQL` 의 `coalesce` 에 **맨 앞 항**을 하나 더함:

```
set shadowing_item_id = coalesce(
      (select i.id from shadowing_items i where i.id = $3),
      (select i.id from shadowing_items i
        where i.level = (select u.current_level from users u where u.id = $2)
        order by i.created_at, i.id limit 1),
      (select i.id from shadowing_items i order by i.created_at, i.id limit 1)
    )
```

⛔ **없는 id 가 오면 조용히 자동 선택으로 떨어짐** — `select` 가 0행이면 `coalesce` 가 다음 항으로
감. 예외를 던지지 않는 것이 기존 관례임(`api/ws.py` 의 `_load_*_or_none` 들이 조회 실패를 세션 실패로
번역하지 않음).
⚠️ **그 관례를 따르는 대가를 적어 둠**: 사용자가 특정 문장을 고른 뒤 그것이 사라졌으면 **다른 문장이
열림.** 그 경우를 화면이 알 수 있게 `session_started` 가 이미 클립 정보를 실어 보내므로, S3 에서 넘긴
id 와 다르면 프론트가 안내를 띄울 수 있음 — 다만 **MVP 에서 그 안내를 만들지 않음**(문장을 지운
직후에만 생기는 경우이고 화면이 이미 그 문장을 목록에서 지웠음).

이어지는 배선 셋:

1. `start_shadowing_session(pool, user_id, *, learning_source=None, item_id: UUID | None = None)` —
   인자 하나를 더하고 SQL 에 `$3` 로 넘김.
2. `api/ws.py` — `websocket.query_params.get("item")` 을 `UUID` 로 파싱하고 실패하면 `None`.
   ⛔ 파싱 실패를 오류로 만들지 않음(같은 관례).
3. `lib/config.ts` 의 `SessionEntry` 에 `itemId?: string` 을 더하고 `sessionSocketUrl` 이
   `item` 질의로 실음.

## §7. 오류 처리 — 스토리보드의 표를 응답으로 옮김

| 무엇이 틀렸나 | 어디가 잡나 | 사용자가 보는 것 |
|---|---|---|
| URL 에서 videoId 를 못 뽑음 | 서버 `422` | 「이 링크에서 영상을 찾지 못했어요」 |
| 영상이 없음 (oEmbed **400**) | 프론트 `fetchVideoMeta` → `null` | 같은 문구 |
| 이미 담은 영상 | 서버 `created=false` | 「이미 담아 둔 영상이에요」 + 그 카드로 이동 |
| oEmbed 네트워크 실패 | 프론트 | 「지금 확인할 수 없어요. 잠시 뒤 다시 시도해 주세요」 |
| 구간이 90초를 넘음 | 서버 `422` (+ 프론트가 담기 버튼을 미리 막음) | 「구간은 90초까지 담을 수 있어요」 |
| 끝점이 시작점보다 이르거나 같음 | 서버 `422` (+ 프론트 선제) | 「구간 끝이 시작보다 뒤여야 해요」 |
| 문장이 비어 있음 | 프론트가 버튼을 막음 + 서버 `422` | 버튼이 눌리지 않음 |
| 영상이 임베드를 막았음 | 플레이어 `onError` (`101`·`150`) | 「이 영상은 앱 안에서 재생할 수 없어요」 + 외부 링크 |
| 영상·문장이 없음 (지운 뒤 새로고침) | 서버 `404` | 「찾을 수 없어요」 + 목록으로 |

⛔ **검사를 프론트와 서버 양쪽에 두는 것이 중복이 아님** — 프론트는 사용자를 **막고**, 서버는 값역을
**가둠**. 프론트만 두면 요청을 직접 보내 우회함. 서버만 두면 사용자가 담기 버튼을 누른 뒤에 실패를 봄.
⚠️ 상한 수치(90초 · 200자 · 1000자)의 정본은 **스키마와 서버**임. 프론트는 그 값을 상수로 갖고,
⛔ **두 곳이 갈렸을 때 서버가 이김**(프론트가 통과시켜도 서버가 `422` 를 냄).

## §8. 테스트 축

⚠️ 함수 이름은 **영어 문장형**(기존 관례). DB 픽스처는 `db_conn`(롤백) · API 는 `api_client`.

### `tests/unit/test_video_url.py`

| 축 | 무엇을 못 박나 |
|---|---|
| 형태 넷을 다 뽑음 | `watch?v=` · `youtu.be/` · `shorts/` · `embed/` |
| 질의 문자열이 붙어도 뽑음 | `&t=42s` |
| 11자가 아니면 `None` | 10자 · 12자 |
| YouTube 도메인이 아니면 `None` | ⛔ **아무 URL 에서 조각을 뽑지 않음** |
| 빈 문자열·공백이면 `None` | |

### `tests/unit/test_videos_service.py` (`db_conn`)

| 축 | 무엇을 못 박나 |
|---|---|
| 담기 → 목록에 뜸 | `upsert_video` + `list_videos` |
| 같은 영상을 다시 담음 → 행이 하나이고 `created=False` 이며 제목이 갱신됨 | upsert 계약 |
| 문장 담기 → `level` 이 `users.current_level` 과 같음 | 질문 3 의 답 |
| 문장 담기 → `source_url` 이 정규화된 `watch?v=` 형태임 | §4 의 규약 |
| 문장 담기 → `youtube_video_id` 가 채워짐 | 연결 |
| 영상을 지움 → **문장이 남고 `youtube_video_id` 가 null 이 됨** | ⛔ 질문 1 의 답 |
| 다른 영상의 문장 id 로 지우기 → 실패하고 그 문장이 남음 | §3 의 하위 자원 규약 |
| `metadata_stale` 이 30일 경계에서 갈림 | ⚠️ 31일 전으로 시각을 밀어 확인함 |

### `tests/integration/test_videos_api.py` (`api_client`)

엔드포인트 여섯의 정상 경로와 `422`·`404` 각 하나. ⛔ **밖으로 나가지 않음** — oEmbed 호출이 프론트에
있으므로 이 테스트에 외부 의존이 없음(그것이 §5 배치의 이득임).

### 기존 파일에 더하는 단정

| 파일 | 더하는 것 |
|---|---|
| `tests/unit/test_schema.py` | `youtube_videos` 의 CHECK 넷과 `shadowing_items` 의 새 CHECK 를 `pg_get_constraintdef` 로 대조 |
| `tests/integration/test_ws.py` | `query_string=b"mode=shadowing&item=<uuid>"` 로 열면 **그 문장이 붙음** · 없는 id 를 주면 **자동 선택으로 떨어짐** |

⛔ **`ty check` 가 `tests/` 도 봄** — 새 테스트 파일의 형이 맞아야 게이트가 통과함.

## §9. 단순 대안 하나 — 검토하고 기각함

**대안: 새 표를 만들지 않고 `shadowing_items` 만 쓴다.** 영상 목록은 `select distinct source_url` 로
얻고 제목은 `source_title` 을 씀.

- 얻는 것: 마이그레이션이 필요 없음. 표 0개 · 컬럼 0개.
- ⛔ **기각한 결정적 이유**: **문장을 담기 전에는 영상이 목록에 없음.** 사용자 지시가
  *"영상을 수집해서, 내가 영상을 보며 공부하고"* 이므로 **영상 자체가 자산**임 — 담아 두고 나중에
  공부하는 것이 이 갈래의 핵심 동작이고, 그것이 성립하지 않으면 기능이 아님.
- 부수 이유 셋: ① 제목·채널을 문장마다 중복 저장함 ② 30일 갱신을 문장마다 해야 함 ③ 영상만 지우는
  동작이 불가능함.

⇒ 표 하나를 더하는 비용이 위 넷보다 작음. **다만 대안이 남긴 교훈을 채택함** — 영상 표에 컬럼을
최소로 둠(썸네일을 조립하고 `user_id` 를 두지 않는 판단이 그것임).

## §10. 이 설계가 정하지 않은 것 — 넘기는 것을 밝힘

1. **영상 검색·추천** — MVP 밖임(스토리보드 §6). 넣으려면 API 키·쿼터·일일 100회 제한이 함께 들어옴.
2. **딕테이션 채점** — 정답이 없어 성립하지 않음. 쉐도잉 연습이 그 역할을 함.
3. **음성 명령으로 이 갈래에 들어가기** — 질문 5 의 대가로 뺐음.
4. **「출처를 잃은 문장」의 화면 처리** — 영상을 지운 뒤 그 문장이 쉐도잉 목록에 남음. 지금은 기존
   화면이 그대로 보여주고 특별한 표시를 하지 않음.
   ⛔ **2026-09-19 사용자 결정 — 이 유보를 그대로 닫는다. 처리하지 않는다.**
   통합테스트 회차(`TASK-229` · 배치 B2)가 이 유보의 실제 대가를 관측했음: **출처를 잃은 문장을 앱
   경로로 지울 수단이 없다** — `DELETE` 엔드포인트가 둘뿐이고 둘 다 `video_id` 를 요구하며(지운
   영상 id·다른 영상 id 양쪽으로 `404`, 행은 남음), 그 문장만 보여 주는 화면도 없음. 그래서 그
   회차가 AC 측정 중 만든 문장 **`408d6cc5-da54-4f82-b3a7-69b32404ecd4` 1건이 DB 에 남아 있음.**
   ⚠️ **그 행을 결함으로 쫓지 말 것** — 유보가 낳은 알려진 잔여이고 사용자가 처리하지 않기로 정했음.
   ⛔ 되살릴 때 챙길 것: 삭제 표면을 만들면 그 행부터 걷을 수 있어야 함(지금은 `video_id` 없이
   문장을 지목하는 경로가 없는 것이 그 자체로 제약임).
5. **30일 지난 메타데이터의 자동 갱신** — 서버가 `stale` 을 표시하고 화면이 다시 담을 때 갱신됨.
   **주기적으로 도는 작업을 만들지 않음**(job 종류를 늘리지 않는 판단).

## §11. 구현 순서 — 태스크로 나누는 근거

의존이 실제로 있는 자리만 순서를 강제함.

```
① 027 마이그레이션 (표 + 컬럼 + CHECK)
     ├─ ② services/video_url.py  (독립 — DB 를 안 씀)
     └─ ③ services/videos.py + models/video.py
              └─ ④ api/videos.py + create_app 등록
                       └─ ⑤ 프론트: lib/youtube.ts · VideoPlayer · 화면 둘 · 진입점
⑥ 쉐도잉 배선 (SQL · start_shadowing_session · ws · config)  ← ① 이후 언제든
⑦ 통합 테스트 (Test Agent)  ← ⑤·⑥ 이후
```

⚠️ **②는 ①과 무관함**(순수 함수) — 병행할 수 있음.
⚠️ **⑥은 ⑤과 무관함** — 서버 쪽 배선이 먼저 서 있어야 ⑤의 [연습하기] 가 붙을 자리가 생김.
