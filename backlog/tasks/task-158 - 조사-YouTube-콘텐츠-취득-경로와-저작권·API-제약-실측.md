---
id: TASK-158
title: '조사: YouTube 콘텐츠 취득 경로와 저작권·API 제약 실측'
status: Done
assignee: []
created_date: '2026-09-17 16:54'
updated_date: '2026-09-17 17:02'
labels: []
dependencies: []
ordinal: 219000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
PRD 5 가 「무제한 YouTube 자동 수집·저작물 전체 저장」을 비범위로 명시했다. 사용자 지시가 그 경계를 옮기므로 어떤 형태가 허용되는지(임베드 재생·메타데이터·자막 참조)를 실측으로 정한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 YouTube Data API v3 의 검색·자막 취득 가능 범위와 쿼터를 확인했다
- [x] #2 자막(caption) 취득의 실제 가능 경로를 확인했다
- [x] #3 저장해도 되는 것과 저장하면 안 되는 것을 갈라 적었다
- [x] #4 API 키 없이 개발·테스트할 수 있는 대체 경로를 정했다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 실측 결과 (2026-09-18 · 공식 문서 직접 조회)

### 1. 자막 취득 — ⛔ 남의 공개 영상 자막을 받을 경로가 없음

`captions.download` (developers.google.com/youtube/v3/docs/captions/download):
- OAuth 2.0 필수임. API 키만으로는 호출되지 않음.
- 문서 문장: `This method requires the user to have permission to edit the video`.
  즉 **영상 소유자만 자기 영상의 자막을 내려받음.**
- scope: `youtube.force-ssl` 또는 `youtubepartner` · 쿼터 200 units.

⇒ **우리가 남의 영상 자막 텍스트를 합법적으로 얻을 수단이 없음.** 이것이 설계의 가장 큰 제약임.

### 2. 스크래핑은 명시적으로 금지됨

Developer Policies Section III.E.6:
`must not ... scrape YouTube Applications or Google Applications, or obtain scraped YouTube data or content`

⇒ 비공식 `timedtext` 엔드포인트나 `youtube-transcript-api` 류를 쓰지 않음. 「남이 스크래핑한
데이터를 받는 것」까지 같은 조항이 금지하므로 서드파티 자막 데이터셋도 쓰지 않음.

### 3. 저장해도 되는 것과 안 되는 것

| | 근거 조항 |
|---|---|
| ⛔ 오디오·영상 콘텐츠 저장·캐시·다운로드 | III.E.1 — `must not download, import, backup, cache, or store copies of YouTube audiovisual content` |
| ⚠️ API 메타데이터는 **30일까지만** | III.E.4.c·III.E.4.d — `for no longer than 30 calendar days` |
| 사용자가 직접 입력한 문장 | YouTube 데이터가 아니므로 이 제한 밖임 |

⇒ 영상 메타데이터(제목·채널·길이·썸네일)를 캐시하려면 **30일 만료·재조회 경로가 설계에 있어야 함.**
⇒ 학습 자산의 정본은 **사용자가 만든 데이터**여야 함 — 그것만 30일 제한에서 자유로움.

### 4. 플레이어

III.I.6: `must not modify, build upon, or block any portion or functionality of a YouTube player`
⇒ 재생은 YouTube IFrame Player 로 하고 컨트롤을 가리지 않음. 구간 반복은 `seekTo` 로 함.

### 5. 쿼터 (determine_quota_cost 문서)

| 메서드 | 비용 |
|---|---|
| `search.list` | 1 unit — 단 **별도 버킷으로 일일 100회 한도** |
| `videos.list` | 1 unit |
| `captions.list` | 50 units |
| `playlistItems.list` | 1 unit |

기본 일일 한도는 그 밖 엔드포인트 합계 **10,000 units** 임.
⇒ `search.list` 100회/일이 실질 병목임. 검색을 사용자 조작마다 부르지 않고 결과를 캐시함
(30일 제한 안에서).

### 6. 결론 — 이 조사가 설계에 넘기는 것

1. 자막을 못 받으므로 **langflix 의 「이중 자막」 을 그대로 베낄 수 없음.**
2. 학습 문장의 출처를 **사용자 입력**으로 두면 저작권·30일 제한·스크래핑 금지를 한꺼번에 피함.
   그리고 듣고 적는 것 자체가 딕테이션 학습이라 학습 가치가 오히려 큼.
3. 영상은 임베드로만 재생하고 우리는 **videoId 와 구간 시각**만 가짐.

## 7. 플레이어 제어 — IFrame Player API 로 되는 것과 안 되는 것 (같은 날 문서 조회)

