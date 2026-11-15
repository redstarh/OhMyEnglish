---
id: TASK-325
title: >-
  아이폰에서 앱 쓰기 — Tailscale serve 로 화면·서버를 한 HTTPS 주소로 묶고 Safari 음성 인식을 실기기로 확인
  (사용자 결정으로 미룸 2026-11-14)
status: In Progress
assignee: []
created_date: '2026-11-14 11:27'
updated_date: '2026-11-15 03:04'
labels: []
dependencies: []
ordinal: 392000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자: 아이폰 사용. 근거(MDN browser-compat-data): Safari 14.1+ 는 webkitSpeechRecognition 지원(소리는 Apple 로 감) · iOS Chrome 은 WebKit 이라 같을 것으로 봄(미확인). 막는 것: ① 아이폰은 HTTPS 에서만 마이크 허용 ② 화면이 서버를 localhost:8002 로 부름 → 한 origin 으로 묶어야 함. 맥에 Tailscale 로그인돼 있음(아이폰은 tailnet 에 없음). 실기기 위험: 읽어 준 직후 인식 전환 · getUserMedia 와 인식기의 마이크 공유 · 받아쓰기 설정. 사용자 결정(AskUserQuestion): 맥에서 먼저 확인하고 모바일은 미룸.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 사용자 승인을 받고 tailscale serve 를 설정함
- [ ] #2 아이폰 Safari 에서 문장 연습의 실시간 표시를 실기기로 확인함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-11-15 준비 완료(사용자 지시 「준비해」): tailscale serve(tailnet only) / → :3000 · /api · /ws → :8002 · resolveApiBase(시험 먼저 — export 없음 실패 → 3 통과) · next.config allowedDevOrigins. 맥에서 확인(b25 tailnet.mjs · IP 고정): isSecureContext 참 · API 같은 출처 · 콘솔 오류 0 · KO 보임 · /ws 서버 도달(404 = 직접 호출과 같음). 이 맥 시스템 DNS 는 자기 tailnet 이름을 못 찾음. 게이트: tsc 0 · eslint 0 · build 0 · node 시험 통과. 남은 것: AC2 아이폰 실기기(사용자).

2026-11-15 사용자: 아이폰 접속 확인함(Tailscale 앱 · tailnet 주소). 남은 AC2: 아이폰 Safari 음성 인식 실시간 표시 확인. 사용자 지적: 모바일 창에서 스크롤이 생김 → TASK-344(모바일 스크롤 없는 디자인).
<!-- SECTION:NOTES:END -->
