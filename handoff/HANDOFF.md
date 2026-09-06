# Handoff — OhMyEnglish

> **두 가지만 담는다: 다음 한 걸음 / 착수 전 필수.** 그 밖은 각 정본이 소유하고 여기서는 **가리키기만** 한다.
> 최종 갱신 **2026-09-06** · 브랜치 `design/first-vertical-slice` · HEAD **`f6c51e8`**
>
> ⚠️ **이전 판(475줄)은 `handoff/backup/2026-09-06/HANDOFF-full-475lines.md`가 소유한다.**
> 슬라이스 1·2 이력 · 인계 기록 · S2-11 서술 · 발음 착수 안내가 거기 있다 — **필요할 때만 열어라.**

---

## 다음 한 걸음 — **원장에서 고른다. 이 문서에서 고르지 않는다**

```bash
backlog task list -s "In Progress"     # 이미 손댄 것부터
backlog task list -s "To Do"           # priority high 와 caps-req 를 먼저 본다
```

**원장이 상태의 정본이다**(`backlog/tasks/*.md`, 29건). 여기에 태스크 목록을 복사하지 않는다.

### ⚠️ 첫 걸음 — `TASK-31` **AC #13** 하나다. 그것만 남았다

**`TASK-31`이 `In Progress`이고 13건 중 12건이 닫혔다.** 남은 #13은 **코드 수정으로 닫히지 않는다** —
`finalLines` 스냅샷의 판별 실험이고 **실제 세션 관통 회차**가 필요하다.

**실험 내용**(발명하지 말고 그대로 해라): `settle()` 없이 `final` 직후 **종단 프레임을 같은 tick에
연달아 주입**해 줄을 잃는지 본다. 잃으면 결함은 "동기 스냅샷 지점"이고, **새로 넣은 MutationObserver
적립(`snapshots` + `judgeFinalLines`)이 그 조건에서도 살아남는지**가 진짜 물음이다.

⚠️ **왜 아직 열려 있나**: T2는 `[]`를 봤고 T5a는 정상 2줄을 봤다. **T5a 에이전트가 자기 관측으로
T2를 반박하지 않았다** — 여유가 9.7초일 때 동작한 것만 보였고, 실제 `session_ended` 경로를 밟지
않았으며(`stub_unresponsive`는 그 프레임을 안 보낸다) settle을 넣어 **문제 조건을 구조적으로
회피했다.** 그 정직함이 이 항목을 살려 뒀다 — **닫혔다고 오인하지 마라.**

⚠️ **감사 세션에 "내가 #13을 산출물 없이 체크하면 미이행으로 올려 달라"고 부탁해 뒀다.**

### 그다음 (원장에서 고른다)

- **`TASK-21`** (high) — 화면 관측 17건. 선행은 `TASK-31`이다. A1-0만 끝났다.
- **`TASK-30`** (high) — 판별력 **관측**. 재설계한 단정 7건의 대조가 실제로 FAIL을 내는지.
  ⚠️ **관측 전에는 그 7건을 `PASS`로 보고하지 않는다.**
- **`TASK-22`** — 결과 화면 5상태·교정 카드 관측.
- **`TASK-6`·`TASK-25`** — 캡틴 결정 2·3(질문 전달 · 시나리오 전달). **같은 자리를 건드리니 함께
  설계한다**(`captain-decisions.md` §2). **AC11-2의 남은 연접이 여기서 닫힌다** — 요구사항을 실제로
  움직이는 것은 프론트 검증 체인이 아니라 이쪽이다.

### ✅ 2026-09-06에 확정된 것 — 재론하지 않는다

- **AC11-2 = `◐ 부분` 확정** (2차 codex 리뷰 `PASS`). 세 연접 중 둘째(질문)가 **소비자 0곳**이다 —
  표시 경로도 **발화 경로(`audio_gateway/nova.py:build_system_prompt`)도** `questions`를 읽지 않는다.
  근거는 `docs/design/2026-09-06-review-outcomes.md` §6이 소유한다.
- **CDP 프레임 주입은 된다** (`TASK-20` T5a, AC 4건 전건 `PASS`, 2회 회차 일치).
  → **C5 폐기와 §7-6 직렬 큐 대안 둘 다 불필요해졌다.**
- **`browser_leg.md` §11의 미결 2·3·5·6이 닫혔다.** 남은 것은 §11-7(`finalLines`)과 T4 몫이다.

