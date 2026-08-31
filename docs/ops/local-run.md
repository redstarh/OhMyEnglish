# 로컬 실행 방법 (DB · 백엔드 · 프론트 · 게이트)

> 2026-08-30에 `handoff/HANDOFF.md`에서 이관했다 — 이것은 세션이 바뀌어도 유효한 **영구
> 지식**이라 handoff(연속성 층)가 아니라 운영 문서가 소유한다. 값은 이관 시점에 코드로
> 재확인했다.

---

## ⚠️ 포트 함정 — 저장소 문서의 8000은 틀렸다

**이 머신의 `:8000`은 StockAgent가 쓴다.**

| 포트 | 서비스 |
|---|---|
| **:8002** | **OhMyEnglish API** (`/health` → `{"status":"ok"}`) |
| :8000 | StockAgent (MOCK) — `openapi.json` title로 식별 |
| :3000 | OhMyEnglish 프론트 (Next.js 16) |
| **:5432** | **PostgreSQL — homebrew `postgresql@17` (기본 경로).** 부팅 시 launchd가 띄운다. ⚠️ **StockAgent와 공유하는 인스턴스**다(`stockagent`·`stocknews*`) — 인스턴스 단위 조작 금지, DB 단위로만 다룬다 |
| :5433 | PostgreSQL (podman `ohmy-pg`) — **폴백**. 2026-08-31에 기본 경로를 :5432로 옮겼고 이 컨테이너는 지우지 않았다 |

`app/frontend/lib/config.ts`의 폴백이 `:8000`이라 `.env.local`이 없으면 프론트가
StockAgent에 붙어 **결과 조회가 조용히 실패한다**. 백엔드는 **반드시 `--port 8002`**로
띄운다.

---

## 실행

```bash
# DB — 기본 경로는 homebrew postgresql@17 (:5432). 보통 부팅 시 이미 떠 있다.
brew services list | grep postgresql@17            # started 인지 확인
# 안 떠 있으면
brew services start postgresql@17
# 붙는지 확인 (psql은 PATH에 없다 — 절대 경로를 쓴다)
PGPASSWORD=ohmy /opt/homebrew/opt/postgresql@17/bin/psql -h 127.0.0.1 -p 5432 -U ohmy \
  -d ohmyenglish -tAc "select current_setting('TimeZone'), count(*) from learning_sessions;"
#   기대: UTC|2   ← TimeZone이 UTC가 아니면 역할 설정이 풀린 것이다(함정 H-S가 안 보이게 된다)

# 폴백 (podman — 이 머신에 docker는 없다). :5432를 못 쓸 때만.
podman machine start && scripts/dev_db.sh start    # postgres:16-alpine, :5433, ohmy/ohmy/ohmyenglish
# ⚠️ 두 곳을 함께 바꿔야 실제로 폴백을 쓴다 — 한쪽만 바꾸면 앱과 도구가 다른 DB를 본다:
#   ① 앱(uvicorn)  : app/backend/.env 의 DATABASE_URL 포트 → 5433 (pydantic Settings가 .env를 읽는다)
#   ② 스크립트·하네스: export DATABASE_URL=postgresql://ohmy:ohmy@localhost:5433/ohmyenglish
#      (scripts/db_utils.py 의 base_dsn()은 **환경변수만** 읽는다 — .env를 읽지 않는다)
# 판별법: `show server_version` 이 17.9 면 :5432(homebrew), 16.15 면 :5433(컨테이너)다.
#   ⚠️ `inet_server_port()` 로는 판별할 수 없다 — 컨테이너 안에서도 5432로 듣기 때문에 둘 다 5432가 나온다
# ⚠️ 폴백 컨테이너의 데이터는 2026-08-31 이관 시점의 **사본**이고 그 뒤 변경이 반영되지 않았다
app/backend/.venv/bin/python scripts/migrate.py   # 001·003·004·005 적용 + 고정 사용자·시나리오 3행 시드 (멱등)
#   ⚠️ `python3 scripts/migrate.py`는 **돌지 않는다** — 시스템 python에 asyncpg가 없다
#      (2026-08-27 실측: ModuleNotFoundError). 반드시 venv python을 쓴다
#   추적은 파일명 기준(`schema_migrations`) — 001을 재작성했다면 dev DB를 drop/재생성해야 한다

# 백엔드 (Python 3.13 venv — uv).  ⚠️ 포트 8002 · --reload 없음(소스 바뀌면 재기동)
cd app/backend && .venv/bin/uvicorn app.api.main:app --port 8002
#   VOICE_ADAPTER=stub(기본) | stub_unresponsive(연결 실패 재현) | nova(실연동)
#   NOVA_ENDPOINTING_SENSITIVITY=HIGH|MEDIUM(기본)|LOW
#   WORKER_ENABLED=false  → 분석 워커 정지 (자격증명 없이 부팅)

# 프론트 (Next.js 16)
cd app/frontend && npm run dev   # :3000. .env.local 이 :8002 를 가리켜야 한다

# Nova 직접 왕복 (자격증명·모델 생존 확인 + 발음 픽스처 ASR 확인)
cd app/backend && .venv/bin/python ../../tests/harness/spike_nova_protocol.py --wav p1a.wav
#   불투명한 AccessDeniedException('') → OMY_SPIKE_CAPTURE_BODY=1 로 본문 포착
```

