---
id: TASK-222
title: '정리 회차: 백엔드 앱 소스 전체 (codebase-cleanup)'
status: Done
assignee: []
created_date: '2026-09-19 00:18'
updated_date: '2026-09-19 01:03'
labels: []
dependencies: []
ordinal: 283000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 결정 2026-09-19 — 범위는 app/backend/app 전체(63파일 15,629줄). 프런트는 테스트 러너가 0건이라 회귀 게이트가 없어 제외했고, 러너 도입은 별 작업으로 둔다. 기준선(이 턴 실측): HEAD 07e81ef · 수집 1400 · 통과 1400(skip 0 이라 두 수가 같음) · ruff exit 0 · ruff format 305 files · ty exit 0 · tsc 0 · eslint 0 · next build 0. 규칙군 전수: 0건 다섯(C4 LOG PIE TID RSE) · PERF 1 RET 1 FURB 2 ISC 2 SIM 3 ARG 4 · ANN 10 RUF 18 PL 23 TRY 59 EM 59. ARG 넷은 포트 구현의 미사용 인자이고 ISC 둘은 의도한 줄바꿈 f-string 이라 둘 다 켜지 않는다. noqa 표식은 BLE001 한 건뿐이고 살아 있다(직전 회차 TASK-144.1 이 그 축을 이미 수확함). ⛔ 문면 정본 검사가 SYSTEM_PROMPT 부분 문자열 12건 포함으로 많다 — 그 문면을 건드리면 FAIL 하고, 그때 검사를 고치지 않고 내 변경을 고친다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 리뷰 여섯 갈래를 읽기 전용으로 돌려 지적을 수집하고 신뢰도로 통합한다
- [x] #2 동작변경=예 인 지적은 갈라내 별 태스크로 등록한다
- [x] #3 적용 뒤 수집 개수가 1400 이상이고 게이트 여덟이 통과한다
- [x] #4 위반 0건 규칙군을 켜서 안전망을 늘린다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 리뷰 여섯 갈래 — 2026-09-19 미도착 상태로 마감

착수: `cb-reuse` · `cb-simplify` · `cb-efficiency` · `cb-altitude` · `cb-stale`(도구 낡음 · 범위가
tests·scripts 까지) · `cb-codex`(외부 모델 · 회귀 위험). 여섯 다 읽기 전용 제약과 건수 상한을 걸어
띄웠음.

경과: 6분에 전부 `running` → 17분에 전부 `idle` → 27분에 직접 제출 요청(`SendMessage` 여섯) →
36분에도 **결과 0건이고 상태 변화도 없었음.**

⚠️ **직전 회차(`TASK-220`)와 다른 모양임** — 그쪽은 같은 지점에서 직접 요청을 보내자 다시 `running`
이 됐고 약 20분에 결과가 왔음. 이번에는 요청 뒤에도 `idle` 그대로였음.
⛔ **원인을 지목하지 않음.** 직전에 표본 다섯으로 「전달 경로 고장」을 단정했다가 틀렸으므로, 지금
말할 수 있는 것은 **「36분과 직접 요청 한 번으로는 도착하지 않았다」** 뿐임.

⇒ **후계 세션이 리뷰를 다시 띄워야 함.** 이 노트의 프롬프트 설계(각도 하나씩 · 읽기 전용 ·
건수 상한 · `동작변경` 표기 · 죽은 코드 주장에는 명령 출력 첨부)는 그대로 재사용하면 됨.

## 이 회차에서 실제로 끝난 것

규칙군 다섯(`C4`·`LOG`·`PIE`·`TID`·`RSE`)을 켰음(`232fda1`) — AC4 충족. 세 트리 전부 0건이라
per-file-ignores 가 필요 없었고, 켜지 않기로 한 것(`ARG` 4건은 포트 구현 · `ISC` 2건은 의도적
줄바꿈 · `TRY`·`EM`·`PL`·`RUF`·`ANN` 은 건수 초과)의 근거를 `pyproject.toml` 에 적었음.

기준선 대조: 수집 **1400 유지** · 통과 **1400** · `ruff` 0 · `format` 305 · `ty` 0 · 프런트 셋 0.
⇒ **회귀 0.** AC1~3 은 리뷰가 와야 닫히므로 미충족으로 남김.

