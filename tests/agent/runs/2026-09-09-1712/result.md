# 회차 2026-09-09-1712 — 결과 조회 API 의 세션 상태 6종 대조

## 0. 이 회차의 한계와 전제 어긋남 — 먼저 읽음

**테스트 원장에 시나리오를 등록하지 않았음.** 정의 §5·§9 는 `tests/agent/backlog/` 원장에
시나리오를 태스크로 두라고 요구하지만, 착수 지시가 쓰기를 `tests/agent/runs/` 아래로만 한정하고
원장 수정과 커밋을 금지했음. 그래서 이 회차는 원장 밖에서 돌았고 **회귀 판정을 하지 않음** —
기준값 여섯은 리포의 하네스 자산(`tests/harness/browser_leg.md` §9)에서 읽은 것이고
이전 회차 대비 회귀는 판정하지 않았음.

⚠️ **원장 자체는 회차 중에 다른 주체가 만들었음** — `tests/agent/backlog/config.yml` 과
`tests/agent/AGENTS.md` 가 17:13(내 측정 구간 안)에 생겼음. `AGENTS.md` 가 backlog.md 1.50.1 의
생성 문구를 그대로 갖고 있어 `backlog init` 산출물임. **내가 만들지 않았음** — 이 회차는
`backlog` 명령을 0회 실행했음. `config.yml` 은 `task_prefix: "ts"` 와 statuses 4개
(`To Do`·`In Progress`·`Blocked`·`Done`)로 정의 §5 와 정확히 일치하나 `tasks/` 는 비어 있음.
누가 만들었는지는 **미확정임** — 관측하지 않았음.

**착수 지시의 환경 전제 3개를 그 자리에서 재검증했고 2개가 어긋났음.**

| 지시가 준 전제 | 재검증 명령 | 관측값 | 판정 |
|---|---|---|---|
| 백엔드 pid `63332` | `lsof -i:8002 -P -n` | **pid `17729`** (기동 2026-09-09 17:09:56 KST) | ⚠️ 어긋남 |
| `VOICE_ADAPTER=stub_unresponsive` | `ps eww 17729` | **`VOICE_ADAPTER=stub`** | ⚠️ 어긋남 |
| `WORKER_ENABLED=false` | `ps eww 17729` | `WORKER_ENABLED=false` | ✅ 일치 |
| 엔드포인트가 `/results/<id>` 상당 | `app/backend/app/api/results.py:131` · `/openapi.json` | `GET /api/sessions/{session_id}/results` | 소스로 확정 |

pid 어긋남의 뜻: 백엔드는 **내 회차 시작(17:12:22) 2분 26초 전에 재기동됐음.** 지시가 준 pid 는
그 이전 프로세스임. `VOICE_ADAPTER` 도 그때 함께 바뀌었을 것으로 보이나 **원인은 미확정임** —
재기동 주체는 다른 세션이고 내가 관측하지 않았음.

두 어긋남이 이 회차의 판정에 영향을 주지 않는 이유: 여섯 세션은 모두 **이미 끝난 보존 세션**
(`ended_at is not null`, 2026-09-06·09-08 생성)이고 결과 조회는 저장된 상태를 읽기만 함.
`VOICE_ADAPTER` 는 새 세션을 시작할 때만 쓰임.

## 1. 환경

| 항목 | 값 |
|---|---|
| HEAD (측정 구간 시작·끝 동일) | `d2fa24d` |
| 브랜치 | `design/first-vertical-slice` |
| 측정 구간 | 2026-09-09 17:12:22 ~ 17:15:49 KST |
| 백엔드 | `127.0.0.1:8002` · pid 17729 · `uvicorn app.api.main:app --port 8002 --log-level info` |
| `/health` | `{"status":"ok"}` HTTP 200 |
| DB | `postgresql://…@localhost:5432/ohmyenglish` · psql `/opt/homebrew/opt/postgresql@17/bin/psql` |

