---
id: TASK-255
title: '워커 회차: 워커를 켜야 지나가는 경로 셋을 닫는다'
status: Done
assignee: []
created_date: '2026-09-19 14:29'
updated_date: '2026-09-19 15:25'
labels: []
dependencies: []
ordinal: 319000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 승인(2026-09-19 · 「그대로 진행함」). 이번 통합테스트가 「워커 회차의 몫」으로 남긴 셋을 닫음 — ⑴ daily_error_summary 의 쓰기 경로(지금까지 정적 대조만 했음) ⑵ summarize_week job 의 처리 절반(이 DB 에서 done 0건 · weekly_reports 가 실사용 경로로 한 번도 채워진 적 없음) ⑶ 실물 Claude 응답이 파서 계약(무대 제목 언어·category 값역)을 지키는가. ⛔ 부수 효과를 사용자가 알고 승인했음: 워커 기동이 미등록 발화 10건에 job 을 걸어 유료 호출을 내고 오류 패턴·복습 일정을 실제로 바꿈. 예상 호출 12~15건. ⛔ 호출 전후 집계를 직접 세어 증거로 남기고 달라진 행을 기록함.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 daily_error_summary 의 쓰기 경로가 실제로 돌아 오늘 행이 사용자 타임존 기준으로 만들어짐
- [x] #2 summarize_week job 이 done 으로 끝나고 weekly_reports 행이 생김
- [x] #3 실물 Claude 응답이 파서 계약을 지킴 — 어긋나면 결함으로 등록됨
- [x] #4 호출 전후 llm_calls·analysis_jobs·error_patterns 집계와 달라진 행이 기록됨
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
⛔ 착수 시점을 미룬 근거 (2026-09-19 · 호출 세션이 직접 셌음). 워커를 켜기 전 기준선을 뜨다 analysis_jobs 의 pending 이 «20건» 인 것을 봤음 — 30분 전 같은 질의는 0건이었음. 그 사이 배치 b10(비용 0 회차)이 돌면서 세션 종료가 job 을 걸고 있었음(회차 하나가 남기는 job 넷 가운데 셋은 세션 종료가 그 자리에서 등록함 · H-CD). ⇒ 지금 워커를 켜면 ⑴ 그쪽 회차의 job 까지 처리해 그 회차의 판정을 오염시키고 ⑵ 호출 수가 승인 근거로 제시한 12~15건이 아니라 30건 가까이로 늘음. ⛔ 사용자에게 12~15건으로 알리고 승인받았으므로 그 수를 넘기는 설계로 바꾸지 않음. ⇒ b10 의 teardown 이 끝난 뒤 pending 을 다시 세어 그 값으로 착수함. ⚠️ 이것이 「수치는 마지막 단계가 끝난 뒤에 다시 읽는다」가 실제로 걸린 자리임 — 앞 값(0건)으로 회차를 띄웠다면 예산과 격리 전제가 둘 다 틀렸음. 기준선(b10 이 도는 중 · 참고용): llm_calls 39 · jobs done 47/failed 64/pending 20 · error_patterns 9 · review_tasks 15 · weekly_reports 0 · daily_error_summary 1.

회차 결과 (2026-09-20 · 이 세션이 직접 돌렸음). 판정: 단정 7건 전부 통과 · 앱 결함 0건 · 유료 호출 11건(승인 근거 12~15건 · 코드 상한 14건). 정본은 tests/harness/runs/2026-09-20-task255-worker.md 이고 증거는 같은 이름의 폴더임(setup.json · run.json · responses.jsonl · verify.json). ⛔ 승인 전제가 사라져 격리 DB 에서 돌렸음: 착수 직전 스윕 대상이 0건이어서 회차가 일을 새로 만들어야 했고, dev DB 에 만들면 픽스처 문장이 사용자의 실제 오류 패턴으로 섞여 TASK-191 의 결정을 되돌리는 일이 됨. ⇒ ohmyenglish_worker 를 마이그레이션+시드로 새로 만들어 run_worker 를 그대로 켰음. dev DB 의 행은 한 건도 바뀌지 않았음. AC#1: 오늘 행 summary_date=2026-09-20(KST)인데 같은 순간 current_date=2026-09-19(UTC) — 두 날짜가 갈리는 구간이라 판별력 있음 · occurrence_count=8 · pattern_count=6. 스윕이 걷은 지난 주 묶음은 2026-09-08 행에 적혀 앵커가 발화 날짜임이 함께 드러났음. AC#2: summarize_week job done · weekly_reports week_start=2026-09-07 1행 · insights.next_scenarios 3건이 실물 모델 출력. AC#3: 무대 제목 'Weekly video call with the partner team in Singapore'(한글 0자) · category=business(값역 안) · 분석 6건 전건 done · 패턴 category 7건 전부 값역 안. AC#4: llm_calls 0→1 · analysis_jobs pending 9→done 11 · error_patterns 2→7 · error_occurrences 3→14 · review_tasks 0→9 · weekly_reports 0→1 · daily_error_summary 0→2 · session_plans 0→2 · 생성 무대 0→1 · 실패 job 0건. 함정 둘을 등록했음 — H-I 확장(recreate_database 가 시드를 넣지 않아 무대 생성이 값역 0으로 거부됨)과 H-CK 신설(직접 만든 BedrockClaudeClient 는 usage_sink 가 없어 호출 9건이 llm_calls 에 0행으로 남았음). 결함 아닌 관측 둘: complete() 가 last_error 를 지우지 않아 재시도 뒤 성공한 job 이 낡은 문면을 들고 done 이 됨(화면은 job 상태로만 판정하므로 사용자에게 새지 않음) · 계획 job 의 model_id 가 us.openai.gpt-5.6-terra 인 것은 결정 121 이 의도한 값임.
<!-- SECTION:NOTES:END -->
