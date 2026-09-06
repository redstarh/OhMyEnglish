# 실측된 함정 — 반복하지 말 것

> **이 파일의 역할**: 실제로 밟아 본 함정만 모은다. 추측한 위험은 넣지 않는다.
> handoff에서 옮겨 왔다 — 함정은 세션 상태가 아니라 **영구 지식**이라서 handoff가 짧게
> 유지되는 것을 방해하면 안 된다.
>
> **읽는 방법**: 전체를 읽지 않는다. 건드릴 영역의 절만 본다.
>
> **추가 규칙**: 항목마다 ① 무엇이 일어났는가 ② 어떻게 알았는가(실측) ③ 대응. 재현 근거가
> 없으면 넣지 않는다. 번호는 재사용하지 않는다(다른 문서가 `H-x`로 인용한다).
>
> 최종 갱신 **2026-09-03** (**H-Y·H-Z 신설** — `explain analyze`가 쓰기 문장을 실제로 실행한다 · 문서 실행 경로에서 앱 INFO 로그가 안 보인다)

---

## 게이트·검사 도구

| # | 함정 | 대응 |
|---|---|---|
| **H-A** | **게이트의 cwd가 판정의 일부다.** 리포루트에는 ruff 설정이 없어 거기서 돌리면 기본 규칙으로 `check .` **56 errors** · `format --check .` **21 files**가 난다. 회귀가 아니라 다른 규칙셋이다 | 반드시 `cd app/backend` 후 판정한다. 설정 SoT는 `app/backend/pyproject.toml` 하나뿐이다 |
| **H-T** | **게이트를 돌리기 전에 DB가 떠 있어야 한다 — 안 떠 있으면 회귀처럼 보인다.** 실측(2026-08-31): `pytest -q`가 **`192 passed, 155 errors`**로 끝났다. 원인은 회귀가 아니라 `OSError: [Errno 61] Connect call failed ('127.0.0.1', 5433)`이었다 — podman **가상머신 자체가** 내려가 있었고(`podman machine list`의 LAST UP이 2개월 전) `ohmy-pg`도 `Exited`였다. 기동 후 **347 passed**로 복귀했다. **📌 그날 이 함정의 뿌리를 없앴다** — dev DB를 podman(:5433)에서 **homebrew `postgresql@17`(:5432)**로 옮겼다. launchd가 부팅 시 띄우므로 "가상머신이 2개월째 내려가 있는" 상태가 생기지 않는다 | **판별이 핵심이다: errors가 100건 넘게 한꺼번에 나면 코드를 의심하기 전에 연결을 의심한다** — 회귀는 이렇게 균일하게 무너지지 않는다. 게이트 기준선은 **347 passed**이고 `192 passed`는 DB 없이 돌 수 있는 부분집합이다. 확인은 `brew services list \| grep postgresql@17`. ⚠️ **이제 :5432가 정본이라 "5432는 남의 것"이라고 읽지 마라** — 이관 전 문서에 그런 서술이 있었다(`shared-database-naming-rules.md`에서 정정). 그 인스턴스는 StockAgent와 **공유**하므로 인스턴스 단위 조작은 하지 않는다 |
| **H-L** | **선언된 게이트에 구멍이 있다 — `ruff format`이 `tests/`를 보지 않는다.** 게이트는 `ruff format --check .`(cwd `app/backend`)이고 그 범위에 `tests/`가 없다. `ruff check`는 `../../tests`를 따로 돌리도록 문서화됐지만 **format은 그 짝이 없다.** 그래서 테스트 파일의 포맷 위반이 **무증상으로 커밋된다** — 두 태스크가 각각 1건씩 남겼고 코드리뷰가 잡았다 | 테스트를 건드린 커밋 전에 `.venv/bin/ruff format --check ../../tests`를 함께 돌린다. 잔존 **4건**(전부 `tests/harness/*`)이 기준선 — 이 수치가 늘면 내가 만든 것이다 |
| **H-K** | **`ty`의 검사 범위는 리포루트 `ty.toml`의 `[src] include = ["app/backend/app", "tests"]`다.** `app/backend/` 직하에 둔 파일은 **조용히 검사되지 않는다** — `x: int = "문자열"`도 통과한다. 타입 방어가 실제로 작동하는지 확인하려다 "ty가 못 잡는다"는 **잘못된 결론**을 낼 수 있다(실제로 한 번 냈다) | 타입 가드 검증용 임시 파일은 **`tests/` 안에** 두고 확인 후 지운다. `ty.toml:8`이 `[tool.ty]`를 pyproject에 추가하지 말라고 경고하는 것도 같은 이유다 |
| **H-F** | `ty`는 `tests/`까지 본다. 억제 주석은 **오류가 보고되는 그 줄**에 붙여야 한다 — 호출 첫 줄에 붙이면 `unused-ignore` 경고가 난다 | `bogus=1,  # ty: ignore[unknown-argument]` |

