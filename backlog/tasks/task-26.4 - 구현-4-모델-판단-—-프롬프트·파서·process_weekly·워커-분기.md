---
id: TASK-26.4
title: '구현 4: 모델 판단 — 프롬프트·파서·process_weekly·워커 분기'
status: Done
assignee: []
created_date: '2026-09-13 23:36'
updated_date: '2026-09-14 00:02'
labels: []
dependencies:
  - TASK-26.2
  - TASK-26.3
parent_task_id: TASK-26
ordinal: 163000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
계획서 Task 4. 모델 호출은 트랜잭션 밖이고 저장은 한 트랜잭션 + complete 임(process_summary 의 규약). ⛔ 워커 분기를 빼면 else 가 process_analysis 로 보내 영구 failed 가 된다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 단정 여섯이 통과한다 — 한국어 요구 · 점수 금지를 두 축으로(금지 문장과 출력 규격) · 0건 주는 모델 미호출 · 저장 멱등 · computed_at · 토큰 기록이 «행으로» 남는지
- [x] #2 워커 분기를 지워 red 를 보고 되돌린다
- [x] #3 개선 패턴에 줄 사실을 정한다 — ⛔ mastery_score 를 쓰지 않는다(전부 0.00)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
완료 2026-09-14 (세션 ohmyenglish-f4).

red 를 먼저 봤음 — 프롬프트/파서는 수집 단계 ImportError, job 쪽은 process_weekly 부재.

단정 열이 통과함(계획의 여섯을 넘었음). 프롬프트 셋: 한국어 요구와 원문 인용 · ⛔ 점수 금지를 «두 축»으로(금지 문면이 있는가 + 출력 규격 절에 score/grade/rating 키가 없는가) · 사실이 프롬프트에 실리는가(없으면 모델이 근거 없이 지어냄). 파서 둘: 정의되지 않은 키 거부 · 상한 초과 거부. job 다섯: 0건 주는 모델 미호출로 빈 모양 done · 정상 응답 저장과 purpose 확인 · 사실이 판단과 같은 행 · 멱등(행 하나) · ⛔ 규격 위반은 저장 안 됨.

⛔⛔ 이 태스크에서 «판별력 없음»을 한 번 실측했음 — 워커 분기를 지우고 test_worker.py 를 돌렸더니 21건이 그대로 통과했음. 즉 그 분기를 재는 단정이 0건이었음(018 주석이 「빼면 기능이 아예 돌지 않는다」로 경고한 자리임). 그래서 test_worker_routes_a_weekly_job_to_process_weekly 를 더했고, 다시 지워 red 를 확인한 뒤 되돌려 green 을 읽었음.

⚠️ 그 단정을 더하다 실수 하나를 냈음 — import 치환이 «호출 인자 자리»에 들어가 이웃 테스트 하나가 함께 깨졌음(NameError). 되돌리고 단일 행 import 를 고쳤음. 교훈: 여러 곳에 같은 패턴이 있으면 치환 대상을 «줄 전체»로 좁혀야 함.

⚠️ conftest 의 fake_claude 에 주간 기본 응답을 매어 뒀음 — 총평이 같은 이유로 그렇게 했음. end_session 이 주간 job 을 조건부로 걸어서 워커 루프 테스트의 큐에 그 테스트가 세우지 않은 호출이 섞임.

⚠️ 테스트 설정 실수 하나 — 발화를 now()(이번 주)에 심어 「0건 주」 갈래가 먼저 걸렸고, 그래서 그 단정이 모델 응답과 무관한 것을 재고 있었음. 지난 주로 옮겨 고쳤음.

게이트: pytest 1177 passed exit 0 · ruff check 0 · format 221 files · ty 0 · tsc exit 0 · eslint exit 0.
<!-- SECTION:NOTES:END -->
