---
id: TASK-60
title: LLM 호출의 토큰 사용량을 기록한다 — 지금은 비용을 볼 수단이 없다
status: Done
assignee: []
created_date: '2026-09-09 13:04'
updated_date: '2026-09-12 00:53'
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
- [x] #1 invoke_model 응답의 usage(input_tokens·output_tokens)를 읽어 호출마다 기록한다 — 기록 위치는 기존 스키마 규약에 맞춰 정하고 마이그레이션이 필요하면 캡틴 승인 절차를 따른다
- [x] #2 기록이 실제로 쌓이는 것을 실물 호출 1회로 확인한다 — 값이 0 이나 null 이 아닌 것을 직접 조회해 본다
- [x] #3 botocore 타임아웃을 확인한다 — SDK 기본값이 길면 종료가 그만큼 늦어진다는 실측이 그 리포에 있다(기본 10분 → 8초로 줄이고 불변식으로 검사했다). TASK-39 와 범위가 겹치면 그쪽에 합친다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-12 세션 ohmyenglish-f4 — 사용자 결정 66(새 표 llm_calls)로 닫았음. 결정 정본은 docs/ops/captain-instruction-register.md 「결정 66」임.

AC#1: 마이그레이션 013 + 배선. models/usage.py(TokenUsage · UsageSink · 갈래 상수) · services/usage.py(record_llm_call · pool_usage_sink) · workers/claude_client.py(extract_usage + 주입된 sink) · api/main.py 배선 · process_plan(purpose=plan) · process_analysis(purpose=analysis). ⛔ sink 를 «주입» 함 — 클라이언트가 DB 를 알면 자격증명·네트워크 없이 도는 단위 테스트가 DB 를 요구함. ⛔ 기록을 extract_text «앞» 에 둠 — 절단·거부도 돈이 나간 호출임.

AC#2 실물 확인 1회(직접 돌린 출력): records_usage True · 행 1건 = provider bedrock · model_id us.anthropic.claude-opus-5 · purpose spike · job_id None · input_tokens 30 · output_tokens 9 · called_at 2026-09-12 00:52:31 UTC(KST 날짜 2026-09-12). 0 도 null 도 아님.

AC#3 botocore 실측: 1.43.78 기본값 connect_timeout 60 · read_timeout 60 · retries None. ⚠️ 이 태스크 설명이 인용한 「기본 10분」은 참고 프로젝트 수치이고 이 리포 값이 아님. 범위가 TASK-39 와 겹치므로 그쪽에 합쳤고, 그 노트에 새 사실을 남겼음 — 재시도가 SDK 안에서 나므로 llm_calls 가 재시도분을 못 봄(중복 과금이 나도 1건으로 보임).

⚠️ 남긴 것: Nova 호출은 아직 적지 않음. 013 의 purpose 값역에 자리(nova)는 있으나 그 클라이언트는 양방향 스트리밍이라 같은 추출기로 읽히지 않음 — 별 태스크가 필요하면 그때 등록함.

테스트 9건: extract_usage 2 · 클라이언트 3(귀속·절단도 기록·usage 없으면 미기록) · 서비스 3(왕복·값역은 CHECK 가 막음·실패를 삼킴) · 배선 게이트 1(sink 를 넘겼는가 + 진짜 쓰는가). 게이트: pytest 984 passed(11.24s) · ruff 0 · format 0 · 게이트 밖 ruff 0 · ty 0.
<!-- SECTION:NOTES:END -->