## DB·테스트 픽스처

| # | 함정 | 대응 |
|---|---|---|
| **H-B** | `python3 scripts/migrate.py`는 **돌지 않는다** — 시스템 python에 asyncpg가 없다 | `app/backend/.venv/bin/python scripts/migrate.py` |
| **H-E** | `db_conn` 픽스처는 테스트 하나를 **트랜잭션 하나**로 감싼다. CHECK 위반이 트랜잭션을 abort시켜 **한 테스트에 `pytest.raises`를 두 번 넣을 수 없다** | 음성 케이스마다 테스트를 쪼갠다 |
| **H-I** | **`db_conn` 픽스처는 마이그레이션만 적용하고 시드는 하지 않는다.** `select id from users limit 1`은 `None`을 돌려주고 not-null 위반으로 죽는다. 시드는 `scripts/migrate.py`의 `seed()`가 하고 `test_schema.py`만 그걸 명시 호출한다 | `db_conn` 테스트는 사용자·세션을 **직접 insert**한다(리포 관례 — `test_schema.py`·`test_utterances.py`·`test_jobs.py` 전부 자기 헬퍼를 쓴다). 커밋된 행이 필요하면 `db_pool`+`committed_session` |
| **H-J** | **트랜잭션 시각 함정은 1회 실행으로 안 드러난다.** `created_at default now()`(= 트랜잭션 시각)로 정렬하는 테스트가 **3회 중 1회만** 실패했다 — 한 번 돌려 통과하면 정상으로 보인다 | 순서·시각에 의존하는 테스트는 **최소 3~5회 반복 실행**으로 판정한다. 근본 대응은 정렬 키를 단조값으로 두는 것(004 `attempt_seq`) |
| **H-S** | **공유 DB의 세션 타임존은 UTC라서 `current_date`가 KST 날짜와 하루 다를 수 있다.** UTC 자정~09:00(KST) 구간이 전부 그 구간이다. 실측(2026-08-31 08:04 KST, `ohmyenglish`): `SHOW TimeZone`→`UTC`, `current_date`→**`2026-08-30`**, `(now() AT TIME ZONE 'Asia/Seoul')::date`→**`2026-08-31`**. **지금은 무해하다** — 우리 코드에 날짜 계산이 0곳이고(`current_date`·`::date`·`date_trunc`·`date.today()`·`datetime.now()` 전부 0건) 시각 컬럼은 전부 `timestamptz`, `date` 컬럼은 0개다. **§11(복습 주기 1·3·7일 · `next_review_at` · 일일 계획)이 이 칸을 처음 밟는다** | 달력 날짜는 `current_date`로 구하지 않는다 — `AT TIME ZONE`으로 사용자 타임존으로 변환한다. tz의 SoT는 **`users.timezone` 컬럼**(기본값 `Asia/Seoul`, 아직 앱이 읽지 않는다)이고 호스트 시간·세션 기본값이 아니다. `ALTER DATABASE … SET TimeZone`은 **걸지 않는다**(En-Coach와 공유 — 상대 서비스의 `current_date`가 조용히 바뀐다). 전역 규약은 `~/.claude/CLAUDE.md` "DB 시각·날짜 규약" |

## 실음성·분석 파이프라인

