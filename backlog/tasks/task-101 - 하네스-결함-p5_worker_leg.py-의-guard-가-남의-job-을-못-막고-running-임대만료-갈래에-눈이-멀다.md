---
id: TASK-101
title: '하네스 결함: p5_worker_leg.py 의 guard 가 남의 job 을 못 막고 running-임대만료 갈래에 눈이 멀다'
status: Done
assignee: []
created_date: '2026-09-10 22:20'
updated_date: '2026-09-10 22:33'
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
- [x] #1 claim 가능 집합을 제품 술어 두 갈래로 계산한다 — pending+available_at 과 running+임대만료+attempts 를 모두 본다. available_at 하나로 판정하지 않는다
- [x] #2 남의 job 에 UPDATE 를 0건으로 만든다 — 내 대상 job 하나만 앞으로 당기고 그것만 스냅샷·복원한다
- [x] #3 guard 와 claim 이 같은 단정을 갖게 한다 — 전역 최소가 기대 세션 것이 아니면 둘 다 거부한다(claim 은 exit 2)
- [x] #4 판별력을 무력화해서 잰다 — 일부러 어긋난 조건을 만들어 guard·claim 이 비영으로 죽는 것을 확인한다. 통과만 보고 닫지 않는다
- [x] #5 이전 스냅샷 파일의 모양을 깨지 않는다 — 과거 회차의 p5-guard.json 을 restore 가 그대로 읽어야 한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-11 완료 — **AC 5건 충족. 정본은 `tests/harness/runs/2026-09-11-task79-task101.md` §3 이다.**

**고친 방향**: 남의 job 을 미래로 미는 대신 **내 job 하나를 전역 최소로 당긴다**(`available_at = 2000-01-01`). `claim_next` 가 `order by available_at limit 1` 이므로 내 것이 집힌다.

- **AC#1** — claim 가능 집합을 제품 술어 **두 갈래**로 계산한다. `LEASE`·`MAX_ATTEMPTS` 를 `app.services.jobs` 에서 **import** 해 파라미터로 넘긴다(숫자로 적으면 제품이 값을 바꿀 때 조용히 낡는다). `clock_timestamp()` 도 제품과 같게 썼다.
- **AC#2** — 남의 job UPDATE **0건**을 기계로 확인했다: 회차 후 `analysis_jobs` 57행을 회차 전 스냅샷과 대조해 **사라진 0 · 새 0 · 어긋난 0**.
- **AC#3** — `_front_runner_is` 하나를 `guard`·`claim` 이 공유한다. **동률도 거부한다**(`order by available_at` 이 같은 값 둘을 만나면 보장이 없다).
- **AC#4** — 판별력 시험 **4건 전부 비영 종료**(guard 에 claim 대상 없는 세션 → 1 · claim 에 남의 세션 → 2 · claim 에 보존 세션 → 2 · guard 에 보존 세션 → 1). 시험 뒤 `attempts` 합 0 · `running` 0. ⛔ **거부만 보고 닫지 않았다** — 성공 경로(guard → claim → 내 job 1건 처리 → status=done)를 같은 회차에서 함께 쟀다.
- **AC#5** — 옛 스냅샷(`runs/2026-09-11-task98-production-prompt/p5-guard.json` · 15건)을 새 `restore` 가 읽어 **복원 15건/15건**, 그 뒤 `analysis_jobs` 어긋난 job **0**.

⛔ **새 단정이 만든 새 위험을 앞단에서 막았다** — `_front_runner_is` 는 「전역 최소가 기대 세션 것인가」만 보므로 **보존 세션을 기대로 주면 통과한 뒤** `claim_next` 가 실제로 집는다(사후 검사는 커밋 다음에야 막는다). `_reject_preserved_expectation` 을 두 팔 맨 앞에 뒀다. 판별력 시험을 설계하다가 발견했고, 시험 3을 그냥 돌렸으면 보존 세션이 손상됐다.

**출력이 조용히 거짓말하던 자리 둘도 고쳤다**: `restore` 가 `done` job 을 `claimable=True` 로 찍던 것(옛 술어) · 0행 UPDATE 를 「복원 1건」으로 보고하던 것(스냅샷 건수를 그대로 찍었다). 후자는 재실행으로 `복원 0건 / 스냅샷 1건` + 경고를 확인했다.

⚠️ **못 잰 것 둘**: `available_at` 동률 거부와 `running`·임대만료 갈래를 **실물로 시험하지 않았다**(동률은 남의 job 을 만져야 하고, 후자는 lease 5분을 넘긴 죽은 claim 이 필요하다). 결함 2 는 **술어 대조로 확정**했고 새 코드가 그 갈래를 계산에 포함하는 것까지가 근거다.

⚠️ 결함 1 의 재현과 순서 함정은 동료 세션(`ohmyenglish-7f`)이 실측해 넘겼다. 그 세션은 `running` job 이 0건이어서 결함 2 를 **우연히 면했다** — 방법이 옳았던 것이 아니다.
<!-- SECTION:NOTES:END -->