⚠️ **2026-09-06에 닫은 것(`TASK-17`·`TASK-29`)의 내용은 여기 적지 않는다 — 원장 노트가 소유한다**
(`backlog task view TASK-29`). 한 가지만 알아 둘 것: **`TASK-29`의 AC 하나를 `TASK-30`으로 옮겼다.
조용히 덮은 것이 아니라 원문과 이유를 그 노트에 남겼다** — 회차가 재설계를 전제해 순환했다.

---

## 착수 전 필수 — 이 세션에서 생긴 규약 4개

| 규약 (`docs/ops/`) | 한 줄 요지 — 상세는 그 문서가 소유한다 |
|---|---|
| `data-first-design-convention.md` | **표·데이터를 먼저 판정한 뒤 코드를 쓴다.** ⚠️ DB 공유가 **스키마 수준**이다(`pg_dump`에 `-n public`) |
| `review-and-decision-protocol.md` | **요구사항 판정을 바꾸는 순간 codex 리뷰를 건다** |
| `captain-instruction-register.md` | 강제 장치 5개. 핵심: **방식이 지시되면 산출물로 대체하지 않는다** |
| `audit-session-brief.md` | 외부 감사 세션이 읽는 브리프 (읽기 전용·매시 감사) |
| `pitfalls.md` | 실측 함정. **H-A**(게이트 cwd) · **H-P**(HEAD 해시는 적는 순간 낡는다) · **H-X**(동시 pytest) · **H-AB~H-AD**(2026-09-06 신규) |

### 캡틴 결정·판정 기록 — 재론하지 않는다

- `docs/design/2026-09-06-captain-decisions.md` — **결정 8건** + 그 결정이 부과하는 제약
- `docs/design/2026-09-06-review-outcomes.md` — **판정 2건이 리뷰로 뒤집혔다.** §2 AC11-2 되돌림 ·
  §4 단정 7건 · **§6 AC11-2를 `부분`으로 확정**(2차 리뷰)
- `docs/design/2026-09-06-captain-response-to-status-report.md` · `…-gap-investigation.md` ·
  `docs/status-report-2026-09-06.html`(**스냅샷이고 정본이 아니다**)

### 회차 기록 (사후 편집하지 않는다) — `tests/harness/runs/`

`2026-09-06-live-plan-1.md`(실물 계획) · `…-browser-leg-1.md`·`…-browser-leg-2-agent.md`(A1-0) ·
**`…-t2-instrument-spike.md`**(계측 신설 · teardown 사고) ·
**`…-t5a-injection-spike.md`**(주입 확정 · 결함 8건) · `…-pattern-baseline.tsv`(baseline 사본)

⚠️ **두 회차 기록은 팀리드가 「직접 확인한 것 / 못 한 것」을 절로 갈라 뒀다** — 그 절을 먼저 읽어라.
남의 관측을 내 증거로 쓰지 않기 위한 것이고, 감사가 그 공백을 실제로 잡아냈다.

---

## 실측값 (2026-09-06, 이 절을 쓴 턴에 직접 실행)

```bash
cd app/backend                                  # 게이트는 이 cwd에서만 판정한다 (함정 H-A)
.venv/bin/pytest -q                             # 595 passed
.venv/bin/ruff check . ; .venv/bin/ruff format --check .   # exit 0 / 32 files
ty check                                        # exit 0
.venv/bin/ruff check ../../tests ../../scripts  # 6 errors  (기준선, 게이트 밖)
.venv/bin/ruff format --check ../../tests       # 4 files   (기준선)
cd ../frontend && npx tsc --noEmit ; npx eslint app lib     # 둘 다 exit 0
```

⚠️ **게이트를 `| tail`로 파이프하지 마라** — 종료 코드가 `tail`의 것이 되어 실패가 통과로 읽힌다.
⚠️ **게이트 밖은 0으로 만들 대상이 아니라 유지 대상이다.** 늘었으면 **네가 편집한 파일만** 포맷한다.

