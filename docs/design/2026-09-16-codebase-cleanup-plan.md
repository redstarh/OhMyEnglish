# OhMyEnglish 코드베이스 정리 계획 (회귀 없이)

> 절차의 정본은 `~/.claude/skills/codebase-cleanup/SKILL.md` 다 — 동료 세션이
> `realtime-meeting` 리포의 실측 회차에서 뽑았다. **이 문서는 그 절차를 이 리포에 배선한 것이고
> 절차를 재서술하지 않는다.**
>
> ⛔ **착수 조건**: 사용자가 「시작」이라고 말하는 것. 사용자 지시가
> *"현재 작업이 완료되면 바로 시작할테니까"* 이므로 이 문서는 **계획까지**다.
>
> ⛔ **지키는 것 하나**: 동작을 바꾸지 않는다. `동작변경=예` 로 분류되는 발견은 실제 결함이어도
> 적용하지 않고 태스크로 갈라낸다 — 섞으면 회귀가 났을 때 원인을 가를 수 없다.

## 1. 기준선 — 2026-09-16 이 세션에서 직접 돌린 값

| 지표 | 값 | 얻는 명령 |
|---|---|---|
| **테스트 수집 개수** | **1273** | `cd app/backend && ./.venv/bin/pytest -q --collect-only` (exit 0) |
| 테스트 통과 | **1273 passed** | `cd app/backend && ./.venv/bin/pytest -q` |
| ruff | 통과 | `./.venv/bin/ruff check .` · `ruff format --check .` (49 files) |
| ty | 통과 | `~/.local/bin/ty check` |
| 프론트 | `tsc --noEmit` exit 0 · `eslint .` exit 0 | `cd app/frontend` |
| 소스 | 백엔드 **13,669줄** · 프론트 **3,029줄** | `find … | xargs wc -l` |
| 테스트 | **35,409줄** | 같음 |
| 커밋 | **928** | `git rev-list --count HEAD` |

⚠️ **수집 개수와 통과 수가 같다**(1273=1273) — 이 리포에는 skip 이 없다는 뜻이고, 그래서
**통과 수만 재도 「테스트를 지워 통과시킨 것」이 수집 개수에서 먼저 드러난다.** 두 수치를 다 적는다.

⛔ **실사용 검증은 유닛 게이트가 대신하지 못한다.** 이 리포의 실사용 경로는 Nova 실물 세션이고
(`tests/harness/ws_session.py --wav`) 비용이 든다 — 그래서 **기준선에는 넣지 않고 최종 게이트에서
정리가 그 경로를 건드렸을 때만** 1회 돌린다. 그 판단 근거를 보고에 적는다.

## 2. 기계적 신호 — 이 리포에서 실제로 재 본 결과

지금 켜진 규칙군은 다섯뿐이다: `select = ["E", "F", "I", "UP", "B"]` (`app/backend/pyproject.toml`).

**「억제 표식은 있는데 규칙이 꺼져 있는」 자리가 21건 있다** — 표식이 아무 일도 하지 않는다.

| 표식 | 건수 | 그 규칙이 켜져 있나 |
|---|--:|---|
| `E402` | 83 | 켜짐 (`E`) — 살아 있는 표식 |
| `PLC0415` | 6 | 꺼짐 |
| `BLE001` | 6 | 꺼짐 |
| `S310` · `ANN001` | 2 · 2 | 꺼짐 |
| `SLF001` · `S603` · `N803` · `DTZ001` · `ARG001` | 각 1 | 꺼짐 |

⛔ **표식을 지우지 않고 규칙을 켜는 쪽을 본다**(스킬 §6). 켰을 때의 위반 수를 직접 셌다:

| 규칙군 | 위반 | 뜻 |
|---|--:|---|
| `BLE` · `DTZ` · `PTH` · `S310` · `SLF001` · `N803` | **0** | **코드를 건드리지 않고 켤 수 있다 — 안전망만 늘어난다** |
| `RET` · `PERF` | 1 · 1 | 켜려면 한 자리씩 손봐야 한다 |
| `SIM` | 3 | 같음 |
| `ARG` · `PLC0415` | 4 · 4 | 같음(표식이 6건 있는 규칙이라 실제로는 대부분 표식으로 덮인다) |
| `RUF` | 18 | 이번 정리 범위 밖 — 별 태스크로 갈라낸다 |
| `ANN` | 9 | 같음 |

⇒ **첫 묶음은 이것이다: 위반 0인 여섯 규칙군을 켠다.** 코드 변경 0줄이고 다음 사람이 같은 실수를
반복하지 못하게 만든다. ⚠️ `BLE` 를 켜면 `noqa: BLE001` 6건이 **살아난다** — 그 표식이 근거를
담고 있으므로 지우지 않는다.

