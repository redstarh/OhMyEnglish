---
id: TASK-180
title: '구현: 낭독 녹음을 브라우저가 디코드하는 WAV 로 내보낸다'
status: Done
assignee: []
created_date: '2026-09-18 01:39'
updated_date: '2026-09-18 01:45'
labels: []
dependencies: []
ordinal: 241000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
지금 get_recording 은 raw PCM(audio/L16)을 주고 브라우저에 그것을 디코드하는 API 가 없다. 프런트 소비자가 0건인 지금 형식을 WAV 로 바꾼다 — 44바이트 RIFF 헤더가 표본율·채널을 실어 new Audio() 가 그대로 디코드한다. 디스크의 .pcm 은 그대로 두고 변환은 읽을 때만 한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 RECORDING_MEDIA_TYPE 이 audio/wav 이고 응답 바이트가 RIFF 로 시작한다
- [x] #2 헤더가 16kHz·16bit·mono 를 싣고 data 청크 길이가 원본 PCM 길이와 같다
- [x] #3 디스크의 원본 파일과 저장 경로는 바뀌지 않는다
- [x] #4 결정 128 을 지시 대장에 등재한다
<!-- AC:END -->
