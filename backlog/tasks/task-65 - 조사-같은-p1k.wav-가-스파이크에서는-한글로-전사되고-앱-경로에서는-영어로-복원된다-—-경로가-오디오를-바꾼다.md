---
id: TASK-65
title: '조사: 같은 p1k.wav 가 스파이크에서는 한글로 전사되고 앱 경로에서는 영어로 복원된다 — 경로가 오디오를 바꾼다'
status: To Do
assignee: []
created_date: '2026-09-09 13:48'
labels: []
dependencies: []
ordinal: 68000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-59 가 통제 대조로 확정했다(runs/2026-09-09-task59-qwen-tts.md §5). 같은 p1k.wav 를 spike_nova_protocol.py 로 보내면 '아이싱크 아이파운드 쓰리 베리 유스풀 비디오즈' 로 전사되고 agent 가 unclear 로 되묻는다. 그런데 5차수 P4 는 앱 경로에서 '영어로 정확히 전사' 를 관측했다. 픽스처는 멀쩡하고 갈라지는 것은 경로다. ⛔ 원인을 단정하지 않는다 — 후보가 여럿이다: AudioContext decodeAudioData 의 리샘플 · 브라우저 캡처의 프레임 케이던스(32ms) · 게이트웨이의 청크 재조립 · endpointing 민감도. 이것이 korean_transcript 보조 신호가 여태 0행인 이유일 수 있다(TASK-13 실측).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 스파이크 경로와 앱 경로에 들어가는 오디오 바이트를 같은 지점에서 떠서 비교한다 — 다르면 어디서 달라지는지 지목한다
- [ ] #2 후보 넷을 하나씩 배제하거나 확정한다. 배제하지 못한 것은 배제하지 못했다고 적는다
- [ ] #3 korean_transcript 보조 신호가 0행인 것과 인과가 있는지 판정한다 — 없으면 없다고 적는다
- [ ] #4 원인이 확정되면 결함인지 설계인지 가른다. 결함이면 수정 태스크를 등록하고 설계면 P4·P12 시나리오의 관측 경로를 스파이크로 바꾼다
<!-- AC:END -->