| 항목 | 값 |
|---|---|
| 테스트 | **595 passed** (582 → +13. AC11-2 강제 +12 · 만성 빈 경로 종단 +1) |
| DB | `:5432` homebrew **17** · 역할 `ohmy` · `TimeZone=UTC` · ⚠️ **같은 DB에 남의 `en_coach` 스키마가 있다 — 우리 것은 `public` 하나** |
| 마이그레이션 | **001·003·004·005·006·007** 적용. 002는 존재한 적이 없다 |
| 표 | **16개**. `session_plans`·`learner_notes`가 007로 생겼다 |
| ⚠️ 보존 대상 | `session_plans` **1행** · `learner_notes` **1행** — 실물 모델 왕복의 **유일한 증거**이고 다시 만들면 비용이 든다. **지우지 마라** |
| 서버 | 백엔드 **:8002 실행 중** pid **30860** — ⛔ **`VOICE_ADAPTER=stub_unresponsive`로 떠 있다** · `WORKER_ENABLED=false` · 프론트 **:3000 실행 중** |
| 미커밋 | `.claude/` · `.mcp.json` · `tmp/`(추적 밖) — **커밋하지도 지우지도 마라** |
| 계측 | `tests/harness/instrument.js` **437줄** · sha256 **`0be00c20a99c4fa9…`** (23917B). ⚠️ **해시는 주석 한 줄로도 바뀐다** — 회차 기록의 해시와 다르면 먼저 `git diff`로 실행 코드 변경 여부를 본다 |
| 절차 문서 | `tests/harness/browser_leg.md` **557줄**. P5가 **4차 정정**됐고 §8-②가 **재계산 → baseline 복원**으로 바뀌었다 |
| baseline 사본 | `tests/harness/runs/2026-09-06-pattern-baseline.tsv`(추적됨) — **DB 표 `harness_pattern_baseline`이 회차마다 drop되므로 이 파일이 마지막 사본이다** |

⛔ **백엔드가 `stub_unresponsive`로 떠 있다 — 이것을 모르면 관측이 전부 어긋난다.**
그 모드는 `session_started`만 보내고 그 뒤 영원히 대기한다(**주입 창**이 그래서 열린다). 즉
**`audio`·`final`·`partial` 프레임이 0건**이고 `A1-1~A1-5`·`A1-8`은 **평가할 수 없다.**
C1 관통이나 A1-4 계수를 재려면 **`VOICE_ADAPTER=stub`(기본)으로 재기동**해야 한다:
`cd app/backend && VOICE_ADAPTER=stub WORKER_ENABLED=false nohup .venv/bin/uvicorn app.api.main:app --port 8002 > /tmp/omy-backend.log 2>&1 &`
⚠️ **로그를 그 경로로 리다이렉트해야 P5가 통과한다**(P5가 로그 pid와 실행 pid를 대조한다).

⚠️ **워커가 꺼져 있다.** 세션을 열어 분석을 돌리려면 켜야 하고, 그러면 **실물 모델 호출 비용**이 든다
(승인된 것은 계획 생성 1회뿐이었다). 켜기 전에 캡틴 확인.

---

## 진입 절차

1. **원장을 조회해 태스크 ID를 말한 뒤 착수한다.** 태스크가 없는 일이면 **먼저 등록한다.**
2. 게이트를 `app/backend` cwd에서 돌려 위 실측값과 대조한다. **다르면 그 차이를 먼저 설명한다.**
   ⚠️ 게이트 전에 DB를 본다 — `brew services list | grep postgresql@17`. 안 떠 있으면 대량 errors가
   나는데 **회귀가 아니라 연결 거부다.** 인스턴스는 **남과 공유**하니 재시작·`ALTER SYSTEM` 금지.
3. 계획서를 열면 **머리말의 「구현 전/후 정정」과 「Task N 착수 전 점검」을 먼저 읽는다.**
4. **태스크 상태는 원장을, 다음 걸음이 바뀌면 이 파일을** 갱신한다.

### ⚠️ 이 리포의 지배 실패 모드 — 누적 25건 + 이 세션에 10건 더

**"검사가 통과했는데 통과한 이유가 틀렸다."** 형태 **7가지의 정본은 여기가 아니다** —
`docs/design/2026-09-06-review-outcomes.md` §4와 `tests/harness/browser_leg.md`의 ⛔ 상자가 소유한다.
**두 곳에 적으면 한쪽이 조용히 낡는다.**

**판별법 한 줄만 여기 남긴다**: 단정을 채택하기 전에 **그 대조가 무력화에서 실제로 FAIL을 내는지**
확인한다. 확인하지 않았다면 "대조 있음"이 아니라 **"판별력 미확인"**이다.

