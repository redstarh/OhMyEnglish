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
> | 실측된 함정 | `docs/ops/pitfalls.md` (H-A~H-V, 22건) |
> | 하네스 차수 | `tests/harness/runs/ROUNDS.md` · `tests/harness/README.md` |
> | **실물 마이크 절차·결과** | **`tests/harness/runs/2026-09-01-mic-1.md`** ← 마이크를 쓸 거면 이것부터 |
> | 5개 층 일관성 점검 | `docs/consistency-audit-2026-09-01.html` |
> | 남은 작업 요약(공유용) | `docs/remaining-work-2026-08-31.html` — **스냅샷이다.** 머리의 갱신 안내를 먼저 읽어라 |
>
> 최종 갱신 **2026-09-01** · 기준 커밋 **HEAD ≥ `0885439`** · 브랜치 `design/first-vertical-slice`
> **이 파일이 유일한 handoff다.** 이전 판은 `handoff/backup/2026-08-30/`.

---

## 지금 어디까지 왔나

**첫 수직 슬라이스가 실물 음성으로 관통했다.** 2026-09-01에 **실물 마이크 1회를 실제로 돌려**
발음 배지·판정 기록·패턴 연결이 동작하는 것을 확인했다. **§10은 9태스크 중 8.5개 완료**
(남은 것은 Task 9 = 하네스 P9~P12). 캡틴 결정 후속 8건 중 **G-1·G-3·G-4 완료**.
**§11(추천 학습 루틴)은 설계만 끝났고 코드가 0줄이다.**

| 되는 것 | 안 되는 것 |
|---|---|
| 실시간 음성 대화·전사문 영속 저장 | **조각 발화가 오탐 패턴을 만든다** (**I-1** — 완화만 했고 미해소) |
| **세션 화면 발음 배지 + 결과 화면 발음 카드** (Task 8 완료) | **§11 추천 루틴 전체** (C절) |
| 문법 오류 분석 → 패턴 병합 → 결과 화면 상위 교정 | **복습 큐·주기 갱신** — 컬럼은 있고 앱 참조 0곳 |
| 발음 시범·재발화 판정 기록 · 종료 수렴 · 패턴 연결 | 음성 명령 제어 — **3단계로 이연**(설계서가 명시) |

✅ **배지는 이제 뜬다.** 이전 판의 "배지가 없는 것이 정상"이라는 서술은 **폐기됐다** —
nova 세션에서 발음 표시가 없으면 그때는 조사할 일이다.
✅ **실물 Nova 왕복 1회 완료.** "왕복 0회" 서술도 폐기됐다. 남은 것은 tool 스키마 대조뿐(Task 9).

---

## 다음 한 걸음

### I-1 — 조각 발화 병합 ((가) 확정, 구현만 남았다)

**착수 가능하다. 착수 전 필수 0건.** 캡틴이 2026-09-01에 **(가) 턴 경계까지 모아서 분석**으로
확정했고, **접점 4곳과 T0(red) 계획 5건이 좌표까지 `TASKS.md` I-1에 있다** — 여기서 재서술하지 않는다.

한 줄 원인: `endpointing` 임계가 **약 480ms**라서 다음 말을 고르는 1초가 발화 종료로 읽히고,
`utterances.py:140`이 조각마다 분석 job을 걸어 **occurrence 13건 중 7건이 오탐**이었다.
**화면 표시는 그대로 두고 분석 입력만 합친다.**

⚠️ **"고칠 자리 한 곳"이 아니다.** 저장 시점에는 그 발화가 마지막인지 알 수 없어 **턴 종료 신호**가
필요하다. 접점은 `utterances.py` · flush 함수 신설 · `session.py` **두 지점** ·
`analysis.py` `_LOAD_INPUT_SQL`. **`session.py`의 세션 종료 쪽 flush를 빠뜨리면 마지막 사용자
묶음이 영원히 분석되지 않는다** — 대화가 사용자 발화로 끝나는 것이 정상이다.

