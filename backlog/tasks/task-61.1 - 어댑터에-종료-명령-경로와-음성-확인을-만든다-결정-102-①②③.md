---
id: TASK-61.1
title: 어댑터에 종료 명령 경로와 음성 확인을 만든다 (결정 102 ①②③)
status: To Do
assignee: []
created_date: '2026-09-14 22:23'
labels: []
dependencies: []
parent_task_id: TASK-61
ordinal: 175000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
결정 102 가 정한 계약을 코드로 옮긴다. 표지는 「Oh My English」 접두어 하나이고, 명령은 종료 하나이고, 확인은 음성 한 번이며 그 답을 command_confirmation 발화로 남긴다. ⛔ 이 태스크의 주체는 개발 세션이다 — 통합 테스트 세션은 계약과 회차만 소유한다. 설계 판단(tool 스키마·프레임 계약·어느 파일이 소유하는가)은 이 태스크가 갖는다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 종료 명령이 Nova tool 로 도착하고 어댑터가 그것을 실행 경로로 받는다 (결정 46 의 수단)
- [ ] #2 확인을 거치지 않고 종료되지 않는다 — 확인 발화가 command_confirmation 으로 저장된다
- [ ] #3 「Oh My English」 접두어가 없는 학습 발화는 명령으로 실행되지 않는다
- [ ] #4 한국어와 영어 두 표현을 모두 받는다
<!-- AC:END -->
