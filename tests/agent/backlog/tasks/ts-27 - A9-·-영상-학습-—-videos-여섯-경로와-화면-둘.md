---
id: TS-27
title: A9 · 영상 학습 — videos 여섯 경로와 화면 둘
status: Done
assignee: []
created_date: '2026-09-19 05:18'
updated_date: '2026-09-19 05:41'
labels: []
dependencies: []
ordinal: 27000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
영역 A9. 대상: GET·POST /api/videos · GET·DELETE /api/videos/{id} · POST /api/videos/{id}/phrases · DELETE .../phrases/{item} · 화면 /videos 와 /videos/[videoId]. TS-8~TS-18 의 회귀 확인. ⚠️ YouTube oEmbed 실호출이 필요하나 무료임. ⚠️ 없는 videoId 는 플레이어가 아무 이벤트도 주지 않음(H-CB).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 담기가 oEmbed 로 제목·채널을 받아 201 created=true 를 줌 (TS-8 회귀)
- [x] #2 URL 형태 넷이 같은 영상 한 행으로 모임 (TS-9 회귀)
- [x] #3 YouTube 가 아닌 호스트·11자 아닌 id·유사 도메인이 422 로 거부됨 (TS-10 회귀)
- [x] #4 문장 담기의 값역 여섯이 422 로 거부되고 영상 출처 문장에는 오디오가 붙지 않음 (TS-12·TS-13 회귀)
- [x] #5 영상을 지워도 담은 문장이 남고 youtube_video_id 만 null 이 됨 (TS-14 회귀)
- [x] #6 화면 /videos 와 /videos/[videoId] 가 200 으로 렌더됨 (TS-17 회귀)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 2026-09-19 배치 B2 회차 — 통과 (AC 6/6)

결과: `tests/agent/runs/2026-09-19-b2/result.md` · HEAD `74fb5c0`(제품 코드 기준. 회차 끝 `81e150e` 는 `app/`·`db/` 를 0건 건드림).

- 회귀 4종: 새로 실패 **0건** · 고쳐짐 0건 · 여전히 실패 0건 · 새 시나리오 0건.
- AC#1 은 실제 브라우저 경로(`localhost:3000/videos` → 확인 → 담기)로 재서 「담았어요.」를 봤고, 201 은 같은 엔드포인트 직접 POST 로 읽었음.
- AC 밖에서 함께 확인한 이전 시나리오: TS-11·TS-15·TS-18 **여전히 통과**.
- ⛔ **TS-16 은 돌리지 않았음** — 세션 행이 같은 시각에 도는 배치 b1 의 자료라 착수 지시가 금지했음. 통과로 세지 않음.
- 추가 경계 3건 통과: 대문자 호스트 · extra 필드 422 · **같은 새 영상 동시 8건 담기에서 행 1개**(created=true 정확히 1건).
- 결함 등록 **0건**. 관측 1건(출처를 잃은 문장을 앱 경로로 지울 수 없음)은 설계서 §10-4 가 명시로 유보한 자리라 결함으로 올리지 않고 result.md §7 에 적었음.
- ⚠️ 이 회차가 만든 문장 `408d6cc5-da54-4f82-b3a7-69b32404ecd4` 가 **되돌려지지 않고 남았음** — AC#5 의 측정 자체가 고아 문장을 만들고 그것을 지울 앱 경로가 없음.
<!-- SECTION:NOTES:END -->
