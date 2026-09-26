---
id: TASK-274
title: 튜터 발화 음성 다시 듣기 백엔드
status: Done
assignee: []
created_date: '2026-09-26 04:24'
updated_date: '2026-09-26 05:09'
labels: []
dependencies: []
ordinal: 338000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
말풍선 [음성] 버튼의 백엔드. 발화는 (session_id, sequence_no) 로 가리킴 — final 프레임이 이미 sequence_no 를 실음. 화면은 같은 화자의 연속 final 을 한 줄로 합치므로 한 줄이 여러 sequence_no 일 수 있음
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 방식을 정해 docs/design 에 남김 — Nova 출력 오디오를 발화별로 보관할지 TTS 로 다시 합성할지
- [x] #2 화면 [음성] 버튼을 연결하고 합쳐진 줄은 순서대로 재생함
- [x] #3 단위 테스트와 게이트 통과
- [x] #4 브라우저가 세션 중 받은 튜터 음성을 발화별로 모아 다시 재생함(서버 API 없음)
- [x] #5 서버·DB 에 오디오를 저장하지 않음(R10-7 유지)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
방식: 안 C(브라우저 메모리) — 근거 docs/design/2026-09-26-utterance-replay-design.md. 서버·DB 변경 0. 구현: VoiceIo.replayPcm(재생 큐와 분리) · page.tsx 가 직전 튜터 final 이후 프레임을 다음 튜터 final 에 붙이고 합쳐진 줄은 이어 붙임 · 음성이 없는 줄은 버튼 비활성. 검증: 프런트는 테스트 러너가 없어 /tmp/t274_drive.py(격리 DB ohmyenglish_t274 · stub_unresponsive :8012 · 사본 :3001 · 헤드리스 Chrome)로 실물 순서 주입 — 버튼 [켜짐,켜짐,꺼짐] · 재생 [750ms,1000ms] PASS. 판별력: 버퍼를 비우지 않는 변이는 [1750,3500] 으로 FAIL. 게이트 tsc 0 · eslint 0 errors. 리뷰(opus) CRITICAL·HIGH 0 · MEDIUM 1·LOW 4 는 설계서 §4 한계로 기록.
<!-- SECTION:NOTES:END -->