| # | 함정 | 대응 |
|---|---|---|
| **H-U** | **발화 종료 감지가 이르면 문장이 쪼개지고, 그 조각이 `error_patterns`에 없는 약점을 만든다.** 실측(2026-09-01, 실물 마이크 1회 · 세션 `bbfc3908`): `endpointingSensitivity=MEDIUM`에서 내 발화 **18건 중 4건이 문장 중간에 쪼개졌다** (쪼개진 조각의 저장 시각 차 1.05~2.54초 — **임계값이 아니다.** 임계는 N-1이 **약 480ms**로 실측했다(`scenarios-N-real-voice.md:52`) 즉 다음 말을 고르는 1초가 발화 종료로 읽힌다)(`"i'm going to"`⇢`"have a meeting"`). `services/utterances.py:140`이 발화마다 무조건 `enqueue_analyze`를 부르므로 **조각이 완전한 문장처럼 분석되고**, 분석기는 "주어 없음"을 정직하게 보고한다 — 주어는 앞 조각에 있다. 결과: occurrence **13건 중 7건이 조각산**이고 패턴 `verb_form_missing_subject`(freq 4)·`verb_form_missing_object`(freq 2)는 **100% 오탐**이다 | **오탐 패턴을 학습자의 실제 약점으로 읽지 마라.** 패턴을 근거로 쓰기 전에 그 occurrence의 `utterance.transcript`가 **문장으로 완결됐는지** 본다(종결 부호·주어 유무). `NOVA_ENDPOINTING_SENSITIVITY=LOW`는 **완화일 뿐 해소가 아니다**(3단뿐이라 조각을 0으로 못 만든다). **📌 2026-09-01 구조적으로 해소했다** — 분석 job은 저장이 아니라 **턴 경계**에서 걸리고(`flush_pending_analysis`), 분석 입력은 묶음 전사문을 이어붙인 것이다. 보존 데이터 재현에서 그 세션의 job이 18건 → 14건이 됐다. **조각은 여전히 생긴다**(임계는 그대로다) — 달라진 것은 조각이 **따로 분석되지 않는다**는 것뿐이다. 구현·잔여 위험은 `TASKS.md` **I-1**이 소유한다. ⚠️ 이 함정으로 이미 만들어진 오탐 패턴 2개는 삭제했지만, **실물 마이크 2회로 재발하지 않는지 확인하는 것이 남았다** |
| **H-V** | **`inet_server_port()`로는 어느 PostgreSQL에 붙었는지 판별할 수 없다.** 컨테이너 안에서도 5432로 듣기 때문에 호스트 :5433으로 붙어도 `5432`가 나온다 — 이관 검증에서 실제로 잘못된 "확인"을 한 번 냈다(2026-09-01) | `show server_version`으로 판별한다 — **`17.9`=homebrew(:5432) · `16.15`=podman 컨테이너(:5433)**. 포트를 물어보지 말고 **서버 정체**를 물어본다 |

## 타입·계약

| # | 함정 | 대응 |
|---|---|---|
| **H-D** | **유니온 타입을 넓히는 변경은 모든 소비처와 함께 착지해야 한다.** `AdapterEvent`에 5번째 타입을 넣자 `ty`가 `session.py`의 `event.kind`를 잡았다 — 분기가 없으면 런타임 `AttributeError`로 세션이 죽는다 | 포트 확장과 `isinstance` 분기를 **한 커밋에** |

## 문서·git

| # | 함정 | 대응 |
|---|---|---|
| **H-C** | `git add -A`가 `.claude/settings.json`을 끌어들인다 (untracked, gitignore 대상 아님) | 경로를 명시해 add한다. **그 파일을 지우지 마라** — 하네스의 "워크트리 금지"가 의존한다 |
| **H-H** | `PRD.md`는 `:29`~`:117`, `requirements-summary.md`는 `:15`~`:60`이 **줄 단위로 인용**된다(실측 13곳·5곳). handoff가 재작성되며 인용 5건이 실제로 깨진 전례가 있다 | 새 내용은 **문서 끝에만** 추가. 기존 절은 **한 줄 → 한 줄** 교체만. 편집 전 `grep -rn "<파일>:[0-9]"`로 살아 있는 인용을 확인한다 |
| **H-G** | macOS에 `tac`이 없다 | `tail -r` 또는 `git log --reverse` |

## 절차·증거

