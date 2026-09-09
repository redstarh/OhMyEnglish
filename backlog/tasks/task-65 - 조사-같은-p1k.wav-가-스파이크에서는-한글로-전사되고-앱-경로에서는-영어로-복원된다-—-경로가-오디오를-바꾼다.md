---
id: TASK-65
title: '조사: 같은 p1k.wav 가 스파이크에서는 한글로 전사되고 앱 경로에서는 영어로 복원된다 — 경로가 오디오를 바꾼다'
status: To Do
assignee: []
created_date: '2026-09-09 13:48'
updated_date: '2026-09-09 16:17'
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
⛔ 2026-09-09 — 결정 49 가 이 태스크를 차단 항목으로 올렸다. 등록 시점보다 값어치가 커졌다.

결정 49 는 발음 판정을 「보조 신호로 축소」하고 그 정본을 한글 전사 감지(note_transcript)로 정했다. 그런데 이 태스크가 조사하려는 것이 정확히 「앱 경로에서 한글 전사가 나오지 않는다」다.

팀리드가 직접 돌려 얻은 수치 (2026-09-09):
- pronunciation_attempts: 4행 · signal_source 전부 nova_tool · target_sound 4행 전부 있음. korean_transcript 0행.
- utterances 에서 speaker='user' 이고 transcript 에 [가-힣] 이 든 행: 0행. 리포 전체 이력이다.

코드 확인: note_transcript 는 services/pronunciation.py:288 의 _HANGUL.search(transcript) 를 통과해야 발동한다. 즉 전사문에 한글이 없으면 그 경로는 아예 실행되지 않는다.

⛔ 따라서 결정 49 가 적은 대가(「복습 시계를 도달 불가로 남긴다」)보다 하나 더 큰 대가가 있다 — 그 신호는 앱 경로에서 여태 한 번도 발동한 적이 없다. 「기록되지만 이어지지 않는다」가 아니라 「기록될 입력 자체가 온 적이 없다」다.

⚠️ 그런데 같은 오디오가 스파이크 경로에서는 한글로 전사된다(TASK-59 회차 · 팀리드 직접 재현 2회). 즉 Nova 의 ASR 능력 문제가 아니고 경로 문제다. 그것을 가르는 것이 이 태스크의 AC#1 이고, 그 답이 결정 49 의 실효성을 정한다.

⚠️ 원인은 여전히 미확정이다. 후보 넷(AudioContext 리샘플 · 32ms 케이던스 · 게이트웨이 청크 재조립 · endpointing) 중 배제된 것이 0개다. 이 노트는 값어치를 올리는 것이고 원인을 좁히지 않았다.
<!-- SECTION:NOTES:END -->