⚠️ **회귀 주의**: E계층은 발화 1건 = job 1건을 기대한다. E1(문장 5개)의 job 수가 **5 → 1로 줄어든다** —
`inject_errors.py`의 `wait_for_jobs` 단정을 함께 고친다.

⚠️ **5차수를 이 수정보다 먼저 열지 않는다** — 오탐이 섞인 데이터로 판정하면 그 판정이 오염된다.

### 그다음 순서 권고

1. **§11 착수 전 문서 정정 2건** (D-5·D-6, `TASKS.md` C절 착수 전 필수) — 코드 변경 0, 30분.
   `impact_score`·`suggested_contexts`는 **컬럼이 아예 없는데** 설계서 4·2개 파일이 전제한다.
2. **G-2**(문서 한 줄) · **G-7**(죽은 함수 삭제) · **G-8**((나) 확정, 필터 한 줄) — 짧고 선행 없음.
3. **§11 슬라이스 1** — 착수 전 필수는 **H-S**(달력 날짜를 `current_date`로 구하지 않는다).
4. **Task 9 · 하네스 5차수** — I-1 수정 후에.

---

## 실측값 (2026-09-01, 이 절을 쓴 턴에 직접 실행)

```bash
cd app/backend                                    # 게이트는 이 cwd에서만 판정한다 (함정 H-A)
.venv/bin/pytest -q                               # 348 passed
.venv/bin/ruff check . && .venv/bin/ruff format --check .   # passed / 27 files formatted
ty check                                          # All checks passed!
.venv/bin/ruff check ../../tests ../../scripts    # Found 6 errors  (베이스라인, 게이트 밖)
.venv/bin/ruff format --check ../../tests         # 4 files         (베이스라인, 함정 H-L)
cd ../frontend && npx tsc --noEmit && npx eslint app lib   # 둘 다 exit 0
```

| 항목 | 값 |
|---|---|
| 테스트 | **348 passed**, skip/xfail 0 (241 → 312 → 327 → 333 → 347 → 348) |
| DB | `:5432` homebrew **17.9** · 역할 `ohmy`에 **`TimeZone=UTC` 고정**. 인스턴스 기본값은 `Asia/Seoul`이라 이게 풀리면 함정 **H-S**가 안 보인다 |
| dev DB 행 | 세션 **3** · 발화 **51** · 패턴 **4** · occurrence **8** · job **21** · 발음시도 **3** |
| 오탐 정리 | 2026-09-01 캡틴 지시로 오탐 패턴 2개 삭제(패턴 6→4 · occ 15→8). **전사문·세션·job은 보존** — I-1 수정 후 같은 좌표로 재대조하기 위해서다 |
| 서버 | `:8002`·`:3000` **내려둠**. `:8000`은 StockAgent(남의 것) |
| 미커밋 | `.claude/` · `.mcp.json` · `backlog/`(untracked) — **커밋하지도 지우지도 마라** |

⚠️ `pronunciation_an_as_a`는 freq 1 · occurrence 0인데 **정상**이다 — 발음 패턴은 **시도 수**를
센다(`docs/database-schema.md:111`). 버그로 오인하지 마라.

---

## 다음 세션 진입 절차

1. 이 파일 → **`TASKS.md` I-1** → 필요할 때만 계획서. `TASKS.md` 전체를 읽지 않는다.
2. 게이트를 `app/backend` cwd에서 돌려 위 실측값과 대조한다. **다르면 그 차이를 먼저 설명한다.**
   ⚠️ **게이트 전에 DB가 떠 있는지 본다** — `brew services list | grep postgresql@17`.
   안 떠 있으면 `brew services start postgresql@17`. DB가 없으면 `pytest`가
   **192 passed · 155 errors**로 끝나는데 **회귀가 아니라 연결 거부다**(함정 **H-T**) —
   errors가 100건 넘게 한꺼번에 나면 코드보다 연결을 먼저 의심한다.
   ⚠️ 그 인스턴스는 **StockAgent와 공유**한다 — 인스턴스 재시작·`ALTER SYSTEM` 금지.
   ⚠️ 어느 서버인지는 `show server_version`으로 본다(**17.9**=homebrew / 16.15=podman 폴백).
   `inet_server_port()`로는 판별할 수 없다(함정 **H-V**).
