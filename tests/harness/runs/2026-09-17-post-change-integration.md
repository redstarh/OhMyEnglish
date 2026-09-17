# 회차 — 기준선 표 이관·프롬프트 변경 뒤 통합 확인 (`TASK-155`)

test-agent 스레드(팀리드 위임) · 2026-09-17 · 브랜치 `design/first-vertical-slice` · 기준 커밋 `a00d826`
`run_id` = `2025f442-8b0d-433a-89a4-036b7a76e043` (직전 회차 `ce91b38e-…` 는 닫혀 있었다)

> **왜 이 회차인가**: 이 세션이 오늘 `TASK-153`(하네스 기준선 표 둘을 `public`/`redstar` →
> `ohmyenglish`/`ohmy` 로 이관) · `TASK-116.5`(`SYSTEM_PROMPT` 규칙 9 에 「소리를 따옴표로 따로 인용하라」)
> 를 넣었다. 게이트는 **테스트 DB** 에서만 도므로 **dev DB 와 실물 소켓 경로**를 지나가는 확인이 따로
> 필요하다. 비교 기준은 `runs/2026-09-17-post-migration-integration.md` 이고 같은 절 구성으로 적는다.
>
> ⛔ **스택은 호출자가 세웠고 이 회차가 손대지 않았다**: 백엔드 pid **19296** ·
> `WORKER_ENABLED=false VOICE_ADAPTER=stub --log-level warning` · `:8002`. 실물 Claude·Nova 호출 **0회**.

---

## 0. 상한과 판정 규칙 — 돌리기 전에 적는다

* **회차 1건 · 시나리오 A1 하나.** 재는 것은 분포가 아니라 **회귀가 없는가** 하나다.
* ⛔ **`TASK-116.5` 의 «준수» 는 이 회차가 재지 못한다** — `VOICE_ADAPTER=stub` 이라 프롬프트가 실려
  나가지 않는다. 재려고 시도하지 않았다. 그 측정은 `TASK-154` 가 갖는다.
* **워커를 켜지 않았다.** 켜면 복습 시계가 움직이고 teardown 이 그것을 되돌리지 못한다
  (`browser_leg.md` §8-0 의 「drift 0 이 되돌아왔다를 뜻하지 않는다」).
* **앱 소스를 고치지 않았다.** `git status` 가 회차 시작·종료에 모두 비어 있고 `HEAD` 가 `a00d826`
  그대로다(회차 중 다른 세션의 커밋도 없었다).
* ⛔ **「통과」를 로그 없음으로 주장하지 않는다** — 로그 채널이 실제로 오류를 잡는지 §3 에서 먼저
  증명했다. 그 증명 없이는 「0건」이 「오류가 없다」와 「로그가 그 프로세스의 것이 아니다」를 구별하지
  못한다.

## 1. 기준선 (회차 전 · 이 회차가 직접 읽었다)

| 표 | 값 |
|---|--:|
| `learning_sessions` | 17 |
| `utterances` | 128 |
| `error_patterns` | 9 |
| `review_tasks` | 15 |
| `analysis_jobs` | 57 |
| `schema_migrations` | 24 |
| `harness_runs` | 27 |
| `harness_sessions` | 99 |
| `harness_pattern_baseline` | 9 |
| `harness_review_task_baseline` | 15 |

호출자가 넘긴 값 여덟과 **전부 같았다** — 회차를 열기 전에 대조했다. 접속 좌표도 직접 읽었다:
`current_database()`=`ohmyenglish` · `current_user`=`ohmy` · `current_schema()`=`ohmyenglish` ·
`search_path`=`ohmyenglish, public`.

**표의 실제 자리** (`pg_class`·`pg_namespace` — `information_schema` 로 묻지 않았다):
`harness_pattern_baseline`·`harness_review_task_baseline`·`learning_sessions`·`utterances`·
`error_patterns`·`review_tasks`·`harness_runs`·`harness_sessions` 여덟이 전부
**`ohmyenglish` 스키마 · 소유자 `ohmy` · `relkind=r`**. `public` 에는 En-Coach 호환 **뷰**만 남았고
(`public.error_patterns` `relkind=v`) **`public.harness_*` 은 하나도 없다.** ⇒ `TASK-153` 이 의도한 자리다.

