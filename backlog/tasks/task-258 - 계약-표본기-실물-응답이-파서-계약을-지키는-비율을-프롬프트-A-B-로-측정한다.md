---
id: TASK-258
title: '계약 표본기: 실물 응답이 파서 계약을 지키는 비율을 프롬프트 A/B 로 측정한다'
status: Done
assignee: []
created_date: '2026-09-19 16:37'
updated_date: '2026-09-19 16:55'
labels: []
dependencies: []
ordinal: 322000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 지시(2026-09-20 · 「계속 진행해」 · 비용 제약 없음). TASK-257 이 프롬프트를 고쳤지만 수정 후 표본이 findings 항목 12개뿐이어서 「위반 빈도가 낮아졌다」를 증명하지 못한 채 닫혔음. 그 공백을 메움 — 같은 전사문 묶음을 두 갈래(수정 전 프롬프트 · 수정 후 프롬프트)로 여러 번 호출해 계약 위반 비율을 세고 그 수를 기록함. ⛔ DB 를 쓰지 않는 순수 경로임: build_prompt → 실물 Claude → parse_analysis 만 지나가고 저장하지 않음(사용량 기록만 격리 DB 에 남김 — H-CK 의 교훈). 계약 위반은 키 이름뿐 아니라 category 값역·origin 값역·pattern_key 형식·confidence 범위를 함께 셈. 전사문은 오류를 셋 이상 담아 «두 번째 항목부터» 흔들리는 자리를 일부러 만듦.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 두 갈래의 호출 수·항목 수·위반 수를 같은 전사문 묶음으로 세어 기록함
- [x] #2 위반 종류를 키 이름·category·origin·pattern_key 형식·confidence 로 갈라 셈
- [x] #3 표본 크기로 무엇을 가를 수 있고 무엇을 못 가르는지 회차 노트에 적음
- [x] #4 표본기가 DB 의 학습 데이터를 한 행도 바꾸지 않음
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
측정 결과 (2026-09-20 · 이 세션이 직접 돌렸음). 표본기 tests/harness/contract_sampler.py · 정본은 tests/harness/runs/2026-09-20-task258-contract-ab.md 임. 네 갈래(수정 전·후 × 기존 패턴 없음·2건) 각 40호출 · 합계 165호출(스모크 5건 포함) · findings 항목 590개 · 계약 위반 0건 · 파서 거부 0건 · 호출 실패 0건 · 토큰 474,364 in / 193,469 out. AC#4: error_patterns 8 · error_occurrences 14 · utterances 12 가 앞뒤로 같음(llm_calls 만 늘었고 그것은 비용 표임). 판정: 수정 전 갈래도 0건이라 TASK-257 의 프롬프트 수정을 「빈도를 낮췄다」로 적을 수 없고, 내가 관측 1건에서 추정한 4%/8% 는 반증됐음(그 정정을 TASK-257 노트와 analysis.py 주석에 적었음). ⛔ 이 회차가 스스로 거짓 신호 하나를 잡았음: 첫 판 계수가 attempts 가 비어 있지 않은 것을 위반으로 세어 32건씩 잡혔는데 전건이 목록 안 key 에 outcome=incorrect 로 정상이었음 — 전사문이 그 패턴을 되풀이하므로 조건이 이미 결과를 예측하는 계수였음. 계수를 계약 셋으로 고치고 --rescan 을 더해 호출 0건으로 다시 셌음.
<!-- SECTION:NOTES:END -->
