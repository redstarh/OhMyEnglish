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
> | 실측된 함정 | `docs/ops/pitfalls.md` (H-A~H-X, 24건) |
> | 하네스 차수 | `tests/harness/runs/ROUNDS.md` · `tests/harness/README.md` |
> | **실물 마이크 절차·결과** | **`tests/harness/runs/2026-09-01-mic-1.md`** ← 마이크를 쓸 거면 이것부터 |
> | 5개 층 일관성 점검 | `docs/consistency-audit-2026-09-01.html` |
> | 남은 작업 요약(공유용) | `docs/remaining-work-2026-08-31.html` — **스냅샷이다.** 머리의 갱신 안내를 먼저 읽어라 |
>
> 최종 갱신 **2026-09-02** · 기준 커밋 **HEAD ≥ `342bc97`** · 브랜치 `design/first-vertical-slice`
> **이 파일이 유일한 handoff다.** 이전 판은 `handoff/backup/2026-08-30/`.

---

## 지금 어디까지 왔나

**첫 수직 슬라이스가 실물 음성으로 관통했고, 거기서 나온 오탐 결함(I-1)을 고쳤다.**
2026-09-01에 **실물 마이크 1회를 실제로 돌려** 발음 배지·판정 기록·패턴 연결 동작을 확인했고,
같은 날 **I-1(조각 발화 병합)을 구현 완료**했다. **§10은 9태스크 중 8.5개 완료**
(남은 것은 Task 9 = 하네스 P9~P12). 캡틴 결정 후속 8건 중 **G-1·G-3·G-4 완료**.
**§11(추천 학습 루틴)은 설계만 끝났고 코드가 0줄이다.**

| 되는 것 | 안 되는 것 |
|---|---|
| 실시간 음성 대화·전사문 영속 저장 | **§11 추천 루틴 전체** (C절) |
| **조각 발화를 턴 경계까지 모아서 분석** (I-1 완료) | **복습 큐·주기 갱신** — 컬럼은 있고 앱 참조 0곳 |
| **잃어버린 묶음을 워커가 회복** (끝난 세션만 스윕) | **`active` 고아 세션은 회복 못 한다** — 종료 기록 전에 죽으면 영구히 안 걷힌다 (**I-4**, 캡틴 결정 대기) |
| **세션 화면 발음 배지 + 결과 화면 발음 카드** (Task 8 완료) | 음성 명령 제어 — **3단계로 이연**(설계서가 명시) |
| 문법 오류 분석 → 패턴 병합 → 결과 화면 상위 교정 | `pending_learning_utterances`는 **앱 호출처 0곳** (죽은 함수 후보 — G-7 계열) |
| 발음 시범·재발화 판정 기록 · 종료 수렴 · 패턴 연결 | |

✅ **배지는 이제 뜬다.** 이전 판의 "배지가 없는 것이 정상"이라는 서술은 **폐기됐다** —
nova 세션에서 발음 표시가 없으면 그때는 조사할 일이다.
✅ **실물 Nova 왕복 1회 완료.** "왕복 0회" 서술도 폐기됐다. 남은 것은 tool 스키마 대조뿐(Task 9).
✅ **"조각 발화가 오탐 패턴을 만든다 — 완화만 했고 미해소"는 폐기됐다.** 분석 job은 이제
저장이 아니라 **턴 경계**에서 걸린다. 보존해 둔 실물 1회 데이터에 새 SQL을 읽기 전용으로 걸어
확인했다: `"i'm going to"` + `"have a meeting"` → `"i'm going to have a meeting"`으로 합쳐지고,
그 세션의 job이 **18건 → 14건**(쪼개진 4건이 묶음으로 흡수)이 된다. 자세한 것은 `TASKS.md` I-1.

---

## 다음 한 걸음

### 실물 마이크 2회 — I-1이 정말 오탐을 없앴는지 대조한다

**착수 전 필수 0건.** I-1은 구현·게이트 통과까지 끝났지만 **실물 음성으로 확인한 것은 아니다** —
스텁·단위 테스트와 보존 데이터에 대한 읽기 전용 재현까지가 지금의 증거다.

절차·판별 3개는 `tests/harness/runs/2026-09-01-mic-1.md` §1이 소유한다. **2회에서 볼 것 3개**:
1. 문장 중간에서 쪼개진 조각이 여전히 생기는가(생겨도 정상 — `LOW` 완화는 조각을 0으로 못 만든다).
   중요한 건 **조각이 생겨도 오탐 패턴이 안 생기는 것**이다.
2. 새로 생긴 `error_patterns`에 `verb_form_missing_subject` 계열이 **없어야** 한다.
3. job 수가 사용자 learning 발화 수보다 **적어야** 한다(묶음으로 흡수된 만큼). 1회 데이터에서는
   18발화 → 14 job이었다.

⚠️ Nova를 건드리면 `spike_nova_protocol.py --wav p1a.wav`로 자격증명 생존을 먼저 확인한다(**과금된다**).