**공유 인스턴스로 판정함** (정의 §2-6). 포트 8002 가 선점돼 있었고 Chrome(pid 22864)이 그것에
ESTABLISHED 연결을 갖고 있었음 — 다른 세션의 브라우저임. 측정 구간 안에서 HEAD 는 `d2fa24d`,
백엔드 pid 는 17729 로 고정이었음. **측정 구간이 끝난 뒤 HEAD 가 움직였고 그 처리는 §10 에 있음.**

## 2. 판정표 — 6/6 PASS

요청 URL 은 전부 `http://127.0.0.1:8002/api/sessions/<전체ID>/results` 이고 응답은 전부 HTTP 200 임.

| 태그 | 세션 전체 ID | 관측 `status` | 기준 `status` | 관측 `corrections` | 기준 `corrections` | 판정 |
|---|---|---|---|---|---|---|
| C3a | `210233be-ecaa-4409-a1af-8b7016cfe7e9` | `analyzing` | `analyzing` | **키 부재** | 키 부재 | **PASS** |
| C3b | `6225ddaf-90a8-43af-9aa8-e003921c75eb` | `final` | `final` | 있음 · **1건** | 1건 | **PASS** |
| C3c | `b2f0d169-3d90-431b-b842-cce21125052a` | `partial_failure` | `partial_failure` | 있음 · **0건** (`[]`) | 0건 | **PASS** |
| C3d | `76d9ef31-0d1b-4c50-b906-f16ee438080e` | `connection_failed` | `connection_failed` | **키 부재** | 키 부재 | **PASS** |
| C3e | `d127dece-d1d1-4329-802d-9b8fd1067388` | `no_utterances` | `no_utterances` | **키 부재** | 키 부재 | **PASS** |
| C3f | `e0c5e580-dfc0-4793-b02d-54cf4346c3c5` | `final` | `final` | 있음 · **2건** | 2건 | **PASS** |

**FAIL 0건 · BLOCKED 0건 · ERROR 0건. 신규 앱 결함 0건 — 작업 원장에 등록한 결함 없음.**

관측된 최상위 키 집합 (증거 `evidence/01-verdict.txt`):

```
C3a ['partial_failure', 'pronunciation', 'status']
C3b ['corrections', 'partial_failure', 'pronunciation', 'status']
C3c ['corrections', 'partial_failure', 'pronunciation', 'status']
C3d ['partial_failure', 'pronunciation', 'status']
C3e ['partial_failure', 'pronunciation', 'status']
C3f ['corrections', 'drill', 'partial_failure', 'pronunciation', 'status']
```

`corrections` 가 `null` 로 실린 응답은 **0건임** — 부재는 전부 키 생략이고 `results.py:122` 의
계약(`if result.corrections is not None`)과 일치함. `pronunciation` 은 여섯 전부에 있고 전부 `[]` 임.
`drill` 은 C3f 에만 있음(`exchanges_observed` 2 / `exchanges_expected` 20).

## 3. 판별력 증명 — 이 판정이 반증될 수 있음을 먼저 보임

6/6 PASS 는 내 드라이버가 무조건 통과하는 것일 수도 있음. **앱을 건드리지 않고 기준값만 어긋나게
바꿔** 드라이버가 FAIL 을 내는지 쟀음 (증거 `evidence/02-falsification.txt`).

| 바꾼 것 | 대상 | 결과 |
|---|---|---|
| `status` 만 틀리게 | C3a · C3f | FAIL 2/2 |
| 건수만 틀리게 (1 → 2) | C3b | FAIL 1/1 |
| 키 유무만 틀리게 (0건 → 부재) | C3c | FAIL 1/1 |
| 키 유무만 틀리게 (부재 → 0건) | C3d | FAIL 1/1 |
| 기준과 동일하게 둠 (대조군) | C3e | PASS 유지 |