| # | 함정 | 대응 |
|---|---|---|
| **H-M** | **"실패하는 테스트를 먼저 썼다"가 증거로 약할 수 있다.** 13건을 먼저 썼지만 실제 red는 **5건**이었다 — 나머지 8건은 구현이 없으면 **자동으로 통과하는 부재 가드**다(핸들러를 통째로 지워도 초록) | 부재를 단정하는 테스트는 red 증거로 쓰지 않는다. **"N건 중 M건이 red였다"**로 세어 적고, 긍정 단정(실제로 만들어진다)이 짝을 이루는지 확인한다 |
| **H-N** | **계획서가 추측으로 적은 테스트 헬퍼 이름은 대체로 실재하지 않는다.** `_prompt_start_payload`·`_drain_adapter_events` 둘 다 없었다 — 진짜는 `_translate_all`·`stream.payloads`(`test_nova.py`), `ScriptedAdapter`·`FakeClient`·`_runner`(`test_gateway.py`) | 계획의 테스트 코드를 베끼기 전에 **그 파일을 열어 실제 헬퍼 이름을 확인**한다. 두 태스크에서 연속으로 걸렸다 |
| **H-O** | **커밋 메시지·handoff에 계산값을 적으면 낡는다.** "269 + 3 = 272"처럼 산수로 쓴 수치가 실제와 다를 수 있다 | 수치는 **그 턴에 실제로 돌린 명령의 출력**만 적는다. 이미 적었으면 되돌려 실측해 확인한다 |
| **H-P** | **인계표에 적은 HEAD 해시는 적는 순간 낡는다** — 그 표를 담은 커밋 자신이 HEAD를 옮긴다. 실측: 기준값 `8a0834e`인데 새 세션이 얻은 값은 `c443109`(= 그 기준값을 적은 docs 커밋). 코드는 같았다 | 기준값은 **`HEAD ≥ <해시>`** 형태로만 적는다. 불일치를 보면 먼저 `git merge-base --is-ancestor <기준> HEAD`와 `git log --oneline <기준>..HEAD`로 **docs-only 1건인지** 확인한다 — 게이트 수치가 같으면 실질 일치다 |
| **H-R** | **`git commit --amend \|\| git commit` 폴백은 앞 커밋을 조용히 덮어쓴다.** 마감 커밋을 그렇게 썼더니 `--amend`가 성공해 직전 커밋(`b9575fb`)이 사라졌다 — 내용은 합쳐져 살아남았지만 **그 커밋의 메시지가 없어지고**, handoff에 적어 둔 기준 해시가 히스토리에 없는 값이 됐다(다음 세션이 대조에서 걸렸다). 덤으로 폴백 문자열의 오타(`Obus`)까지 커밋됐다 | 커밋 실패를 폴백으로 감싸지 않는다. 한 번에 하나의 `git commit`만 쓰고, 실패하면 원인을 보고 다시 한다. `--amend`는 **의도적으로 앞 커밋을 고칠 때만** 단독으로 쓴다 |
| **H-X** | **두 세션이 `pytest`를 동시에 돌리면 서로를 깨뜨린다 — 회귀로 오인한다.** `tests/conftest.py`의 session 스코프 `test_database`가 매 실행 시작에 `recreate_database`를 부르고, 그것은 `DROP DATABASE IF EXISTS "ohmyenglish_test"` + `CREATE DATABASE`다(`scripts/db_utils.py:53-54`). 즉 **테스트 DB는 실행마다 파괴되는 공유 자원**이다. 실측(2026-09-02): 코드 리뷰를 subagent에 위임한 직후 게이트를 돌렸더니 `7 failed, 356 passed, 2 errors in 9.24s`가 나왔다 — 평소 `365 passed in 4.3s`다. 직후 8회 연속 재실행은 전부 clean이었고 같은 순서를 재현해도 나지 않는다. **원인은 추정이 아니라 확정이다** — 그 리뷰어가 뮤테이션 하나당 전체 스위트 1회를 써서 **총 17회**(재검증 요청 직후에만 8회) 돌렸다고 스스로 보고했다 | **판별 2개: ① 실행 시간이 평소의 2배 이상 ② 실패가 재현되지 않는다.** 둘이 겹치면 코드가 아니라 **동시 실행**을 의심한다(H-T=연결, H-W=설정과 같은 계열이다). **리뷰·검증을 subagent에 위임할 때 위임 프롬프트에 "전체 `pytest`를 돌리지 마라"를 명시한다** — 게이트 수치를 함께 넘겨 재실행 이유를 없애고, 뮤테이션 검증이 필요하면 **개별 파일 + `-c pyproject.toml`**(H-W)로 좁히게 한다. 이 함정을 처음 만든 것이 바로 "뮤테이션 1건당 전체 스위트 1회" 패턴이다. ⚠️ **깨진 수치를 근거로 커밋 메시지·handoff를 쓰지 마라**(H-O의 변종이다) |
| **H-W** | **테스트 파일을 인자로 지목하면 `pytest` 설정이 통째로 무시된다 — 전건 실패가 회귀처럼 보인다.** 실측(2026-09-01): `cd app/backend && .venv/bin/pytest -q ../../tests/unit/test_utterances.py`가 **20건 전부 0.29초에 실패**했고 사유는 `async functions are not natively supported`였다. cwd도 맞고 `pyproject.toml`의 `asyncio_mode = "auto"`도 그대로다 — 인자 경로가 `testpaths` 밖이라 pytest가 **rootdir을 리포 루트로 다시 계산**하면서 `app/backend/pyproject.toml`을 못 읽은 것이다 | **판별: 전건이 1초 안에 균일하게 실패하면 코드가 아니라 설정 로딩을 의심한다** (H-T와 같은 모양의 함정이고, 거기서는 연결이었다). 부분 실행은 **`-c pyproject.toml`을 붙인다** — `.venv/bin/pytest -q -c pyproject.toml ../../tests/unit/test_utterances.py`. 인자 없는 `pytest -q`는 `testpaths`를 쓰므로 영향 없다 |
| **H-Y** | **`explain analyze`는 UPDATE/DELETE를 실제로 실행한다 — 계획만 보는 명령이 아니다.** 실측(2026-09-03): I-4 리퍼 SQL의 비용을 재려고 dev DB에서 `explain analyze update learning_sessions ... returning s.id`를 돌렸다. `Execution Time 0.389 ms`·`SubPlan 1 (never executed)`라는 원하던 증거는 얻었지만, 그 UPDATE는 그 순간 **실제로 실행됐다**. 아무것도 바뀌지 않은 것은 조건에 맞는 행이 0건이었기 때문일 뿐이다(`Rows Removed by Filter: 3` · `rows=0` · `active` 세션 0건). `active` 세션이 하나라도 있었다면 살아 있는 세션을 `failed`로 닫았을 것이다 | **쓰기 문장의 비용은 `begin; explain analyze ...; rollback;`으로 잰다.** `analyze` 없는 `explain`은 실행하지 않지만 실측 시간을 주지 않으므로, 시간이 필요하면 트랜잭션으로 감싼다. dev DB는 **마이크 회차 대조용 데이터를 보존 중**이라(handoff 「보존 이유」) 한 행이라도 바뀌면 그 대조가 깨진다 |
| **H-Z** | **문서가 지정한 실행 명령으로 띄우면 앱의 INFO 로그가 하나도 안 보인다.** 실측(2026-09-03): `.venv/bin/uvicorn app.api.main:app --port 8002 --log-level info`(`docs/ops/local-run.md`)로 띄우고 세션을 891회 돌렸는데 `analysis worker started`(INFO)가 **0건**이었고, **같은 실행에서** `텍스트가 아닌 프레임을 무시했다`(WARNING)는 출력됐다. uvicorn은 자기 로거(`uvicorn.*`)만 설정하고 **root 로거에는 핸들러를 두지 않아** `logging.lastResort`가 WARNING 이상만 stderr로 흘린다 | **운영상 반드시 보여야 하는 사건을 INFO로 찍지 마라.** I-4 리퍼 로그가 그래서 `logger.warning`이고 tripwire가 지킨다(`test_the_reaper_reports_above_info_so_the_documented_run_shows_it` — 레벨을 내리면 red). ⚠️ **로그에 안 나오는 것을 "안 일어났다"로 읽지 마라** — DB 상태로 교차 확인한다(이 함정을 발견한 경위가 그것이다: 리퍼는 정상 동작했는데 로그만 없었다). 기존 INFO 로그(`analysis worker started` · I-1 스윕 회복)는 **여전히 안 보인다** — 로깅 설정을 세우는 것은 별건이다 |
| **H-AA** | **게이트 밖 스크립트는 조용히 낡는다 — 그리고 그것을 발견하는 시점이 "실물로 확인해야 할 때"다.** 실측(2026-09-04): 슬라이스 1의 실물 검증(L2)을 하려고 `scripts/smoke_analysis.py`(W-live)를 돌렸더니 첫 줄부터 `RuntimeError: claim할 job이 없다`로 죽었다. 원인은 내 변경이 아니다 — **I-1**(`4441e81`, 2026-09-02)이 분석 job 등록을 저장 시점에서 **턴 경계**(`flush_pending_analysis`)로 옮겼는데 그 스크립트의 마지막 수정은 `44611e7`(2026-08-31)이었다. 즉 **이틀 동안 W-live 스모크는 돌지 않았고 게이트가 초록이라 아무도 몰랐다**. 이 스크립트는 실물 Claude를 호출하므로 게이트에 넣을 수 없다 | **앱의 "언제 무엇이 등록되는가"를 바꿀 때 `scripts/**`와 `tests/harness/**`를 함께 grep한다** — 그 경로는 게이트가 지켜 주지 않는다. 판별: 스모크가 **첫 단계에서** 죽으면 코드 회귀보다 **스크립트가 낡았을 가능성**을 먼저 본다(`git log -1 -- <스크립트>` vs 그 경로를 바꾼 커밋의 날짜를 비교). 새 규약을 발명해 고치지 말고 **같은 일을 하는 테스트 헬퍼를 베낀다**(여기서는 `tests/integration/test_pipeline.py`의 `_close_turn`) |
| **H-Q** | **인계용으로 만든 tmux 세션이 실제로 쓰이지 않을 수 있다.** 3-15를 띄웠지만 캡틴은 같은 창(3-14)에서 새 컨텍스트를 시작했고 3-15 pane은 빈 셸이었다 | 정리 전에 `tmux capture-pane -p -t <세션> \| tail`로 **거기서 실제로 작업 중인지** 본다. 빈 셸이면 인계 대상이 아니다. `tmux display-message -p '#{session_name}'`으로 **내가 어느 세션인지** 먼저 확인한다 — 자기 자신을 kill하지 않기 위해 |
| **H-AD** | **크론 발동을 폴링으로 관측할 수 없다 — 관측이 대상을 없앤다.** 이 하네스의 `CronCreate` 잡은 예약된 분에 정시 발동하지 않고 **그 이후 REPL이 idle이 되는 시점에** 발동한다(실측: 슬롯 `:23`인 잡이 **12:31:12**에 발동 — 8분 늦다). 그래서 `sleep`으로 기다리며 확인하려 하면 **기다리는 그 순간 세션이 mid-query라 idle이 아니고, 테스트하려는 발동을 자기가 막는다.** 관측자 효과다. ⚠️ 그리고 **자기 세션이 idle로 판정됐는지는 세션 안에서 볼 수 없다** — 하네스 내부 상태다. 실측 사고(2026-09-06): 감사 세션의 `durable` 크론(`82bc95e7`, `7 * * * *`)이 1회 발동 뒤 **59분 무발동**이었고, 등록은 정상이었다(`.claude/scheduled_tasks.json`에 실재 · `CronList`에 `[session-only]` 태그 없음) | **폴링하지 않는다. 턴을 끝내 REPL을 idle로 둔다** — 그것이 유일한 관측 방법이다. 무발동을 조사할 때는 ① `CronList`로 등록과 `[session-only]` 태그를 본다(태그가 있으면 세션 스코프라 등록 세션이 바뀌면 죽는다 — 실측 선례 `fff38ea1`) ② 발동 이력의 대리 지표를 본다(`.harness/audit-heartbeat.txt` 같은 것) ③ **그 구간에 세션이 바빴는지를 함께 적는다** — 바쁜 세션의 무발동은 idle 부재로 설명되므로 **대조군이 되지 못한다.** ⚠️ 표본 1~2회로 "스케줄러 고장"을 단정하지 않는다. **원인 미확정으로 적는 것이 정확한 보고다.** 출처: 감사 세션(`ohmyenglish-69`)의 관측 — 그 세션은 문서를 쓰지 않으므로 작업 세션이 대신 등재했다 |
| **H-AC** | **하네스가 앱의 계산식을 복제하면 그 복제가 낡고, 낡은 식을 공유 dev DB에 쓴다 — 캡틴 데이터가 사라진다.** 실측(2026-09-06, T2 스파이크): `browser_leg.md` §8-② teardown이 `error_patterns.frequency`를 "앱과 같은 식으로" 재계산했는데 그 식은 `services/analysis.py`의 것 **하나뿐**이었다. **`frequency`의 writer는 둘이다** — `analysis.py`는 `error_occurrences` 행 수를, `pronunciation.py:_RECOUNT_PATTERN_FROM_ATTEMPTS_SQL`은 **`pronunciation_attempts` 행 수**와 `max(resolved_at)`을 쓴다(`pronunciation.py`가 그 이유를 명시한다: 발음 시도는 occurrence를 만들지 않는다). 그래서 재계산이 **모든 발음 패턴을 0으로 덮었다**: `pronunciation_an_as_a`가 `2 / 2026-09-03 13:51:26.680389+00` → `0 / NULL`. 직접 대조로 확정 — 그 패턴은 `frequency` 컬럼 **2**인데 `error_occurrences` 행 **0**이고, 나머지 6개는 컬럼과 행 수가 정확히 일치한다 | **teardown은 계산하지 말고 baseline에서 복원한다.** 복원은 멱등이고 수식이 없어 앱 로직이 바뀌어도 낡지 않는다. **baseline이 없으면 멈추고 ERROR로 보고한다 — 재계산으로 대체하지 않는다.** 그리고 "occurrence 0건 = 하네스 잔여물"이라는 판정도 발음 패턴에는 성립하지 않으므로 삭제 조건에 `pronunciation_attempts` 부재를 함께 요구한다. ⚠️ **일반화: 어떤 컬럼을 하네스가 되돌리려면 그 컬럼의 writer를 전부 grep해서 센다**(`grep -rn "set <컬럼> ="`). 하나만 보고 "앱과 같은 식"이라고 쓰면 나머지 writer의 데이터를 파괴한다 |
| **H-AB** | **단위 테스트가 값을 인자로 직접 넘기면 호출자(배선)를 재지 못한다 — 이 리포에서 세 번 걸렸다.** ① 2026-09-05: `process_plan`의 허용 집합에서 `\| {metric.pattern_id …}` 절을 통째로 지워도 **549건 전부 통과** ② 2026-09-06: `deepest_pattern_id=…` 배선을 `None` 고정으로 바꿔도 **593건 전부 통과** ③ 2026-09-06(독립 리뷰가 지적): 그 배선의 **반대 분기**("만성 목록이 비면 강제하지 않는다")도 단위에서만 재고 종단 픽스처가 없었다 — 막히면 복습 전용 사용자의 계획이 **영구히 거부**된다. 셋 다 같은 형태다: 단위가 `parse_plan(deepest_pattern_id=…)`을 **인자로 직접** 부르므로 호출자가 정말 그 값을 계산해 넘기는지는 재지 않는다 | **배선 보호는 배선 줄만 무력화해 확인한다.** ⚠️ **가드 본문을 무력화하면 단위도 함께 red가 되어 "배선이 보호되는가"를 가리지 못한다** — 실측(2026-09-06): `models/plan.py`의 `is not None` 가드를 지우면 **2건 red**(단위 + 통합)이지만, `services/plan.py`의 `deepest_pattern_id=None if …`을 `UUID(int=0)`으로 바꾸면 **정확히 1건 red**(통합만)다. 후자만이 배선 보호를 증명한다. **분기가 둘이면 둘 다 종단으로 잰다** — 강제하는 쪽만 재면 통과시키는 쪽이 무보호로 남는다 |
