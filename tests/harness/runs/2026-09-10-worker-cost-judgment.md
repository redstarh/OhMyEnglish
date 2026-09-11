# 보충 판정 — 워커 기동의 파괴 범위와 **소비 없는 대안 경로**

> 앞선 회차 기록 `2026-09-10-test-status-probe.md` 의 보충임. 팀리드 정정(2026-09-10)이 요구한
> 판정 셋에 답함. ⛔ **워커를 켜지 않았고 C3e·C3a 를 소비하지 않았음.** DB 는 SELECT 만 했음.
>
> ⛔ **`d127dece`·`210233be` 에 대한 UPDATE·DELETE 0건임.**

---

## 1. 팀리드 정정 둘을 확인함

| 정정 | 확인 결과 |
|---|---|
| `browser_leg.md` 가 워커 기동을 금지함 (`:166-171`) | **맞음.** 보존 세션 **C3a** `210233be`(`analyzing`) · **C3e** `d127dece`(`no_utterances`)를 파괴한다고 명시하고 그 둘을 *"재실행 비용을 0으로 만드는 근거"* 로 부름 |
| 스파이크 직결은 `learning_sessions` 를 만들지 않음 | **맞음.** 따라서 `TASK-78` AC#3 의 종단 재료가 되는 것은 **앱 경로 회차뿐임** |

⚠️ **한 가지는 반영하지 않음 — 근거를 함께 적음.** 정정이 `TASK-78` AC#3 의 필요 조건을 「앱 경로
회차 **+ 워커**」로 적으라고 했으나, **워커 부분은 앞 기록 §9.1 이 코드로 반증했음.** AC#3 의 종단
셋(`pronunciation_attempts` 행 · `error_patterns` 패턴 · `next_review_at`)이 전부
`session.py:319 record_attempt` 연쇄 안에서 만들어지고 워커를 지나지 않음. `review.py:3` 이
*"세션·워커는 배선만 한다"* 고 못박음. **그래서 이 문서는 「앱 경로 회차 + 워커 불필요」로 적음.**
정정의 앞부분(앱 경로 필요)은 그대로 반영함.

## 2. 워커 ON 의 파괴 범위 — **파괴하지 않고 SELECT 로 셈**

`_FLUSH_ENDED_SESSIONS_SQL`(`services/utterances.py:200`)의 `run_ends` CTE 를 **INSERT 를 떼고**
그대로 재현해 돌렸음. `ENDED_SESSION_STATUSES = ("completed", "failed")`(`sessions.py:51`)이고
DB 의 13 세션이 전부 그 둘이므로 **전 세션이 스윕 대상임.**

```
would_enqueue:  d127dece-…  →  3
합계 3
```

⛔ **스윕이 걷을 대상은 `d127dece`(C3e) 의 3건뿐임.** 다른 세션은 0건임 — 「묶음 계산에 따라 다른
세션에도 job 이 생길 수 있다」는 내 우려가 반증됐음.

그러나 **워커 ON 의 전체 파괴 범위는 스윕만이 아님.** `claim_one` 이 기존 `pending` 을 집음.

| 경로 | 대상 | 결과 |
|---|---|---|
| 스윕(`flush_ended_sessions`) | C3e 에 `analyze_utterance` **3건 등록** | C3e 의 `no_utterances` 소멸 → `analyzing` |
| `claim_one` ① | C3a `210233be` 의 `analyze_utterance` **pending 3건** | C3a 의 `analyzing` 소멸 · 실물 Claude **3건** |
| `claim_one` ② | `plan_next_session` **pending 4건**(`210233be`·`b2f0d169`·`d127dece`·`76d9ef31`) | `session_plans` 증가 · 실물 Claude **4건** |
| `claim_one` ③ | 스윕이 새로 만든 C3e 의 3건 | 실물 Claude **3건** |

**실물 Claude 호출 최대 10건** + `error_patterns`·`error_occurrences`·`review_tasks` 변동.
⚠️ 그 변동이 `TASK-84` 의 판정 대상(`error_patterns` 10 · `review_tasks` 17)과 섞임.

## 3. 소비 대가 — C3e·C3a 는 각각 **유일 표본**임 (직접 세어 확인)

세션 13건을 조회해 `analyzable`(user·learning 발화 수) · `au_total` · `au_nonterm` 을 셌음.

