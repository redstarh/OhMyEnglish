# Handoff — 요구사항 v1.1 구현 갈래

> **이 파일은 짧게 유지한다.** 담는 것은 **지금 어디까지 왔는가 / 다음 한 걸음이 무엇인가**
> 둘뿐이다. 전체 작업 지도와 진행 상태는 **`TASKS.md`**, 함정은 `docs/ops/pitfalls.md`,
> 결정과 근거는 `docs/design/**`이 소유한다 — 여기에 복사하지 않는다(한쪽이 낡는다).
>
> 최종 갱신 **2026-08-28** · 기준 커밋 **HEAD ≥ `21ebf80`** · 브랜치 `design/first-vertical-slice`

---

## 지금 어디까지 왔나

**요구사항 v1.1 §10(발음 시범·재발화) 9태스크 중 7개 완료.** §11(추천 학습 루틴)은 설계만 끝났고
코드가 0줄이다.

지금 `VOICE_ADAPTER=nova`로 돌리면 **Nova가 발음을 교정하고, 기록이 남고, 약점 패턴까지 쌓인다.**

| 되는 것 | 안 되는 것 |
|---|---|
| Nova가 발음을 지적하고 문장을 다시 읽어준다 (지시문 규칙 7~10) | **화면 배지** — 프론트가 `pronunciation` 프레임을 모른다(Task 8) |
| `toolUse` → `PronunciationEvent` → DB 저장 | **결과 화면 발음 카드** (Task 8) |
| 한글 전사 신호 (`note_transcript`) | 되묻기 문구 감지 — **만들지 않는다**(캡틴 결정) |
| 세션 종료 시 대답기다림 → `incorrect` 수렴 (종료 기록과 한 트랜잭션) | 복습 과제 생성 — §11의 몫 |
| **약점 패턴 연결** — 판정·수렴 경로 불문 `error_patterns` upsert (`21ebf80`) | |

⚠️ **배지 없음은 정상이다.** nova로 띄웠는데 배지가 없다고 정상인 어댑터·세션을 디버깅하지 마라.
⚠️ **실물 Nova 왕복은 아직 안 했다** — 단위 테스트만이다. `TASKS.md` A-3.

---

## 다음 한 걸음

### 계획 Task 8 — 결과 화면 발음 카드 (백엔드 + 프론트)
계획: `docs/design/2026-08-27-pronunciation-echo-plan.md:1344`

⏸ **착수 전 캡틴 결정 B-1이 필요하다** — 판정↔시범 짝짓기에 상관키가 없어 한 행의
`target_form`과 `spoken_form`이 어긋날 수 있다(실측 재현). Task 8이 바로 그 쌍을 학습자에게
렌더하므로 먼저 정한다. **선택지 2개와 근거, 그리고 함께 실어야 할 `signal_source`·수렴 행
해석은 `TASKS.md` A-2 한 절에 다 있다** — 여기 복사하지 않는다(한쪽이 낡는다).

---

## 실측값 (2026-08-28, 이 절을 쓴 턴에 직접 실행)

```bash
cd app/backend                                    # 게이트는 이 cwd에서만 판정한다 (함정 H-A)
.venv/bin/pytest -q                               # 319 passed
.venv/bin/ruff check . && .venv/bin/ruff format --check .   # passed / 27 files formatted
ty check                                          # All checks passed!
.venv/bin/ruff check ../../tests ../../scripts    # Found 6 errors  (베이스라인, 게이트 밖)
.venv/bin/ruff format --check ../../tests         # 4 files         (베이스라인, 함정 H-L)
```

| 항목 | 값 |
|---|---|
| 테스트 | **319 passed**, skip/xfail 0 (Task 7이 +7. v1.1 착수 전 241 → 312 → 319) |
| dev DB 마이그레이션 | **4개** — 001 · 003 · 004 · 005. `app/backend/.venv/bin/python scripts/migrate.py`(멱등) |
| dev DB 행 | 세션 2 · 발화 6 · 패턴 1 · occurrence 2 · job 3 · `pronunciation_attempts` **0** · **발음 패턴 0** |
| 미커밋 | `.claude/`(untracked) — **지우지 마라** |