**어긋남 5/5.** 세 종류(상태 문자열 · 교정 건수 · 키 유무)를 각각 잡음. 특히 C3c·C3d 는
「0건」과 「키 부재」를 드라이버가 구분한다는 증거임 — 이 회차의 핵심 계약이 그것임.

경계값도 함께 쟀음: 존재하지 않는 세션(형식 정상 UUID) → **HTTP 404** `{"detail":"session not found"}` ·
UUID 가 아닌 값 → **HTTP 422** `uuid_parsing`. 즉 여섯 건의 200 은 고정 응답이 아님.

## 4. DB 보조 확인 — SELECT 만

응답 본문이 1순위이고 아래는 보조임. 상태를 만드는 재료가 문서 기록과 일치하는지만 봄.

접두사 여섯이 `learning_sessions` 에서 **각각 유일하게** 풀리고 내가 호출한 전체 ID 와 일치했음
(`evidence/05-db-prefix-resolve.txt`). `76d9ef31` 만 `status='failed'` 이고 나머지 다섯은
`completed` 임 — `connection_failed` 판정과 정합함.

`analyze_utterance` job 배치 (`evidence/06-db-jobs-and-patterns.txt`):

| 접두사 | job 배치 | API 상태 |
|---|---|---|
| `210233be` | `pending` 3 | `analyzing` |
| `6225ddaf` | `done` 1 | `final` |
| `b2f0d169` | `done` 2 · `failed` 1 | `partial_failure` |
| `d127dece` | (행 없음) | `no_utterances` |
| `e0c5e580` | `done` 3 | `final` |

`browser_leg.md` §9 가 적어 둔 조성 방법과 정확히 일치함. ⚠️ **내 첫 쿼리가 이것을 놓쳤음** —
`analyze_utterance` 행은 `session_id` 가 `NULL` 이고 `utterance_id` 로만 걸림. `utterances` 를
경유해 조인해야 보임. 1차 쿼리는 `analysis_jobs.session_id` 로 직접 걸어 「210233be 에
analyze_utterance 가 없다」는 **잘못된 부정 관측**을 냈음. 결함으로 올리기 전에 내 드라이버를
먼저 의심하라는 정의 §7-7 이 여기서 실제로 걸렸음.

**가장 값어치 있는 보조 관측 — `d127dece`**: 이 세션은 DB 에 `article_missing_the_before_place_noun`
패턴 1개 · occurrence **2건**을 갖고 있음. 그런데 API 는 `corrections` 키를 **생략함.** 즉 키 부재가
「데이터가 없어서」가 아니라 **「잠정 노출 금지」 계약이 능동으로 억제한 결과**임이 관측됐음
(`results.py:10-13`). 나머지 키 부재 2건(`210233be`·`76d9ef31`)은 패턴이 0건이라 이 구분을
보여주지 못함 — 억제 계약의 유일한 실증 표본이 `d127dece` 임.

교정 건수 대조: `6225ddaf` 구분 패턴 1개 → API 1건 · `e0c5e580` 구분 패턴 2개(occurrence 4건) →
API 2건. 건수가 occurrence 가 아니라 **구분 패턴 수**로 접힌다는 것이 두 표본에서 일치함.

## 5. 재현

여섯 건을 한 번 더 받아 1차 응답과 바이트 단위로 대조했고 **여섯 전부 동일**했음
(`evidence/08-rerun-diff.txt`). 간헐 실패 없음. 회차 중 픽스처가 파괴되지 않았음.

## 6. 금지 항목 준수 자기 신고