## 정정 — 리뷰 여섯이 «도착했음» (약 46분 · 직접 요청 뒤)

앞 노트의 「36분에도 결과 0건이라 버렸음」은 **틀렸음.** 여섯 다 결과를 냈음.
⇒ 두 회차에서 같은 형태가 반복됐음: `idle` 이 된 뒤에도 20~46분까지 결과가 올 수 있고,
**직접 제출 요청이 그 전달을 촉발하는 것으로 보임**(둘 다 요청 뒤에 왔음 · 인과는 미확정).
⛔ **`idle` 을 완료도 미완료도로 읽지 않음** — 이 세션이 그 오독을 두 번 했음.

## 갈래 수렴으로 세운 신뢰도 (스킬 §3)

**3갈래가 같은 자리를 지목 — 가장 값이 큼**

1. `services/recordings.py:557` — 2다리 고아 스윕만 살아 있는 세션을 리터럴 `"active"` 로 판정함.
   정본은 `sessions.LIVE_SESSION_STATUSES` 이고 같은 파일이 세 자리에서 그것을 읽음(`:107`·`:124`·
   `:396`). `TASK-140` 이 025 의 `paused` 추가에 맞춰 세 자리를 고치고 **이 한 자리를 지나쳤음.**
   ⇒ 정지 중 쉐도잉 세션의 열린 `.part` 가 「`.part` 는 언제나 고아」 규칙으로 지워짐. 워커 유휴
   1Hz 경로라 도달성이 높음. 단순화·고도·효율 세 갈래가 각각 짚었음. **동작변경=예.**
2. `workers/analysis_worker.py:220-239` — job 종류를 if/elif 로 갈라내고 나머지를 `process_analysis`
   로 보냄. codex 가 **테스트 공백을 확인했음**: `JOB_TYPE_SUMMARIZE_WEEK` 만 라우팅 테스트가 있고
   (2026-09-14 에 그 분기를 지웠는데 21건이 통과한 사건 때문에 생겼음) **scenario·summarize 분기는
   같은 공백이 열려 있음.** 단순화·고도도 같은 자리를 지목했음.

**2갈래**

3. `services/jobs.py:386` — `f"{type(exc).__name__}: {exc}"` 가 15 자리에 복제됨(다섯 모듈 각 3).
   `last_error` 는 partial_failure 화면이 읽는 계약인데 그 형식의 소유자가 없음. 동작변경=아니오.

**1갈래이지만 계측이 단단함 (효율)**

4. `analysis_jobs.utterance_id` 를 종단 행까지 덮는 인덱스가 없어 결과 폴링(2초)과 유휴 스윕(1Hz)이
   표 전체를 훑음. 실측 계획 둘 다 Seq Scan(`_JOB_COUNTS_SQL` 0.329ms · `flush_ended_sessions`
   0.643ms). 대안은 `create index on analysis_jobs (utterance_id, job_type)` 한 줄.
5. `jobs.py:266`·`:284` — 리퍼·claim 두 문장이 매초 전체 순차 스캔. ⛔ **`jobs.py:257-260` 의
   *"one indexed UPDATE"* 서술이 실제 계획과 어긋남**(계획은 Seq Scan). 대안은 부분 인덱스
   `(available_at) where status in ('pending','running')`. UNION ALL 재작성은
   `for update skip locked` 를 실을 수 없어 기각(직접 확인).
6. `recordings.py:544-561` — 세션 디렉터리마다 조회 2건인 N+1. 매초 왕복 2N 건.
7. 유휴 회복 스윕 셋이 1Hz 인데 고유 해상도는 60초·1일임(`ORPHAN_IDLE_GRACE=60s` · 당일 경계).
   **동작변경=예**(회복 지연이 늘고 그 지연이 화면에 보임).

## 나머지 지적 전문 — 갈래별

**재사용 7건** (전부 동작변경=아니오 · `cb-reuse`)
1. `models/{scenario_draft:57,session_summary:70,weekly_report:51}.py` 의 `_loaded()` 가 예외 클래스만
   다른 **바이트 동일 3벌**(기계 diff 로 0줄 차이 확인). ⚠️ `_json_candidates` 는 결정 86 으로 2벌을
   «일부러» 두고 parity 테스트로 묶었는데 **`_loaded` 에는 그 테스트가 없음.**
