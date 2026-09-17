# 회차 — 026 이관 뒤 통합 확인 (사용자 지시: 「개발이 마무리되면 테스트는 필수로 진행해」)

세션 `ohmyenglish-44` · 2026-09-17 · 브랜치 `design/first-vertical-slice` · 기준 커밋 `da0192a`
`run_id` = `ce91b38e-c008-4038-9309-5c915616cae6`

> **왜 이 회차인가**: 이 세션이 오늘 `TASK-41`(표를 `public` → `ohmyenglish` 스키마로 이관) ·
> `TASK-148`(모드 정책을 표로) · `TASK-147`(왕복 배치화)을 넣었다. 게이트 1283건은 **테스트 DB** 에서만
> 도므로 **dev DB 와 실물 소켓 경로**를 지나가는 확인이 따로 필요하다.
>
> ⛔ **스택**: 백엔드 `:8002` `WORKER_ENABLED=false VOICE_ADAPTER=stub --log-level warning`
> (문서가 지정한 baseline 형태) · 실물 Claude·Nova 호출 **0회**.

---

## 0. 상한과 판정 규칙 — 돌리기 전에 적는다

* **회차 1건 · 시나리오 A1 하나.** 늘리지 않는다 — 재는 것은 「분포」가 아니라 **경로가 새 스키마를
  지나가는가** 하나다.
* **워커를 끈다.** 분석이 돌면 `error_patterns`·복습 시계가 움직이고 teardown 이 그것을 되돌려야 한다
  (`browser_leg.md` §8-0 의 「drift 0 이 되돌아왔다를 뜻하지 않는다」). 끄면 그 위험이 아예 없다.
* **판정**: 세션 행이 `ohmyenglish` 스키마에 있고 · 발화가 저장되고 · 결과 API 가 200 이고 ·
  백엔드 로그 오류가 0 이고 · teardown 뒤 표 넷이 **기준선과 정확히 같으면** 통과.
* ⛔ **「통과」를 로그 없음으로 주장하지 않는다** — 아래 수치를 전부 직접 읽었다.

## 1. 기준선 (회차 전)

| 표 | 값 |
|---|--:|
| `learning_sessions` | 17 |
| `utterances` | 128 |
| `error_patterns` | 9 |
| `analysis_jobs` | 57 |
| `harness_sessions` | 98 |

## 2. 관측

**API 프리플라이트** — DB 를 타는 엔드포인트 넷이 전부 `200` 이고 실데이터였다:
`/api/daily-summary` · `/api/history` · `/api/sessions/next-plan`(한국어 이유 문장) ·
`/api/weekly-report`. 백엔드 로그 오류 **0건**.

**실물 소켓 세션** (`ws_session.py --scenario A1`) — 프레임 **17개**,
순서 `session_started → (final/partial ×3턴) → audio ×3 → session_ended`.
원자료: `.harness/evidence/A1-frames.json`.

| 확인 | 값 |
|---|---|
| `learning_sessions` 의 실제 스키마 | **`ohmyenglish.learning_sessions`** (`pg_class`·`pg_namespace` 조회) |
| 그 세션 행 | `mode=speaking` · `status=completed` · `learning_source=recommended` |
| 발화 | **6건** (agent/user) |
| 하네스 등록 | `harness_sessions` 에 `A1` |
| 결과 API | `200` · `{"status":"analyzing", …}` — 워커를 껐으므로 `analyzing` 이 정답이다 |
| 백엔드 로그 오류 | **0건** |

**teardown 대조** — 하네스 세션을 cascade 로 지운 뒤 네 표가 **전부 기준선과 같았다**:
`learning_sessions` 17 · `utterances` 128 · `error_patterns` 9 · `analysis_jobs` 57.
⚠️ `analysis_jobs` 는 회차 중 63 까지 올랐고(턴마다 job 이 걸린다) cascade 로 57 로 돌아왔다.
⚠️ `error_patterns` 는 회차 내내 9 였다 — 워커를 껐으므로 분석 쓰기가 없었다.

## 3. ⛔ 이 회차가 잡은 결함 하나 — 게이트가 잡지 못하는 자리였다

**`psql_cli.psql()` 이 `insert … returning` 의 명령 태그를 함께 돌려줬다.**

`.harness/run_id.txt` 를 그 헬퍼로 쓰니 파일이 **47바이트**였다 — 내용은
`<uuid>\nINSERT 0 1` 이다(36바이트여야 한다). `ws_session.py`·`inject_errors.py` 는 그 값을 SQL 에
**그대로** 넣으므로 1회차에서 실제로 `INSERT01` 오염이 나 세션 하나가 미등록으로 남았고,
`tests/harness/README.md` 가 그것을 경고로 남겨 두었다. 그 경고가 가리키던 기전이 바로 이것이다.

⛔ **`strip()` 이 막아 주지 않는다.** 그 함수는 앞뒤 **공백**만 걷는다 — 명령 태그는 내용이다.
그런데 오늘 낮에 이 자리를 고치면서 README 에 *"`psql_cli.psql()` 은 stdout 을 `strip()` 해서
돌려주므로 위 방식은 그 오염을 만들지 않는다"* 라고 **틀린 문장을 적었다.**

⚠️ **왜 낮에 못 잡았나 — 검증 입력이 반증할 수 없는 것이었다.** 그때는
`psql('select gen_random_uuid()')` 로 확인했고 36바이트가 나와 통과했다. **`select` 에는 명령 태그가
없다.** 즉 그 확인은 「오염이 없다」를 세운 것이 아니라 **오염이 생길 수 없는 입력을 골랐던 것**이다.
⇒ 규율: **고치는 대상과 같은 모양의 입력으로 재현한다.** 여기서는 `insert … returning` 이다.

**고친 것**: `psql_cli.psql()` 에 `-q` 를 넣어 태그를 없앴고, 같은 명령을 다시 돌려 파일이
**36바이트**인 것을 확인했다. README 의 틀린 문장은 **지우지 않고 정정으로 남겼다** — 그 문장을
믿고 넘어갈 다음 사람을 막는 것이 그 자리의 값이다.

## 4. 판정

**통과.** 026 이관 뒤에도 실물 소켓 경로가 새 스키마를 지나가고, 결과 API·일일·히스토리·주간 경로가
전부 200 이며, teardown 이 기준선으로 정확히 복귀한다.

⚠️ **이 회차가 세우지 못한 것**: 실물 Claude·Nova 왕복(0회) · 브라우저 레그(C계층) · 분석 워커를
지나가는 경로. 그 셋은 각자의 절차가 소유하고 이 회차의 범위가 아니다.

⛔ **남는 관찰 하나**: `harness_sessions` 에 학습 세션이 지워진 고아 행이 **89건** 있다. 이 회차가
만든 것이 아니고(회차 전에도 88건) 그 표가 「어느 세션이 하네스 것이었나」의 기록이라 정상이다 —
세는 서술을 남기는 대신 이 문장으로 남긴다.