| 금지 | 준수 여부 |
|---|---|
| `pytest` 를 어떤 형태로도 돌리지 않음 | ✅ 0회. 실행한 명령 목록에 `pytest` 없음 |
| 워커를 켜지 않음 | ✅ `WORKER_ENABLED` 를 읽기만 했음. 워커 기동 명령 0회 |
| 백엔드를 재기동·종료하지 않음 · `VOICE_ADAPTER` 미변경 | ✅ pid 17729 가 측정 구간 시작·끝 동일. `ps`·`lsof` 는 읽기 |
| DB 는 SELECT 만 | ✅ `INSERT`/`UPDATE`/`DELETE`/`DROP`/`ALTER` 0회. 실행한 SQL 은 전부 `select` 와 `show search_path` |
| 대상 소스·테스트·원장 미수정 | ✅ 소스·테스트·`backlog/` 에 쓴 것 0건 |
| 커밋하지 않음 | ✅ 내가 실행한 `git` 명령은 `rev-parse`·`status`·`log`·`show`·`check-ignore` 뿐. **단 §10 을 함께 읽어야 함** — 내 증거 파일이 다른 세션의 커밋에 함께 담겼음 |
| 전역·공유 설정 미변경 | ✅ 앱 설정표·오디오 장치·Chrome 을 건드리지 않았음 |

## 7. 쓰기 경계 — OS 보장 없음

이 회차는 **서브에이전트 호출이라 전용 런처(`~/.claude/test-agent/run.sh`)의 OS 샌드박스 보장이
없음.** cwd 가 리포 루트이고 `Write`·`Bash` 로 대상 소스를 쓸 수 있는 상태였음. 즉 쓰기 경계는
**정의 §1-1 의 규칙만으로 유지됐음.**

규칙만으로 유지됐다는 것의 검증 가능한 근거: 이 회차가 만든 파일은 전부
`tests/agent/runs/2026-09-09-1712/` 아래에 있고, 그 밖에 쓴 것은 임시 파일 `/tmp/_openapi.json` ·
`/tmp/_dsn.txt` 둘뿐임 (`/tmp` 는 정의가 허용한 경로임). 대상 소스에 내가 만든 수정이 하나도
나타나지 않은 것이 그것을 뒷받침함.

⚠️ `/tmp/_dsn.txt` 에 DB 자격증명이 평문으로 남았음. 회차 정리에서 지웠음(확인함).

## 8. 실행한 명령 목록

```
git rev-parse --short HEAD
git status --short --branch ; git status --short -uall -- tests/agent
git log --oneline -3 ; git log --oneline d2fa24d..HEAD ; git log --name-status … -- tests/agent
git show --stat --name-status 07c9ab1 ; git show --name-only 07c9ab1
git check-ignore -v tests/agent/runs/…
lsof -ti:8002 ; lsof -i:8002 -P -n
find app tests -newermt '-30 minutes' -type f …
ps eww 17729 ; ps -o pid,ppid,lstart,command -p 17729
curl -sS http://127.0.0.1:8002/health
curl -sS http://127.0.0.1:8002/openapi.json
curl -sS http://127.0.0.1:8002/api/sessions/<전체ID>/results        # 6건 × 2패스 = 12회
curl -sS http://127.0.0.1:8002/api/sessions/00000000-0000-4000-8000-000000000000/results
curl -sS http://127.0.0.1:8002/api/sessions/not-a-uuid/results
grep -rn <접두사 6개> --include=… .
grep -rn "APIRouter|include_router" app/backend/app/api/main.py …
psql "$DATABASE_URL" -c "select … from information_schema.tables …"
psql "$DATABASE_URL" -c "select … from information_schema.columns where table_name in ('error_occurrences','analysis_jobs')"
psql "$DATABASE_URL" -c "show search_path"
psql "$DATABASE_URL" -c "select … from learning_sessions where left(id::text,8) in (…)"
psql "$DATABASE_URL" -c "select … from analysis_jobs join utterances … group by …"
psql "$DATABASE_URL" -c "select … from error_occurrences join utterances join error_patterns … group by …"
/usr/bin/python3  (판정·판별력 계산 · json.tool 정렬)
diff -q  (1차 vs 2차)
mkdir -p tests/agent/runs/2026-09-09-1712/evidence ; rm -f /tmp/_dsn.txt /tmp/_openapi.json
```