⚠️ **발음 데이터는 dev DB에 0건이다.** Task 7은 통합 테스트(롤백 트랜잭션)로만 검증됐다 —
화면에서 발음 카드를 보려면 실물 Nova 왕복이 먼저다(A-3).

---

## 인계 기록

| 언제 | 이전 → 다음 | 4개 지표 대조 |
|---|---|---|
| 2026-08-28 | `claude_air_3-14` → **같은 창의 새 컨텍스트** (3-15는 빈 셸이라 쓰이지 않았고 정리됨) | ✅ **4/4 일치** — HEAD만 docs 커밋 1건 차이(실질 일치) |

함정 **H-P**(인계표의 HEAD는 적는 순간 낡는다)·**H-Q**(인계용 tmux 세션이 안 쓰일 수 있다)로 남겼다.

---

## 다음 세션 진입 절차

1. 이 파일 → **`TASKS.md`의 A 표 한 줄** → `handoff/HANDOFF.md`(실행 방법이 필요할 때만).
   `TASKS.md` 전체를 읽지 않는다.
2. 게이트를 `app/backend` cwd에서 돌려 위 실측값과 대조한다. 다르면 그 차이를 먼저 설명한다.
3. Nova를 건드리면 `spike_nova_protocol.py --wav p1a.wav`로 자격증명 생존을 먼저 확인한다.
4. 계획서를 열면 **머리말의 "구현 후 정정" 표를 먼저 읽는다** — 본문 코드 블록 5건이 낡았다.
   특히 테스트 헬퍼 이름은 추측이라 실재하지 않는다(함정 H-N).
5. **B-1을 먼저 정하고** Task 8부터 TDD. **태스크 상태가 바뀌면 `TASKS.md`를, 다음 한 걸음이
   바뀌면 이 파일을** 갱신한다 — 별도 지시를 기다리지 않는다.

---

## 다음 태스크가 바로 쓸 시그니처

계획 본문의 서술은 낡았다. 실제 계약은 이것이고 정본은 설계서 §3.1a·§3.2다.

```python
from app.services.pronunciation import (
    link_pattern,         # 시도 1건 → error_patterns. 조건(incorrect+target_sound)은 SQL이 갖는다
    note_transcript,      # 학습자 전사문을 보고 신호가 보이면 기록 (감지기 묶음)
    record_attempt,       # Nova tool 생명주기 — **자기 트랜잭션을 연다**. 패턴 연결까지 한 단위
    record_signal,        # 단발 관측 1건 — outcome에 'pending'이 없고 패턴을 만들지 않는다
    resolve_dangling,     # 종료 수렴 + 패턴 연결 — 호출자의 트랜잭션에 합류한다
)
from app.services.sessions import end_session   # conn을 받는 원시 함수
```

Task 8이 읽을 컬럼은 `pronunciation_attempts`의 `target_form`·`spoken_form`·`outcome`·
`signal_source`·`pattern_id`. 패턴의 `frequency`는 **발음 시도 수**다(문법의 occurrence 수와
다른 규약 — `docs/database-schema.md:111`).
**규칙은 서비스가 소유하고 세션은 배선만 한다**(§3.1a) — 새 감지기를 `session.py`에 박지 말고
`note_transcript` 안에 넣는다.

---

## 이 갈래의 문서 지도

| 문서 | 역할 |
|---|---|
| **`TASKS.md`** | **전체 작업·진행 상태의 정본.** 무엇이 남았나 |
| `docs/PRD.md` (v1.1) §10·§11 | 요구사항 정본 |
| `docs/design/2026-08-27-pronunciation-echo-{design,plan}.md` | §10 **결정과 근거의 정본**(§3.1a 소유 경계·§3.2 생명주기·§4.3 패턴·§6.1 제약) + 9태스크 계획(머리말에 정정표) |
| `docs/design/2026-08-25-learning-coach-agent-design.md` | §11 설계 (정본 승격, 2슬라이스) |
| `docs/ops/pitfalls.md` | 실측된 함정 H-A~H-Q |
| `tests/harness/runs/2026-08-27-P-tooluse-spike/` · `docs/storyboard.html` | tool use 실증 원자료 · 03b 발음 시범 화면 |