2. `jobs.py:386` 실패 메시지 15자리 → `report_exception(pool, job, exc)` 신설.
3. 세션 전사문 서브쿼리가 `session_summary.py:50` 과 `scenario_generator.py:140` 에 동일 복제.
   `sessions.py:190 LIVE_SESSION_STATUSES_SQL` 이 「단편을 상수로 내보내 f-string 에 끼우는」 기전의
   선례임.
4. naive datetime 가드 메시지가 `recordings.py:298`·`:427`·`daily_summary.py:358` 에 복제 —
   `jobs.py:106 _require_aware` 가 소유자. **호출부 네 곳은 그대로 둠**(이중 검사가 의도임).
5. 「학습자의 당일」 계산이 `daily_summary._today_in` 과 `recordings.day_start_for` 두 곳.
   `day_start_for` 독스트링이 이미 「둘째 소비자가 생기면 공용으로 옮긴다」고 예고했음.
6. `fixtures._tone_wav` 가 RIFF 헤더를 손으로 조립 — `recordings.wav_from_pcm` 과 **6444바이트 동일**
   (직접 돌려 확인). ⛔ 직접 import 하면 `TASK-221` 이 없앤 `app.services` 전이 의존이 되살아남 ⇒
   조립을 순수 모듈(`models/recording.py`)로 옮기고 규격을 인자로 받는 형태가 맞음.
7. `nova.py:1505`·`:1607`·`:1639` 의 `contentEnd` 봉투 3벌 → `_content_end(name)`.
⚠️ **의도된 중복 9건은 보고에서 제외했음**(결정 86 · `RECORDING_*` 대 `nova.SAMPLE_RATE_HZ` 등).
⚠️ 낡은 주석 1건: `scenario_progress.py:34` 가 「공용 타임존 헬퍼를 만들지 않았다」고 적었으나 같은
파일이 `:30` 에서 그것을 import 함(`TASK-146` 이 만들었음).

**단순화 8건** (`cb-simplify`)
1. `pronunciation.py:85`+`:412` — pending/판정 UPDATE 두 벌이 두 컬럼만 다르고 `_insert_attempt`
   호출 2벌은 인자까지 동일. 약 60줄이 12줄로 접힘. 주석이 그 위험을 이미 적어 뒀음(가드가 주석임).
2. `recordings.py:557` — 위 수렴 1번.
3. `results.py:154` — `partial_failure` 가 `status == "partial_failure"` 와 다섯 갈래 전부에서 같음
   ⇒ 필드를 없애고 property 로. ⚠️ 프런트가 그 키를 선언만 하고 읽지 않음(`lib/api.ts:88`).
4. `jobs.py:386` — 위 수렴 3번(같은 자리).
5. `analysis_worker.py:156` — 90줄 루프 본문·5단 들여쓰기. `_HANDLERS` 표 + 유휴 블록 추출로 약 10줄.
6. `api/ws.py:151-234` — `_load_*_or_none` 네 벌이 fallback 만 다른 같은 5줄. 이미 하나가 갈렸음.
7. `sessions.py:498`·`:595` — `start_shadowing_session` 이 `create_session` 의 insert 를 재구현(10줄).
8. `session.py:903` — `_send` 가 아무것도 더하지 않는 한 홉(12 호출부). 값이 가장 낮음.
⚠️ 비발견 2건: `scenario_progress.py` 는 제품 호출자가 0이지만 **의도임**(독스트링이 근거) ·
`jobs.enqueue_analyze` 는 죽지 않았음(`tests/harness/inject_errors.py:174` 가 부름).

**고도 6건** (`cb-altitude`)
1. `recordings.py:557` — 위 수렴 1번. **동작변경=예**
2. `session_summary.py:133`·`scenario_generator.py:274`·`weekly_report.py:340` — `jobs.complete` 의
   lease 판정 반환값을 **다섯 호출부 중 셋이 버림.** 둘은 각자 사설 `_LeaseLost` 를 만들어 롤백하고
   셋은 남의 job 에 쓴 결과를 그대로 커밋함. ⇒ `complete` 가 `jobs.LeaseLost` 를 올리게 하면 예외
   클래스 2벌이 1벌로 줄고 미검사 반환값 3이 0이 됨(총 장치 순감). **동작변경=예**
