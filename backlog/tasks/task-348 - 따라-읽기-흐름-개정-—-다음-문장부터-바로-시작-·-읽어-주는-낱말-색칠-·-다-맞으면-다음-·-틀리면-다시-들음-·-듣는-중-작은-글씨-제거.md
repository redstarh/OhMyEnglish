---
id: TASK-348
title: >-
  따라 읽기 흐름 개정 — 다음 문장부터 바로 시작 · 읽어 주는 낱말 색칠 · 다 맞으면 다음 · 틀리면 다시 들음 · 듣는 중 작은 글씨
  제거
status: In Progress
assignee: []
created_date: '2026-11-17 12:57'
updated_date: '2026-11-17 13:08'
labels: []
dependencies: []
ordinal: 415000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 지시 2026-11-17 · 결정은 docs/design/2026-11-14-live-readback-transcript-design.md §12.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Start speaking 한 번으로 저장된 다음 문장에서 듣기가 시작됨
- [x] #2 읽어 주는 동안 낱말이 차례로 색칠됨(경계 신호 없으면 시간 비례) — 단위 시험
- [x] #3 자동 모드: 모든 낱말이 맞으면 다음 문장, 틀리면 같은 문장을 다시 들음, 말 없음은 멈춤
- [x] #4 듣는 중 작은 글씨 제거 · 미확정 글자를 확정 글자와 같은 모양으로 보임
- [x] #5 게이트(tsc·eslint·node 시험·next build)와 mobile-fit · 가짜 인식기 흐름 시험 통과
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-11-17 구현: lib/speechHighlight.ts(wordCountAt · wordSchedule · node 시험 4) · speak() onWords(경계 신호 우선 · 없으면 시간 비례) · SpokenSentence 색칠 · LiveLine 꼬리표·기울임 제거 · 「I'm listening」 안내 제거 · 자동 모드 다 맞음→다음 자리 즉시 저장 후 다음 · 틀림→같은 문장 다시 들음(합성 재생 없음) · 말 없음·판정 불가→멈춤 · autoStart(Start speaking · Day 고르기 · ?day=) 마운트 때 한 번. 시험: tests/agent/tools/readback-flow.mjs 7건 통과(맞음 규칙을 끄는 변이에서 ③·④·⑥ 실패 — 판별력 확인) · mobile-fit 16 · progress-idle-save 3 · tsc 0 · eslint 0 · node --test 64 · next build 0. 남은 것: 아이폰 실기기 확인(낱말 경계 신호가 오는지 · Start speaking 한 번에 소리가 나는지) · codex 리뷰.
<!-- SECTION:NOTES:END -->