3. **마이크를 쓸 거면 `tests/harness/runs/2026-09-01-mic-1.md` §1을 먼저 읽는다** —
   절차·판별 3개·개입을 거는 방법이 거기 있다. Nova를 건드리면
   `spike_nova_protocol.py --wav p1a.wav`로 자격증명 생존을 먼저 확인한다(**과금된다**).
4. 계획서를 열면 **머리말의 "구현 후 정정" 표를 먼저 읽는다** (함정 **H-N**).
5. **태스크 상태가 바뀌면 `TASKS.md`를, 다음 한 걸음이 바뀌면 이 파일을** 갱신한다 —
   별도 지시를 기다리지 않는다.

---

## 인계 기록

- **2026-08-28** `claude_air_3-14` → 같은 창의 새 컨텍스트: ✅ 4/4 일치.
- **2026-08-30** `claude_air_3-14` → `claude_air_3-15`: ✅ 4/4 일치. 그 세션이 기준 해시 오류를
  잡아냈다 — 인계 확인이 실제로 작동한 사례다(함정 **H-R**).

### 다음 세션이 대조할 기준값 (이 절을 쓴 턴에 직접 실행해 얻었다)

| # | 지표 | 값 |
|--:|---|---|
| 1 | HEAD | **`HEAD ≥ 0885439`** — 반드시 `≥`로 읽는다(함정 **H-P**). 이 문서를 담은 커밋 자신이 HEAD를 옮긴다 |
| 2 | 다음 한 걸음 | **I-1 — 조각 발화 병합** ((가) 확정, 구현만 남았다). 접점 4곳·T0 5건은 `TASKS.md` I-1 |
| 3 | 게이트 | **348 passed** · ruff·format(27파일)·ty clean · `tests/**` 베이스라인 **6 errors·4 files** · 프론트 `tsc`·`eslint` exit 0 |
| 4 | 착수 전 필수 | **I-1은 0건 — 바로 착수한다.** 단 §11로 가려면 문서 정정 2건(D-5·D-6)이 선행이다 |

인계 확인은 새 세션이 **직접 돌려 얻은** 4개가 위 값과 일치하는 것이다 — "읽었다"는 지표가 아니다.
절차는 `~/.claude/rules/session-handover.md`, 함정은 `pitfalls.md` **H-P**·**H-Q**.

---

## 발음 서비스 계약 (§10을 다시 건드릴 때)

정본은 설계서 §3.1a·§3.2·§4.3이다. 계획서 본문 서술은 낡았다.

```python
from app.services.pronunciation import (
    link_pattern,         # 시도 1건 → error_patterns. 조건(incorrect+target_sound)은 SQL이 갖는다
    note_transcript,      # 학습자 전사문을 보고 신호가 보이면 기록 (감지기 묶음)
    record_attempt,       # Nova tool 생명주기 — **자기 트랜잭션을 연다**
    record_signal,        # 단발 관측 1건 — outcome에 'pending'·'incorrect'가 없다
    resolve_dangling,     # 종료 수렴 + 패턴 연결 — 이것도 자기 트랜잭션을 연다
)
```

**규칙은 서비스가 소유하고 세션은 배선만 한다**(§3.1a) — 새 감지기를 `session.py`에 박지 말고
`note_transcript` 안에 넣는다.

⚠️ **`target_sound` 값역이 계획과 다르다** — 실측 키는 `am_as_i_m`·`w_as_vw`·`an_as_a`로
**음소 치환이 하나도 없다**(표본 3건). §10이 의도한 "발음"과 어긋나는지는 `TASKS.md` **I-2**.