## 2. 관측

### 2-1. API 프리플라이트 — 넷 전부 `200`

| 경로 | 코드 | 본문 |
|---|--:|---|
| `/api/daily-summary` | 200 | `summary_date=2026-09-17` · `analyzed=false` · 키 전부 있음 |
| `/api/history` | 200 | `streak{current:0,longest:2}` + `days` 배열 (3568바이트) |
| `/api/sessions/next-plan` | 200 | 한국어 이유 문장 + `target_level=A2` |
| `/api/weekly-report` | 200 | `{"week_start":null,"analyzed":false,"metrics":{},"insights":{}}` |

⚠️ `/api/weekly-report` 의 빈 값은 결함이 아니다 — `daily.py:get_weekly_report` 가 *"행이 없어도 404 가
아니다 … `analyzed` 가 그것을 값으로 말한다"* 를 명시한 규약이고 키가 전부 실려 있다.
teardown 뒤에 넷을 **다시** 불러 전부 `200` 인 것을 확인했다.

### 2-2. 실물 소켓 세션 (`ws_session.py --scenario A1`)

프레임 **17개**, 순서 `session_started → (final/partial ×3턴) → audio ×3 → session_ended` —
기준 회차와 **글자 그대로 같다**. `elapsed` 0.037s. 원자료: `.harness/evidence/A1-frames.json` (2.0k).

| 확인 | 값 |
|---|---|
| `session_id` | `d45f3270-4dbd-4016-ae0f-adc4d7682a18` |
| 그 행이 실제로 어느 표인가 | **`ohmyenglish.learning_sessions`** (`tableoid` → `pg_class` 조회) |
| 세션 행 | `mode=speaking` · `status=completed` · `learning_source=recommended` |
| 발화 | **6건** (agent/user 교대) |
| 하네스 등록 | `harness_sessions` 에 `run_id=2025f442…` · `scenario=A1` |
| `analysis_jobs` | 이 세션에 **3건** 전부 `pending` — 워커를 껐으므로 정답이다 |
| 결과 API | **200** · `{"status":"analyzing","partial_failure":false,"pronunciation":[],"awaiting_analysis":false}` |
| 회차 중 표 값 | `learning_sessions` 18 · `utterances` 134 · `analysis_jobs` 63 · `error_patterns` 9 · `review_tasks` 15 |

`error_patterns`·`review_tasks` 가 회차 내내 움직이지 않았다 — 워커를 껐으므로 분석 쓰기가 없었다.

### 2-3. `browser_leg.md` §8-0 — drift 대조와 재스냅샷이 새 스키마·소유자에서 그대로 돈다

**① drift 대조 (`drop` 전에 · 네 컬럼 전부)**

| 대조 | 값 |
|---|--:|
| `harness_pattern_baseline` ⨝ `error_patterns` (`frequency`·`last_seen_at`·`next_review_at`·`mastery_score`) | **0** |
| 그 조인 행 수 / baseline 행 수 | 9 / 9 |
| `harness_review_task_baseline` ⨝ `review_tasks` (`status`·`completed_at`·`due_at`) | **0** |
| 그 조인 행 수 / baseline 행 수 | 15 / 15 |

**② 파일 사본 대조 (`drop` 전에)** — DB 표 하나에 진실을 걸지 않는다.
`runs/2026-09-17-pattern-baseline-v3.tsv`(9행) 와 **완전 일치**,
`runs/2026-09-17-review-task-baseline.tsv`(15행) 와 **집합 일치**.
⚠️ review 쪽은 **행 순서만** 달랐다 — 파일은 다른 정렬 키로 떴다(값은 15행 전부 같다). 정렬을 맞춰
비교하면 차이 0이다. 파일 머리말에 정렬 키를 적어 두면 다음 회차가 이 확인에 1분을 덜 쓴다.

**③ 재스냅샷** — `drift 0` 을 통과한 뒤 `drop`/`create table as` 를 **`ohmy` 로** 돌렸다(superuser 를
쓰지 않았다). 결과: 두 표가 다시 **`ohmyenglish` 스키마 · 소유자 `ohmy`** 에 9행·15행으로 생겼고,
재스냅샷 직후 drift 가 둘 다 **0**, 값이 파일 사본과 다시 **일치**했다.
⇒ `TASK-153` 이 닫으려던 것 ⑴ (`ohmy` 로 읽지도 지우지도 못했다) 이 실제로 닫혔다.

