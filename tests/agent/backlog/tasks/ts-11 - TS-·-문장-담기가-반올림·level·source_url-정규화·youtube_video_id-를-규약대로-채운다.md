---
id: TS-11
title: TS · 문장 담기가 반올림·level·source_url 정규화·youtube_video_id 를 규약대로 채운다
status: Done
assignee: []
created_date: '2026-09-17 18:03'
updated_date: '2026-09-17 18:13'
labels: []
dependencies: []
ordinal: 11000
---

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 소수 셋째 자리가 둘째 자리로 반올림됨
- [x] #2 level 이 users.current_level 과 같음
- [x] #3 source_url 이 정규화된 watch?v= 형태임
- [x] #4 youtube_video_id 가 그 영상 id 임
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
회차 2026-09-18-0303 · HEAD 29aeaeb. AC 넷 전부 충족.
반올림은 ROUND_HALF_UP 임(실측: 10.005→10.01 · 30.995→31.00 · 70.125→70.13 · 70.135→70.14 · 50.4449→50.44).
level=A2 = users.current_level · source_url 정규화는 youtu.be 로만 담은 영상에서도 watch?v= 형태였음.
⚠️ 설계서 §3 의 필드 이름(start_sec·end_sec)이 구현(clip_start_sec·clip_end_sec)과 다름 → 문서 결함 TASK-171.
증거: runs/2026-09-18-0303/evidence/TS-11-post-phrase.txt · TS-11-db-row.txt · TS-11-rounding.txt
<!-- SECTION:NOTES:END -->
