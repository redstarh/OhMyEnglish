---
id: TS-2
title: J2 · 결과 화면의 상태 하나가 사람이 읽을 수 있는 문구로 나옴
status: Done
assignee: []
created_date: '2026-09-09 08:20'
updated_date: '2026-09-09 08:29'
labels: []
dependencies: []
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
근거: app/frontend/app/results/[sessionId]/page.tsx:22-28 STATUS_LABEL · :157 상태 렌더 · :204-236 발음 카드. 전제: 보존 세션 6개 중 하나를 재방문(실물 호출 0회). 절차: 1) 보존 세션의 GET results 응답 본문 저장 2) 응답 각 필드를 프론트 소스의 문구 상수와 대응 3) 기계 키가 사용자 눈에 노출되는지 확인. 판정 수단: HTTP 응답 본문 + 프론트 소스 파일:줄 대조. 위험도: 중간. 회차: tests/agent/runs/2026-09-09-1722
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 보존 세션 최소 1건의 결과 응답 status 를 200 으로 받음
- [x] #2 그 status 가 STATUS_LABEL 에 한국어 문구로 매핑됨
- [x] #3 응답에 실린 표시 필드가 화면 문구 상수로 전부 대응됨
- [x] #4 기계 키(pattern_key·target_sound·signal_source 등)가 사용자 눈에 렌더되지 않음
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
판정: PASS. 실물 호출 0회. 상태 5종(analyzing/final/partial_failure/connection_failed/no_utterances) 전부를 HTTP 200 으로 열어 한국어 문구 매핑 확인. 발음 카드 3장을 실물 데이터(bbfc3908)로 조립해 확인. 기계 키 노출 0건 — pattern_key 는 React key 로만, category·target_form·occurrences 는 미렌더, signal_source 는 분기 조건, target_sound 는 API 응답에 없음. 미관측 1건: signal_source != nova_tool 인 '관찰된 신호' 카드는 DB 에 데이터 0건이라 소스 대조만 함. 증거: tests/agent/runs/2026-09-09-1722/evidence/TS-2-results-*.json (8건).
<!-- SECTION:NOTES:END -->
