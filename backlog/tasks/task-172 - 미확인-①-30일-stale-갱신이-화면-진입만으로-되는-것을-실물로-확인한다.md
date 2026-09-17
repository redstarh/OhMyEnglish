---
id: TASK-172
title: '미확인 ①: 30일 stale 갱신이 화면 진입만으로 되는 것을 실물로 확인한다'
status: Done
assignee: []
created_date: '2026-09-17 22:06'
updated_date: '2026-09-17 22:20'
labels: []
dependencies: []
ordinal: 233000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
지난 세션이 서버 쪽(metadata_stale 계산·upsert 갱신)만 확인하고 화면 거동을 못 봤다. app/frontend/app/videos/page.tsx 의 refreshStale 이 목록 진입 시 oEmbed 로 제목·채널을 다시 받아 POST /api/videos 로 갱신한다 — 그 경로가 실물 브라우저에서 도는 것을 관측한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 담아 둔 영상의 metadata_fetched_at 을 31일 전으로 밀고 GET /api/videos 가 metadata_stale=true 를 주는 것을 확인함
- [x] #2 목록 화면에 진입하는 것만으로 그 행의 metadata_fetched_at 이 최근 값으로 바뀌는 것을 DB 에서 확인함
- [x] #3 갱신 사실을 알리는 문구가 화면에 뜨지 않는 것을 확인함 (설계서 §1 질문 2 의 「조용히」)
- [x] #4 관측 증거를 태스크 노트에 남김
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 실측 2026-09-18 KST (DB 시각은 UTC 표기)

경로: 브라우저(headless Chrome) → oEmbed → POST /api/videos → DB. 실물 영상 `jNQXAC9IVRw`(Me at the zoo · jawed).

1. 담기 직후 `metadata_fetched_at` = `2026-09-17 22:19:24+00` · `stale=f`.
2. 시험 조건: `update youtube_videos set metadata_fetched_at = now() - make_interval(days => 31)` → `2026-08-17 22:19:42+00`.
   ⚠️ 표시가 틀려서 고친 것이 아니라 시험 조건을 만든 것임 (CLAUDE.md DB 규약 4 와 구분됨).
3. `GET /api/videos` → `metadata_stale: true`. (AC 1)
4. `/videos` 화면 진입만 함 — 다른 조작 없음. 5초 뒤 `metadata_fetched_at` = `2026-09-17 22:19:52+00` · `stale=f`. (AC 2)
5. 화면에 갱신 알림 없음 — `[role=status]`·`[role=alert]` 요소 **0개**이고 본문에도 문구 없음. 스크린샷으로 직접 확인함. (AC 3)

## ⛔ 이 회차가 찾은 함정 — 브라우저 검증은 `localhost` 로 연다

`127.0.0.1:3000` 으로 열면 **hydration 이 아예 안 된다.** Next dev 가 그 호스트를 다른 origin 으로 보고
dev 리소스를 차단함(`⚠ Blocked cross-origin request to Next.js dev resource … from \"127.0.0.1\"` — 프론트 로그).
증상은 **버튼이 잠긴 채 아무 반응이 없음**이고 브라우저 콘솔에는 오류가 **없다.**
판정: DOM 노드에 React 내부 키(`__reactProps$…`)가 **0개**이고, 클라이언트에서만 렌더되는 문구(빈 목록 안내)가 **없다.**

⚠️ **판별력 없는 검사에 속았음**: 청크를 `fetch` 로 다시 받아 보고 15개 전부 200 이라 「스크립트가 실려 있다」로 읽었음.
`fetch` 는 그 차단을 거치지 않으므로 **스크립트 태그 로딩 차단을 그 검사로는 잡을 수 없음.**

⚠️ 부수 확인: `thumbnailUrl` 이 조립한 `i.ytimg.com` 썸네일이 실제로 렌더됨(설계서 §2 가 「문서화된 계약이 아니다」라 적어 둔 자리).
<!-- SECTION:NOTES:END -->
