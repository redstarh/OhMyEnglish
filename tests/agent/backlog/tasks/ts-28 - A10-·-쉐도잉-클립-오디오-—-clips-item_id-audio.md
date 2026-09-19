---
id: TS-28
title: 'A10 · 쉐도잉 클립 오디오 — clips/{item_id}/audio'
status: Done
assignee: []
created_date: '2026-09-19 05:18'
updated_date: '2026-09-19 05:41'
labels: []
dependencies: []
ordinal: 28000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
영역 A10. 대상: GET /api/shadowing/clips/{item_id}/audio. 근거: 설계서 2026-09-14-shadowing-clip-audio-design.md. ⚠️ 시드 클립 오디오 파일이 리포에 있어야 함 — git check-ignore 판정은 exit 69(Xcode 라이선스)를 「무시됨」으로 접지 않도록 주의함(H-CH).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 시드된 클립의 오디오가 200 으로 나오고 본문 길이가 0 이 아님
- [x] #2 영상에서 담은 문장은 오디오가 없어 404 로 갈림 (TS-13 과 같은 경계)
- [x] #3 없는 item_id 가 404 로 갈림
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 2026-09-19 배치 B2 회차 — 통과 (AC 3/3)

결과: `tests/agent/runs/2026-09-19-b2/result.md` · HEAD `74fb5c0`(제품 코드 기준).

- AC#1: `GET /api/shadowing/clips/00000000-0000-0000-0000-000000000201/audio` → **200 · 559616바이트 · audio/wav**. 본문을 파일로 받아 `file(1)` 로 `RIFF … WAVE audio, Microsoft PCM, 16 bit, mono 16000 Hz` 를 확인했음(헤더만 믿지 않았음).
- **H-CH 함정을 피해 판정했음**: `assets/clips/…-201.wav` 가 `git ls-files --error-unmatch` **exit 0**(추적됨) · `git check-ignore` **exit 1**(무시되지 않음). 이 회차에서 `69` 는 나오지 않았으나 종료 코드를 `0`·`1`·`69` 셋으로 갈라 봤음.
- AC#2: 영상에서 담은 문장 → **404**. 같은 드라이버가 시드 클립에 200·559616바이트를 냈으므로 **관측력이 증명됨**(§7-7).
- AC#3: 없는 UUID → **404**. 곁가지로 꼴이 틀린 id → 422 · 경로 탈출 시도 → 404.
- 결함 등록 **0건**. 회귀 4종 전부 0건.
- ⚠️ 증거의 오디오 본문 전체(559616바이트)는 리포에 넣지 않고 앞 1024바이트만 `TS-28-ac1-seeded-clip-head1k.bin` 로 남겼음.
<!-- SECTION:NOTES:END -->
