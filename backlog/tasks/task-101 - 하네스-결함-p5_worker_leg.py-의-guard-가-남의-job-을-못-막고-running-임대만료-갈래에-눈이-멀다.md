---
id: TASK-101
title: '하네스 결함: p5_worker_leg.py 의 guard 가 남의 job 을 못 막고 running-임대만료 갈래에 눈이 멀다'
status: In Progress
assignee: []
created_date: '2026-09-10 22:20'
updated_date: '2026-09-10 22:20'
labels: []
dependencies: []
ordinal: 104000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
동료 세션(ohmyenglish-7f)이 첫 결함을 재현해 넘겼고 팀리드가 제품 술어를 읽어 둘째 결함을 더 찾았다. 소유는 이 갈래다(도구가 이 갈래 산출물).

결함 1 — guard 의 범위. guard 는 PRESERVED 6개 세션의 job 만 비켜 두는데 claim_next 는 claim 가능한 모든 job 중 available_at 이 가장 이른 것을 집는다. 실측(동료 세션): 24597f0f 의 analyze_utterance 가 집혀 status=running·attempts=1·lock 이 커밋됐다. --expect-session 은 처리만 막고 claim 자체를 막지 못한다. 동료가 baseline 으로 복원해 analysis_jobs drift 0 을 확인했다.

결함 1-b — 순서 함정. 남의 job 을 손으로 밀고 나서 guard 를 돌리면 guard 가 밀린 값을 「원값」으로 스냅샷해 restore 가 거짓 복원을 한다. 동료가 그 순서를 회차 기록 §8.1 에 적었다.

⛔ 결함 2 — 팀리드가 app/services/jobs.py 의 claim 술어를 직접 읽어 찾았다. claim 조건이 두 갈래다: (status=pending and available_at <= now()) OR (status=running and locked_at < now() - LEASE and attempts < MAX_ATTEMPTS). 즉 running-임대만료 갈래의 claim 가능성은 available_at 과 무관하다. 그런데 도구의 claimable_now 는 available_at <= now() 하나뿐이라 그 갈래에 구조적으로 눈이 멀다 — available_at 을 30일 뒤로 밀어도 그 job 은 여전히 집힌다.

고치는 방향(단순 대안을 골랐다): 남의 행을 밀지 않고 «내 job 하나»를 앞으로 당긴다. claim_next 가 order by available_at limit 1 이므로 내 job 이 전역 최소이면 내 것이 집힌다. 그러면 남의 데이터 쓰기가 0건이 되고 순서 함정이 사라진다. 그리고 claim 가능 집합을 제품 술어 두 갈래로 계산해 「최소가 내 것이 아니면 거부」를 단정으로 둔다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 claim 가능 집합을 제품 술어 두 갈래로 계산한다 — pending+available_at 과 running+임대만료+attempts 를 모두 본다. available_at 하나로 판정하지 않는다
- [ ] #2 남의 job 에 UPDATE 를 0건으로 만든다 — 내 대상 job 하나만 앞으로 당기고 그것만 스냅샷·복원한다
- [ ] #3 guard 와 claim 이 같은 단정을 갖게 한다 — 전역 최소가 기대 세션 것이 아니면 둘 다 거부한다(claim 은 exit 2)
- [ ] #4 판별력을 무력화해서 잰다 — 일부러 어긋난 조건을 만들어 guard·claim 이 비영으로 죽는 것을 확인한다. 통과만 보고 닫지 않는다
- [ ] #5 이전 스냅샷 파일의 모양을 깨지 않는다 — 과거 회차의 p5-guard.json 을 restore 가 그대로 읽어야 한다
<!-- AC:END -->