| 조건 | 해당 세션 | 무엇의 표본인가 |
|---|---|---|
| `analyzable > 0` **이고** `au_total = 0` | **`d127dece` 하나** | `awaiting_analysis=True` 를 낼 수 있는 **유일 세션.** A3-1 5상태 라벨의 `no_utterances` 표본 |
| `au_nonterm > 0` | **`210233be` 하나** | `analyzing` 상태의 **유일 표본** |

⛔ **워커 ON 은 5상태 표본 중 2개를 동시에 파괴함.** A3-1 은 「5상태 라벨」을 재는데 3상태만 남음.

⚠️ **C3e 는 A4-1 음성 대조에서는 이미 제외됐음** — `browser_leg.md:343` 이 2026-09-09 에
*"음성 대조는 `partial_failure`(C3c)를 쓴다 — `no_utterances`(C3e)가 아니다"* 로 정정했음.
`page.tsx:129` 의 `showCorrections` 게이트 때문에 C3e 에서는 교정 컨테이너가 마운트조차 되지 않아
그 0 이 카드 경로를 배제하지 못함. **그래서 C3e 의 쓰임은 A3-1 과 `awaiting_analysis` 표본 둘임.**

**재생성 비용**: `browser_leg.md:695` 가 조성 방법을 적음 — *"앱 경로 세션 → `analyze_utterance`
job 전부 삭제"*. 즉 앱 경로 세션 1회(지금 `nova` 구성이라 Nova 유료 호출 1건) + job DELETE 임.
⚠️ C3b 만 조성에 *"워커를 잠깐 켜 실물 호출 1건"* 이 들었고 **C3e 는 들지 않음.**

## 4. ⛔ 판정 — **C3e 를 소비할 필요가 없음.** 소비 없는 경로가 이미 리포에 있음

### 4.1 회복을 세션 하나로 좁히는 SQL 이 이미 있음

`services/utterances.py:196` 이 그것임.

```python
_FLUSH_ONE_SESSION_SQL = _RUN_END_FLUSH_TEMPLATE.format(session_filter="u.session_id = $4")
...
async def flush_pending_analysis(conn, session_id: UUID) -> list[UUID]:   # :207
```

**전체 스윕과 같은 묶음 정의를 쓰고 대상 세션만 다름**(:241 이 그렇게 적음). 즉 새 표본 세션만
회복시킬 수 있고 **C3e 는 걷히지 않음.**

### 4.2 job 1건만 처리하는 실행체가 이미 있고 실증됐음

`tests/harness/p5_worker_leg.py` 가 그것임. docstring 이 방어 셋을 적음.

- ⛔ **`run_worker` 를 부르지 않음** — 그 루프가 `sweep_lost_runs` → `flush_ended_sessions` 를 부르고
  그것이 `H-AT` 경로 ②임. **그 함수를 import 하지 않으므로 구조적으로 지나가지 않음**
- `H-AT` 경로 ①(claim 이 기존 pending 을 집음)은 **`guard`** 로 막음 — 보존 세션 job 의
  `available_at` 을 미래로 비켜 두고 원래 값을 JSON 스냅샷으로 뜸. `restore` 가 되돌림
- **보존 세션 job 이 전부 비켜져 있는지 먼저 검사하고, 하나라도 claim 가능하면 실행을 거부함**
- 소유 세션 해소를 `coalesce(j.session_id, u.session_id)` 로 함 — 앞 기록 §5 가 만난
  「`analyze_utterance` 의 `session_id` 가 NULL」을 정확히 그렇게 풂
- 스냅샷을 `/tmp` 에 두지 않고 회차 디렉터리에 두고 커밋함

⚠️ **이미 한 번 값어치를 증명했음** — 2026-09-10 회차가 `claim` **전에** SELECT 로 찾아 멈춰서
`C3a` 손상을 면했음(정본 `runs/2026-09-10-task82-p5-p6.md` §2).

### 4.3 그래서 `TASK-79` AC#2 를 C3e 없이 닫는 경로