3. `analysis_worker.py:220-239` + `analysis.py:564-572` — 라우팅 표가 코드에 없고 주석 네 자리에
   있으며, 서비스의 종류 가드가 잘못 부른 호출자를 대신 거절함.
4. `daily_summary.py:312`·`367`·`424`·`454` — `timezone: str | None = None` 을 네 함수에 옵셔널로
   넘기는 근거가 한 호출자의 왕복 절약뿐이고, 라우터 둘은 언제나 값을 줌 ⇒ 필수 키워드로 바꾸면
   호출부 변경이 0이고 네 함수에서 조건 한 줄씩이 사라짐.
5. `nova.py:1401-1437` — 번역기가 싣지 않은 `toolUseId` 를 어댑터가 원본 body 로 되돌아가 덧칠함.
   `_on_control_tool_use` 가 처음부터 싣게 하면 이름 재판정·`model_copy` 재구성이 함께 사라짐.
6. `claude_client.py:182`·`:240` — 「규격 분기의 유일한 판정자」로 선언한 `is_openai_model` 을 응답
   쪽 두 함수가 쓰지 않음(모양 훑기와 키 폴백으로 대신함) ⇒ 선언한 소유가 실제로는 셋.
⚠️ 팩토리의 불리언 셋을 열거형으로 접는 것은 **제안에서 뺐음** — 그 표를 소유한
`services/session_modes` 를 팩토리가 import 할 수 없음(층 규칙).

**도구 낡음 6건 — 거짓 신호** (전부 동작변경=아니오 · `cb-stale` · 각각 증명 붙음)
1. `tests/unit/test_config.py:657` `test_credential_strings_isolated_to_config_module` — grep stdout 에서
   `config.py` 없는 줄 수만 셈. ⛔ **grep 이 대상에 닿았는지 검사하지 않음**: BSD grep 은 「디렉터리
   없음」과 「일치 0건」이 **rc·stdout·stderr 가 모두 같음**(빈 임시 디렉터리로 증명). 둘째 거짓 신호는
   면제가 줄 전체 부분문자열인 것 — `nova.py` 주석이 `config.py` 를 언급만 해도 같은 줄의 실제 참조가
   면제됨. ⇒ 양성 대조 추가 + 면제를 정확 경로로 + `returncode in (0,1)` 가름(`test_shadowing_seed.py:181`
   이 선례이고 그것은 **이 세션의 `TASK-219` 가 만든 것**).
2. `tests/unit/test_plan_models.py:404` `test_cefr_levels_match_the_schema_check` — 이름은 SQL CHECK 와의
   일치를 약속하는데 본문은 리터럴 튜플 한 줄. SQL 을 입력으로 받지 않음(그 파일의 `.sql` grep 0건).
   슬립 입력: 마이그레이션 001:18 에서 `'C2'` 삭제 → 통과함. ⇒ `test_schema.py:1665 _check_values` 가
   올바른 걸음걸이이나 **그 정규식이 소문자 전용이라 CEFR 대문자를 못 뽑음**(실측: `[]` → 넓히면 여섯)
   ⇒ 문자 집합을 `[A-Za-z_0-9]` 로 넓히는 것이 선행함.
3. `tests/unit/test_weekly_report_job.py:257` `test_the_insight_cap_matches_the_prompt` — 프롬프트 빌더를
   import 하지 않으므로 **어떤 입력으로도 실패할 수 없음.** 슬립 입력: `weekly_report.py:228-232` 의
   `최대 {max_points}개` 를 `최대 5개` 로 굳힘 → 정상 응답이 매번 거부되는데 통과함.
4. `scripts/smoke_analysis.py:392` — `"the" in target_form` 이 `there`·`them`·`these`·`another`·
   `whether`·`together` 에도 참임(실측 표). 실물 모델 증거의 유일한 자리인데 낱말 경계가 없음.
5. `tests/unit/test_scenario_prompt.py:98`·`test_summary_prompt.py:95`
   `test_is_deterministic_for_the_same_input` — 한 프로세스에서 순수 함수를 두 번 부름. 프로세스 간
   불안정이 관측 창 밖임: `PYTHONHASHSEED=random` 4회에서 **단정은 매번 통과하는데 프롬프트 바이트가
   실행마다 달랐음**. 슬립 입력은 `allowed_categories` 에 `frozenset` — 같은 파일 `:241` 은 tuple,
   `:257` 은 `frozenset` 을 같은 인자에 넘김. 지금 제품을 붙들고 있는 것은 SQL 의 `order by 1` 하나뿐.
