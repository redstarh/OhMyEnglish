---
id: TASK-190
title: '조사: analysis_jobs 큐 실태와 처리 방침을 정한다'
status: Done
assignee: []
created_date: '2026-09-18 02:28'
updated_date: '2026-09-18 03:55'
labels: []
dependencies: []
ordinal: 251000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
이 턴 실측 — pending 59 · done 44 · failed 2. 워커를 켜면 pending 만큼 Bedrock 비용이 난다. failed 2 의 원인과 pending 의 나이 분포를 보고 방침을 정한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 failed 2 의 원인을 확인한다
- [x] #2 pending 59 의 나이 분포와 비용 크기를 적는다
- [x] #3 처리 방침을 정하고 근거를 적는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 조사 결과 2026-09-18 — pending 전부가 하네스·회차 산출물임

### failed 2 의 원인 — 둘 다 «일부러 만든» 상태임

| id | attempts | last_error | created |
|---|--:|---|---|
| `88f8bd58` | 1 | `E2E-S step5 forced failure` | 2026-08-24 |
| `d8f8e97d` | 0 | `harness: C3c 상태 조성` | 2026-09-06 |

⇒ 실제 결함이 아님. **그대로 둠** — 그 회차의 기록이고 지우면 「왜 failed 가 있었나」에 답할 자리가 없어짐.

### pending 62건의 종류 (이 턴 실측 · 앞서 59 였고 내 쉐도잉 세션이 3건 더 만들었음)

| job_type | pending | 발화 연결 | 기간 |
|---|--:|--:|---|
| `analyze_utterance` | 28 | 28 | 09-06 ~ 09-17 |
| `plan_next_session` | 14 | 0 | 09-06 ~ 09-18 |
| `summarize_week` | 10 | 0 | 09-17 ~ 09-18 |
| `summarize_session` | 10 | 0 | 09-17 ~ 09-18 |

### ⛔ 결정적 사실 — 실제 학습 발화가 0건임

`analyze_utterance` 28건이 가리키는 발화의 문장 분포:

| 문장 | 건수 |
|---|--:|
| `I usually go to office by subway.` | 8 |
| `I usually go to gym after work.` | 8 |
| `I need to finish my homework tonight.` | 8 |
| 한글 음차 3종(`마이티니시트더리포트…` 등) | 3 |
| `he finished the first version of the pile.` | 1 |

앞 셋은 **스텁 픽스처(`FIXTURE_TURNS`)** 이고 같은 문장이 8번씩이라 회차 8회의 산출물임. 음차 3건은
Qwen3 TTS 음성 테스트, 마지막 1건은 실물 회차의 오인식 전사임. ⇒ **사용자가 실제로 말한 학습 발화가
하나도 없음.**

⚠️ **낭독은 job 을 만들지 않음이 함께 확인됐음** — job 이 붙은 발화는 `learning` **68건뿐**임.
설계서 §4.1(낭독은 분석에서 빠진다)이 실물로 지켜지고 있음.

### 비용 크기

같은 모델(`us.anthropic.claude-opus-5`)의 `llm_calls` 실측 평균이 입력 **4,126** · 출력 **1,132**
토큰/호출임(`purpose=spike` 3건). 62건이면 약 **0.26M 입력 · 0.07M 출력**.
Anthropic 1차 단가(입력 $5/1M · 출력 $25/1M)로 **약 $3** 임.
⚠️ **이 리포는 Bedrock 경유라 단가가 다를 수 있음** — 1차 단가는 상한의 참고값으로만 씀.
⚠️ `llm_calls` 에 `purpose=analysis` 가 **0건**임 — done 44건은 이 기록이 붙기 전이나 하네스가 만든
것임. 배선 자체는 정상임(`api/main.py` 가 `pool_usage_sink` 를 분석 클라이언트에 줌).

### 방침 — 처리하지 않고 `failed` 로 표시함

⛔ **워커를 켜서 비우는 것이 첫 권고였고 조사가 그것을 뒤집었음.** 처리하면 **테스트 문장이
`error_patterns`·복습 과제·주간 요약에 섞임** — `H-AC` 가 경고한 「하네스가 앱 데이터를 오염시킨다」와
같은 방향이고, 그 오염은 학습 계획을 움직이므로 해가 실재함. 돈도 약 $3 나감.

⛔ **삭제하지 않음** — 되돌릴 수 없고 「어느 회차가 무엇을 남겼나」가 기록으로 값이 있음.
⇒ `status='failed'` 로 두고 `last_error` 에 이유를 적음. 워커의 claim 조건이 `pending` 과 락 만료된
`running` 뿐이므로(`services/jobs.py:294-298`) **다시 집지 않음.**
⚠️ `status` 값역에 「취소」가 없음(`pending·running·done·failed`) — 그래서 `failed` 를 씀.
⚠️ `attempts` 는 건드리지 않음.

### 남는 구조 문제 — 별도 태스크로 등록함

하네스 회차가 돌 때마다 앱 큐에 job 이 쌓이고 teardown 이 그것을 걷지 않음. 이번에 62건이 그렇게
모였고 앞으로도 같은 속도로 쌓임.
<!-- SECTION:NOTES:END -->
