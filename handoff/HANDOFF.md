# Handoff — OhMyEnglish (단일 연속성 문서)

> **이 파일에는 두 가지만 담는다: 지금 어디까지 왔는가 / 다음 한 걸음이 무엇인가.**
> 그 밖의 것은 각 정본이 소유하고 여기서는 **가리키기만** 한다 — 복사하면 한쪽이 낡는다.
>
> | 찾는 것 | 어디 |
> |---|---|
> | 전체 작업·진행 상태·미결정 | **`TASKS.md`** (상태의 정본) |
> | 요구사항 | `docs/PRD.md` v1.1 |
> | 결정과 근거 | `docs/design/**` |
> | 실행 방법·포트·게이트 | **`docs/ops/local-run.md`** |
> | 실측된 함정 | `docs/ops/pitfalls.md` (H-A~H-Q) |
> | 하네스 차수·시나리오 | `tests/harness/runs/ROUNDS.md` · `tests/harness/README.md` |
> | 한 장 요약(공유용) | `docs/status-report-2026-08-29.html` |
>
> 최종 갱신 **2026-08-30** · 기준 커밋 **HEAD ≥ `b3a37b9`** · 브랜치 `design/first-vertical-slice`
> **이 파일이 유일한 handoff다.** 2026-08-30에 갈래별 4개를 하나로 합쳤다(이전 판은
> `handoff/backup/2026-08-30/`).

---

## 지금 어디까지 왔나

**첫 수직 슬라이스가 돌아간다** — 음성 세션 → 전사 저장 → 비동기 문법 분석 → 결과 화면.
**요구사항 v1.1 §10(발음 시범·재발화)은 9태스크 중 7개 완료**, §11(추천 학습 루틴)은 설계만
끝났고 코드가 0줄이다.

`VOICE_ADAPTER=nova`로 띄우면 Nova가 발음을 교정하고, 판정이 기록되고, 약점 패턴까지 쌓인다.

| 되는 것 | 안 되는 것 |
|---|---|
| 실시간 음성 대화·전사문 영속 저장 | **발음 화면·결과 카드** — 프론트가 `pronunciation` 프레임을 모른다 (A절 Task 8) |
| 문법 오류 분석 → 패턴 병합 → 결과 화면 상위 교정 | **§11 추천 루틴 전체** (C절) |
| 발음 시범·재발화 판정 기록, 한글 전사 신호, 종료 수렴 | **복습 큐·주기 갱신** (R11-6) |
| 발음 오류 → `error_patterns` 연결 (판정·수렴 **경로 불문**) | 되묻기 문구 감지 — **만들지 않는다**(결정) |

⚠️ **배지가 없는 것은 정상이다.** nova로 띄웠는데 화면에 발음 표시가 없다고 정상인
어댑터·세션을 디버깅하지 마라 — 프론트가 아직 그 프레임을 모른다.
⚠️ **실물 Nova 왕복은 0회다.** 발음 기능은 단위·통합 테스트만 통과했다 (`TASKS.md` A-3).

---

## 다음 한 걸음

### A절 Task 8 — 결과 화면 발음 카드 (백엔드 + 프론트)

계획: `docs/design/2026-08-27-pronunciation-echo-plan.md:1344`
**차단 없음.** B-1(판정↔시범 상관키)은 최신순 수용으로 결정됐다.

