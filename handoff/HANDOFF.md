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
> | 실측된 함정 | `docs/ops/pitfalls.md` (H-A~H-V) |
> | 하네스 차수·시나리오 | `tests/harness/runs/ROUNDS.md` · `tests/harness/README.md` |
> | 한 장 요약(공유용) | `docs/status-report-2026-08-29.html` |
> | **남은 작업만 모은 보고(공유용)** | `docs/remaining-work-2026-08-31.html` — 상태 정본은 아니다, `TASKS.md`를 따른다 |
>
> 최종 갱신 **2026-09-01** · 기준 커밋 **HEAD ≥ `d34e1b7`** · 브랜치 `design/first-vertical-slice`
> **이 파일이 유일한 handoff다.** 2026-08-30에 갈래별 4개를 하나로 합쳤다(이전 판은
> `handoff/backup/2026-08-30/`).

---

## 지금 어디까지 왔나

**첫 수직 슬라이스가 돌아간다** — 음성 세션 → 전사 저장 → 비동기 문법 분석 → 결과 화면.
**요구사항 v1.1 §10은 9태스크 중 8.5개 완료** — 2026-09-01에 **Task 8이 닫혔다**(세션 화면 배지
A-5까지). 남은 것은 Task 9(하네스 P9~P12)다. 캡틴 결정 후속 8건 중 **G-1·G-3·G-4 완료**.
§11(추천 학습 루틴)은 설계만 끝났고 코드가 0줄이다.

`VOICE_ADAPTER=nova`로 띄우면 Nova가 발음을 교정하고, 판정이 기록되고, 약점 패턴까지 쌓인다.

**이 세션에서 닫힌 것 2개** (2026-08-30):
- **캡틴 결정 B-1~B-10 전건 종결.** 거기서 나온 작업 8건이 `TASKS.md` **G절**이다 — 아직 착수 0.
- **En-Coach와 DB 공유 구성 완료.** 같은 DB(`ohmyenglish`) + 스키마 분리. En-Coach가 규칙을
  지켜 실제로 붙었다(실측: `en_coach` 스키마에 `ec_*` 9개 + 자기 `schema_migrations`,
  우리 `public`에 `ec_` 표 0개). 규칙 정본은 `docs/ops/shared-database-naming-rules.md`.

| 되는 것 | 안 되는 것 |
|---|---|
| 실시간 음성 대화·전사문 영속 저장 | **조각 발화가 오탐 패턴을 만든다** (I절 **I-1** — 완화만 했고 미해소) |
| **세션 화면 발음 배지 + 결과 화면 발음 카드** (Task 8 완료, `9b7985f` + A-5) | — |
| 문법 오류 분석 → 패턴 병합 → 결과 화면 상위 교정 | **§11 추천 루틴 전체** (C절) |
| 발음 시범·재발화 판정 기록, 한글 전사 신호, 종료 수렴 | **복습 큐·주기 갱신** (R11-6) |
| 발음 오류 → `error_patterns` 연결 (판정·수렴 **경로 불문**) | 되묻기 문구 감지 — **만들지 않는다**(결정) |

✅ **배지는 이제 뜬다** (2026-09-01 캡틴이 눈으로 확인). 이전 판의 "배지가 없는 것이 정상"이라는
서술은 **폐기됐다** — nova 세션에서 발음 표시가 없으면 그때는 조사할 일이다.
⚠️ **실물 Nova 왕복은 1회 했다**(2026-09-01, 세션 `bbfc3908`). 판정 품질은 "교정을 잘 해줬다"는
캡틴 관측이 있으나 **`target_sound` 값역이 계획과 다르다** — 관측 키는 `am_as_i_m`·`w_as_vw`·
`an_as_a`로 음소 치환이 하나도 없다(`TASKS.md` **I-2**, 표본 3건이라 재검토 대상).
⚠️ **그 세션이 오탐 패턴 2개를 남겼다** — I-1.

---

## 다음 한 걸음

### I-1 — 조각 발화가 오탐 패턴을 만든다 (구조적 해소 · 착수 전 캡틴 결정)

**2026-09-01 실물 마이크 1회(G-4)에서 관측됐다.** Task 8·A-5는 **완료**됐고(캡틴이 배지를
눈으로 확인) 이 결함이 그 세션의 산출물이다. 상세·후보·수치는 `TASKS.md` **I-1**이 소유한다.

