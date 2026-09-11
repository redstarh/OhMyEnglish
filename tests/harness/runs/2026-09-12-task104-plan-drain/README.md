# TASK-104 회차 — 계획 job 을 소화했고 **보존 세션 4건은 하네스가 거부했음**

> 소유 `TASK-104`. 세션 `ohmyenglish-40`(테스트 하네스 갈래) · 2026-09-12 ·
> 브랜치 `design/first-vertical-slice`. 사용자가 「지금 소화함」을 골랐음.
>
> ⛔ **판정 요지 넷.**
>
> 1. **계획이 갱신됐음** — `session_plans` **3 → 6** · `learner_notes` **4 → 7** ·
>    최신 행이 `2026-09-11 00:08` → **`2026-09-11 22:40`** (직접 조회).
> 2. ⛔ **계획 job 7건 중 4건은 소화하지 못했음** — 하네스가 *"보존 세션이다. 그 job 은 어떤
>    경우에도 처리하지 않는다"* 로 **거부**함(`browser_leg.md` §9). 즉 이 태스크의 「소화」는
>    **구조적으로 절반만 가능**함.
> 3. **`TASK-109` 를 재현했고 성질이 좁혀졌음** — 모델이 없는 키를 붙여 계획이 버려지는데
>    **재시도로 회복**됨(1회차 거부 → 2회차 성공). 그리고 키가 매번 다름.
> 4. **보존 세션 기준선 drift 0건** — `verify` 전후 diff 가 비었음.

---

## 1. 소화 전에 적은 것 (AC#1)

⛔ **태스크의 전제 둘이 낡아 있었음**(이 회차에 직접 조회).

| 태스크가 적은 것 | 실제 |
|---|---|
| pending **15**건 | **14**건 — `analyze_utterance` 7 · `plan_next_session` 7 |
| `session_plans` 최신이 `2026-09-08 22:58` 에 멈춤 | **`2026-09-11 00:08:24`** · 세션 `33447835` |

**대상과 비대상을 갈랐음.** `plan_next_session` 만 소화하고 `analyze_utterance` 7건은 건드리지
않았음. ⛔ 근거는 기준선 파일을 **직접 열어** 얻었음 —
`runs/2026-09-10-task82-p5-p6/results-api-baseline.json` 이 고정하는 필드는
`status` · `partial_failure` · `pronunciation` · `corrections` · `drill` 다섯이고
**`next_plan` 을 담지 않음.** 그리고 분석 job 7건 중 **3건이 보존 세션 `210233be` 의 것**이라
소화하면 그 세션 `status` 가 `analyzing` → `final` 로 바뀌어 기준선이 깨짐.

**방법**: ⛔ `run_worker` 를 부르지 않았음. 그 루프는 큐가 비면 `sweep_lost_runs` →
`flush_ended_sessions` 를 불러 **보존 세션에 job 을 새로 만들어 처리**하고 2026-09-09 에 그 경로로
보존 세션 둘이 파괴됐음(`H-AT` 경로 ②). 대신 `p5_worker_leg.py` 의
`guard(--job-type plan_next_session)` → `claim` → `restore` 를 세션마다 돌았음 —
`claim_next` 에 종류 필터가 없어 **guard 로 내 job 을 전역 최소로 당기는 것이 유일한 선택 방법**임.

## 2. 결과 (AC#2)

| 세션 | 보존 | 결과 | Claude 호출 |
|---|---|---|--:|
| `24597f0f` | — | 1회차 **거부**(`level.reason_en` 이 없는 키) → 2회차 **성공** · `session_plans` 1행 | 2 |
| `d727f79d` | — | **성공** · `status=done attempts=1` | 1 |
| `f8ebc78b` | — | **성공** · `status=done attempts=1` | 1 |
| `210233be` | ✅ 보존 | ⛔ **하네스가 거부** — 처리하지 않음 | 0 |
| `76d9ef31` | ✅ 보존 | ⛔ **하네스가 거부** | 0 |
| `b2f0d169` | ✅ 보존 | ⛔ **하네스가 거부** | 0 |
| `d127dece` | ✅ 보존 | ⛔ **하네스가 거부** | 0 |

**실물 Claude 호출 4회**(태스크가 적은 「최대 15회」보다 훨씬 적음 — 계획만, 그중 절반이 거부됨).

**표 전후** (직접 조회): `session_plans` 3 → **6** · `learner_notes` 4 → **7** ·
pending job 14 → **11**(계획 4 · 분석 7). **안 바뀐 것**: `error_patterns` 9 ·
`error_occurrences` 24 · `review_tasks` 15 · `pattern_attempts` 19.

⚠️ **`24597f0f` 의 job 은 `status=done attempts=2` 인데 `last_error` 가 남아 있음** — 1회차의
사유이고 2회차가 성공했다. **`last_error` 의 존재를 실패로 읽으면 안 된다** — `status` 를 본다.

