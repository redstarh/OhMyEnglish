---
id: TASK-65
title: '조사: 같은 p1k.wav 가 스파이크에서는 한글로 전사되고 앱 경로에서는 영어로 복원된다 — 경로가 오디오를 바꾼다'
status: Done
assignee: []
created_date: '2026-09-09 13:48'
updated_date: '2026-09-09 16:27'
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
- [x] #1 스파이크 경로와 앱 경로에 들어가는 오디오 바이트를 같은 지점에서 떠서 비교한다 — 다르면 어디서 달라지는지 지목한다
- [x] #2 후보 넷을 하나씩 배제하거나 확정한다. 배제하지 못한 것은 배제하지 못했다고 적는다
- [x] #3 korean_transcript 보조 신호가 0행인 것과 인과가 있는지 판정한다 — 없으면 없다고 적는다
- [x] #4 원인이 확정되면 결함인지 설계인지 가른다. 결함이면 수정 태스크를 등록하고 설계면 P4·P12 시나리오의 관측 경로를 스파이크로 바꾼다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-09 완료. 정본은 tests/harness/runs/2026-09-09-task65-session-context.md 다.

⛔ 제목이 틀렸다. 경로가 오디오를 바꾸는 것이 아니었다 — 세션의 첫 발화가 이후 턴의 ASR 언어를 고정한다. 오디오는 변수가 아니었다.

AC#1 — 바이트를 떠서 비교하는 대신 배제로 답했다. 하네스 브라우저 주입이 AudioContext 를 두 번 지나가는 것을 코드로 확인하고(app/frontend/lib/audio.ts:18), 그 변환만 afconvert 로 떼어내 재현했다(16k→48k→16k, md5 달라짐). 전사문이 여전히 한글이었으므로 리샘플은 원인이 아니다. 앱 프롬프트 단독 팔도 앞서 한글이었으므로 프롬프트도 아니다.

AC#2 — 후보 넷 중 리샘플을 배제했다. 나머지 셋(32ms 케이던스·게이트웨이 청크 재조립·endpointing)은 배제하지 않았고 배제할 필요가 없어졌다 — 양성 원인을 찾았기 때문이다. ⛔ 그 셋을 배제했다고 적지 않는다.

AC#3 — korean_transcript 0행과의 인과에 답했다. 유력한 설명이 나왔다: 학습자의 첫 발화는 보통 알아들을 만한 영어이므로 세션이 영어로 고정되고, 그 뒤 발화는 아무리 틀려도 영어로 복원된다. ⚠️ 앱 경로에서 직접 확인한 것은 아니고 스파이크 표본으로 유도한 것이다.

AC#4 — 설계(모델 거동)이지 앱 결함이 아니다. 그래서 P4·P12 의 관측 경로를 고쳤다(scenarios-P-pronunciation.md §3.2): 그 픽스처를 세션의 첫 발화로 줘야 한다. 스파이크에 --wav a,b 팔을 더했고 쉼표가 없으면 거동이 이전과 글자 그대로 같다.

⛔ 곁가지가 본류보다 크다 — 결정 49 의 사실 전제 둘이 반증됐다. 앱 프롬프트에서 toolChoice 강제 없이 toolUse 가 왔고(다중 턴 4건 중 3건) 코칭 발화와 동시에 왔다(audioOutput 118·174·203). target_sound 도 실렸다(th_as_t · th_as_s · sh_sound). 규칙 9 의 name the sound 까지 이행한 회차가 있다. 빠진 변수는 다중 턴 세션이었고 TASK-67 의 팔 열 개는 전부 단일 발화였다. 그 결정을 다시 묻는 것은 제품 요구사항 판단이라 팀리드가 뒤집지 않는다 — 사용자에게 올렸다.
<!-- SECTION:NOTES:END -->