착수 시 챙길 2건은 `TASKS.md` **A-2**에 있다 — ① 응답에 `signal_source`를 함께 싣는다
(신호 행의 `target_form`은 문장이 아니라 설명 문구라서 구분 없이 렌더하면 "이렇게
발음하세요"로 보인다) ② `incorrect`인데 `spoken_form`이 null인 행은 **대답 없이 끝난 시도**다.

⚠️ 패턴의 `target_form`은 이제 `th_as_s` 같은 **기계 키**다(일반형). 화면에 그대로 렌더하면
학습자가 그 키를 본다 — 표시 문구는 Task 8이 `category`와 함께 정한다.

### 그다음 — 캡틴 결정에서 생긴 작업 8건

2026-08-30에 B-1~B-10이 **전건 종결**됐고, 거기서 나온 작업이 `TASKS.md` **G절 G-1~G-8**이다.
어느 것도 착수하지 않았다. 착수 순서에 영향을 주는 것만 적으면:

- **G-8**(`frequency` 이중 writer)은 **착수 전 캡틴에게 해석을 확인한다** — 스키마가 걸리고
  캡틴 문구가 두 안 중 어느 쪽인지 갈린다. 후보와 근거는 G절 끝에 있다.
- **G-4**(실물 마이크 요청)는 **내가 요청할 차례다**("요청하면 진행하겠슴"). G-1·G-3으로
  지시문을 확정한 뒤 요청하면 한 세션에 마이크 1회 + 픽스처 보정을 함께 닫는다.
- **G-1·G-5**는 같은 통로(§11 지시문 가변부)를 쓴다 — 따로 만들지 마라.

---

## 실측값 (2026-08-30, 이 절을 쓴 턴에 직접 실행)

```bash
cd app/backend                                    # 게이트는 이 cwd에서만 판정한다 (함정 H-A)
.venv/bin/pytest -q                               # 327 passed
.venv/bin/ruff check . && .venv/bin/ruff format --check .   # passed / 27 files formatted
ty check                                          # All checks passed!
.venv/bin/ruff check ../../tests ../../scripts    # Found 6 errors  (베이스라인, 게이트 밖)
.venv/bin/ruff format --check ../../tests         # 4 files         (베이스라인, 함정 H-L)
```

| 항목 | 값 |
|---|---|
| 테스트 | **327 passed**, skip/xfail 0 (v1.1 착수 전 241 → 312 → 327) |
| dev DB 마이그레이션 | **4개** — 001 · 003 · 004 · 005 (`schema_migrations`가 파일명으로 추적, 멱등) |
| dev DB 행 | 세션 2 · 발화 6 · 패턴 1 · occurrence 2 · job 3 · `pronunciation_attempts` **0** · 발음 패턴 **0** |
| 미커밋 | `.claude/`(untracked) — **커밋하지 말고 지우지도 마라**(B-9 결정) |

⚠️ **발음 데이터가 dev DB에 0건이다.** 통합 테스트는 롤백 트랜잭션이라 흔적을 남기지 않는다 —
화면에서 발음 카드를 보려면 실물 왕복이 먼저다.

---

## 다음 세션 진입 절차

1. 이 파일 → **`TASKS.md`의 해당 절 표 한 줄** → 필요할 때만 계획서. `TASKS.md` 전체를 읽지 않는다.
2. 게이트를 `app/backend` cwd에서 돌려 위 실측값과 대조한다. **다르면 그 차이를 먼저 설명한다.**
3. Nova를 건드리면 `spike_nova_protocol.py --wav p1a.wav`로 자격증명 생존을 먼저 확인한다.
4. 계획서를 열면 **머리말의 "구현 후 정정" 표를 먼저 읽는다** — 본문 코드 블록 5건이 낡았고,
   테스트 헬퍼 이름은 추측이라 실재하지 않는다(함정 H-N).
5. **태스크 상태가 바뀌면 `TASKS.md`를, 다음 한 걸음이 바뀌면 이 파일을** 갱신한다 —
   별도 지시를 기다리지 않는다.

---

## 발음 서비스 계약 (Task 8이 바로 쓴다)

계획서 본문 서술은 낡았다. 실제 계약은 이것이고 정본은 설계서 §3.1a·§3.2·§4.3이다.

```python
from app.services.pronunciation import (
    link_pattern,         # 시도 1건 → error_patterns. 조건(incorrect+target_sound)은 SQL이 갖는다
    note_transcript,      # 학습자 전사문을 보고 신호가 보이면 기록 (감지기 묶음)
    record_attempt,       # Nova tool 생명주기 — **자기 트랜잭션을 연다**. 패턴 연결까지 한 단위
    record_signal,        # 단발 관측 1건 — outcome에 'pending'·'incorrect'가 없다
    resolve_dangling,     # 종료 수렴 + 패턴 연결 — 이것도 자기 트랜잭션을 연다(savepoint 합성)
)
from app.services.sessions import end_session   # conn을 받는 원시 함수
```

Task 8이 읽을 컬럼: `pronunciation_attempts`의 `target_form`·`spoken_form`·`outcome`·
`signal_source`·`pattern_id`. 패턴의 `frequency`는 **발음 시도 수**다(문법의 occurrence 수와
다른 규약 — `docs/database-schema.md:111`).
**규칙은 서비스가 소유하고 세션은 배선만 한다**(§3.1a) — 새 감지기를 `session.py`에 박지 말고
`note_transcript` 안에 넣는다.

---

## 인계 기록

- **2026-08-28** `claude_air_3-14` → 같은 창의 새 컨텍스트: ✅ **4/4 일치**(HEAD만 docs 커밋 1건 차이).
  3-15는 빈 셸이라 쓰이지 않고 정리됨.

인계 확인은 새 세션이 **직접 돌려 얻은** 4개(HEAD · 다음 한 걸음 · 게이트 실측 · 착수 전 필수
건수)가 위 실측값과 일치하는 것이다 — "읽었다"는 지표가 아니다. 절차는
`~/.claude/rules/session-handover.md`, 함정은 `pitfalls.md` **H-P**·**H-Q**.
