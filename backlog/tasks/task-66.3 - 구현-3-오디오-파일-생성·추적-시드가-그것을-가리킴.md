---
id: TASK-66.3
title: '구현 3: 오디오 파일 생성·추적 + 시드가 그것을 가리킴'
status: Done
assignee: []
created_date: '2026-09-13 22:11'
updated_date: '2026-09-13 22:32'
labels: []
dependencies: []
parent_task_id: TASK-66
ordinal: 151000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
계획서 Task 3. TTS 회차 1회가 필요하다(2026-09-09 생성물이 /tmp 에서 사라졌음). 잰 길이가 16.64 와 다르면 그것이 새 실측이고 clip_end_sec 을 그 값으로 고친다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 assets/clips/<id>.wav 가 추적되고 git check-ignore 가 무시하지 않는다
- [x] #2 시드 단정 둘이 통과한다 — 파일명 규약과 파일 존재·추적
- [x] #3 파일을 옮겨 red 를 보고 되돌린다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
완료 2026-09-14 (세션 ohmyenglish-f4).

⛔ 실측이 앞 회차와 달랐음. 같은 전사문·같은 화자(Sohee·en)로 다시 합성했더니 17.36초였고 2026-09-09 회차는 16.64초였음 — TTS 가 회차마다 같은 길이를 내지 않음. 그래서 clip_end_sec 을 17.36 으로 뒀고, 그 값은 「그 전사문의 길이」가 아니라 «리포에 담긴 그 파일의 길이»임.

정확한 측정: 277760 frames / 16000 Hz = 17.360000 초. 파일은 559616 바이트(546KB) · 1ch · 16000 Hz · Int16. git check-ignore exit=1(무시되지 않음).

단정 셋을 뒀음 — 파일명 규약 · 파일 존재와 추적 · 시간 창과 파일 길이의 대조. 셋째 것이 값을 기억으로 적지 못하게 함(파일에서 다시 읽음).

판별력: 파일을 옮겨 2 failed · 시간 창을 17.37 로 흔들어 1 failed 를 봤음.

⛔ 그 되돌림에서 함정을 새로 밟았고 H-BS 로 등록했음 — 되돌린 뒤에도 red 였고 원인이 소스가 아니라 __pycache__ 였음. pyc 헤더의 mtime·크기가 되돌린 소스와 일치해(같은 자리수 치환 + 같은 초) 파이썬이 옛 바이트코드를 실행했음. diff -q 는 「원본과 동일함」으로 통과시켰음.

⚠️ dev DB 는 아직 16.64 임 — 이미 동기화한 값이 낡았으므로 TASK-66.9 에서 022 적용과 함께 재시드가 필요함.
<!-- SECTION:NOTES:END -->