한 줄 요약: `endpointing`이 **1.05~2.54초 침묵**에 문장을 끊어 내 발화 18건 중 4건이 쪼개졌고,
`services/utterances.py:140`이 조각마다 분석 job을 걸어 **occurrence 13건 중 7건이 오탐**이 됐다.
패턴 `verb_form_missing_subject`(freq 4)·`verb_form_missing_object`(freq 2)는 **100% 조각산**이다.

`NOVA_ENDPOINTING_SENSITIVITY=LOW`를 넣어 **완화**했지만 3단뿐이라 해소가 아니다.
결정할 것은 **(가) 턴 경계까지 모아 분석**(하네스 N8이 예정) vs **(나) 조각 제외**다.
⚠️ **오탐 패턴 2개가 dev DB에 살아 있다** — 지울지도 캡틴 결정이다(두면 다음 세션 프롬프트에 실린다).

📌 배지 구현의 상세·결정 이력은 `TASKS.md` **A-5**가 소유한다 (여기서 재서술하지 않는다 — 3층 분리 규약).

### 그다음 — 캡틴 결정에서 생긴 작업 8건 중 남은 6건

`TASKS.md` **G절**. **G-1·G-3은 `efc6264`로 완료.** 착수 순서에 영향을 주는 것만 적으면:

- **G-4**(실물 마이크 요청)는 **내가 요청할 차례다**("요청하면 진행하겠슴"). 선행(지시문)이
  끝났으니 **A-5 배지를 올린 직후 요청**하면 한 세션에 배지·판정 품질·픽스처를 함께 닫는다.
- **G-8**(`frequency` 이중 writer)은 **착수 전 캡틴에게 해석을 확인한다** — 스키마가 걸리고
  캡틴 문구가 두 안 중 어느 쪽인지 갈린다. 후보와 근거는 G절 끝에 있다.
- **G-2·G-7**은 선행이 없고 짧다(문서 한 줄 · 죽은 함수 삭제) — 아무 때나 끼워 넣을 수 있다.
- **G-5**는 위 📌 때문에 **기각안을 다시 검토**해야 한다.

---

## 실측값 (2026-08-30, 이 절을 쓴 턴에 직접 실행)

```bash
cd app/backend                                    # 게이트는 이 cwd에서만 판정한다 (함정 H-A)
.venv/bin/pytest -q                               # 348 passed
.venv/bin/ruff check . && .venv/bin/ruff format --check .   # passed / 27 files formatted
ty check                                          # All checks passed!
.venv/bin/ruff check ../../tests ../../scripts    # Found 6 errors  (베이스라인, 게이트 밖)
.venv/bin/ruff format --check ../../tests         # 4 files         (베이스라인, 함정 H-L)
cd ../frontend && npx tsc --noEmit && npx eslint app lib   # 둘 다 무출력(clean)
```

| 항목 | 값 |
|---|---|
| 테스트 | **348 passed**, skip/xfail 0 (241 → 312 → 327 → 333 → 347 → 348). +1은 endpointing 노브가 `sessionStart`에 실리는지 보는 테스트 — `.env`를 LOW로 튜닝했을 때 그 성질을 지키는 테스트가 없어 실패를 회귀로 오인했다 |
| 공유 DB | **⚠️ 2026-08-31에 호스트가 바뀌었다: podman :5433 → homebrew `postgresql@17` :5432** (함정 H-T). 같은 날 실측: `en_coach` 스키마에 표 **14개**(`ec_*` 13 + 추적표) — 8-30에 기록한 10개에서 늘었는데 **불일치가 아니라 En-Coach의 진도다**. 우리 `public`은 13개(우리 10 + 하네스 3), `ec_` 오염 **0**. 이관 후 행 수는 전부 동일(세션 2 · 발화 6 · 패턴 1 · occurrence 2 · job 3 · 사용자 1 · 시나리오 3) |
| DB 타임존 | 역할 `ohmy`에 **`TimeZone=UTC` 고정**. :5432 인스턴스 기본값은 `Asia/Seoul`이라 그대로 쓰면 **함정 H-S가 안 보인다**. `ohmyenglish_test`도 UTC로 확인했다. 인스턴스 기본값은 건드리지 않았다(StockAgent 공유) |
| dev DB 마이그레이션 | **4개** — 001 · 003 · 004 · 005 (`schema_migrations`가 파일명으로 추적, 멱등) |
| dev DB 행 | **2026-09-01 마이크 세션 후**: 세션 3 · 발화 51 · 패턴 6 · occurrence 15 · job 21 · `pronunciation_attempts` **3** · 발음 패턴 **1**. ⚠️ 패턴 6개 중 **2개는 조각산 오탐**이다(I-1) — 이 수치를 "학습자의 약점 6종"으로 읽지 마라 |
| 미커밋 | `.claude/` · `.mcp.json` · `backlog/`(모두 untracked) — **커밋하지 말고 지우지도 마라**. `.claude/`는 B-9 결정, `.mcp.json`·`backlog/`는 캡틴이 진행 중인 원장(Backlog.md) 도입이다(태스크 0건 = 아직 미이행, 원장은 여전히 `TASKS.md`) |