| 필요 | 수단 | 판정 |
|---|---|---|
| 특정 시각부터 재생 | `seekTo(seconds, allowSeekAhead)` · `cueVideoById({startSeconds})` | 됨 |
| 구간 끝 지정 | `cueVideoById`·`loadVideoById` 의 `endSeconds` | 됨 |
| 구간 **반복** | 직접 지원이 없음 — `onStateChange` 에서 종료를 받아 `seekTo` 로 되돌림 | 우리가 구현함 |
| 현재 재생 시각 읽기 | `getCurrentTime()` | 됨 — 문장 담기의 시각 근거가 이것임 |
| 상태 변화 감지 | `onStateChange` (`-1` 미시작 · `0` 종료 · `1` 재생 · `2` 정지 · `3` 버퍼링 · `5` 준비) | 됨 |
| 플레이어 생성 | `onYouTubeIframeAPIReady()` 안에서 `new YT.Player(id, {videoId, playerVars, events})` | 됨 |
| 자막 **텍스트** 읽기 | 없음. `setOption('captions','fontSize', -1..3)` 로 **크기만** 조절함 | ⛔ 안 됨 |

⇒ 자막 텍스트는 플레이어 쪽으로도 못 가져옴. `TASK-158` 1항의 결론이 두 경로에서 같음.
⇒ 구간 반복은 `onStateChange` 기반으로 우리가 만들며, 그것이 유일한 구현 부담임.

## 8. AC 4 — API 키 없이 개발·테스트하는 경로

기존 앱의 `VOICE_ADAPTER=stub` 관례를 그대로 따름. `search.list` 가 일일 100회로 제한되므로
개발·테스트에서 실제 검색을 부르지 않는 것이 오히려 기본값이어야 함.
⇒ 어댑터 경계를 두고 stub 을 기본으로 함. 실제 키는 실물 확인 회차에서만 켬.
⚠️ 어댑터 이름과 설정 키의 최종 형태는 기존 관례를 읽은 뒤 설계서가 확정함(`TASK-159`·`TASK-161`).

## 9. ⛔ 가장 값 있는 실측 — API 키가 **아예 필요 없음**

`search.list` 의 일일 100회가 병목이라고 위에 적었는데, **검색 자체를 MVP 에서 빼면 그 병목이
사라짐.** 사용자가 영상 링크를 붙여넣는 경로 하나만 두면 됨(langflix 의 주 문구도
`YouTube 링크 하나만으로 학습 코스 즉시 생성` 임).

그러면 남는 필요는 「제목·썸네일을 얻는 것」뿐이고 그것은 **oEmbed 로 인증 없이 됨.**

실측 (2026-09-18 · 직접 호출):

```
GET https://www.youtube.com/oembed?url=<watch URL>&format=json
→ HTTP 200
{"title": "...", "author_name": "...", "author_url": "...",
 "thumbnail_url": "https://i.ytimg.com/vi/<id>/hqdefault.jpg",
 "thumbnail_width": 480, "thumbnail_height": 360, "html": "<iframe ...>"}
```

- API 키·OAuth 없이 200 임.
- 주는 것: 제목 · 채널명 · 채널 URL · 썸네일 URL·크기 · 임베드 iframe HTML.
- 안 주는 것: **영상 길이**. ⇒ 길이는 서버가 알 필요가 없음 — 플레이어의 `getDuration()` 이
  브라우저에서 주고, 구간 상한은 스키마 CHECK(`clip_end_sec - clip_start_sec <= 90`)가 이미 지킴.

⇒ **결론: MVP 는 YouTube Data API 를 쓰지 않음.** 필요한 외부 호출은 oEmbed 하나이고 키가 없음.
그래서 설정에 새 비밀값이 늘지 않고, stub 어댑터도 「키가 없어서」가 아니라 「테스트에서 밖으로
나가지 않기 위해」만 필요함.

⚠️ **검색을 넣는 것은 나중 결정으로 미룸** — 넣으면 API 키 · 쿼터 관리 · 일일 100회 제한이
한꺼번에 들어옴. 링크 붙여넣기로 학습이 성립하므로 MVP 에서 그 비용을 지불하지 않음.

## 10. oEmbed 의 오류·URL 경계 실측 (같은 날 직접 호출)

| 입력 URL | HTTP | 결과 |
|---|---|---|
| `watch?v=ZZZZZZZZZZZ` (없는 영상) | **400** | 본문이 JSON 이 아님 |
| `youtu.be/<id>` | 200 | 정상 |
| `youtube.com/shorts/<id>` | 200 | 정상 |
| `watch?v=<id>&t=42s` | 200 | 정상 |

⇒ **없는 영상은 404 가 아니라 400 임.** 「404 면 없는 영상」으로 판정하면 틀림.
⇒ oEmbed 는 URL 변형을 스스로 받아 주지만 **우리는 videoId 를 따로 추출해야 함** — 저장·중복 판정·
임베드 생성이 id 를 필요로 함. 다룰 형태는 넷임: `watch?v=` · `youtu.be/` · `shorts/` · `embed/`.
⇒ 400 은 「없는 영상」과 「형태가 틀린 URL」을 함께 뜻하므로 사용자에게는 한 문장으로 알림.

⚠️ **oEmbed 가 200 을 주는 것이 「임베드 가능」을 보장하지 않음** — 임베드를 막은 영상은 플레이어가
`onError` 로 알림(`101`·`150` 이 그 코드임). 그 처리는 화면 쪽 몫이고 설계서가 가져감.
<!-- SECTION:NOTES:END -->
