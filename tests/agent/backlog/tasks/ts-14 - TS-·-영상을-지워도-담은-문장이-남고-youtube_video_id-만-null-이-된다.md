---
id: TS-14
title: TS · 영상을 지워도 담은 문장이 남고 youtube_video_id 만 null 이 된다
status: Done
assignee: []
created_date: '2026-09-17 18:03'
updated_date: '2026-09-17 18:13'
labels: []
dependencies: []
ordinal: 14000
---

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 DELETE 가 204 임
- [x] #2 그 문장 행이 남아 있음
- [x] #3 youtube_video_id 가 null 임
- [x] #4 source_url 이 그대로 남음
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
회차 2026-09-18-0303 · HEAD 29aeaeb. 가장 중요한 계약 — 통과.
영상 A(dQw4w9WgXcQ)에 담긴 문장 11건 전부가 DELETE 뒤 남고 youtube_video_id 만 null 이 됐음.
source_url·source_title·clip_start_sec·clip_end_sec·level 이 그대로였고, 그 문장을 참조한
learning_sessions 행(547c3c46)도 남았음. 지운 뒤 그 문장 id 로 쉐도잉 세션이 다시 열림(출처를 잃어도 연습이 성립함).
증거: runs/2026-09-18-0303/evidence/TS-14-video-delete.txt
<!-- SECTION:NOTES:END -->