| 단계 | 무엇 | 파괴하는 것 | 선행 조건 |
|--:|---|---|---|
| 1 | 앱 경로로 새 세션 1건 생성(`p_app_path.py`) | 없음 — 내 세션임 | 지금 구성으로 가능 |
| 2 | 그 세션의 `analyze_utterance` job 삭제 → 등가 `awaiting_analysis=True` | 내 세션의 job 만 | **DB 쓰기 승인** |
| 3 | 화면을 열어 폴링이 조기에 멈추지 않는 것을 관측 (**앞 조각**) | 없음 | **계측 신설**(하네스에 그 키를 재는 코드 0건) |
| 4 | `flush_pending_analysis(conn, <새 세션>)` 를 직접 불러 job 되살림 | 그 세션만 — **C3e 는 걷히지 않음**(§4.1) | 짧은 드라이버 **신설** |
| 5 | `p5_worker_leg.py` 의 `guard`→`claim`→`restore` 로 그 job 1건만 처리 | 없음 — guard 가 보존 job 을 비켜 둠 | 실물 Claude **1건** |
| 6 | 화면이 교정을 표시하는 것을 관측 (**뒤 조각**) | 없음 | 3의 계측 |

⛔ **이 경로에서 C3e·C3a·plan job 4건이 전부 보존됨. 워커 ON 이 필요 없음.**

### 4.4 ⛔ 팀리드의 읽기를 반증함 — C3e 회복은 AC#2 의 좋은 관측 기회가 아님

정정이 *"C3e 가 바로 `TASK-79` AC#2 가 관측하려는 상태로 보임 … 워커를 켜는 순간 C3e 가 실제로
회복 경로를 밟고, 그것이 AC#2 후반부의 관측 기회임"* 이라 적었음. **상태의 동일성은 맞으나 그것을
쓰는 것이 낫다는 결론은 성립하지 않음.** 이유 셋임.

1. **AC#2 는 특정 세션을 지목하지 않음.** 문면은 *"스윕을 늦춰도 화면이 교정을 놓치지 않는 것을
   관측한다"* 이고 어느 세션이어야 한다는 조건이 없음. 등가 상태로 성립함.
2. **워커 ON 은 관측에 필요한 것보다 훨씬 많이 파괴함.** 필요한 것은 job 1건 회복 + 1건 처리인데,
   워커는 §2 의 4경로를 **동시에** 열어 실물 호출 10건과 표본 2개를 소비함. **관측 1건의 대가로
   유일 표본 2개를 내는 거래임.**
3. **관측 자체가 C3e 를 되돌릴 수 없게 만듦.** 회복이 끝나면 그 세션은 `final` 또는
   `partial_failure` 가 되고 `no_utterances` 표본이 리포에서 사라짐 — A3-1 이 5상태를 못 채움.

⚠️ **다만 정정이 옳게 지적한 것 하나**: 그 관측은 **일회성**임. 등가 표본을 쓰더라도 한 세션은
관측과 동시에 소비됨. 그래서 **관측 순서를 미리 정해 한 표본에서 앞 조각과 뒤 조각을 함께 받는
것**이 필요함(§4.3 의 3 과 6 을 같은 세션에서 함).

## 5. 요약 — 소비 없이 얻는 것과 소비해야 얻는 것

| | 얻는 것 | 대가 |
|---|---|---|
| **소비 없음** | `awaiting_analysis=True` 응답 관측 | 이미 얻었음(앞 기록 §8.1) |
| **소비 없음** | 화면 폴링이 조기에 멈추지 않는 것(**앞 조각**) — C3e 를 **읽기만** 함 | 계측 신설 |
| **소비 없음** | 회복 뒤 화면이 교정을 표시하는 것(**뒤 조각**) — 새 표본 + `flush_pending_analysis` + `p5_worker_leg` | 앱 경로 세션 1회 · 실물 Claude 1건 · DB 쓰기 승인 · 드라이버 신설 |
| **소비 필요** | C3e **자체**가 회복 경로를 밟는 것 | C3e(`no_utterances` 유일 표본) + C3a(`analyzing` 유일 표본) + 실물 Claude 최대 10건 + 7개 표 기준선 |

⛔ **마지막 줄을 요구하는 AC 가 지금 없음.** `TASK-79` AC#2 는 등가 표본으로 닫힘. 그래서
**워커 ON 은 지금 필요하지 않다는 것이 이 문서의 판정임.**

⚠️ **판정만 냈음** — C3e 를 소비하지 않았고 워커를 켜지 않았음. 트레이드오프의 결정은 사람 몫이고,
이 문서는 그 결정이 필요한지 자체를 되물음.