## 3. 리뷰 배정 — 읽기 전용 · 각도 하나씩 · 파일이 겹치지 않게

파일 인벤토리를 재서 나눌 수 있음을 확인했다(동료 세션의 물음 ②에 대한 답: **나눌 수 있다**).
백엔드 상위 파일이 뚜렷하게 갈라진다 — `audio_gateway/nova.py` 1,497줄 · `session.py` 856 ·
`services/pronunciation.py` 838 · `sessions.py` 728 · `review.py` 656 · `analysis.py` 626 ·
`plan.py` 605 · `recordings.py` 553 · `api/ws.py` 513.

| 갈래 | 각도 | 읽을 범위 |
|---|---|---|
| R1 | 재사용 | `services/**` (20파일 · 7,394줄) |
| R2 | 단순화 | `audio_gateway/**` (7파일 · 2,830줄) |
| R3 | 효율 | `services/review.py` · `daily_summary.py` · `results.py` · `weekly_report.py` |
| R4 | 고도 | `api/**` · `models/**` (16파일 · 2,516줄) |
| R5 | 도구 낡음 | `tests/harness/**` · `scripts/**` |
| R6 | 외부 리뷰어(codex) | 위 결과가 지목한 자리만 — 범위를 좁게 준다(실측 규약) |

⛔ 각 갈래에 넣을 제약은 스킬 §2 가 소유한다. 이 리포에서 **반드시 덧붙일 제약 하나**:
**주석 분량을 리뷰 대상에서 뺀다.** 이 리포의 주석은 실측 근거·뒤집힌 판정·함정을 담은 자산이고
(`⛔`·`⚠️` 로 표시된 자리) 그것을 「군더더기」로 지우면 다음 세션이 같은 함정을 다시 밟는다.

⚠️ **리뷰는 겹쳐도 되고 적용만 겹치면 안 된다** — R1 과 R3 의 범위가 겹치는 것은 의도다(각도가
다르면 같은 파일에서 다른 것을 본다). 겹침이 금지되는 것은 §4 의 적용 묶음이다.

## 4. 적용 묶음 — 파일이 겹치지 않게 (겹침 0으로 설계했다)

| 묶음 | 파일 | 왜 이 묶음인가 |
|---|---|---|
| A1 | `app/backend/pyproject.toml` | 위반 0인 규칙군 여섯을 켠다. **코드 0줄** |
| A2 | `services/pronunciation.py` · `services/review.py` | 가장 큰 두 서비스이고 서로 부른다 |
| A3 | `services/sessions.py` · `services/recordings.py` | 방금 결정 119 로 값역 정본을 공유했다 |
| A4 | `services/analysis.py` · `services/plan.py` · `workers/claude_client.py` | 모델 호출 축 |
| A5 | `audio_gateway/nova.py` · `audio_gateway/session.py` | 프로토콜 축 — 가장 위험하므로 마지막 |
| A6 | `api/**` · `models/**` | 경계 층 |

⛔ **각 묶음은 커밋하지 않는다.** git index 는 다중 세션 공유 자원이라 동시에 `git add` 하면 남의
미완성 변경이 섞인다 — 커밋은 리드가 마지막에 **경로를 열거해서** 한다(이 리포의 함정 목록에도
같은 규약이 있다).
⛔ **A5 는 단독으로 돌린다.** 그 두 파일이 이 리포에서 회귀 비용이 가장 크고(실시간 프로토콜),
정리 중 유일하게 사람 역할 E2E 가 필요할 수 있는 자리다.

## 5. 최종 게이트 — 리드가 직접 돌린다

```bash
cd app/backend && ./.venv/bin/pytest -q --collect-only   # ⚠️ 1273 이상인가 (파이프 없이)
cd app/backend && ./.venv/bin/pytest -q                  # exit 0
cd app/backend && ./.venv/bin/ruff check .; echo "exit=$?"
cd app/backend && ./.venv/bin/ruff format --check .; echo "exit=$?"
~/.local/bin/ty check; echo "exit=$?"
cd app/frontend && npx tsc --noEmit; echo "exit=$?"
cd app/frontend && npx eslint .; echo "exit=$?"
```

⛔ **`cmd | tail` 뒤의 `$?` 는 `tail` 의 것이다**(스킬 §6 — 동료 세션이 실제로 밟았다).
종료 코드는 파이프 없이 본다.

**실사용 게이트는 조건부다**: A5(프로토콜 축)나 녹음·발음 경로를 건드렸으면 Nova 실물 세션 1회를
`ws_session.py --wav` 로 돌린다(검증 전용 DB · `:8013` · 오늘 그 절차로 두 번 돌렸다). 건드리지
않았으면 돌리지 않고 **그 판단 근거를 보고에 적는다.**

