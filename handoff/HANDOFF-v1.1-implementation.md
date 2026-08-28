# Handoff — 요구사항 v1.1 구현 갈래

> **이 파일은 짧게 유지한다.** 담는 것은 **지금 어디까지 왔는가 / 다음 한 걸음이 무엇인가**
> 둘뿐이다. 전체 작업 지도와 진행 상태는 **`TASKS.md`**, 함정은 `docs/ops/pitfalls.md`,
> 결정과 근거는 `docs/design/**`이 소유한다 — 여기에 복사하지 않는다(한쪽이 낡는다).
>
> 최종 갱신 **2026-08-28** · 기준 커밋 **HEAD ≥ `8a0834e`** · 브랜치 `design/first-vertical-slice`

---

## 지금 어디까지 왔나

**요구사항 v1.1 §10(발음 시범·재발화) 9태스크 중 6개 완료.** §11(추천 학습 루틴)은 설계만 끝났고
코드가 0줄이다.

지금 `VOICE_ADAPTER=nova`로 돌리면 **Nova가 발음을 교정해 주고 기록도 남는다.**

| 되는 것 | 안 되는 것 |
|---|---|
| Nova가 발음을 지적하고 문장을 다시 읽어준다 (지시문 규칙 7~10) | **화면 배지** — 프론트가 `pronunciation` 프레임을 모른다(Task 8) |
| `toolUse` → `PronunciationEvent` → DB 저장 | **약점 패턴 연결** (Task 7) |
| 한글 전사 신호 (`note_transcript`) | **결과 화면 발음 카드** (Task 8) |
| 세션 종료 시 대답기다림 → `incorrect` 수렴 (종료 기록과 한 트랜잭션) | 되묻기 문구 감지 — **만들지 않는다**(캡틴 결정) |

⚠️ **배지 없음은 정상이다.** nova로 띄웠는데 배지가 없다고 정상인 어댑터·세션을 디버깅하지 마라.
⚠️ **실물 Nova 왕복은 아직 안 했다** — 단위 테스트만이다. `TASKS.md` A-3.

---

## 다음 한 걸음

### 계획 Task 7 — 패턴 연결 (`error_patterns` upsert)
계획: `docs/design/2026-08-27-pronunciation-echo-plan.md`

**착수 전 필수 3건은 `TASKS.md` A-1에 있다** — 트랜잭션 소유권 / 경로 불문 패턴 생성 /
`target_form` not null. 그것을 읽지 않고 시작하면 부분 실행과 무증상 미충족이 생긴다.

`TASKS.md` **B-4**(발음 `pattern_key` 값역)가 Task 7 전 캡틴 결정 항목이다 — 기본안(§5.6 규약
재사용)으로 진행해도 되지만 결정 여부를 먼저 확인한다.

---

## 실측값 (2026-08-28, 이 절을 쓴 턴에 직접 실행)

```bash
cd app/backend && .venv/bin/pytest -q              # 312 passed
cd app/backend && .venv/bin/ruff check .            # All checks passed!
cd app/backend && .venv/bin/ruff format --check .   # 27 files already formatted
cd app/backend && ty check                          # All checks passed!
cd app/backend && .venv/bin/ruff check ../../tests ../../scripts        # Found 6 errors (베이스라인)
cd app/backend && .venv/bin/ruff format --check ../../tests             # 4 files (베이스라인, 함정 H-L)
```

| 항목 | 값 |
|---|---|
| 테스트 | **312 passed**, skip/xfail 0 (v1.1 착수 전 241) |
| dev DB 마이그레이션 | **4개** — 001 · 003 · 004 · 005. `app/backend/.venv/bin/python scripts/migrate.py`(멱등) |
| dev DB 행 | 세션 2 · 발화 6 · 패턴 1 · occurrence 2 · job 3 · `pronunciation_attempts` **0** |
| 미커밋 | `.claude/settings.json`(untracked) — **지우지 마라** |

⚠️ 게이트는 **`app/backend` cwd에서** 판정한다(함정 H-A). `tests/**` 두 수치는 선언된 게이트 밖이라
따로 돌려야 한다(H-L).

---

## 인계 기록

| 언제 | 이전 세션 → 새 세션 | 4개 지표 대조 |
|---|---|---|
| 2026-08-28 | `claude_air_3-14` → **`claude_air_3-15`** (iTerm2 창에 생성 완료, attached) | ⏳ **대기 중 — 새 세션의 보고를 아직 못 받았다** |