⚠️ **2026-09-06에 이 형태로 3건이 더 걸렸고 `docs/ops/pitfalls.md`에 등재했다**:
**H-AB**(배선은 배선 줄만 무력화해 확인한다 — 가드 본문을 건드리면 단위도 함께 red가 되어
못 가린다) · **H-AC**(하네스가 앱 계산식을 복제하면 낡고 **공유 dev DB를 파괴한다**) ·
**H-AD**(크론 발동은 폴링으로 관측할 수 없다 — 관측이 대상을 없앤다).

### 인계 지표 4개 — 새 세션은 **직접 돌려** 얻고 대조한다

| # | 지표 | 기준값 (이 세션이 마감 시점에 직접 돌려 얻었다) |
|--:|---|---|
| 1 | `git rev-parse --short HEAD` | **`f6c51e8`** 이상 (`HEAD ≥ f6c51e8`. 이 값을 적은 커밋 자신이 HEAD를 옮기므로 등호를 요구하지 않는다 — 함정 H-P) |
| 2 | `backlog task list -s "In Progress"` | **`TASK-31`(high) · `TASK-6` · `TASK-7`** 세 건. 다음 걸음은 **`TASK-31` AC #13** |
| 3 | 게이트 | `app/backend` cwd에서 **595 passed** · `ruff check` 통과 · `ruff format` 32 files · `ty` 통과. 프론트 `npx tsc --noEmit`·`npx eslint app lib` **둘 다 exit 0** |
| 4 | 착수 전 필수 | **1건** — `TASK-31` AC #13은 **세션 관통 회차**가 필요하고, 그러려면 백엔드를 **`VOICE_ADAPTER=stub`으로 재기동**해야 한다(지금은 `stub_unresponsive`) |

⚠️ **3번이 핵심이다** — 읽기는 전달을 증명하지 못하고 **직접 돌린 출력**만 데이터다.
하나라도 다르면 **그 차이를 먼저 설명한다.**

### ⚠️ 캡틴이 해야 하는 것 1건

**감사 세션이 들어오는 메시지마다 캡틴에게 승인을 묻는다.** 배달 통지가 그것을 명시했다 —
*"held for the **recipient** user's approval"*. ⚠️ **작업 세션의 `SendMessage` 허용으로는 풀리지
않는다**(그것은 보내는 쪽이다. 2026-09-06에 `.claude/settings.local.json` allow에 추가했다).
**받는 쪽 게이트이고 그 세션의 권한 모드가 소유한다** — 캡틴이 그 창에서 풀어야 한다.
⚠️ 전역·프로젝트 `settings.json`에서 **해당 키를 찾지 못했다**(직접 grep) → 설정 항목이 아니라
**세션 권한 모드**로 보인다. **확정하지 않았다.**

생존 신호는 이제 둘이다: `.harness/audit-heartbeat.txt`(**매 회차 `>`로 덮인다 — 이력이 없다**) ·
**`.harness/audit-fire-log.txt`(append-only, 감사자가 2026-09-06에 신설)** — 발동 이력은 이쪽을 본다.

⛔ **크론 발동이 불안정하다 — 원인 미확정이다.** 감사 잡(`82bc95e7`, 슬롯 `:07`)이 자동 발동
**1회뿐**이고, 작업 세션 잡(`460b4089`, 슬롯 `:23`)도 12:31 이후 조용했다. **둘 다 조용하지만
작업 세션은 그 구간에 계속 바빴으므로 대조군이 못 된다**(idle 부재로도 설명된다).
판별법과 관측자 효과는 `docs/ops/pitfalls.md` **H-AD**가 소유한다 — **폴링하지 마라.**

⚠️ **원장의 `created_date`·`updated_date`는 UTC다 — KST보다 9시간 이르다**(감사 발견, 직접 확인).
시각 간격으로 지연을 논할 때 보정해라.

---

_2026-09-06: 475줄에서 이 크기로 줄였다. 지운 것은 지우지 않고_
_`handoff/backup/2026-09-06/HANDOFF-full-475lines.md`로 옮겼다 — 슬라이스 1·2 이력 · 인계 기록 ·_
_S2-11 서술 · 발음 착수 안내. **이 문서는 다음 걸음과 착수 전 필수만 담는다.**_
