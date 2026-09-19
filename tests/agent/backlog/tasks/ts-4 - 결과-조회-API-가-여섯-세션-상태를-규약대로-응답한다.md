---
id: TS-4
title: 결과 조회 API 가 여섯 세션 상태를 규약대로 응답한다
status: In Progress
assignee: []
created_date: '2026-09-09 08:23'
updated_date: '2026-09-19 11:43'
labels: []
dependencies: []
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
기준 커밋 3ce3e62 · 추적 미커밋 0건. GET /api/sessions/<id>/results (app/backend/app/api/results.py:131 · prefix 47행). 보존 세션 6건 재방문이라 실물 호출 0회. 증거는 runs/2026-09-09-1712/evidence/ 의 응답 본문 원본이고 메인이 직접 읽어 대조했다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 R2 규칙 1 — 세션 status 가 failed 면 그 세션의 job 이 무엇이든 connection_failed 이고 corrections 키가 부재하다
- [x] #2 R2 규칙 2 — analyze_utterance job 이 0건이면 no_utterances 이고 corrections 키가 부재하다
- [x] #3 R2 규칙 3 — non-terminal job 이 하나라도 있으면 analyzing 이고 corrections 키가 부재하다 (done 인 발화가 있어도 노출하지 않는다)
- [ ] #4 R2 규칙 4 — failed job 이 있고 non-terminal 이 없으면 partial_failure 이고 성공분 교정을 포함한다
- [x] #5 R2 규칙 5 — job 이 1건 이상이고 전부 done 이면 final 이고 교정이 실린다
- [ ] #6 우선순위가 지켜진다 — 규칙 1 과 규칙 3 을 동시에 만족하는 세션이 connection_failed 로 판정된다
- [x] #7 이 회차가 판정에 쓴 행을 직접 심고 회차 끝에 지웠다 (세션 uuid 를 기준선에 적지 않는다)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
기준선을 규칙 단위로 바꿨음 (2026-09-19 · TASK-243 · 결함 TASK-230).

원래 AC 여섯은 세션 uuid 와 상태를 1대1로 적어 두었음(210233be=analyzing 등). 그것이 조용히 낡음 — 그 세션의 job 이 나중에 바뀌면 같은 API 가 다른 상태를 냄. 실측(2026-09-19 회차 B1): 210233be 가 analyzing → partial_failure 로, d127dece 가 no_utterances → final 로 바뀌어 있었고, 원인은 API 결함이 아니라 픽스처 데이터 변화였음(d127dece 의 job 3건은 2026-09-18 03:56:57 에 워커 기동이 새로 등록해 done 으로 끝났음 — 함정 H-CD 가 적은 그 사건임). 그 회차가 두 건을 「새로 실패」로 올릴 뻔했고 analysis_jobs 를 직접 조회해서야 갈랐음.

고른 안: TASK-230 의 제안 ⑴(세션 대응 대신 R2 규칙 번호로 회귀를 봄) + ⑵(회차마다 상태별 픽스처를 심어서 씀)을 함께 씀. AC 는 규칙을 가리키고, 그 규칙을 만족하는 행은 회차가 격리 사용자로 심었다가 지움.

버린 안과 근거:
- ⑵ 단독: 실행 방법으로는 옳으나 AC 문면이 여전히 「어떤 행을 심었는가」에 매여, 심는 방식이 바뀌면 문면이 또 낡음. 그래서 ⑴ 과 함께 씀.
- ⑶ 보존 픽스처를 워커의 미등록 발화 스윕 대상에서 뺌: 기각함. 테스트 픽스처를 지키려고 «생산 코드»(워커)의 동작을 바꾸는 것이고, 그 예외가 생기면 스윕의 계약에 테스트 전용 갈래가 남음. 회귀 기준선의 문제를 앱 쪽으로 옮기는 것임.

R2 다섯 규칙의 정본은 app/backend/app/services/results.py 모듈 docstring 임 — 우선순위 순서대로 정확히 하나만 매칭된다는 계약을 그 문서가 가짐. AC 는 그 번호를 가리키고 값을 복제하지 않음.

상태를 To Do 로 내렸음 (2026-09-19 · TASK-243). 이유: AC 를 규칙 단위로 다시 썼으므로 예전 Done 의 근거(세션 uuid 대응)가 더 이상 이 AC 를 충족하지 않음. 미체크 AC 를 남긴 채 Done 으로 두지 않음.

이 턴에 직접 읽어 확인한 것 — 회차 B1 의 증거 파일을 열어 봤음(tests/agent/runs/2026-09-19-b1/evidence/):
- AC#2 규칙 2: TS-22-ac1-seeded-two-states.txt 의 seed-A·seed-B 가 no_utterances 이고 corrections 키 부재임. 확인함.
- AC#3 규칙 3: 같은 파일의 seed-C 가 analyzing 이고 corrections 키 부재임. 확인함.
- AC#1 규칙 1: TS-22-ac1-six-states.txt 의 76d9ef31 이 connection_failed 이고 corrections 키 부재임. 확인함.
- AC#5 규칙 5: 같은 파일의 6225ddaf 가 final 이고 corrections 1건임. 확인함.
- AC#7: 그 회차가 격리 사용자로 세션 셋을 심고 회차 끝에 전부 지웠으며 누출 0건을 확인했다고 적었음(TS-30 노트와 같은 규약). 확인함.

아직 앱 경로로 관측되지 않은 것 둘 — 이것이 다음 회차의 몫임:
- AC#4 규칙 4 의 「성공분 교정을 포함한다」: 회차가 본 partial_failure 세션(b2f0d169)은 corrections 가 0건이라 그 절반을 «긍정으로» 보이지 못함. done job 이 교정을 남긴 partial_failure 를 심어야 함.
- AC#6 우선순위: 규칙 1 과 규칙 3 을 동시에 만족하는 세션을 앱 경로로 열지 않았음.

⚠️ 단위 검사가 그 둘을 덮고 있고 이 턴에 직접 돌려 통과를 봤음 — unit/test_results.py 의 test_failed_session_yields_connection_failed_even_with_done_job 과 test_partial_failure_includes_successful_corrections(2 passed). ⛔ 그것으로 이 AC 를 체크하지 않음: 이 시나리오의 값어치는 «앱 경로(HTTP)» 관측이고, 단위 검사는 그 층을 덮지 않음. 두 근거를 섞으면 「통과했는데 통과한 이유가 틀렸다」가 됨.
<!-- SECTION:NOTES:END -->
