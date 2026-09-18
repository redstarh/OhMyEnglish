---
id: TASK-204
title: '결함 후보: Nova 사용량 4행이 날짜가 달라도 값이 같아 비용을 잴 수 없다'
status: To Do
assignee: []
created_date: '2026-09-18 05:42'
labels: []
dependencies: []
ordinal: 265000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-189 의 비용 크기를 재려고 llm_calls 를 읽다가 드러났다. purpose='nova' 4행이 2026-09-12·17·18·18 로 날짜가 다른데 input_tokens 216 · input_speech_tokens 150 · input_text_tokens 66 · output 전부 0 으로 «완전히 같다». 코치가 소리로 말하므로 output_speech_tokens 가 0 일 수 없다 ⇒ 스트림 합계가 아니라 어느 고정 지점(promptStart·설정)만 적히는 것으로 보인다. TASK-124 의 목표(Nova 도 llm_calls 에 적는다)가 절반만 이뤄졌고, 그 결과 Nova 축의 비용을 우리 데이터로 잴 수 없다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 네 행이 같은 값인 기전을 코드에서 특정한다
- [ ] #2 Nova 스트림의 실제 입력·출력 토큰이 어디서 오는지 확인한다
- [ ] #3 고칠 수 있으면 고치고 못 고치면 그 한계를 문서에 남긴다
<!-- AC:END -->