## 9. 증거 파일

`tests/agent/runs/2026-09-09-1712/evidence/` 아래:

| 파일 | 내용 |
|---|---|
| `00-health.txt` | `/health` 응답 |
| `C3{a..f}-<전체ID>.json` · `.url` | 1차 응답 본문 6건과 요청 URL |
| `pass2/C3*.json` | 2차 응답 본문 6건 |
| `01-verdict.txt` | 판정표와 최상위 키 집합 |
| `02-falsification.txt` | 판별력 증명 (기준값 변형 시 어긋남 5/5) |
| `03-notfound.json` · `04-baduuid.json` (+ `-code.txt`) | 404 · 422 경계 |
| `05-db-prefix-resolve.txt` | 접두사 → 전체 ID 유일 해소 |
| `06-db-jobs-and-patterns.txt` | job 배치 · 구분 패턴 수 |
| `07-bodies-pretty.txt` | 응답 본문 6건 정렬 출력 |
| `08-rerun-diff.txt` | 1차 vs 2차 대조 |

## 10. 공유 인스턴스 사고 — 내 증거가 다른 세션의 커밋에 쓸려 들어갔음

정의 §2-6 이 요구하는 「회차 끝에 HEAD 가 움직였는지」 확인에서 나온 것임.

**관측**: 측정 구간 끝(17:15:49)에 `git rev-parse` 가 `d2fa24d` 를 냈음. 그 직후 다시 재면
`07c9ab1` 임. 그 커밋의 타임스탬프가 **17:15:49** 로 내 마지막 확인과 같은 초임.
그 커밋이 담은 파일 목록에 **내 증거 파일 31개 전부**가 `A`(추가)로 들어 있음.

```
07c9ab1 test: C1 실행체에 유실 방지 — 종료 클릭 실패가 관측 전체를 버리지 않게 함
  A tests/agent/AGENTS.md
  A tests/agent/backlog/config.yml
  A tests/agent/runs/2026-09-09-1712/evidence/…      ← 31개, 내 산출물
  A backlog/tasks/task-53 - …md
  M tests/harness/c1_session_walkthrough.py
```

**판정**: 나는 커밋을 실행하지 않았음(§6). 다른 세션이 자기 변경을 커밋할 때 워킹트리 전체를
담는 방식으로 올려 **내 미커밋 증거가 함께 담겼음.** 내 `result.md` 는 그 커밋 뒤(17:16 이후)에
써서 아직 미추적임 — 그것이 시각 순서의 증거임.

**이 사고가 판정을 오염시키지 않은 근거**: 그 커밋이 바꾼 것은 `tests/harness/c1_session_walkthrough.py`
와 `backlog/tasks/task-53…md` 뿐이고 **`app/` 아래는 한 파일도 없음**(`git show --name-only` 로 확인).
즉 결과 조회 API 의 코드는 측정 구간 안에서도 뒤에서도 바뀌지 않았음. 여섯 측정은 전부
**`d2fa24d` 에 대한 것**이고, `d2fa24d`→`07c9ab1` 사이에 앱 동작을 바꾼 변경이 없으므로
`07c9ab1` 에도 그대로 유효함.

**호출자가 알아야 할 위험**: 이 리포에서 두 세션이 동시에 일하는 동안 한쪽이 워킹트리 전체를
커밋하면 **다른 쪽의 미완성 산출물이 그쪽 커밋 이력에 섞임.** 이번에는 증거 파일이라 해가
없었지만, 반대 방향(내가 앱 소스를 고친 상태였다면)에서는 남의 커밋에 내 변경이 실려 나감.
회차 산출물을 커밋 경계 밖에 두려면 `tests/agent/runs/` 를 `.gitignore` 에 두는 판단이 필요하고,
그 판단은 이 리포 소유자의 몫임 — 내가 `.gitignore` 를 고치지 않았음.
