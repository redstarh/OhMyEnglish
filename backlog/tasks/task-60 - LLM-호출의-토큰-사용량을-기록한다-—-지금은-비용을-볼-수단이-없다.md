---
id: TASK-60
title: LLM 호출의 토큰 사용량을 기록한다 — 지금은 비용을 볼 수단이 없다
status: In Progress
assignee: []
created_date: '2026-09-09 13:04'
updated_date: '2026-09-12 00:25'
labels: []
dependencies: []
ordinal: 63000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
우리는 Bedrock 호출의 토큰 사용량을 어디에도 기록하지 않는다(직접 확인: analysis_jobs 에 토큰 컬럼이 없고 workers/claude_client.py 가 usage 를 읽지 않으며 그 파일 주석이 스스로 「토큰을 직접 다루지 않는다」고 적는다). 그래서 비용이 어디로 새는지 관측할 수 없고 어떤 개선을 해도 효과를 비교할 기준선이 없다. realtime-meeting 은 호출마다 토큰을 기록했고 예열 호출조차 「실제로 돈이 나가는 호출」이라며 함께 기록했다. ⛔ prompt cache 는 적용 대상이 아니다 — 우리 고정 프리픽스가 2,469자(약 617~1,646 토큰)로 최소 4,096 토큰에 못 미친다(근거는 fit-gap 문서 F1). 이 태스크는 캐시가 아니라 관측을 붙이는 것이다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 invoke_model 응답의 usage(input_tokens·output_tokens)를 읽어 호출마다 기록한다 — 기록 위치는 기존 스키마 규약에 맞춰 정하고 마이그레이션이 필요하면 캡틴 승인 절차를 따른다
- [ ] #2 기록이 실제로 쌓이는 것을 실물 호출 1회로 확인한다 — 값이 0 이나 null 이 아닌 것을 직접 조회해 본다
- [ ] #3 botocore 타임아웃을 확인한다 — SDK 기본값이 길면 종료가 그만큼 늦어진다는 실측이 그 리포에 있다(기본 10분 → 8초로 줄이고 불변식으로 검사했다). TASK-39 와 범위가 겹치면 그쪽에 합친다
<!-- AC:END -->
