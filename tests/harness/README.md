# 테스트 하네스 자산

돌고 있는 OhMyEnglish 스택(백엔드 `:8002` · 프론트 `:3000` · PG `:5432` — 2026-08-31에
podman `:5433`에서 homebrew `postgresql@17`로 옮겼다, 함정 H-T)을 사람 대신
끝까지 조작해 종단 경로를 검증하는 도구들이다. **절차 정본은
`docs/ops/2026-08-26-test-harness.html`**이고, 이 폴더는 그 절차가 쓰는 실행 자산과 회차 기록을
담는다.

`pytest`가 도는 `unit/`·`integration/`과 성격이 다르다 — 여기 있는 것은 **실행 중인 앱과 실제
Claude·실제 브라우저를 상대로 도는 스크립트**이므로 pytest 수집 대상이 아니다(파일명이 `test_`로
시작하지 않는 이유다).

## 구성

| 경로 | 무엇 |
|---|---|
| `ws_session.py` | `/ws/session` 한 세션을 끝까지 관측해 프레임을 기록한다 (A·B계층) |
| `inject_errors.py` | 임의 오류 문장을 앱 경로로 주입해 Agent의 패턴 분석을 관측한다 (E계층) |
| `scenarios-E-agent-learning.md` | 학습 패턴 분석·학습 제시 시나리오 정의 |
| `scenarios-N-real-voice.md` | 실음성(Nova Sonic) 테스트 가능성 검토와 준비 상태 |
| `runs/<날짜>-run-N.md` | 회차 기록 — 판정과 발견 사항 |
| `runs/<날짜>-run-N/` | 그 회차의 원자료(프레임 JSON·로그·스크린샷) |

런타임 상태(현재 run_id, 통보 주소, 백엔드 로그)는 저장소 밖의 `.harness/`에 둔다
(`.git/info/exclude` 등록). 이 폴더에는 **판정에 쓰인 증거만** 복사해 남긴다.

⛔ **`spike_nova_protocol.py` 의 원자료 파일명 — 2026-09-09 변경**(`TASK-68`). 예전에는 고정
이름 3개에만 써서 **회차를 한 번 더 돌리면 앞 회차의 원자료가 사라졌다**(추적 밖이라 복구
불가. 실제로 5차수 통제 대조의 원본이 그렇게 덮였다). 지금은 기본값이
`.harness/evidence/<팔>-<픽스처>-<UTC시각>.json` 이라 **회차가 서로를 덮지 않는다.**
고정 이름 파일은 **「가장 최근」 포인터**로 함께 갱신되며 **덮인다** — 판정 근거로 인용할 것은
스크립트가 마지막에 출력하는 `raw -> …` 경로다. 특정 경로에 쓰려면 `--out` 을 준다.

## 실행 전 필수

```bash
# 1) 스택 신원 확인 — :8000 은 StockAgent다. version 키가 있으면 잘못된 포트다.
curl -s localhost:8002/health          # {"status":"ok"} 여야 한다

# 2) 프로세스가 현재 소스보다 나중에 떴는지 — --reload 없이 뜬 프로세스는 갱신되지 않는다
ps -o lstart= -p $(lsof -nP -iTCP:8002 -sTCP:LISTEN -t)
find app/backend/app -name '*.py' -newermt '<위 시각>'   # 결과가 있으면 재기동하고 시작한다

# 3) 회차를 연다 — .harness/run_id.txt (ws_session.py·inject_errors.py 가 이 파일을 읽는다)
# ⛔ DB 접근은 psql_cli.py 하나로 한다. podman exec 를 쓰지 않는다 — dev DB 는 homebrew :5432 이고
#    podman 폴백(:5433)은 2026-09-17 에 지웠다(함정 H-T · TASK-149). 그 헬퍼는 DATABASE_URL 을
#    따라가므로 앱이 보는 DB 에 붙는다(정본은 browser_leg.md §7).
cd app/backend && .venv/bin/python -c "
import sys; sys.path.insert(0, '../../tests/harness')
from psql_cli import psql
run_id = psql(\"insert into harness_runs (git_commit, note) values ('<커밋>','<메모>') returning id\")
open('../../.harness/run_id.txt', 'w').write(run_id)
print(run_id)
"
```

⛔ **패턴 baseline SQL 은 이 문서에 옮겨 적지 않는다 — 정본은 `browser_leg.md` §8-0 이다.**
옮겨 적었던 판이 낡아 `next_review_at`·`mastery_score` 와 `harness_review_task_baseline` 을
빠뜨렸고, 그래서 「§8-0 을 따랐다」가 참인데도 복습 시계가 움직인 채 남았다(2026-09-10 · `TASK-83`).
회차를 열었으면 그 절의 SQL 을 위와 같은 방식으로 `psql_cli.py` 에 던진다.

`run_id.txt`에 **개행이나 psql 부산물이 섞이면 안 된다** — 스크립트가 그 값을 SQL에 그대로
넣는다(1회차에서 실제로 `INSERT01`이 섞여 세션 하나가 미등록으로 남았다).

⛔ **이 자리에 적었던 「`strip()` 하므로 오염되지 않는다」는 틀렸고 2026-09-17에 고쳤다.**
`strip()` 은 앞뒤 **공백**만 걷는다 — `insert … returning` 은 반환값 뒤에 **명령 태그**를 붙이므로
`run_id.txt` 가 `<uuid>\nINSERT 0 1` **47바이트**로 적혔다(직접 확인). `psql_cli.psql()` 에 `-q` 를
넣어 태그를 없앴고, 위 명령을 다시 돌려 **36바이트**인 것을 확인했다.
⚠️ **`select` 로 확인했더니 통과했다** — `select` 에는 태그가 없어서다. 그래서 그 검증은 이 결함을
**반증할 수 없는 입력**이었다. 이 헬퍼를 고칠 때는 반드시 `insert … returning` 으로 재현한다.

## 실행

```bash
cd app/backend
.venv/bin/python ../../tests/harness/ws_session.py --scenario A1
.venv/bin/python ../../tests/harness/ws_session.py --scenario A2 --junk --send-audio 3
.venv/bin/python ../../tests/harness/ws_session.py --scenario B5 --timeout 20
.venv/bin/python ../../tests/harness/inject_errors.py --scenario E1
```

두 스크립트 모두 **만든 세션을 `harness_sessions`에 즉시 등록**한다. 브라우저 레그는 그 훅이
없으므로 teardown 직전에 시간창 스윕으로 등록한다.

## 정리 (반드시)

공유 dev DB를 쓰므로 격리 책임이 하네스에 있다. 절차 문서 §10의 3단계를 그대로 따른다 —
① 하네스 세션 삭제(cascade) → ② `frequency`·`last_seen_at`을 **앱과 같은 식으로 재계산** →
③ baseline에 없던 0-occurrence 패턴만 삭제. 그리고 세션 수·패턴 수·`frequency`가 baseline과
일치하는지 **대조까지 해야 정리가 끝난 것이다**.

백엔드를 재기동한 시나리오는 baseline 명령으로 되돌린다 —
`WORKER_ENABLED=false VOICE_ADAPTER=stub .venv/bin/uvicorn app.api.main:app --port 8002 --log-level warning`.
플래그는 `.env`를 고치지 않고 환경변수로만 넘긴다.
⛔ **`WORKER_ENABLED=false` 를 빼지 마라 — 기본값이 `True` 다**(함정 `H-AS`). 빼면 워커가 켜져
버드록 비용이 나가고 `browser_leg.md` §9 의 보존 세션이 파괴된다.