✅ **발음 데이터가 실물로 3건 생겼다**(2026-09-01). 이전 판의 "dev DB에 0건" 서술은 폐기됐다.
시도 3건은 `outcome` `correct`·`correct`·`incorrect`이고 마지막 1건이 패턴에 연결됐다.
통합 테스트가 롤백 트랜잭션이라 흔적을 남기지 않는다는 사실 자체는 그대로 유효하다.

---

## 다음 세션 진입 절차

1. 이 파일 → **`TASKS.md`의 해당 절 표 한 줄** → 필요할 때만 계획서. `TASKS.md` 전체를 읽지 않는다.
2. 게이트를 `app/backend` cwd에서 돌려 위 실측값과 대조한다. **다르면 그 차이를 먼저 설명한다.**
   ⚠️ **게이트 전에 DB가 떠 있는지 본다** — `brew services list | grep postgresql@17`.
   **dev DB는 2026-08-31에 podman(:5433) → homebrew `postgresql@17`(:5432)로 옮겼다**(함정 **H-T**).
   보통 부팅 시 launchd가 띄우므로 손댈 일이 드물다. 안 떠 있으면 `brew services start postgresql@17`.
   DB가 없으면 `pytest`가 **192 passed · 155 errors**로 끝나는데 **회귀가 아니라 연결 거부다** —
   errors가 100건 넘게 한꺼번에 나면 코드보다 연결을 먼저 의심한다.
   ⚠️ 그 인스턴스는 **StockAgent와 공유**한다 — 인스턴스 재시작·`ALTER SYSTEM` 금지, DB 단위로만 다룬다.
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
- **2026-08-30** `claude_air_3-14` → **`claude_air_3-15`**: ✅ **4/4 일치** (새 세션이 직접
  돌려 얻은 값으로 대조 완료). 그 세션이 기준 해시 오류를 잡아냈다 — 인계 확인이 형식이
  아니라 실제로 작동한 사례다(함정 H-R).
  - **차이 1건(코드 아님) → 해소됨**: 미커밋 `docs/research/`의 출처가 "미확인"으로 남았다가
    3-14가 자기 조사 산출물로 커밋해 확정됐다(`3badf37`). 캡틴이 별도 폴더로 옮겨 진행한다.

### 다음 세션이 대조할 기준값 (이 절을 쓴 턴에 직접 실행해 얻었다)

| # | 지표 | 값 |
|--:|---|---|
| 1 | HEAD | **`HEAD ≥ efc6264`** — 반드시 `≥`로 읽는다(함정 H-P). `--amend`로 기준 해시를 잃지 않도록 마감 커밋에 `--amend` 폴백을 쓰지 않는다(함정 H-R) |
| 2 | 다음 한 걸음 | **I-1 — 조각 발화가 오탐 패턴을 만든다** (구조적 해소 후보 (가)/(나) 중 캡틴 결정 대기). A-5·Task 8·G-4는 2026-09-01에 **완료** |
| 3 | 게이트 | **348 passed** · ruff·format(27파일)·ty clean · `tests/**` 베이스라인 **6 errors·4 files** · 프론트 `tsc --noEmit`·`eslint` clean |
| 4 | 착수 전 필수 | **I-1 결정 1건 + §11 문서 정정 2건**(D-5·D-6, `TASKS.md` C절). 이전 기록의 "0건" — A-2 후단 2건(`9b7985f`) · A-5 검증 수단(캡틴 결정) · 지시문 선행(`efc6264`) 모두 해소. 단 배지에 **기계 키를 렌더하지 마라** |

미커밋은 `.claude/` · `.mcp.json` · `backlog/`(모두 untracked)이고 **커밋하지도 지우지도
않는다** — 위 실측값 표의 "미커밋" 행이 각각의 사유를 갖는다.

인계 확인은 새 세션이 **직접 돌려 얻은** 4개(HEAD · 다음 한 걸음 · 게이트 실측 · 착수 전 필수
건수)가 위 실측값과 일치하는 것이다 — "읽었다"는 지표가 아니다. 절차는
`~/.claude/rules/session-handover.md`, 함정은 `pitfalls.md` **H-P**·**H-Q**.
