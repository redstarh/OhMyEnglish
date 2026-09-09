---
id: TASK-61
title: '신규 기능: 음성 명령으로 학습 제어 (PRD Voice Control) — 스키마는 이미 준비됨'
status: To Do
assignee: []
created_date: '2026-09-09 13:11'
labels: []
dependencies: []
ordinal: 64000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
PRD §4-8 이 「UI와 음성 명령을 모두 통한 학습 제어」를 요구하고 Voice Control 절이 지원 명령을 열거한다: 학습 시작/계속/추가 학습 · 모드 변경 · 반복 · 천천히 말하기 · 힌트 요청 · 다음 문제 · 일시 정지 · 종료 · 복습·리포트 보기. 한국어와 간단한 영어를 모두 지원한다(예: 「추가 연습 시작」 · 「질문 다섯 개 더」 · 「Repeat that slowly.」).

⛔ 요구사항인데 원장에 태스크가 없었다(2026-09-09 사용자 질문에서 발견). 등록 누락이다.

이미 있는 것: ① 스키마가 최초 001 마이그레이션부터 받아들인다 — learning_sessions.started_via CHECK 에 voice_command · utterances.utterance_type CHECK 에 voice_command 와 command_confirmation ② Nova 의 tool 호출이 실물에서 작동한다(발음 tool 로 실증 · promptStart.toolConfiguration → toolUse → contentEnd(TOOL_USE)) ③ services/utterances.py 가 voice_command 를 「저장은 되지만 교정 대상이 아니다」로 이미 다룬다.
없는 것: 어댑터의 명령 실행 경로 하나다 — nova.py:112 가 「명령 실행 경로(voice_command 발화)는 이 어댑터에 없다」고 명시한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 명령 인식 수단을 정한다 — Nova tool 호출로 할지 전사문 패턴으로 할지 근거와 함께 고른다. ⛔ tool 은 이미 작동이 실증됐고 전사문 패턴은 오인식에 약하다
- [ ] #2 command_confirmation 을 쓴다 — 스키마가 그것을 두고 있는 이유가 오인식 방어다. 되돌릴 수 없는 명령(종료)은 확인을 거친다
- [ ] #3 지원 명령의 최소 집합을 정해 구현한다 — PRD 가 열거한 열 가지를 한 번에 다 하지 않고 시작·종료·반복부터 한다
- [ ] #4 한국어와 영어 명령을 모두 받는다 — PRD 가 그 예시를 든다
- [ ] #5 판별력을 게이트로 고정한다 — 명령이 아닌 학습 발화가 명령으로 오인되지 않는 음성 대조를 넣는다
<!-- AC:END -->