## 3. `TASK-109` 가 좁혀진 것

거부 사유 원문: `plan contract violated: plan response failed validation: 1 validation error for
PlanOutput / level.reason_en / Extra inputs are not permitted`.

⛔ **동료 세션이 본 키는 `level.reason_note` 였고 이 회차는 `level.reason_en` 이다** — 즉 **특정
키 하나의 문제가 아니라 모델이 «없는 키를 만드는» 성향**이고 이름이 매번 다르다. 그래서
「그 키를 스키마에 더한다」로 닫히지 않는다.

⚠️ **그리고 재시도로 회복됐다** — 1회차 거부 뒤 2회차가 통과해 계획 행이 생겼다. 이것이 이
회차가 더한 새 사실이다: 이 결함은 **계획을 영구히 막지 않고 attempts 를 태운다**(상한 5).
⇒ `TASK-109` 의 등급을 정할 때 그 구분이 필요하다 — 「계획이 안 생긴다」가 아니라
「계획이 늦게 생기고 재시도 예산을 먹는다」다.

⚠️ **`TASK-108`(deepest recurrence 미포함)은 이 회차에서 관측되지 않았다** — 4회 호출 중 0건.
동료 세션은 같은 공유 DB 에서 그것을 봤으므로 **재료가 아니라 비결정성의 차이**로 보인다.

## 4. ⛔ 규약 충돌 — 이것이 이 회차의 가장 단단한 산출물 (AC#3)

**충돌하는 두 요구가 같은 DB 에 있다.**

| | 무엇 | 어디가 소유하나 |
|---|---|---|
| A | **보존 세션의 결과 API 상태를 바꾸지 않는다** | `browser_leg.md` §9 · `H-AT` · `H-AY` |
| B | **계획이 갱신되어야 한다**(정지가 조사 대상이 된다) | `TASK-100` → `TASK-104` |

⛔ **A 는 규약이 아니라 «집행»이다.** `p5_worker_leg.py` 가 보존 세션의 job 에
*"어떤 경우에도 처리하지 않는다"* 로 **거부**한다 — 사람이 잊는 것을 막는 코드다. 그래서
**B 를 그 4건에 대해 만족시키는 방법이 지금 없다.**

**그 4건이 남긴 실제 상태**: 보존 세션 4개는 **계획 job 을 영구히 pending 으로 들고 있다.**
`attempts=0` 이라 재시도 상한에도 걸리지 않아 **큐에서 사라지지 않는다.**

**⇒ 다음에 이 자리를 건드리는 세션이 고를 것 셋** (⛔ 이 회차가 고르지 않는다 — 보존 세션의
수명은 사람이 정한다):

1. **보존을 끝낸다.** 그 6개 세션이 무엇을 위한 기준선인지 다시 보고, 필요 없어졌으면 보존을
   해제하고 소화한다. ⚠️ 해제하면 `results-api-baseline.json` 이 무효가 되므로 **그것을 쓰는
   회차 절차를 함께 고쳐야 한다.**
2. **그 4건을 큐에서 내린다.** `status='failed'` + `last_error='보존 세션 — 의도적 미처리'` 로
   종결해 **pending 집계가 거짓 신호를 내지 않게** 한다. ⚠️ 그것은 DB 쓰기이므로 승인이 필요하다.
3. **그대로 둔다.** 대신 **pending 집계를 볼 때 보존 세션 몫을 빼고 읽는 규약**을 만든다 —
   그러면 「job 이 쌓였다」는 관측이 다시 이 조사를 유발하지 않는다.

⚠️ **3번을 고를 때 필요한 명령**(이 회차에서 확인한 것):

```sql
select j.job_type, count(*)
  from analysis_jobs j
  left join utterances u on u.id = j.utterance_id
 where j.status = 'pending'
   and left(coalesce(j.session_id, u.session_id)::text, 8) not in
       ('210233be','6225ddaf','76d9ef31','b2f0d169','d127dece','e0c5e580')
 group by 1;
```

## 5. 재현

```bash
cd app/backend
.venv/bin/python ../../tests/harness/p5_worker_leg.py verify          # 보존 세션 기준선
.venv/bin/python ../../tests/harness/p5_worker_leg.py guard \
    --expect-session <8자> --out <회차디렉터리>/guard-<8자>.json --job-type plan_next_session
.venv/bin/python ../../tests/harness/p5_worker_leg.py claim --expect-session <8자>
.venv/bin/python ../../tests/harness/p5_worker_leg.py restore --in <회차디렉터리>/guard-<8자>.json
```

증거: `verify-before.txt` · `verify-after.txt`(**diff 가 비었음**) · `guard-*.json` 3건
(비보존 세션 것만 — 보존 세션은 guard 가 거부해 스냅샷이 만들어지지 않는다).