**④ `pg_dump -n ohmyenglish`** — `TASK-153` 이 닫으려던 것 ⑵ (`H-BT`: `redstar` 소유 표 하나가 덤프
전체를 막았다) 를 직접 쟀다. 종료코드 **0** (파이프에 걸지 않고 직접 읽었다) · **141k** ·
`COPY` 블록 **21개**. 덤프 안의 행 수가 DB 와 정확히 같다:
`harness_pattern_baseline` 9 · `harness_review_task_baseline` 15 · `error_patterns` 9 ·
`review_tasks` 15 · `learning_sessions` 17 · `utterances` 128 · `schema_migrations` 24.
⇒ 「데이터 0줄인 덤프를 떴다고 믿는」 함정(`-n public`)에 걸리지 않았다.

### 2-4. teardown

`①-a` 시간창 스윕(`WINDOW_START` = `2026-09-17 03:06:25.59414+00`) → 창 안의 세션은 **내 것 하나뿐**
이었다(§8-3 2번대로 지우기 전에 남의 것을 먼저 봤다) → `① DELETE 1` · `② UPDATE 0` · `③ DELETE 0`.

**④ 대조**: 시드 사용자 패턴 9 = baseline 9 · pattern drift **0**(2컬럼·4컬럼 둘 다) ·
review drift **0** · 내 `run_id` 에 남은 살아있는 세션 **0**. 삭제한 세션의 결과 API 는 `404`
(`{"detail":"session not found"}`) — 지운 것이 실제로 지워졌다.
teardown 뒤 두 baseline 표의 값이 **다시 파일 사본과 일치**했다.

| 표 | 기준선 | teardown 뒤 | 판정 |
|---|--:|--:|---|
| `learning_sessions` | 17 | **17** | 같다 |
| `utterances` | 128 | **128** | 같다 |
| `error_patterns` | 9 | **9** | 같다 |
| `review_tasks` | 15 | **15** | 같다 |
| `analysis_jobs` | 57 | **57** | 같다 |
| `schema_migrations` | 24 | **24** | 같다 |
| `harness_runs` | 27 | **28** | **+1 — 이 회차가 연 `run` 행이다. 감사 기록이라 지우지 않는다** |
| `harness_sessions` | 99 | **100** | **+1 — 학습 세션이 지워진 고아 행. 「무엇을 지웠는지」의 기록이라 남는다** |

⚠️ 여덟 중 둘이 늘어난 것은 **회귀가 아니라 설계**다. 기준 회차도 같은 모양이었다
(`harness_sessions` 98 → 99). teardown 이 지우는 것은 `learning_sessions` 이고 감사 두 표는 남는다.

**⑤ 프로세스·환경**: §8-⑤ 의 예외를 적용했다 — 백엔드를 **호출자가 세웠으므로 재기동하지 않고
「무변경」을 증거로 적는다**. `lsof -nP -iTCP:8002 -sTCP:LISTEN -t` = **19296**(회차 시작과 같은 pid) ·
`ps -p 19296 -Eww` 의 `WORKER_ENABLED=false`·`VOICE_ADAPTER=stub`(회차 시작과 같음) ·
`/health` = `{"status":"ok"}`. `app/backend/.env` 는 열지도 않았다.

## 3. ⛔ 「로그 오류 0건」을 주장하기 전에 채널을 증명했다

**문제**: `/tmp/omy-backend.log` 가 회차 내내 **0바이트**였다. 그 상태의 「오류 0건」은 「오류가
없다」와 **「그 파일이 지금 도는 백엔드의 것이 아니다」** 를 구별하지 못한다.
⚠️ 그리고 `browser_leg.md` §2 의 P5 가 쓰는 신원 확인(`Started server process [pid]` 를 로그에서
찾는다)이 **이 스택에서는 성립하지 않는다** — 그 줄은 INFO 이고 백엔드가 `--log-level warning` 으로
떠 있어 애초에 찍히지 않는다.

