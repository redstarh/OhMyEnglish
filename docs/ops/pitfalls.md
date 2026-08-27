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
> 최종 갱신 **2026-08-28**

---

## 게이트·검사 도구

| # | 함정 | 대응 |
|---|---|---|
| **H-A** | **게이트의 cwd가 판정의 일부다.** 리포루트에는 ruff 설정이 없어 거기서 돌리면 기본 규칙으로 `check .` **56 errors** · `format --check .` **21 files**가 난다. 회귀가 아니라 다른 규칙셋이다 | 반드시 `cd app/backend` 후 판정한다. 설정 SoT는 `app/backend/pyproject.toml` 하나뿐이다 |
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