6. `tests/integration/test_pronunciation_service.py:628` — `None == None` 로 만족됨(그 컬럼이 실제로
   nullable 이고 `None` 이 같은 파일 `:609` 에서 정상 결과로 단정됨). ⚠️ 범위 한정: 전면 회귀는 같은
   파일 `:474` 가 잡으므로 이 단정 하나의 판별력 문제임.
⚠️ 버린 후보 3건의 근거도 함께 왔음(`test_shadowing_seed.py` 의 빈 루프는 `:174` 가 막음 등).

**회귀 위험 8건** (`cb-codex` · 전부 동작변경=예 · 「정리하다 조용히 깨질 자리」)
정리 적용 시 **건드리면 안 되는 자리** 목록이므로 적용 묶음과 함께 읽어야 함.
- 테스트가 **못 잡는** 것 넷: ⑴ 워커 라우팅 분기(scenario·summarize) ⑵ `session.py:406-428`
  `_record_pronunciation` 을 `create_task` 로 바꾸면 pending 행 경쟁으로 **엉뚱한 행이 닫힘**(동시성
  테스트 0건) ⑶ `ws.py:344` `live_sessions.add` 를 뒤로 옮기면 리퍼가 준비 중 세션을 `failed` 로 닫음
  ⑷ `recordings.py:335-356` `finalize_recording` 의 「rename 먼저, 포인터 나중」을 뒤집으면 포인터만
  있는 행이 생김(부분 커버리지만 있음).
- 테스트가 **잡는** 것 넷: `_close_and_record` 의 `pool.acquire()` 두 블록 병합(`TASK-137` 재발) ·
  `ws.py:366-368` 지역변수 이름을 함수명과 같게 바꾸면 `UnboundLocalError` · `_store_final` 의
  `create_task`+`shield` 제거 · `_save_final` 에서 `_paused` 검사를 분류보다 앞으로 옮기면 음성 resume
  이 영구 불가(`_classify_user_final` 이 순수해 보이지만 상태를 바꿈).

**효율이 계측해서 버린 것**: 오디오 프레임 왕복 base64(31Hz 이지만 같은 함수의 네트워크 전송에 묻힘) ·
세션 시작의 `pool.acquire()` 다섯(세션당 1회 · 뒤가 초 단위 핸드셰이크) · job 1건당 1회 경로들.

## 갈라낸 태스크 여섯 (스킬 §3 의 「갈라낸다」)

| 태스크 | 무엇 | 동작변경 |
|---|---|---|
| `TASK-223` | 결함: 고아 스윕이 정지 중 세션의 `.part` 를 지움 (**3갈래 수렴**) | 예 |
| `TASK-224` | 결함 후보: lease 를 잃은 뒤 커밋하는 호출부 셋 | 예 |
| `TASK-225` | 워커 라우팅을 표로 + 누락 분기 테스트 | 예(테스트 먼저) |
| `TASK-226` | 적용: 동작변경 없는 지적 전부(재사용 7 · 단순화 6 · 고도 3) | 아니오 |
| `TASK-227` | 효율: `analysis_jobs` 인덱스 둘 + 왕복 줄이기 | 아니오 |
| `TASK-228` | 테스트 강화: 거짓 신호 여섯 | 아니오 |

⛔ **이 회차에서 적용한 것은 규칙군 다섯뿐임**(`232fda1`). 사용자 결정(2026-09-19)이 「결과만 받아
원장에 적고 마감」이었으므로 나머지는 전부 위 태스크로 넘겼음.
⛔ **`TASK-226` 을 착수하기 전에 이 노트의 회귀 위험 8건을 읽음** — 그 목록이 「정리하다 조용히
깨질 자리」이고 넷은 테스트가 못 잡음.

## 기준선 대조 (마감 시점 실측)

수집 **1400 유지** · 통과 **1400** · `ruff` 0 · `format` 305 · `ty` 0 · `tsc` 0 · `eslint` 0 ·
`next build` 0 ⇒ **회귀 0.** 파일을 고친 리뷰어는 없었음(여섯 다 읽기 전용 제약을 지켰음).
<!-- SECTION:NOTES:END -->