### 그다음 순서 권고

1. **§11 착수 전 문서 정정 2건** (D-5·D-6, `TASKS.md` C절 착수 전 필수) — 코드 변경 0, 30분.
   `impact_score`·`suggested_contexts`는 **컬럼이 아예 없는데** 설계서 4·2개 파일이 전제한다.
2. **G-2**(문서 한 줄) · **G-7**(죽은 함수 삭제 — `pending_learning_utterances`도 후보에 올랐다) ·
   **G-8**((나) 확정, 필터 한 줄) — 짧고 선행 없음.
3. **§11 슬라이스 1** — 착수 전 필수는 **H-S**(달력 날짜를 `current_date`로 구하지 않는다).
4. **Task 9 · 하네스 5차수** — I-1이 해소됐으므로 **이제 열어도 된다**. 이전 판의 "5차수를 I-1
   수정보다 먼저 열지 않는다"는 제약은 **해제됐다**. 단 5차수는 I-1 **이후** 코드로 돌려야 한다.
   `inject_errors.py`가 문장마다 턴을 닫도록 바뀐 것을 먼저 읽어라(모듈 docstring의 ⚠️).

---

## 실측값 (2026-09-02, 이 절을 쓴 턴에 직접 실행)

```bash
cd app/backend                                    # 게이트는 이 cwd에서만 판정한다 (함정 H-A)
.venv/bin/pytest -q                               # 366 passed  (부분 실행은 -c pyproject.toml — 함정 H-W)
# ⚠️ 게이트를 `| tail`로 파이프하지 마라 — exit code가 tail의 것이 되어 실패가 && 체인을
#    통과한다(실측 사고 1건). ⚠️ 리뷰를 subagent에 위임한 동안 게이트를 겹쳐 돌리지 마라 —
#    테스트 DB는 실행마다 DROP/CREATE되는 공유 자원이다 (함정 H-X).
.venv/bin/ruff check . && .venv/bin/ruff format --check .   # passed / 27 files formatted
ty check                                          # All checks passed!
.venv/bin/ruff check ../../tests ../../scripts    # Found 6 errors  (베이스라인, 게이트 밖)
.venv/bin/ruff format --check ../../tests         # 4 files         (베이스라인, 함정 H-L)
cd ../frontend && npx tsc --noEmit && npx eslint app lib   # 둘 다 exit 0
```

| 항목 | 값 |
|---|---|
| 테스트 | **366 passed**, skip/xfail 0 (241 → 312 → 327 → 333 → 347 → 348 → 366) |
| I-1 순증 | 새 테스트 **19건** − 폐기 **1건** = +18. 폐기 근거는 `TASKS.md` I-1 (**되살리지 말 것**) |
| DB | `:5432` homebrew **17.9** · 역할 `ohmy`에 **`TimeZone=UTC` 고정**. 인스턴스 기본값은 `Asia/Seoul`이라 이게 풀리면 함정 **H-S**가 안 보인다 |
| dev DB 행 | 세션 **3** · 발화 **51** · 패턴 **4** · occurrence **8** · job **21** · 발음시도 **3** |
| 오탐 정리 | 2026-09-01 캡틴 지시로 오탐 패턴 2개 삭제(패턴 6→4 · occ 15→8). **전사문·세션·job은 보존** — I-1 수정 후 같은 좌표로 재대조하기 위해서다 |
| 서버 | `:8002`·`:3000` **내려둠**. `:8000`은 StockAgent(남의 것) |
| 미커밋 | `.claude/` · `.mcp.json` · `backlog/`(untracked) — **커밋하지도 지우지도 마라** |

⚠️ `pronunciation_an_as_a`는 freq 1 · occurrence 0인데 **정상**이다 — 발음 패턴은 **시도 수**를
센다(`docs/database-schema.md:111`). 버그로 오인하지 마라.

---

## 다음 세션 진입 절차

1. 이 파일 → **`tests/harness/runs/2026-09-01-mic-1.md` §1**(다음 걸음이 마이크 2회다) →
   I-1이 무엇을 바꿨는지 알아야 하면 **`TASKS.md` I-1**. `TASKS.md` 전체를 읽지 않는다.
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
| 1 | HEAD | **`HEAD ≥ 342bc97`** — 반드시 `≥`로 읽는다(함정 **H-P**). 이 문서를 담은 커밋 자신이 HEAD를 옮긴다 |
| 2 | 다음 한 걸음 | **실물 마이크 2회 — I-1 오탐 해소 대조**. I-1 구현은 완료(`TASKS.md` I-1) |
| 3 | 게이트 | **366 passed** · ruff·format(27파일)·ty clean · `tests/**` 베이스라인 **6 errors·4 files** · 프론트 `tsc`·`eslint` exit 0 |
| 4 | 착수 전 필수 | **0건.** 마이크 2회도 §11 문서 정정도 선행 조건이 없다 (§11 슬라이스 1로 가려면 D-5·D-6이 선행) |

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