## 6. 이 리포 특유의 함정 — 착수 전에 읽는다

1. ⛔ **`pytest` 는 `app/backend` 에서 인자 없이 돌린다.** 경로를 주면 `asyncio_mode` 가 안 잡혀
   async 테스트가 전부 실패하고, 리포 루트에서 돌리면 경로 의존 테스트 10건이 깨진다. 부분 실행은
   `-o asyncio_mode=auto` 를 붙인다.
2. ⛔ **게이트 도구는 `python3` 에 없다** — `app/backend/.venv/bin/` 이고 `ty` 만 `~/.local/bin` 이다.
   툴 호출 사이에 cwd 가 남으므로 **절대 경로**를 쓴다.
3. ⛔ **`git add <디렉터리>` 금지.** 커밋 전 `git diff --cached --name-only` 로 건수를 센다.
4. ⛔ **새 로그를 `info` 로 두지 않는다** — 지정된 실행이 `--log-level warning` 이라 그 아래는 한 줄도
   보이지 않는다. 크기를 세야 하는 로그는 `warning` 이다.
5. ⛔ **주석은 자산이다** — `⛔`·`⚠️` 가 붙은 자리는 실측 근거·뒤집힌 판정·함정이다. 옮길 때 함께
   옮기고 지우지 않는다.
6. ⚠️ **정리로 줄 수가 늘 수 있다** — 근거 주석을 새 함수로 옮기면 그렇다. 줄 수를 지표로 쓰지 않는다.
7. ⛔ **문면을 정본으로 검사하는 단정이 일곱 건 있다 — FAIL 하면 검사를 고치지 말고 내 변경을 고친다.**
   ⚠️ **건수를 「여덟」로 적었던 것을 정정했다**(2026-09-17 착수 시점에 전수로 세었다):
   `pytest -k "matches_the or isolated_to"` 가 **7건**을 수집하고 **7 passed** 다. 착수 전에 그 일곱이
   전부 통과함을 확인했으므로 **나중에 하나라도 FAIL 하면 그것은 이 회차의 변경 탓이다.**
   동료 세션이 같은 부류를 밟아 알려 준 함정이고, **나도 오늘 밟았다**: `TASK-142` 에서 새 예외 문면에
   자격증명 환경변수 이름을 적었더니 `test_config.py::test_credential_strings_isolated_to_config_module`
   이 FAIL 했다(F5 규약을 `grep` 으로 판정하는 검사다). 검사를 고치지 않고 문면을 바꿨다.
   착수 전에 뽑아 둘 목록: `test_config.py`(자격증명 문자열) · `test_nova.py` 둘(상수 대 SQL · 상수 대
   **프롬프트 문장**) · `test_weekly_report_job.py`(상한 대 프롬프트) · `test_sessions.py`(상수 대
   `information_schema`) · `test_shadowing_seed.py` 둘 · 그 외 하나.
   ⛔ **그중 «프롬프트 문면» 검사는 성격이 다르다 — FAIL 하면 문면을 맞추지 말고 「내가 프롬프트를
   건드렸는가」를 먼저 본다.** 문서·주석은 고쳐도 동작이 그대로지만 프롬프트 문장을 고치면 **모델
   출력이 바뀐다** — 즉 그 FAIL 은 `동작변경=예` 영역에 들어갔다는 신호이고, 건드렸다면 정리 범위
   밖으로 갈라낸다(동료 세션의 지적이고 이 리포에서 확인했다).
   ⚠️ **그 부류는 하나다 — 둘이 아니다**(직접 읽어 정정했다): 진짜 프롬프트 문면 검사는
   `test_nova.py::test_the_base_level_range_constant_matches_the_fixed_prompt`
   (`f"at {_BASE_LEVEL_RANGE} level" in SYSTEM_PROMPT`) 하나다.
   `test_weekly_report_job.py::test_the_insight_cap_matches_the_prompt` 는 이름과 docstring 이
   「프롬프트와 파서가 같은 수」를 주장하지만 **단정은 `MAX_INSIGHT_POINTS == 3` 뿐**이다 — 그 값이
   프롬프트와 파서에 **인자로 함께 흘러** 어긋날 수 없는 구조라서 그렇다.
   ⇒ 그 자리는 **R5(도구 낡음) 각도의 후보**다: 이름이 실제 단정보다 넓어 **거짓 안심**을 준다.

## 7. 착수하면 등록할 것

이 계획의 실행 태스크는 **착수 시점에** 등록한다(A1~A6 를 서브태스크로). 지금 등록하지 않는 이유는
사용자의 착수 신호를 기다리는 상태에서 원장에 열린 태스크를 늘리면 **잔여가 실제보다 커 보이기**
때문이다 — 이 계획 문서 자체가 그 목록의 정본이다.
