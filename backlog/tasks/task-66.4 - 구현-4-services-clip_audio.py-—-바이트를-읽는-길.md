---
id: TASK-66.4
title: '구현 4: services/clip_audio.py — 바이트를 읽는 길'
status: Done
assignee: []
created_date: '2026-09-13 22:11'
updated_date: '2026-09-13 22:36'
labels: []
dependencies:
  - TASK-66.1
parent_task_id: TASK-66
ordinal: 152000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
계획서 Task 4. 낭독과 합치지 않는다 — 수명주기가 반대다. 만료를 재지 않는 것이 그 성질이다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 단정 다섯이 통과한다 — media type · id 로 조립 · 정상 · 접근 불가 셋 · 만료 없음
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
완료 2026-09-14 (세션 ohmyenglish-f4).

red 를 먼저 봤음 — ModuleNotFoundError 로 수집 단계에서 멈췄음.

단정 다섯이 통과함: media type 이 audio/wav 로 낭독의 audio/L16 과 다름 · 경로가 파일명이 아니라 id 로 조립됨 · 정상 경로가 바이트를 줌 · 접근 불가 세 형태가 전부 None(행 없음·포인터 null·파일 없음) · 400일 지난 행에서도 바이트가 나옴(만료를 재지 않음).

게이트: 5 passed · ruff check 0(docstring 첫 줄 E501 둘을 두 줄로 갈라 고쳤음) · format 정합 · ty 0.

⚠️ 판별력 시험을 이 태스크에서는 따로 돌리지 않았음 — 모듈이 없던 상태의 red 가 다섯 단정 모두에 대해 이미 관측됐기 때문임(수집 실패라 전부 실행되지 않았음). ⛔ 그것으로 「각 단정의 판별력」이 확정되지는 않으므로 66.5 의 API 단정이 같은 축을 HTTP 에서 다시 잼.
<!-- SECTION:NOTES:END -->