**이전 세션이 기록한 대조 기준** (새 세션은 이 4개를 **직접 돌려** 얻고 일치를 보고해라):

| # | 지표 | 값 |
|--:|---|---|
| 1 | HEAD | **`8a0834e`** (`git rev-parse --short HEAD`) |
| 2 | 다음 한 걸음 | **계획 Task 7 — 패턴 연결** (§F 규약 정리는 `8a0834e`로 종결됐다) |
| 3 | 게이트 | **312 passed** · ruff·format(27파일)·ty clean (cwd `app/backend`) |
| 4 | 착수 전 필수 | **3건** — `TASKS.md` A-1 |

⚠️ **이전 세션(`claude_air_3-14`)을 아직 kill하지 않았다.** 4개가 데이터로 일치한 뒤에
`tmux kill-session -t claude_air_3-14`를 **새 세션이** 실행한다. 불일치가 있으면 그 차이를
먼저 설명하고, 정리하지 않는다.

인계 시 새 세션이 **직접 돌려 얻은** 4개(HEAD 해시 · 다음 한 걸음 · 게이트 실측 · 착수 전 필수
건수)를 보고하고, 이전 세션이 대조 결과를 위 표에 적은 **뒤에** 정리한다.
절차는 `~/.claude/rules/session-handover.md`.

---

## 다음 세션 진입 절차

1. 이 파일 → **`TASKS.md`의 A 표 한 줄** → `handoff/HANDOFF.md`(실행 방법이 필요할 때만).
   `TASKS.md` 전체를 읽지 않는다.
2. 게이트를 `app/backend` cwd에서 돌려 위 실측값과 대조한다. 다르면 그 차이를 먼저 설명한다.
3. Nova를 건드리면 `spike_nova_protocol.py --wav p1a.wav`로 자격증명 생존을 먼저 확인한다.
4. 계획서를 열면 **머리말의 "구현 후 정정" 표를 먼저 읽는다** — 본문 코드 블록 5건이 낡았다.
   특히 테스트 헬퍼 이름은 추측이라 실재하지 않는다(함정 H-N).
5. Task 7부터 TDD. **태스크 상태가 바뀌면 `TASKS.md`를, 다음 한 걸음이 바뀌면 이 파일을**
   갱신한다 — 별도 지시를 기다리지 않는다.

---

## 다음 태스크가 바로 쓸 시그니처

계획 본문의 서술은 낡았다. 실제 계약은 이것이고 정본은 설계서 §3.1a·§3.2다.

```python
from app.services.pronunciation import (
    note_transcript,      # 학습자 전사문을 보고 신호가 보이면 기록 (감지기 묶음)
    record_attempt,       # Nova tool 생명주기 — signal_source 인자가 없다(항상 nova_tool)
    record_signal,        # 단발 관측 1건 — outcome에 'pending'이 없다
    resolve_dangling,     # 종료 수렴 — 세션 종료 기록과 같은 트랜잭션에서
)
from app.services.sessions import end_session   # conn을 받는 원시 함수
```

**규칙은 서비스가 소유하고 세션은 배선만 한다**(설계서 §3.1a). 새 감지기를 `session.py`에
박지 마라 — `note_transcript` 안에 넣는다.

---

## 이 갈래의 문서 지도

| 문서 | 역할 |
|---|---|
| **`TASKS.md`** | **전체 작업·진행 상태의 정본.** 무엇이 남았나 |
| `docs/PRD.md` (v1.1) §10·§11 | 요구사항 정본 |
| `docs/design/2026-08-27-pronunciation-echo-design.md` | §10 설계 — **결정과 근거의 정본** (§3.1a 소유 경계 · §3.2 생명주기 · §6.1 제약) |
| `docs/design/2026-08-27-pronunciation-echo-plan.md` | §10 구현 계획 9태스크 (머리말에 정정표) |
| `docs/design/2026-08-25-learning-coach-agent-design.md` | §11 설계 (정본 승격, 2슬라이스) |
| `docs/ops/pitfalls.md` | 실측된 함정 H-A~H-O |
| `tests/harness/runs/2026-08-27-P-tooluse-spike/` | tool use 실증 원자료 |
| `docs/storyboard.html` | 03b 발음 시범 · 03c 추천 루틴 화면 |