**신원은 파일 내용이 아니라 fd 로 확인했다** — 이것이 P5 의 방식보다 강하다:

```
lsof -p 19296 → Python 19296 redstar 1w REG /private/tmp/omy-backend.log
                Python 19296 redstar 2w REG /private/tmp/omy-backend.log
```

즉 그 파일은 pid 19296 의 **stdout·stderr 그 자체**다.

**판별력은 무력화해서 쟀다.** 앱 소스를 고치지 않고, 값역 밖 `?source=` 로 `/ws/session` 에 붙였다
(`ws.py:303` 의 `logger.exception` 경로 · `learning_sessions_learning_source_check` 가 insert 를 거부한다).
결과: 로그가 **0줄 → 32줄**(`세션 행을 만들 수 없어 연결을 닫는다` + `CheckViolationError` 트레이스백)
이 되고, 클라이언트는 `{"type":"session_failed","reason":"session_create_failed"}` 를 받고 `1000` 으로
닫혔고, **`learning_sessions` 는 18 에서 움직이지 않았다**(insert 가 거부됐으므로 행이 생기지 않는다).

⇒ **채널이 오류를 잡는다는 것이 증명됐고, A1 회차와 teardown 이 그 채널에 남긴 줄은 0이다.**
주입 뒤에도 로그는 정확히 32줄에 머물렀다(33줄 이후가 없다) — 32줄 전부가 내가 만든 것이다.

⚠️ **이 자리를 다음 회차가 다시 발명하지 않게 적는다**: `--log-level warning` 스택에서는 P5 의 로그
기반 신원 확인을 **`lsof -p <pid>` 의 fd 1w·2w 로 갈아탄다.** 그것이 이 회차가 실제로 쓴 방법이다.

## 4. 판정 — 통과 (회귀 0건)

| AC | 판정 | 근거 |
|---|---|---|
| #1 API 프리플라이트 넷이 200 이고 로그 오류 0 | **통과** | 넷 전부 `200`(teardown 뒤 재확인도 `200`) · 회차 로그 **0줄**, 그 채널이 오류를 잡는다는 것을 §3 에서 32줄로 증명했다 |
| #2 실물 소켓 세션이 `ohmyenglish` 스키마에 기록되고 결과 API 200 | **통과** | `tableoid`→`pg_class` 가 `ohmyenglish.learning_sessions` · 발화 6건 · 결과 API `200 analyzing` |
| #3 §8-0 의 drift 대조와 스냅샷이 새 스키마·소유자에서 그대로 돈다 | **통과** | drift 0/0(9=9 · 15=15) · `ohmy` 로 `drop`+`create` 성공 → `ohmyenglish`/`ohmy` 9행·15행 · `pg_dump -n ohmyenglish` exit 0 · 141k |
| #4 teardown 뒤 표가 기준선과 정확히 같다 | **통과** | 다섯(17·128·9·15·57) + `schema_migrations` 24 가 전부 같다. 감사 두 표만 +1 (설계상 남는 행) |

⚠️ **이 회차가 세우지 못한 것 — 범위 밖이다**:
`TASK-116.5` 의 프롬프트 **준수**(코치가 실제로 소리를 따로 인용하는가 — `stub` 이라 프롬프트가 실려
나가지 않는다 · `TASK-154` 소유) · 실물 Claude·Nova 왕복(0회) · 브라우저 레그(C계층) ·
분석 워커를 지나가는 경로 · 프런트엔드 화면.

⛔ **결함 0건.** `TASK-153` 이 닫으려던 두 결과(⑴ `ohmy` 가 못 읽고 못 지운다 · ⑵ 덤프 전체가 막힌다)
가 실제로 닫힌 것을 각각 재서 확인했고, `TASK-116.5` 는 이 경로에 회귀를 남기지 않았다.

⛔ **남는 관찰 하나**: `harness_sessions` 의 고아 행이 이 회차 뒤 **100건**이다. 이 회차가 1건을
더했고 나머지는 이전 회차들의 것이다 — 그 표가 「어느 세션이 하네스 것이었나」의 감사 기록이라
정상이다. 세는 서술을 남기지 않고 이 문장으로 남긴다.