---

## 검증 게이트

```bash
cd app/backend && .venv/bin/pytest -q && .venv/bin/ruff check . \
  && .venv/bin/ruff format --check . && ty check
```

⚠️ **cwd가 게이트의 일부다.** ruff 설정은 `app/backend/pyproject.toml` 하나뿐이고
리포루트에는 없다 → 리포루트에서 돌리면 ruff 기본 규칙이 적용돼 수십 건이 난다. 그건
회귀가 아니라 다른 규칙셋이다. 반드시 `app/backend` cwd에서 판정한다(함정 H-A).

`tests/`와 `scripts/`는 위 `ruff check .` **범위 밖**이라 따로 돌린다(함정 H-L):

```bash
cd app/backend && .venv/bin/ruff check ../../tests ../../scripts   # 베이스라인 6건 잔존
cd app/backend && .venv/bin/ruff format --check ../../tests        # 베이스라인 4 files
```

하위 경로를 직접 주면 `-c pyproject.toml`을 함께 준다 — rootdir이 리포 루트로 잡혀
`asyncio_mode=auto`를 못 찾는다:

```bash
cd app/backend && .venv/bin/pytest -c pyproject.toml ../../tests/integration/test_x.py -q
```

---

## `.env` (app/backend, gitignore 대상)

`config.py`의 `prepare_bedrock_credentials()` 우선순위:

1. `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` (+임시면 `AWS_SESSION_TOKEN`) → **SigV4**.
   이때 `AWS_BEARER_TOKEN_BEDROCK`을 프로세스 환경에서 **제거**해 단일 경로를 강제한다.
   **Nova 양방향은 이 경로만 가능하다.**
2. 없으면 `AWS_BEARER_TOKEN_BEDROCK` 폴백 — Claude invoke는 되지만 Nova는 403.
3. 둘 다 없으면 워커 기동 시 `RuntimeError`.

현재 `.env`는 ①번으로 동작한다. ⚠️ **이 access key는 대화 기록을 경유했다 — 로테이션 권장**
(`docs/ops/iam-setup-nova-sigv4.md` §6).

`DATABASE_URL`은 필수 설정이고 기본값은 `postgresql://ohmy:ohmy@localhost:5432/ohmyenglish`다
(`scripts/db_utils.py`). 다른 앱과 이 DB를 공유하려면 `docs/ops/shared-database-guide.md`.

⚠️ **테스트·스모크 DB는 이 DSN에서 DB 이름만 바꿔 만들어진다**(`db_utils.dsn_for`) — 즉
`ohmyenglish_test`·`ohmyenglish_smoke`도 같은 서버에 생긴다. dev와 test를 서로 다른 서버로
나눌 수는 없다(그러려면 코드를 고쳐야 한다). 두 DB는 매 실행마다 drop/create되는 **파괴 대상**이고
`ohmyenglish`는 아니다.

⚠️ **역할 `ohmy`에 `TimeZone=UTC`가 걸려 있다.** :5432 인스턴스 기본값은 `Asia/Seoul`인데,
그대로 쓰면 `current_date`가 KST와 같아져 **함정 H-S가 화면에서 사라진다** — §11 복습 주기 코드가
로컬에서만 맞고 UTC 서버에서 깨진다. 역할 단위라 새로 만드는 DB에도 자동 적용된다.
인스턴스 기본값은 **건드리지 않았다**(StockAgent가 같은 인스턴스를 쓴다).
