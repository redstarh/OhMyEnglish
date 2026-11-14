---
id: TASK-325
title: >-
  아이폰에서 앱 쓰기 — Tailscale serve 로 화면·서버를 한 HTTPS 주소로 묶고 Safari 음성 인식을 실기기로 확인
  (사용자 결정으로 미룸 2026-11-14)
status: To Do
assignee: []
created_date: '2026-11-14 11:27'
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
- [ ] #1 사용자 승인을 받고 tailscale serve 를 설정함
- [ ] #2 아이폰 Safari 에서 문장 연습의 실시간 표시를 실기기로 확인함
<!-- AC:END -->
