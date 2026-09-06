# 브라우저 레그 (C계층) — 절차 정본

> 계획서 `docs/design/2026-09-05-frontend-test-agent-plan.md`의 **T1 산출물**. 시나리오 C1~C5의 판정은 여기 적힌 단정만으로 한다.
>
> **자기완결이다.** DB 접근·teardown·프리플라이트를 `tests/harness/README.md`나 `docs/ops/2026-08-26-test-harness.html`에 **위임하지 않는다** — 그 두 문서는 dev DB가 podman `:5433`에서 homebrew `postgresql@17`(:5432)로 이관된 뒤에도 `podman exec` 명령을 들고 있어(함정 H-T) 따라가면 앱이 보는 DB가 아닌 곳을 건드린다. 그 문서들의 정정은 계획서 T7이 소유하고 **이 문서는 그 수정에 의존하지 않는다.**
>
> 프론트엔드에는 테스트 러너가 0개이고 선언된 게이트(`npx tsc --noEmit` · `npx eslint app lib`)는 **렌더 결과를 재지 않는다.** 이 레그가 그 공백을 브라우저로 직접 관측해 메운다. **게이트가 아니다** — `app/frontend/**`를 바꾼 태스크의 9단계에서 프론트 게이트가 exit 0인 것을 먼저 확인한 뒤 부르고, 결과는 게이트 수치와 **별도 항목**으로 보고한다.

## §1. 계측 대조 규칙 — 이 문서가 낡지 않게 하는 유일한 수단

> `app/frontend/**`의 **렌더·색·오디오 경로**를 바꾼 태스크는, 이 문서의 단정 중 **그 경로를 재는 단정을 함께 갱신**해야 완료다. 갱신하지 않으면 다음 회차가 거짓 초록을 낸다.

게이트로는 이 부패를 잡지 못한다 — **계측이 낡으면 초록으로 낡는다.** 실측 선례: `runs/2026-08-26-run-1.md`가 C1~C4 전건 PASS를 내면서 `F-1 · HIGH`(다크모드에서 확정 전사문 대비 1.05:1)를 잡아냈고, **그 F-1의 지시된 수정**(하드코딩 색 → CSS 토큰)이 run-1의 C2 단정(`#999` 문단 개수)을 무효로 만들었다. 지금 그 단정을 그대로 돌리면 개수는 **항상 0 → 자동 통과**다. 감지가 실패한 것이 아니라 **수정과 계측을 함께 옮기는 일**이 실패했다.

## §2. 프리플라이트 — 전부 직접 돌려 출력을 읽는다

하나라도 어긋나면 **단정 평가로 넘어가지 않는다.** 「관측」은 T1 작성 시점에 작성자가 직접 돌린 출력이다.

| # | 명령 | 통과 조건 | 관측 (2026-09-06) |
|---|---|---|---|
| P1 | `curl -s http://localhost:8002/health` | `{"status":"ok"}` — **`version` 키가 있으면 StockAgent다. 즉시 멈춘다** | `{"status":"ok"}` (`version` 없음) |
| P2 | `cat app/frontend/.env.local` | `NEXT_PUBLIC_API_BASE=http://localhost:8002` | 일치 |
| P3 | `git check-ignore -v app/frontend/.env.local` | 무시됨을 확인한다 — **P2가 없는 머신에서는 폴백이 `http://localhost:8000`이고 그것은 StockAgent다**(`lib/config.ts:API_BASE`). 조용히 남의 앱을 검증한다 | `app/frontend/.gitignore:34:.env*` |
| P4 | `brew services list \| grep postgresql` | `postgresql@17  started` | `postgresql@17 started` |
| P5 | 아래 파이썬 한 덩이 (⚠️ **1회차 정정 — 원래 명령은 거짓 통과를 냈다**) | **결과가 비어야 한다.** 백엔드는 `--reload` 없이 뜨므로 소스가 프로세스보다 새로우면 갱신되지 않는다 | 회차마다 다시 잰다 |
| P6 | `curl -s localhost:3000 -o /dev/null -w '%{http_code}'` | `200` | 회차마다 다시 잰다 |
| P7 | `grep -c 'superpowers-chrome' .claude/settings.local.json` | `2` 이상 (`Skill(superpowers-chrome:browsing)` + `mcp__…chrome__use_browser`) | `2` |
| P8 | `n=$(ps -axo comm= \| awk -F/ '{print $NF}' \| grep -c '^pytest'); echo "P8: pytest ${n}건"; [ "$n" -eq 0 ]` (⚠️ **2회차 재정정**) | `pytest 0건` — 테스트 DB가 실행마다 DROP/CREATE되는 공유 자원이다 (함정 H-X) | 회차마다 다시 잰다 |
| P9 | §7의 DSN 확인 명령 | `ohmyenglish` | `ohmyenglish` |

⚠️ **P5·P8은 1회차에서 원래 검사식이 거짓 통과를 냈다 — 고친 형태를 쓴다.**

- **P8**: `ps aux | grep -c '[p]ytest'`가 **3**을 냈으나 실제 `pytest`는 **0건**이었다. 잡힌 것은
  **검사를 실행한 셸 자신의 명령줄**이다(그 명령에 `pytest`라는 낱말이 들어 있다). `[p]` 트릭은
  grep 자신만 피하고 **호출한 셸은 피하지 못한다.** → **프로세스 이름**(`comm`)으로 센다.
- **P5**: `ps -o lstart=`가 로케일 문자열(`2026년 9월 6일 …`)을 내고 `find -newermt`가 그것을
  **거부한다** — 명령이 오류로 끝나는데 출력이 비어 보여서 "새로운 소스 없음"으로 읽힌다.
  ⚠️ **macOS `ps`는 `etimes`를 지원하지 않는다**(형식 목록을 출력한다). 아래를 쓴다:

⚠️ **2회차 재정정 — 1차 정정이 더 나빴다.** 아래 형태를 쓴다. 1차 정정은 `glob`이 **상대경로**라
**다른 cwd에서 돌리면 `srcs`가 0건이 되고 "통과"를 단정했다**(팀리드가 `/tmp`에서 재현: `소스 0건`인데
`P5: 통과`). `stat`은 절대경로라 예외조차 나지 않는다. **원래 형태는 최소한 오류를 냈지만 1차 정정은
조용히 통과했다** — 같은 거짓 통과를 더 나쁜 형태로 바꾼 것이다.
⚠️ **에이전트 스레드는 bash 호출마다 cwd가 초기화된다** — 상대경로에 기대면 안 된다.

⚠️ **3회차 재정정 (2026-09-06) — 2차 정정에는 전제가 빠져 있었다.** 로그 파일이 **지금 도는 백엔드의
것인지** 확인하지 않았다. 팀리드 실측: `/tmp/omy-backend.log`는 pid **15648**(이미 종료됨)이 쓴 것이고
실제로 `:8002`를 듣는 프로세스는 pid **41641**이었다. 즉 **다른 프로세스의 기동 시각과 소스를
비교하고 있었다** — 그러면 검사가 아무것도 보장하지 않는다(더 오래된 로그일수록 통과가 어려워지니
방향은 안전하지만, **로그가 소스보다 새로우면 낡은 백엔드가 조용히 통과한다**).

⚠️ **4차 재정정 (2026-09-06, 같은 날 두 번째) — 로그 파일의 생성 시각을 기동 시각으로 쓸 수 없다.**
`>` 리다이렉트는 파일을 **잘라내기만 하고 inode 를 유지한다** → `stat -f %B`(생성 시각)가 **처음 만든
시각에 머문다.** 실측: 백엔드를 재기동한 직후에도 `birth=1788656298`(낡음) · `mtime=1788665741`(방금)
이었고, 그래서 **방금 띄운 백엔드가 "소스보다 낡았다"는 거짓 실패**를 냈다.
→ 기동 시각은 **프로세스에서** 얻는다. ⚠️ **macOS `ps`는 `etimes`를 지원하지 않는다**(`keyword not
found`) — `etime`은 지원하고 `[[dd-]hh:]mm:ss`의 **로케일 무관 숫자 형식**이다(실측 `00:58`).

```bash
python3 - <<'PY'
import subprocess, glob, os, re, time
root = subprocess.run(["git","rev-parse","--show-toplevel"],capture_output=True,text=True).stdout.strip()
assert root, "리포 루트를 못 찾았다 — git 저장소 안에서 돌려라"
# ① 실제로 포트를 **듣고 있는** pid. ⚠️ 명령줄을 스캔하지 않는다 — 검사 스크립트 자신의
#    명령줄에 "--port 8002" 가 들어 있어 셸이 함께 잡힌다(P8 과 글자 그대로 같은 거짓 양성).
out = subprocess.run(["lsof","-nP","-iTCP:8002","-sTCP:LISTEN","-t"],capture_output=True,text=True)
pids = sorted({int(x) for x in out.stdout.split()})
assert len(pids) == 1, f"8002 를 듣는 프로세스가 정확히 1개여야 한다 — {pids}"
pid = pids[0]
# ② 로그가 **그 프로세스의 것**인지 (신원 확인). 이것이 없으면 ③이 뜻을 갖지 않는다.
log = "/tmp/omy-backend.log"
assert os.path.exists(log), f"{log} 이 없다 — 백엔드를 어느 로그로 띄웠는지 확인해라"
started = re.findall(r"Started server process \[(\d+)\]",
                     open(log, encoding="utf-8", errors="replace").read())
assert started, "로그에 'Started server process' 가 없다 — 백엔드 로그가 아니다"
assert started[-1] == str(pid), (
    f"로그가 지금 도는 백엔드의 것이 아니다: 로그 pid={started[-1]} · 실행 pid={pid}"
)
# ③ 기동 시각은 **프로세스에서** 얻는다 (로그 파일 생성 시각을 쓰지 않는다 — 위 4차 정정).
et = subprocess.run(["ps","-p",str(pid),"-o","etime="],capture_output=True,text=True).stdout.strip()
m = re.fullmatch(r"(?:(?:(\d+)-)?(\d+):)?(\d+):(\d+)", et)
assert m, f"ps etime 을 해석할 수 없다: {et!r}"
d, h, mi, s = (int(x) if x else 0 for x in m.groups())
start = time.time() - (d*86400 + h*3600 + mi*60 + s)
# ④ 소스가 프로세스보다 새로운지
srcs = glob.glob(os.path.join(root,"app/backend/app/**/*.py"), recursive=True)
assert srcs, "소스가 0건이다 — 경로가 틀렸다. 0건 검사로 통과를 단정하지 않는다"
newer = [os.path.relpath(p, root) for p in srcs if os.path.getmtime(p) > start]
print(f"P5: pid {pid} · 기동 {et} 전 · 소스 {len(srcs)}건 →",
      "통과" if not newer else f"실패 — {len(newer)}건: {newer}")
assert not newer
PY
```

**⚠️ 이 검사의 핵심 단정 넷 — 하나라도 빠지면 공허 통과가 된다.** (셋이었고 4차 정정으로 넷이 됐다)
1. **`len(pids) == 1`** — 듣는 프로세스를 `lsof`로 찾는다. **명령줄 스캔 금지**(셸 자기 자신이 잡힌다).
2. **로그 pid == 실행 pid** — 로그가 그 프로세스의 것임을 세운 **뒤에야** 시각 비교가 뜻을 갖는다.
3. **기동 시각은 `ps -o etime=`에서** 얻는다. **`stat %B` 금지** — `>`가 inode 를 유지해 낡는다.
4. **`assert srcs`** + **검사한 개수 출력** — 0건을 검사하고 통과를 단정하는 것이 이 절이 막으려는
   바로 그 실패다. 개수가 없으면 공허 통과를 구별할 수 없다.

**판별력 확인 (2026-09-06 팀리드 실측)**: 임계값을 흔들어 비교가 실제로 반응함을 확인했다 —
임계 `0` → **32/32**건이 "더 새로움" · 임계 `1시간 전` → **2/32** · 임계 `지금+1시간` → **0/32**.
그리고 재기동 **전**에는 이 검사가 정확히 실패했고(로그 pid 15648 ≠ 실행 41641) 재기동 **후**에
통과했다. **양쪽을 다 봤으므로 "판별력 미확인"이 아니다.**

⚠️ **P5가 실패하면 소스를 고치는 것이 아니라 백엔드를 재기동한다** — `--reload`가 없어 소스가 반영되지
않은 것이 실패의 뜻이다. 재기동 명령은 `docs/ops/local-run.md`가 소유한다.

⚠️ **P9는 표의 마지막 행이다** — 2026-09-06까지 이 산문 아래에 홀로 떨어져 있어 표로 렌더되지 않았다.
표 안으로 되돌렸다. **프리플라이트는 P1~P9 아홉 건이고 여덟 건이 아니다.**

⚠️ **설정 파일을 고치지 않는다.** P7이 실패하면 `.claude/settings*.json`·`.mcp.json`을 **편집하지 말고** 무엇이 없는지 적어 **"캡틴 몫"으로 보고하고 멈춘다.** 권한 설정은 사용자 소유다.

**기동 순서**(L4): DB(:5432) → 백엔드(:8002) → 프론트(:3000) → 브라우저. CORS가 `http://localhost:3000` 하드코딩이라 **두 번째 프론트를 :3001에 띄울 수 없다.** 플래그(`VOICE_ADAPTER` 등)는 **`app/backend/.env`를 고치지 않고 환경변수로만** 넘긴다 — 복구를 잊으면 영구화된다.

```bash
cd app/backend && .venv/bin/uvicorn app.api.main:app --port 8002 --log-level warning   # --reload 없음
cd app/frontend && npm run dev                                                          # :3000
```

## §3. 회차를 연다 — `.harness/browser_run_id.txt`

계획서 §13-4 미결(회차를 열 것인가)을 **여기서 닫는다: 연다.** 근거 둘 — ① §8의 복원 SQL이 `run_id`로 범위를 좁힌다. 회차 없이 돌면 "최근 세션"을 DB에서 추정해야 하고 그러면 캡틴이 같은 시각에 만든 세션을 지울 수 있다. ② `harness_sessions`는 "무엇을 지웠는지"의 감사 기록이다.

⚠️ **`.harness/run_id.txt`를 덮지 않는다** — `ws_session.py`가 **import 시점에** 그 파일을 읽으므로 다른 세션의 진행 중 회차 포인터를 하이재킹한다(작성 시점에 그 파일이 실재한다). 브라우저 레그는 **별도 파일** `.harness/browser_run_id.txt`를 쓴다. 새 수단이 아니라 파일명 하나다.

⚠️ **1회차 정정 — 원래 명령이 이 함정을 막지 못했다.** `tr -d ' \n'`으로 공백만 지우면
`INSERT 0 1`의 **`01`이 UUID 뒤에 붙어** 길이가 38이 된다(1회차에서 실제로 그랬다). 아래처럼
**UUID 형태를 정규식으로 추출**하고 **길이를 단정**한다 — 아래 절이 경고만 하고 명령이 막지 않으면
같은 사고가 반복된다.

```bash
cd app/backend && .venv/bin/python - <<'PY' > ../../.harness/browser_run_id.txt
import re, sys, subprocess
sys.path.insert(0, "../../tests/harness")
from psql_cli import psql
commit = subprocess.run(["git","rev-parse","--short","HEAD"],capture_output=True,text=True).stdout.strip()
out = psql(f"insert into harness_runs (git_commit, note) values ('{commit}','browser-leg') returning id")
m = re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", out)
assert m, f"UUID 를 못 찾았다: {out!r}"
print(m.group(0), end="")
PY
# 개설 직후 반드시 확인한다 — 36자여야 한다.
# ⚠️ **리포 루트에서 돌린다.** 위 블록이 `cd app/backend` 로 들어간 채 끝나므로 이어서 돌리면
#    `FileNotFoundError` 로 죽는다 (T5a D-2 실측 — 파일은 정상 기록됐는데 검증만 막혔다).
#    §2 가 스스로 경고하는 "에이전트 스레드는 bash 호출마다 cwd 가 초기화된다"와 같은 부류다.
python3 -c "import subprocess,os; r=subprocess.run(['git','rev-parse','--show-toplevel'],capture_output=True,text=True).stdout.strip(); v=open(os.path.join(r,'.harness/browser_run_id.txt')).read(); assert len(v)==36 and v.count('-')==4, f'오염됨: {v!r} (len={len(v)})'; print('run_id OK:', v)"
```

이 파일에 **개행이나 psql 부산물이 섞이면 안 된다** — 값이 SQL에 그대로 들어간다(1회차에서 `INSERT01`이 섞여 세션 하나가 미등록으로 남았다). **브라우저 레그에는 세션 자동 등록 훅이 없다**(세션을 만드는 주체가 브라우저다) → **teardown 직전에 시간창 스윕으로 등록한다**(§8 ①-a).

## §4. 계측 자기검사 — 조용히 퇴화하면 시끄럽게 죽인다

계측 스크립트(`tests/harness/instrument.js`, 계획서 T2 산출물)는 아래를 만족해야 하고 하나라도 어긋나면 **ERROR로 끝낸다. 단정 평가로 넘어가지 않는다.**

1. `eval` 반환값이 정확히 `'instrumented'`다.
2. 후킹 대상의 **존재를 먼저 단정**하고 없으면 throw한다. 조용히 건너뛰면 계수가 0이 되고 **0은 "고장"과 구별되지 않는다.**
3. ⚠️ **후킹 대상이 셋이고 형태가 서로 달라 같은 방식으로 단정할 수 없다** (2026-09-06 재설계로 하나가 늘고 하나가 바뀌었다):
   - `WebSocket.prototype.onmessage` — **접근자 프로퍼티**라 `Object.getOwnPropertyDescriptor`가 `get`/`set`을 준다(서버→클라이언트 프레임 계수).
   - **`WebSocket.prototype.send`** — **메서드**. ⚠️ **새로 추가된 대상이다**(A1-7의 계수 지점을 `sendAudio`에서 여기로 옮겼다). payload를 파싱해 `type`별로 나눠 센다 — `audio`와 `end_session`을 **따로** 세는 것이 A1-7 음성 대조의 근거다.
   - **`AudioBufferSourceNode.prototype.start`** — **메서드**. ⚠️ **`createBufferSource`를 대체한 대상이다.** 명세상 `start`는 `AudioBufferSourceNode`가 자기 것으로 갖고 `stop`은 `AudioScheduledSourceNode`에 있어 **둘이 다른 자리일 수 있다.** 호출 인자(`when`)도 함께 적립한다(A1-4 대조 ②).
   
   **어느 프로토타입에서 성립하는지는 T2에서 실측해 확정한다**(§11-2). 여기서 정답을 단정하지 않는다.
4. `window.__omy`가 없거나 **아래 키 중 하나라도 빠져 있으면 PASS를 낼 수 없다.** ⚠️ **재설계로 키가 늘었다** — T2가 채워야 하는 계약이다:
   - `recv` — 서버→클라이언트 프레임 종류별 계수(A1-1·A1-2·A1-3·A1-6).
   - **`sent`** — 클라이언트→서버 프레임을 `type`별로 나눈 계수. **`audio`와 `end_session`을 따로 담는다**(A1-7 측정과 그 음성 대조가 같은 객체에서 나온다).
   - **`started`** — `start` 호출 계수와 **호출 인자 `when`의 배열**(A1-4 측정과 대조 ②).
   - **`finalLines`** — `final`마다 적립한 확정 줄 `textContent` **배열**(A1-5 내용 단정). 개수만 담지 않는다.
   
   ⚠️ **계수와 대조가 같은 객체에서 나오는 것이 의도된 것이다** — 대조를 별도 경로로 재면 그 경로가 조용히 죽었을 때 "대조가 0이다"를 "무력화 성공"으로 오독한다.

**계수 지점은 `AudioBufferSourceNode.prototype.start`다 — `createBufferSource`가 아니다.**
⚠️ **2026-09-06 재설계(`TASK-29`)**: `lib/audio.ts:enqueueAudio`는 노드 **생성**(`createBufferSource`)과 재생 **시작**(`source.start(startAt)`)을 **별개 줄에서** 부른다(직접 읽어 확인). 생성만 세면 `start` 줄을 지워도 계수가 3을 유지한다 — **소리는 나지 않는데 통과하는** 형태다(계수 지점 ≠ 효과 지점). `start`가 효과 지점이다.

`sampleCount === 0`을 early-return하므로(`enqueueAudio`) 프레임당 **정확히 한 번**이다. `window.Audio`를 세는 run-1 방식은 **항상 0**이다: `lib/audio.ts` 모듈 docstring 제목이 "왜 `MediaRecorder`와 `new Audio()`를 쓰지 않는가"이고 재생은 `VoiceIo.enqueueAudio`가 한다.

⚠️ **`start`를 어느 프로토타입에서 후킹하는지는 T2 실측이다**(§11-2) — 명세상 `start`는 `AudioBufferSourceNode`가 자기 것으로 갖고 `stop`은 `AudioScheduledSourceNode`에 있어 **둘이 다른 자리일 수 있다.** 정답을 여기서 단정하지 않는다.

## §5. 단정 표 — 기대값의 유도 방식과 음성 대조

**유도 방식**: ⓐ 픽스처에서 **연역** · ⓑ 런타임에 토큰/API에서 **유도** · ⓒ 그 둘이 불가능(이유를 적는다). ⚠️ **"코드 인용이 붙어 있다"는 기준이 아니다** — 하드코딩된 `#595959`도 `globals.css` 인용을 가질 수 있고 그러면 **인용이 붙은 채로 썩는다.**

> ## ⚠️ 판별력 재설계 — **7건을 고쳤다** (2026-09-06 · `TASK-29`)
>
> **독립 리뷰(codex, 2026-09-06)가 A1-4 · A1-5 · A1-7 · A3-1 · A4-1 · A4-2 · A5-1에서 거짓 통과
> 경로를 찾았다.** 상세와 공통 형태는 `docs/design/2026-09-06-review-outcomes.md` §4가 소유한다 —
> 여기서 재서술하지 않는다. **아래 표의 그 일곱 행이 재설계된 판이다.**
>
> ⚠️ **이 문서가 "단정 18건 · 음성 대조 빈칸 0건"을 품질 근거로 내세운 것이 오판이었다.**
> 그것은 대조가 **있다**는 지표이고 대조에 **판별력이 있다**는 지표가 아니다. 1회차에서 자기
> 검사식 3건이 이미 거짓 통과를 냈고, 리뷰가 7건을 더 찾았다.
>
> **재설계에 쓴 수단 4가지 — 새 단정을 쓸 때도 이 순서로 고른다**:
> ① **계수 지점을 효과 지점으로 옮긴다** — A1-4 `createBufferSource`→`start` ·
>    A1-7 `sendAudio`→`WebSocket.prototype.send`. 만든 것을 세지 않고 **쓴 것**을 센다.
>    ⚠️ **A1-7은 서술 정정이다 — 계측을 고친 것이 아니다.** 2026-08-26 원본 스크립트
>    (`docs/ops/2026-08-26-test-harness.html`)는 **이미 `WebSocket.prototype.send`를 후킹하고
>    `type === 'audio'`로 걸러 세고 있었다**(직접 읽어 확인). 낡은 것은 스크립트가 아니라 **이
>    문서의 A1-7 서술**("계측이 `sendAudio` 호출을 계수")이었고, 그 서술대로 새 계측을 만들면
>    실제로 뚫렸을 것이다. **재설계가 A1-7에 실제로 더한 것은 계수 지점이 아니라 `end_session`
>    동반 계수**다(계수 0이 "전송 없음"인지 "후킹 고장"인지 가른다). A1-4는 이와 달리 **스크립트
>    자체가 낡았다**(`window.Audio` 계수 → 항상 0).
> ② **전역 검색을 요소 지목 + 등호로 바꾼다** — A3-1 · A4-2 · A5-1. 껍데기·뒤바뀜·동적 문구가
>    한 번에 닫힌다. 「DOM에 있다」는 포함 검사가 이 문서에서 거짓 통과를 가장 많이 만들었다.
> ③ **개수 단정에 내용 단정을 더한다** — A1-5 · A4-1. 개수를 **버리지 않고 더한다**(개수는
>    선택자가 살아 있음을 증명하고 내용은 렌더가 살아 있음을 증명한다 — 서로를 대신하지 못한다).
> ④ **기대값이 0이 될 수 없게 표본을 고른다** — A4-1은 `N >= 1`을 전제하고, 0이면 FAIL이 아니라
>    **BLOCKED**다(화면 결함이 아니라 표본 선택 실패다).
>
> **규약은 그대로다**: 단정을 채택하기 전에 **그 대조가 무력화에서 실제로 FAIL을 내는지**
> 확인한다. 확인하지 않았다면 "대조 있음"이 아니라 **"판별력 미확인"**으로 적는다.
>
> ⛔ **재설계는 판별력을 *설계*했을 뿐 *관측*하지 않았다.** 각 대조가 실제로 FAIL을 내는지는
> T2·T3·T4 회차에서 확인한다. **확인 전에는 그 단정을 `PASS`로 보고하지 않는다.**
>
> ⛔ **재설계 후에도 회차에서 판별력 미확인으로 남을 수 있는 것 2건**:
> **A1-7** — 무음 스트림 대조가 `0`을 못 내면(§11-4) · **A4-2** — 그 회차 세션의 교정이
> **1건뿐이면** 기대값 교차 대조를 평가할 수 없다. 둘 다 그 회차 기록에 그대로 적는다.

**ⓐ의 근거**: `app/backend/app/audio_gateway/fixtures.py:FIXTURE_TURNS`는 **3턴**이고 세 응답 모두 **7 단어**다. `stub.py:_partial_prefixes`가 `sorted({max(1,7//3), max(1,2*7//3)})` = `{2,4}` → **턴당 partial 2개**. `stub.py:StubVoiceAdapter.events`가 턴마다 `agent final → user partial ×2 → user final → TONE_WAV_FRAME`을 낸다. **픽스처가 바뀌지 않는 한 다른 값이 나올 수 없다** — 관측에서 귀납한 값이 아니다. run-1이 같은 값을 적은 것은 **보강 정황이지 독립 확증이 아니다**(그 기록이 스스로 작성자=검증자임을 적었다). `>=`를 쓰지 않고 **등호로 조인다** — `>=`는 프레임이 중복 도달해도 통과한다.

### C1 — 세션 관통 (`VOICE_ADAPTER=stub`)

| # | 단정 | 기대 · 유도 | 음성 대조 (무력화 수단) |
|---|---|---|---|
| A1-0 | idle 화면 추천 이유 줄 | 접두 `오늘 이걸 연습해요:`(`page.tsx:NEXT_PLAN_PREFIX`)를 가진 `<p>` 개수 == `GET /api/sessions/next-plan`의 `reason`이 null이면 0, 아니면 1 — **ⓑ API에서 유도**(화면의 상류라 순환이 아니다) | **학습 시작 클릭 후 그 `<p>`가 0개다** — `page.tsx:271`이 `state === "idle"`로 가둔다. 사라지지 않으면 이 요소가 계획 표시라는 전제가 무효다 (상태 전이) |
| A1-1 | `recv.final` | **6** = 3턴 × (agent 1 + user 1) — ⓐ | `VOICE_ADAPTER=stub_unresponsive` → **0** (환경변수) |
| A1-2 | `recv.partial` | **6** = 3턴 × 2 — ⓐ | 같은 대조 → **0** (환경변수) |
| A1-3 | `recv.audio` | **3** = 3턴 × `TONE_WAV_FRAME` 1 — ⓐ | 같은 대조 → **0** (환경변수) |
| A1-4 | 재생 **시작**(`AudioBufferSourceNode.prototype.start` 호출 수) | **3** — ⓐ. `enqueueAudio`가 프레임당 노드 1개를 만들어 `start`를 1회 부른다. ⚠️ **`createBufferSource` 계수를 버렸다** — 생성만 세면 `start` 줄이 지워져도 3이 나온다(§4). ⛔ **`VOICE_ADAPTER=stub`에서만 측정한다** — `stub_unresponsive`는 `audio` 프레임을 0건 보내므로 이 단정을 **평가할 수 없다**(T2·T5a 실측: `started.count` 0·1). ⚠️ **T2에서 3이 나오지 않은 원인은 화면 결함이 아니다**: 세션이 23ms에 자기종료해 `voiceRef.current`가 채워지기 전에 프레임이 도착하고 `page.tsx`의 `enqueueAudioFrame`이 `if (!voice) return`으로 버린다. **그러므로 A1-4는 세션 길이가 워클렛 준비보다 긴 구성에서만 유효하고, 그 구성이 확보되기 전에는 `측정 불가`로 보고한다**(FAIL 아님) | ① `VOICE_ADAPTER=stub_unresponsive` → **0** (환경변수) ② **`started.calls`의 `when`이 비감소이고 첫째 < 셋째다** — `nextStartTime`이 `buffer.duration`만큼 밀리는 것이 큐잉의 효과다. 세 값이 전부 같으면 큐가 동작하지 않은 것이고 **계수만 맞은 것**이다 ③ **`started.calls[i].afterRecvAudio`로 어느 수신 프레임에서 났는지 확인한다**(2026-09-06 계측에 추가한 프레임 태깅). 태깅이 없던 동안 T2의 0/1 원인 판정이 **순서에서의 추론**에 머물렀다 (인자·태그 검사) |
| A1-5 | 확정 줄 수 **와 내용** | 접두 `질문: `/`답변: `를 가진 `<p>` **6개**이고, **DOM 순서대로 `textContent`가 정확히** `질문: {FIXTURE_TURNS[i][0]}` / `답변: {FIXTURE_TURNS[i][1]}` (i=0,1,2 교대) — ⓐ. 스텁이 픽스처 문장을 **축자로** 흘린다(`stub.py`가 `FIXTURE_TURNS`의 question·answer를 그대로 `text=`에 넣는다 — 직접 읽어 확인). I-8 병합(`page.tsx:123`)은 **연속 동일 화자**에만 걸리고 픽스처는 교대하므로 병합 0회. ⚠️ **개수 단정을 버리지 않고 내용 단정을 더했다** — 개수만 세면 `{line.text}` 보간이 사라져도 6개가 남는다 | ⛔ **스냅샷 시점을 고르지 않는다 — `omy.judgeFinalLines(expected)`를 쓴다**(2026-09-06 계측 신설). 동기 스냅샷은 React commit 전이라 `[]`가 되고 rAF는 `router.push` 이후라 역시 `[]`가 된다(T2에서 **서로 반대로** 실패했다). MutationObserver가 DOM이 바뀔 때마다 적립하고, 판정은 **셋을 함께** 본다: ① 관측 **최대 개수 == 기대 개수**(초과 없음) ② 그 최대 지점의 `texts`가 **순서까지 일치** ③ `count`가 **비감소**(전사문은 append-only, 병합은 개수를 늘리지 않는다). ⚠️ **"기대값과 같은 스냅샷이 하나 있다"만으로 판정하면 골라내기다** — 그래서 셋을 함께 건다. **판별력 실측(팀리드, 2026-09-06)**: 합성 5시나리오에서 정상만 pass — 본문삭제 → `texts` 실패 · 초과렌더 → `count` 실패 · 순서뒤바뀜 → `texts` 실패 · 개수감소 → `nonDecreasing` 실패. ④ 그 밖에 **기대 문장 6개가 각각 20자 이상**(실제 최단 35자)이고 **sentinel 변형이 어떤 `<p>`와도 같지 않다** (문자열 변형) |
| A1-6 | 결과 화면 이동 | URL이 `/results/<session_id>` — **ⓑ `session_started` 프레임의 `session_id`를 계측이 기록해 대조** | `stub_unresponsive` → URL이 `/`에 남고 `사유: voice_adapter_connect_timeout`이 뜬다 (환경변수) |
| A1-7 | 마이크 합성 → WS **실제 송신** | 계측이 `WebSocket.prototype.send`를 후킹해 payload를 파싱하고 `type === "audio"`인 프레임을 계수 → **> 0**, 그리고 각 프레임의 `data`가 빈 문자열이 아니다 — ⓑ. ⚠️ **이 문서가 적었던 `sendAudio` 계수 서술을 버렸다**(원본 스크립트는 이미 `send`를 후킹했다 — ⛔ 상자 ①): `ws.ts:SessionSocket.send`가 `readyState !== OPEN`이면 **조용히 버린다**(전송하지 않고 반환) → 소켓이 닫혀 실제 전송이 0이어도 `sendAudio` 계수는 증가한다(계수 지점 ≠ 효과 지점). `WebSocket.prototype.send`는 그 early-return을 통과한 호출만 본다 | ① **같은 후킹으로 `type === "end_session"` 프레임을 함께 센다 — 정확히 1건.** 이것이 0이면 `audio` 계수 0은 "전송 없음"이 아니라 **후킹 고장**이다. 2회차에서 A1-0에 쓴 것과 같은 형태의 구별이다. ⚠️ 이 값은 **세션 종료 클릭 후에** 읽는다(그전에는 아직 보내지 않았다) ② ⛔ **무음 계수 대조는 폐기했다 — 원리적으로 0이 될 수 없다**(T2 실측 · 팀리드가 코드로 확인). `lib/audio.ts`의 캡처 워클렛 `process()`가 **진폭과 무관하게** 512샘플마다 `postMessage`한다(무음 게이트 없음) → 무음·유음이 프레임 **146**건 · 바이트 **199,728**로 **완전히 같다.** ③ **대체 대조 — PCM 내용을 센다.** 계측이 `sentAudioNonZeroFrames`(0이 아닌 샘플이 있는 프레임 수)를 함께 기록한다. `config.silentMic = true`에서 **`sent.audio > 0`이면서 `sentAudioNonZeroFrames === 0`**이 되어야 하고, 톤에서는 둘이 같아야 한다. **팀리드가 이 판별력을 실측했다**(2026-09-06): 같은 바이트 길이(각 1368)의 무음·톤 프레임을 후킹에 넣어 `audio 2` · `nonZeroFrames 1` — **바이트로는 못 가르고 내용으로는 갈린다.** ⚠️ 이 대조는 **계측 단위에서 확인됐고 세션 관통에서는 미확인이다**(그 구성은 `stub`가 필요하다) |
| A1-8 | DB 전사문 행 수 | `utterances` **6행** — ⓐ (final 6건. partial은 저장되지 않는다) | `stub_unresponsive` 세션의 `utterances` **0행** (환경변수) |

### C2 — 렌더 위계 (측정 절차는 §6. **라이트·다크 두 모드 필수**)

| # | 단정 | 기대 · 유도 | 음성 대조 (무력화 수단) |
|---|---|---|---|
| A2-1 | partial 줄은 muted | 접두 `<p>` 1개 + 그 `getComputedStyle(...).color` == **probe 유도 muted 값** — ⓑ | **주입을 아예 생략한 회차에서 접두 `<p>`가 0개**(§6-0). 이것이 없으면 주입이 조용히 실패해도(`ws.ts:isServerEvent` 게이트가 프레임을 거르거나 `ws.ts:74`의 `catch`가 파싱 실패를 삼키는 경로) 측정과 대조가 **둘 다** 통과한다 (주입 생략) |
| A2-2 | 확정 줄은 foreground | partial 줄이 사라지고(`setPartialLine(null)`) 접두 `<p>` 1개의 색 == **probe 유도 foreground 값** — ⓑ | ① 위와 같은 주입 생략 ② **probe 두 값이 실제로 서로 다름** — 같으면 위계 단정이 무의미하게 통과한다 (probe 비교) |
| A2-3 | 토큰이 모드별로 다르다 | 라이트의 muted 유도값 ≠ 다크의 muted 유도값 — ⓑ | **같은 모드에서 두 번 읽으면 같은 값이다** — 다르면 `Emulation.setEmulatedMedia`가 실제로 걸리지 않았다는 증거 (모드 전환 생략) |

### C3 결과 화면 · C4 교정 카드 · C5 발음 배지

| # | 단정 | 기대 · 유도 | 음성 대조 (무력화 수단) |
|---|---|---|---|
| A3-1 | 5상태 라벨 | **상태 요소 하나의 `textContent`가 기대 라벨과 정확히 같다.** 요소는 **구조로** 지목한다 — `main`의 **첫 직계 `<p>`**(`results/[sessionId]/page.tsx`가 `result`가 있을 때 그 자리에 `STATUS_LABEL[result.status]`를 한 번 렌더하고, 앞선 두 `<p>`는 `!sessionId`·`!result` 조건이라 `result`가 있으면 **둘 다 부재**다 — 직접 읽어 확인). 라벨 값은 `STATUS_LABEL` — **ⓒ 하드코딩**: 화면이 소유하는 한국어 문구이고 API는 기계값(`status`)만 준다. ⚠️ **DOM 전역 검색을 버렸다** — API가 실어 보낸 **동적 문구**(교정 `reason` 등)가 같은 라벨을 포함하면 전역 검색은 못 막는다. 요소를 지목하고 **등호로** 재면 그 경로가 닫히고, 「다른 출현은 전부 주석이다」라는 grep 근거에 더는 의존하지 않는다 | **다른 상태의 세션을 재방문하면 같은 요소의 `textContent`가 그 상태의 라벨로 바뀐다** — 요소가 **상태에 의해 구동됨**을 증명한다. 상수를 렌더하고 있으면 바뀌지 않는다. ⚠️ 이전 판의 "나머지 4개 라벨이 DOM에 없다"는 동적 문구에 뚫린다 (상태별 세션 재방문) |
| A3-2 | 없는 세션 | 존재하지 않는 uuid로 방문하면 **5개 라벨 전부 부재** + 오류 문구 — ⓑ | 실제 세션 방문 시 그 오류 문구가 **부재**해야 한다 (URL 조작 · 상호 대조) |
| A4-1 | 교정 카드 구조 | 접두 `원문:`·`교정문:`를 가진 `<p>`가 **각 N개**, N = `GET /api/sessions/{id}/results`의 `corrections.length` — **ⓑ API에서 유도**(상류라 순환이 아니다). ⚠️ **`N >= 1`을 전제로 단정한다** — `corrections`가 빈 세션을 primary로 쓰면 `0 == 0`이 되어 **카드 구현이 없어도 통과한다.** primary는 `corrections`가 **비지 않은** 세션을 고른다(§9의 보존 목록). N이 0이면 FAIL이 아니라 **BLOCKED**다 — 화면 결함이 아니라 **표본 선택 실패**다. 그리고 각 카드가 `<p>` **정확히 3개**를 가지며 **라벨 없는 셋째 줄이 비어 있지 않다** | `corrections`가 빈 세션(`no_utterances`)에서 두 접두가 **0개** — ⚠️ 이것은 **음성 대조로만 쓰고 primary로 쓰지 않는다** (세션 재방문) |
| A4-2 | 이유 문구 **카드별** 관통 | 각 i에 대해 `원문: {corrections[i].original_span}`을 담은 **그 카드 `<div>` 안의** 라벨 없는 셋째 `<p>`의 `textContent`가 `corrections[i].reason`과 **정확히 같다** — ⓑ. 카드 컨테이너는 실재한다: `results/[sessionId]/page.tsx`의 `corrections.map`이 `original_span`·`correction`·`reason` 세 `<p>`를 **한 `<div>`에** 담는다(직접 읽어 확인). ⚠️ **DOM 전역 포함 검사를 버렸다** — 이유가 **카드끼리 뒤바뀌어도** 전역 검색은 전부 "있다"를 낸다. ⚠️ **대조 전에 `reason`이 빈 문자열이 아님을 단정한다** — 비었으면 FAIL이 아니라 **BLOCKED**(모델이 안 채운 것이지 화면 결함이 아니다) | ① `reason`에 sentinel을 덧붙인 변형이 그 카드의 셋째 `<p>`와 **같지 않다** (문자열 변형) ② **교정 2건 이상인 세션에서 `reason`을 서로 맞바꾼 기대값으로 다시 재면 FAIL이 난다** — 뒤바뀜을 실제로 잡는지 증명한다. **앱 소스를 고치지 않고 기대값만 바꿔** 계산한다. ⚠️ 교정이 1건뿐인 세션에서는 이 대조를 **평가할 수 없다** → 그 회차의 A4-2는 **판별력 미확인**으로 적는다 (기대값 교차) |
| A5-1 | 배지 4 outcome | `pending`·`correct`·`incorrect`·`unclear`를 각각 주입 → **배지 요소가 정확히 1개**이고 그 `textContent`가 `app/page.tsx:PRONUNCIATION_BADGE`의 해당 문구와 **정확히 같다.** 요소는 `p[aria-live="polite"]`로 지목한다 — 프론트 전체에 `aria-live`가 **1건뿐**임을 직접 확인했다(`app/page.tsx`의 배지). **ⓒ 하드코딩**: 프레임은 기계값 `outcome`만 나르고 문구는 화면 상수다. ⚠️ **"대상 문구가 DOM에 있다"를 버렸다** — 그것은 배지 4종을 **전부** 렌더해도 통과한다. **요소 개수 1 + 등호**가 그 경로를 닫는다. ⚠️ 세 문구가 `/results/*`의 `OUTCOME_LABEL`에도 있는 문제는 **요소를 지목하므로 더는 성립하지 않는다** | ① **주입하지 않으면 배지 요소가 DOM에 부재**(`app/page.tsx`의 `{pronunciation && …}`) (주입 생략) ② **4 outcome을 순차 주입하며 같은 요소의 `textContent`가 매번 바뀐다** — 상수를 렌더하고 있으면 바뀌지 않는다 (순차 주입) |
| A5-2 | `target_sound` 미렌더 | 주입한 `target_sound`에 **sentinel 값**을 넣고 DOM 전체에서 **0건** — ⓑ 런타임 유도(설계서 §10 미결 4) | **같은 프레임의 `outcome` 문구는 있어야 한다**(A5-1) — DOM 검색 자체가 동작함을 증명한다. 둘 다 0이면 주입이 실패한 것이다 (동일 프레임 대조) |

## §6. C2 측정 절차 — 타이밍에서 떼어낸다

run-1의 스로틀 스크립트는 **회수 불가로 확정**됐다(지목된 CDP 캐시 세션이 존재하지 않고 전체 캐시에 `__omy` 0건). 스텁 `events()`에 지연을 넣지 않는다 — ① 생산 코드에 테스트 전용 경로 ② D계층 통합 테스트가 스텁 타이밍에 의존 ③ `sleep`이 모든 백엔드 테스트를 느리게 한다. 검증하려는 규칙("partial은 muted, final은 foreground")은 **시간의 함수가 아니다**:

⛔ **전 과정을 `eval` 한 번에 넣는다 (2026-09-06 T5a 실측 — 이것을 안 지키면 반드시 실패한다).**
클릭 → 주입 → 판독을 **액션 여러 개로 쪼개지 마라.** 창은 10초인데 **에이전트 라운드트립이 약 30초**다
(실측: `click` 액션 다음 `eval`이 페이지에 닿기까지 약 30 s, 실패 회차의 첫 스냅샷이 pre-click
마커로부터 **37,992 ms**). ⚠️ **이 문서가 그것을 명시하지 않아 T5a 첫 회차가 실제로 창을 넘겼다** —
문서를 성실히 따른 결과였다. **병목은 페이지가 아니라 라운드트립이다**: 페이지 쪽 8프레임 주입은
`session_started`로부터 **256 ms**(창의 **2.6%**)에 끝난다.

0. **주입 전에 센다** — 접두 `<p>`가 **0개**임을 확인한다. 0이 아니면 그 회차는 **ERROR**다(측정으로 넘어가지 않는다). 이것이 A2-1·A2-2의 음성 대조다.
   ⚠️ **`active` 도달 후에 센다** (T5a D-7 — 비용 0의 강화). 클릭 전에 재면 **컨테이너가 아직
   마운트되지 않아** 0일 수 있고, 그러면 **주입 경로가 죽어 있어도 이 대조가 통과한다.** `active`
   도달 시점(전사문 컨테이너가 `대화를 기다리는 중...`을 그리고 버튼이 `학습 종료`인 상태)에서
   0개임을 재면 그 경로가 닫힌다. T5a가 둘 다 재서 둘 다 0이었다.
1. `partial` 프레임만 주입 → 접두 `<p>`가 **1개**로 늘었음을 확인하고 `getComputedStyle(...).color`를 읽는다.
2. `final` 프레임 주입 → 다시 읽는다. partial 줄이 사라졌는지와 확정 줄의 색을 함께 단정한다.

**대상 요소를 색으로 고르지 않는다.** 색은 *재려는 값*이므로 선별에 쓰면 자기순환이다. `--foreground-muted`는 `app/frontend/app/page.tsx`에 **7건** 있고(`grep -c`로 확인) partial 줄과 무관한 muted 요소가 최소 5개다(`듣고 있어요...` `:321` · `사유: {failureReason}` `:355` · 안내 문구 등) — "muted 요소가 있다" 형태의 단정은 **주입이 실패해도 통과한다.** 선별은 **구조로만** 한다: `<strong>`의 텍스트가 `질문: `/`답변: `인 `<p>`. 그 접두를 가진 `<p>`는 확정 줄(`page.tsx:307~312`)과 partial 줄(`:313~317`) **둘뿐**이고, 어느 것이 무엇인지는 **주입한 프레임이 정한다.**

**기대값은 하드코딩하지 않고 런타임에 유도한다.** 임시 probe 요소에 `style.color = 'var(--foreground-muted)'`를 걸고 `getComputedStyle(probe).color`를 읽는다. ⚠️ `getPropertyValue('--foreground-muted')`를 직접 비교하지 않는다 — 그쪽은 `#595959` 형태로 측정 대상의 `rgb(89, 89, 89)`와 문자열이 다르다. probe를 거치면 **같은 엔진이 같은 표현으로** 정규화한다. **단정의 정본은 색값이 아니라 `globals.css` 머리주석의 위계 계약**이다(`:5~7` — "강조 대상은 `--foreground`, 덜 강조할 보조 문구는 `--foreground-muted` … '덜 강조'를 밝기가 아니라 **대비**로 표현하기 때문에 배경이 뒤집혀도 살아남는다"). 팔레트가 바뀌어도 이 단정은 살아남는다. 모드 전환은 `measure_contrast.py`가 이미 쓰는 CDP `Emulation.setEmulatedMedia`를 재사용한다(새 수단 0개).

**주입 창** — `VOICE_ADAPTER=stub_unresponsive`로 띄운다. `audio_gateway/session.py:102`가 `session_started`를 `_connect()`(`:104` → `:126 asyncio.wait_for(self._adapter.start(), …)`)보다 **먼저** 보내고, `stub.py:70`의 `await asyncio.Event().wait()`는 영원히 끝나지 않으므로 소켓이 살아 있고 경쟁 프레임이 **0인 구간**이 열린다(세 줄 모두 직접 읽어 확인). ⚠️ **창은 유한하다 — `session.py:53 CONNECT_TIMEOUT = 10.0`.** T5a 실측: `session_started` →
`session_failed`가 **10,023 ms**(1회차 10,071 ms)로 그 상수와 일치한다.

**✅ 창에서 주입이 실제로 먹는다 — T5a ④가 확정했다**(§11-5·6 닫힘). 주입 8프레임이 창의 **2.6%**
(256 ms)에 끝났고 2회 독립 회차가 일치했다. **§7-6의 직렬 큐 대안으로 내려갈 필요가 없다.**

⛔ **창 이탈 판별의 근거를 정정한다 (T5a D-8 — 이전 서술이 틀렸다).**
이전 판은 *"`사유:` 요소엔 접두가 없으므로 **접두 `<p>` 개수가 늘지 않는다**"*로 판별했다.
**실제로는 개수가 늘지 않는 것이 아니라 0으로 떨어진다.** `page.tsx`가 전사문 컨테이너를
`state === "active" || state === "ending"`으로 가두고 `failed`는 **별도 블록**이라(팀리드가 직접 읽어
확인) `session_failed`에서 **컨테이너가 통째로 언마운트된다** — T5a 실측: 접두 `<p>` **2 → 0** ·
배지 **1 → 0** · `사유:` `<p>` **0 → 1**.

→ **판별 자체는 성립한다**(창을 넘긴 회차에서는 기대 개수가 절대 나오지 않는다). 바뀐 것은 근거이고,
**틀린 근거를 남기면 다음 회차가 "개수가 그대로면 창 안"이라고 오독한다.** 판별은 이렇게 한다:
**기대 개수가 나오지 않고 `사유:` `<p>`가 1개면 창을 넘긴 것**이다. 그때는 **FAIL이 아니라 ERROR로
보고하고 재시도한다** — 전 과정을 한 `eval`에 넣는 방식으로 바꾼다(위 ⛔).

⚠️ T5a에서 CDP 주입이 실패해 지연 방식으로 내려가야 한다면 **단일 직렬 큐로만** 간격을 벌린다. 프레임마다 독립 `setTimeout`을 걸면 `final`이 지연된 `partial`보다 먼저 디스패치되어 재려는 전이가 성립하지 않는다.

## §7. DB 접근 — 이 문서가 정본이다

**`tests/harness/psql_cli.py`만 쓴다. `podman exec`를 쓰지 않는다.** 이 헬퍼는 `DATABASE_URL`(`scripts/db_utils.py:base_dsn`)을 따라가므로 설정이 가리키는 DB에 붙는다.

```bash
cd app/backend && .venv/bin/python -c "
import sys; sys.path.insert(0,'../../tests/harness')
from psql_cli import psql, psql_binary
print(psql_binary()); print(psql('select current_database()'))
"
```

작성자가 직접 돌린 출력(2026-09-06): `/opt/homebrew/opt/postgresql@17/bin/psql` · `ohmyenglish`. 세 사실이 여기 걸린다 — **백엔드 venv가 필요하다**(`db_utils`가 최상단에서 `asyncpg`를 import한다) · **`DATABASE_URL`은 환경변수로만 읽는다**(`app/backend/.env`만 고쳐도 반영되지 않는다. 기본값 `postgresql://ohmy:ohmy@localhost:5432/ohmyenglish`가 현재 `.env`와 일치한다) · **homebrew `postgresql@17`은 keg-only라 `psql`이 PATH에 없다**(`psql_binary()`가 keg를 찾는다).

⚠️ **DB 공유가 스키마 수준이다.** 같은 데이터베이스 `ohmyenglish` 안에 다른 프로젝트의 `en_coach` 스키마가 있고 소유자가 다르다(직접 확인: `en_coach:en_coach` · `public:pg_database_owner` · `current_user = ohmy`). **우리 것은 `public` 하나뿐이다** → `pg_dump`를 범위 없이 돌리면 `permission denied for schema en_coach`로 막힌다. **`-n public`을 붙인다.**

## §8. teardown — 매 태스크의 일부다

공유 dev DB를 파괴적으로 쓴다. **세션 수·패턴 수·`frequency`를 baseline과 대조하는 것까지가 끝**이다. 전제: 회차 시작 시각(`WINDOW_START`)과 `.harness/browser_run_id.txt`(§3). SQL은 §7의 헬퍼로 던진다. `00000000-0000-0000-0000-000000000001`은 시드 사용자 id다.

**0. 회차 시작 전에 baseline을 뜬다** (없으면 캡틴의 패턴을 함께 지울 위험을 배제할 수 없다). `frequency`·`last_seen_at`을 함께 뜬다 — 마지막 대조(④)와 **복원(②)**이 그 두 값을 요구한다.

⛔ **무조건 `drop`하지 않는다 (2026-09-06 정정).** 이전 판은 `drop table if exists`로 시작했다.
그러면 **앞 회차의 teardown이 ②를 못 끝내고 죽은 경우**(파괴적 UPDATE는 이미 실행됨) 새 회차가
**오염된 값을 새 baseline으로 스냅샷**하고, 그 순간 원값의 사본이 **영구히 사라진다.**
baseline은 DB 표라서 그 표가 유일한 사본이다.

**먼저 drift를 본다 — 0이 아니면 멈춘다:**

```sql
-- 앞 회차가 정상 종료했으면 0이다. 0이 아니면 미완 teardown 이고, 그 상태에서 재스냅샷하면
-- 오염된 값이 진실이 된다.
select count(*) from harness_pattern_baseline b join error_patterns p on p.id = b.id
 where p.frequency <> b.frequency or p.last_seen_at is distinct from b.last_seen_at;
```

- 표가 **없으면** → 아래로 진행한다(첫 회차).
- 표가 있고 **drift 0** → 아래로 진행한다(재스냅샷해도 같은 값이다).
- 표가 있고 **drift > 0** → ⛔ **`ERROR`로 멈춘다.** 먼저 §8-②의 복원을 돌려 drift를 0으로 만든
  뒤에 회차를 연다. **재스냅샷으로 덮지 않는다.**

```sql
drop table if exists harness_pattern_baseline;
create table harness_pattern_baseline as
  select id, pattern_key, frequency, last_seen_at from error_patterns
   where user_id = '00000000-0000-0000-0000-000000000001';
```

**그리고 파일로도 뜬다** — DB 표 하나에 진실을 걸지 않는다. 마지막으로 검증된 사본:
**`tests/harness/runs/2026-09-06-pattern-baseline.tsv`**(추적됨, drift 0에서 떴다).
값이 정당하게 바뀌면(앱이 실제 학습으로 갱신) 새 날짜로 새 파일을 뜨고 이 줄을 갱신한다.

**①-a 세션을 시간창 스윕으로 등록한다** (자동 등록 훅이 없다 — §3):

```sql
insert into harness_sessions (run_id, session_id, scenario)
select '<browser_run_id>', s.id, '<C1|C2|…>'
  from learning_sessions s
 where s.user_id = '00000000-0000-0000-0000-000000000001'
   and s.started_at >= '<WINDOW_START>'
on conflict do nothing;
```

**① 세션 삭제** — cascade가 `utterances` → `{error_occurrences, analysis_jobs}`까지 지운다:

```sql
delete from learning_sessions
 where id in (select session_id from harness_sessions where run_id = '<browser_run_id>')
   and id not in (<§9의 보존 id 목록>);
```

**② `frequency`·`last_seen_at`을 baseline에서 **복원**한다 — 재계산하지 않는다.**

⛔ **이전 판의 재계산 SQL은 캡틴 데이터를 파괴했다 (2026-09-06 실측, T2 스파이크).**
`pronunciation_an_as_a`가 `frequency 2 / last_seen_at 2026-09-03 13:51:26.680389+00` →
**`0 / NULL`**로 덮였다. ④의 drift 대조가 잡아냈고 ⓿의 baseline이 있어 복원했다.
**baseline 없이 돌았다면 조용히 사라졌다.**

**근본 원인 — 팀리드가 직접 확인했다(추측 아님): `frequency`의 writer가 둘인데 이전 판이 하나만
베꼈다.**

| writer | 세는 것 | 대상 |
|---|---|---|
| `services/analysis.py:_RECOUNT_PATTERN_SQL` | `error_occurrences` 행 수 | 문법 패턴 |
| `services/pronunciation.py:_RECOUNT_PATTERN_FROM_ATTEMPTS_SQL` | **`pronunciation_attempts` 행 수** · `max(resolved_at)` | 카테고리 `pronunciation_intonation` |

`pronunciation.py`가 그 이유를 명시한다 — *"발음 시도는 `error_occurrences`를 만들지 않아 문법 경로의
occurrence 재계산을 쓸 수 없다."* 실측 대조(직접 쿼리): `pronunciation_an_as_a`는 `frequency` 컬럼 **2**
인데 `error_occurrences` 행 **0**이고, 나머지 6개 패턴은 컬럼과 행 수가 **정확히 일치**한다.
→ 이전 판의 식은 **모든 발음 패턴을 구조적으로 0으로 덮는다.** 하네스 데이터와 무관한 결함이다.

⚠️ **범위도 틀렸다 — 두 번째 결함이다.** 그 UPDATE의 서브쿼리는 `where ep.user_id = <시드 사용자>`로만
좁혀서 **회차가 건드리지도 않은 패턴 7건 전부를 다시 썼다**(실측 `UPDATE 7`). 즉 하네스가 만든 변화를
되돌리는 것이 아니라 **그 사용자의 모든 패턴을 자기 식으로 다시 계산**했다. 아래 복원식은 두 결함을
함께 닫는다: **계산하지 않고**(writer 문제), **값이 실제로 다른 행만 만진다**(범위 문제).

```sql
-- 복원. 하네스는 회차 창 안에서만 행을 더하고 ①에서 그 세션을 지웠으므로, 남아야 하는 값은
-- **정확히 baseline** 이다. 멱등이고 수식이 없으므로 앱 로직이 바뀌어도 낡지 않는다.
update error_patterns p
   set frequency = b.frequency, last_seen_at = b.last_seen_at
  from harness_pattern_baseline b
 where p.id = b.id
   and (p.frequency <> b.frequency or p.last_seen_at is distinct from b.last_seen_at);
```

⚠️ **baseline 표가 없으면 여기서 멈추고 `ERROR`로 보고한다. 재계산으로 대체하지 않는다** — 그것이
이 결함의 원인이었다. **하네스가 앱의 계산식을 복제하면 그 복제가 낡고, 낡은 것을 dev DB에 쓴다.**
복원은 계산하지 않으므로 그 부류의 실패를 구조적으로 배제한다.

⚠️ **전제**: 회차 중에 **앱의 정상 세션이 함께 돌지 않았다.** 돌았다면 그 변경도 되돌려진다.
§8은 이미 배타적 사용을 전제하고, 이전 판의 재계산도 같은 전제였다(더 나쁜 방식으로).

**③ baseline에 없던 0-occurrence 패턴만 삭제**:

```sql
delete from error_patterns p
 where p.user_id = '00000000-0000-0000-0000-000000000001'
   and p.id not in (select id from harness_pattern_baseline)
   and not exists (select 1 from error_occurrences eo where eo.pattern_id = p.id)
   -- ⚠️ 발음 시도는 occurrence 를 만들지 않는다(②의 표) → "occurrence 0건 = 잔여물"이
   -- 발음 패턴에는 성립하지 않는다. 시도가 달린 패턴은 남긴다.
   and not exists (select 1 from pronunciation_attempts pa where pa.pattern_id = p.id);
```

⚠️ **baseline에 있는 패턴은 이 delete가 건드리지 않는다**(`not in baseline`) — 캡틴의
`pronunciation_an_as_a`는 baseline에 있어 안전했다. 위 추가 조건은 **회차가 새로 만든** 발음 패턴을
"occurrence 0건"만으로 잔여물로 오판해 지우는 것을 막는다.

**④ 대조 — 여기까지가 teardown이다.**

```sql
select count(*) from error_patterns where user_id = '00000000-0000-0000-0000-000000000001';   -- baseline 행 수와 같아야 한다
select count(*) from harness_pattern_baseline b join error_patterns p on p.id = b.id
 where p.frequency <> b.frequency or p.last_seen_at is distinct from b.last_seen_at;           -- 0이어야 한다
select count(*) from learning_sessions s join harness_sessions h on h.session_id = s.id
 where h.run_id = '<browser_run_id>';                                                          -- 보존 id 개수와 같아야 한다
```

**⑤ 프로세스·환경 복원**: 백엔드를 §2의 baseline 명령으로 되돌리고 `curl localhost:8002/health`로 확인한다. `.env`는 고치지 않았으므로 복원할 것이 없다.

⚠️ **예외 — 백엔드를 호출자가 세웠으면 ⑤를 건너뛰고 「무변경」을 증거로 보고한다** (T5a D-5).
지금 문장 그대로 따르면 **남의 세션이 세운 환경을 덮어쓴다.** 판별은 간단하다: 회차 브리프가 모드를
지정하며 "손대지 마라"고 했으면 그 프로세스는 호출자 소유다.
그때 보고할 증거 3개(T5a가 실제로 남긴 형태):
`lsof -nP -iTCP:8002 -sTCP:LISTEN -t`가 **회차 시작과 같은 pid** · `ps -p <pid> -Eww`의
`VOICE_ADAPTER`·`WORKER_ENABLED`가 **회차 시작과 같음** · `/health`가 `{"status":"ok"}`.
**`app/backend/.env`를 열지도 않는다.**

**보존 대상 — ①에서 제외하고 보고에 적는다**: (a) **§9의 C3용 `session_id` 5개** — 지우면 다음 회차가 실물 Claude 1회를 다시 쓴다. (b) **실패한 시나리오의 세션** — 재현 근거를 지우면 재현할 수 없어지는 것이 더 비싸다.

## §9. 실물 Claude 호출 상한 — **1회** · 보존 session_id

상한 1회는 발명값이 아니다 — 이 리포는 실물 검증을 1회 단위로 승인해 왔다(`S2-L2` 실물 계획 생성 1회 · 슬라이스 1 `L1`·`L2` · `G-6`의 `W-live` 1회·`E2E-S` 1회 · `G-4` 실물 마이크 1회). **실물 호출이 필요한 태스크는 C3·C4(계획서 T4) 하나뿐이다** — C1·C2·C5는 `VOICE_ADAPTER=stub`이고 분석 워커를 쓰지 않으므로 **0회**다. **재실행 비용은 0으로 만든다**: 최초 1회만 세션을 만들어 분석을 돌리고 그 `session_id`를 아래에 적어, 이후 회차는 `/results/<id>`를 **재방문**한다(세션을 새로 만들지 않으므로 화면 검증이 백엔드 재기동과 분리된다).

| 상태 | `session_id` |
|---|---|
| `analyzing` (C3a) · `final` (C3b) · `partial_failure` (C3c) · `connection_failed` (C3d) · `no_utterances` (C3e) | **5개 전부 T4에서 실측해 채운다** |

⚠️ 이 5개는 **teardown ①에서 제외한다**(§8 보존 대상 a).

## §10. 판정 어휘와 보고

산출물은 `PASS` / `FAIL` / `BLOCKED` / `ERROR` 넷 중 하나 + **단정별 근거**다. 새 어휘를 만들지 않는다.

⛔ **자동 저장 파일을 창 안 관측의 증거로 쓸 수 없다 (2026-09-06 T5a D-1·D-6 — 구조적 결함이다).**

`use_browser`는 `.png`·`.html`·`.md`를 **액션이 끝난 뒤에** 저장한다. 그런데 §6의 주입 창(10초)이
라운드트립(~30초)보다 짧아 **클릭·주입·판독을 한 `eval`에 넣어야 하고**, 그러면 `eval`이 반환하는
순간의 화면은 **이미 창 밖**이다. T5a 실측: 그 회차의 `054-eval.html`에 `aria-live` **0건** ·
주입한 전사문 문구 **0건** · 배지 문구 **0건**이고 `voice_adapter_connect_timeout`만 1건이었다 —
**주입이 실패한 것이 아니라 캡처 시점이 창 밖이었다.**
그리고 **`-console.txt`는 빈 스텁이다** — 팀리드가 직접 확인: **58바이트**, 내용은
`# Console Log` + `# TODO: Console logging not yet implemented` 두 줄뿐이다(모든 액션에서 동일).
→ **§10이 약속했던 증거 4종 중 세 개는 창 밖 상태만 담고 하나는 비어 있다.**

**그래서 증거 규약을 바꾼다 — 창 안 관측은 `eval`의 반환값이 증거다:**

1. **`eval` 반환값에 DOM 자체를 실어 보낸다** — 개수·`textContent`만 반환하면 제3자가 재확인할 수
   없다. 판정 대상 요소의 **`outerHTML`**(배지·단정 요소)과 컨테이너의 **`innerHTML`**을 함께 담는다.
   ⚠️ T5a는 이것을 하지 않았다(개수와 `textContent`만 반환) → 그 회차의 AC ①②③은
   **자동 아티팩트로 재확인할 수 없고** 재현 경로가 "같은 payload를 다시 돌린다" 하나뿐이다.
2. **회차 기록에 그 반환 JSON을 옮긴다.** 회차 기록이 증거의 소유자다.
3. **계측 판을 sha256으로 고정한다.** T5a가 임시 CORS 서버로 파일을 그대로 받아 `eval`하고 페이지
   안에서 sha256을 계산해 대조했다 — **전사 드리프트가 구조적으로 0이 된다.** 손으로 옮겨 적지 마라.
   ⚠️ **해시는 회차 기록에만 적는다. 이 문서에 박지 마라** — 주석 한 줄만 고쳐도 낡는다(실측: 같은 날
   docstring 정정으로 `66384c9106…`→`e1342aca…`로 바뀌었고 실행 코드 변경은 0줄이었다).
4. `.png`·`.html`은 **창 밖 상태(실패 화면·idle 화면)의 증거로는 여전히 유효하다** — 버리지 않는다.

- **음성 대조에서 FAIL이 나지 않으면 그 단정은 무효다.** PASS라고 보고하지 않는다.
- 계측 `eval` 반환값이 `'instrumented'`가 아니면 **ERROR로 끝낸다**(§4). 주입 창 이탈도 **ERROR**다(§6).
- `audio` 송신 계수가 `0`일 때의 판별 — ⛔ **이전 규칙("`end_session`도 0이면 후킹 고장이므로 ERROR")은 오진을 냈다**(T5a D-2·T2 실측). 그 회차에서 **후킹은 정상이었고**(HMR 소켓 프레임을 실제로 잡았다) 원인은 **세션 길이**였다: 스텁 세션이 23ms에 자기종료해 캡처 프레임 1건(512샘플@16kHz = **32ms**)이 만들어지기 전에 끝나고, `학습 종료` 버튼에 도달하지 못해 `end_session`도 0이 된다. **그 규칙대로면 엉뚱한 곳을 고친다.** 세 갈래로 가른다:
  1. **`sent.foreign > 0`이거나 `meta.socketUrls`가 비어 있지 않다** → 후킹은 **살아 있다.** 원인을 세션 쪽에서 찾는다(아래 2·3).
  2. **`recv.session_started === 1`인데 `sent.audio === 0`** → **세션이 너무 짧거나 워클렛 준비가 늦었다.** `started.calls`와 `recv.audio`를 함께 읽어 확인하고 **BLOCKED**로 보고한다(화면 결함이 아니다).
  3. **`meta.socketUrls`가 비어 있다**(어떤 소켓도 관측되지 않았다) → 그때만 **후킹 고장 = ERROR**다.
  ⚠️ headless AudioContext의 suspend는 **원인 후보에서 내려갔다** — T5a 프로브에서 제스처 안에서 만든 컨텍스트는 즉시 `running`이었다(§11-3).
- **BLOCKED가 되는 표본 조건 2개**(FAIL과 구별한다 — 화면 결함이 아니라 표본 선택 실패다): `corrections[].reason`이 빈 문자열(A4-2) · `corrections.length === 0`인 세션을 primary로 잡았을 때(A4-1).
- **판별력 미확인은 `PASS`가 아니다.** 그 회차에서 대조를 평가할 수 없었으면(A1-7의 무음 대조 · A4-2의 교정 1건) 그 사실을 회차 기록에 적고 **`PASS`로 올리지 않는다**(⛔ 상자).
- **수치는 그 회차에 직접 돌린 출력만 적는다.** 계산값·낡은 값 금지. **앱 소스를 고치지 않는다** — 실패는 고치는 것이 아니라 보고하는 것이다.
- **보고를 그대로 믿지 않는다** — 호출자가 단정 하나는 직접 재현한다. 행 수는 직접 세고 화면은 자동 저장된 `.html`·`.png`를 직접 읽는다. 불일치하면 **직접 검증이 이기고 보고를 폐기한다.**
- 브라우저 레그 결과를 **게이트 수치와 섞어 보고하지 않는다.**
- ⛔ **DB 수치는 baseline / 회차 후 / teardown 후 **3열**로 남긴다.** 하나라도 빠지면 **사후 대조가
  원리적으로 불가능하다** — teardown이 걷어간 값은 나중에 조회해도 없다. 실측 사고(2026-09-06):
  팀리드가 T2 결과를 사후 조회로 대조해 "에이전트 수치가 어긋난다"고 **오판했다.** 에이전트의 3열
  기록이 옳았고 그 기록이 없었으면 판정이 뒤집힌 채로 남았다. 대상 표 6개:
  `learning_sessions` · `analysis_jobs` · `utterances` · `error_patterns` ·
  **`session_plans` · `learner_notes`**(뒤 둘은 보존 대상이라 **세 시점 모두 1행**임을 명시한다).

## §11. 아직 답을 발명하지 않은 것

| # | 무엇 | 어디서 닫는가 |
|---|---|---|
| 1 | ~~타임아웃·재시도·폴링 대기 값 전부~~ → **✅ 대부분 닫혔다. 아래 실측표를 쓴다** | **T5a 실측**(2회차 · 1회차 교차 확인). 남은 것은 T4의 결과 화면 폴링 대기뿐이다 |
| 2 | ~~`start`를 어느 프로토타입에서 후킹하는가~~ → **✅ 닫혔다.** `start` 소유자는 **`AudioBufferSourceNode`** · `createBufferSource` 소유자는 **`BaseAudioContext`**(`AudioContext.prototype`에서 `getOwnPropertyDescriptor`는 `undefined`). ⚠️ **`start`는 `AudioBufferSourceNode`와 `AudioScheduledSourceNode` 양쪽에 own property**이고 가까운 쪽이 인스턴스 조회에서 이긴다. **`stop`은 `AudioBufferSourceNode`에 없고 `AudioScheduledSourceNode`에만 있다** — §4-3의 "둘이 다른 자리일 수 있다"가 `stop`에서 실현된다 | **T2 + T5a 실측 · 팀리드가 브라우저로 직접 재현**(Chrome 152.0.0.0) |
| 3 | headless AudioContext가 suspend되는가 → **부분적으로 닫혔다.** 제스처 **전** 생성은 `suspended`, 제스처(클릭) **안**에서 생성하면 `running`이다(T5a 프로브: 생성 즉시 `running` 1 ms · `addModule` 2 ms · `resume` 0 ms). ⚠️ **`audio` 계수 0의 원인은 suspend가 아니었다** — T2에서 세션이 23ms에 자기종료해 프레임이 만들어지기 전에 끝났다 | **닫힘.** 남은 것은 `audio` 계수를 실제로 재는 구성이고 `stub`(비-unresponsive)에서만 가능하다 |
| 4 | **A1-7의 음성 대조가 실제로 FAIL을 내는가** — 재설계로 후보가 바뀌었다: ① `end_session` 1건 동반 계수(후킹 고장 구별 — **이것은 확실히 성립한다**) ② **무음 합성 스트림에서 `audio` 계수가 0이 되는가**(이것이 미결이다) | **T2 스파이크.** ②가 0을 못 내면 A1-7을 **판별력 미확인으로 남긴다**(채택하되 `PASS`로 올리지 않는다) |
| 5 | ~~CDP `onmessage` 주입이 실제로 되는가~~ → **✅ 된다. 가장 넓게 걸렸던 미결이 닫혔다.** `pronunciation`·`partial`·`final` 3종 전부 주입이 먹었고 **2회 독립 회차가 일치**했다. `inject()`가 `recv`를 오염시키지 않는 것도 **설계 주장에서 관측으로 승격**됐다(8프레임 주입 후 `recv` 불변 · `injected` 0→8) | **T5a ①②③ `PASS`.** C5 폐기·직렬 큐 대안 **둘 다 불필요** |
| 6 | ~~주입 창이 10초 안에 끝나는가~~ → **✅ 닫혔다. 다만 병목을 잘못 짚고 있었다**(T5a D-3): 페이지 쪽은 **256 ms**(창의 **2.6%**)로 여유가 압도적이고 실제 병목은 **에이전트 라운드트립(~30 s)**이다. 그래서 조건은 "10초 안에 끝나는가"가 아니라 **"전 과정을 한 `eval`에 넣었는가"**다(§6 ⛔) | **T5a ④ `PASS`** |
| 7 | 확정 줄 수·**내용**(A1-5) **스냅샷 시점의 방법** — 소프트 내비게이션은 `window.__omy`를 파괴하지 않으므로 계측이 `final`마다 DOM을 적립한다. ⚠️ **재설계로 적립 대상이 개수에서 `textContent` 배열로 늘었다.** rAF인지 MutationObserver인지는 미정 | **T2에서 실측해 확정한다** |
| 8 | C3용 보존 `session_id` 5개(§9) | **T4에서 채운다** |
| 9 | **A4-2의 기대값 교차 대조를 평가할 수 있는 세션이 있는가** — 교정이 **2건 이상**인 세션이 §9 보존 목록에 필요하다. 1건뿐인 세션만 있으면 그 대조는 영구히 평가 불가다 | **T4에서 보존 목록을 채울 때 `corrections.length`를 함께 적어 확인한다** |
| 10 | **A4-1의 primary 세션이 `corrections`를 비우지 않는가** — 9번과 같은 자리에서 확인한다(둘 다 표본 조건이고 화면 결함이 아니다) | **T4** |

### ✅ 1회차에서 닫힌 것 1건 — 답이 예상한 둘 중 어느 것도 아니었다

⛔ **아래는 계측을 걸지 않은 경로에만 적용된다 (T5a·T2 실측으로 범위가 좁혀졌다).**
**계측을 클릭 전에 걸면 `navigator.mediaDevices.getUserMedia`가 교체되어 권한 대화상자가 아예 뜨지
않는다** — T2·T5a 두 스파이크 모두 `dialog::accept` 없이 세션이 열렸다(합계 5회차).
→ **정상 절차(계측을 먼저 거는 경로)에서는 대화상자 처리 단계가 필요 없다.** 아래 서술은
**계측 없이 화면만 볼 때**(예: A1-7의 옛 대조 후보 ①, 지금은 폐기됨) 유효하다.
⚠️ **`dialog::accept`를 기다리며 멈추지 마라** — 오지 않는 것을 기다리면 창(10초)을 넘긴다.

**마이크 권한 거동**(계획서 I-4). 계획서는 두 갈래를 예상했다 — ⓐ `getUserMedia`가 실패해
`microphone_permission_denied`가 뜨거나 ⓑ headless가 **가짜 장치로 조용히 성공**한다.
**실제로는 셋째다: 권한 대화상자가 떠서 페이지 평가가 막힌다.**

- 대화상자가 뜬 동안 `eval`이 **`undefined`를 돌려주고** 세션 정보가 사라진다 → **DOM을 읽을 수 없다.**
  이것을 "계측 실패"로 오독하면 엉뚱한 곳을 고친다.
- **처리한 뒤에야** DOM을 읽을 수 있다: `dialog::dismiss`(거부) 또는 `dialog::accept`(허용).
- **거부하면 ⓐ가 성립한다** — 화면이 `연결에 실패했습니다 / 사유: microphone_permission_denied /
  다시 시도`로 바뀌는 것을 1회차에서 관측했다.
- ⚠️ **`getUserMedia` 실패 시 소켓이 열리기 전에 끝난다** — 1회차에서 `learning_sessions`가
  **7 → 7**로 변화가 없었다. 즉 **거부 경로는 DB에 세션을 만들지 않는다.**

→ **C1(세션 관통)을 돌릴 때는 `dialog::accept`가 필요하다.** 거부하면 세션이 열리지 않아 `recv.*`
단정을 전혀 잴 수 없다. **모든 브라우저 절차의 첫 단계에 "대화상자 처리"를 넣는다.**

⚠️ **`accept`는 실제 마이크를 켠다.** 그 경로를 처음 쓸 때 무엇이 관측되는지는 **T2 스파이크**가
확정한다(위 3·4번과 같은 회차에서 본다).

1~6은 계획서가 "실측 후 정한다"로 남긴 항목을 **그대로 넘긴 것**이다(§13-1·3c·3·3b·2 + N-3). 7·8은 이 문서가 새로 남겼고, **9·10은 2026-09-06 판별력 재설계가 새로 열었다** — 재설계가 표본에 조건을 걸었으므로(A4-1 `N >= 1` · A4-2 교정 2건 이상) **그 조건을 만족하는 세션이 실재하는지가 새 미결이 된다.** 대조를 강하게 만들면 표본 요구가 올라간다. **이 문서가 닫은 계획서 미결 2건**: §13-4(회차를 여는가 → **연다**, `.harness/browser_run_id.txt` · §3) · §13-9(`e8b7e17`의 추천 이유 한 줄 → **A1-0으로 넣는다.** 새 시나리오를 만들지 않는다 — 계약이 `page.tsx:271`·`:277`에서 읽히고 기대값이 API에서 유도되며 음성 대조가 상태 전이로 성립한다).

## §12. 자기검증

- **단정 18건** — C1 9(A1-0~A1-8) · C2 3(A2-1~A2-3) · C3 2(A3-1~A3-2) · C4 2(A4-1~A4-2) · C5 2(A5-1~A5-2). **2026-09-06 재설계는 단정을 늘리지 않고 7건의 내용을 바꿨다.**
- ⛔ **"음성 대조 빈칸 0건"을 품질 근거로 쓰지 않는다.** 이전 판이 그 지표로 18건 전건을 방어했고 **리뷰에서 7건이 뚫렸다**(⛔ 상자). 빈칸 수는 대조가 **있다**는 지표일 뿐이다. **지표는 각 대조가 무력화에서 FAIL을 내는지이고, 그것은 회차에서만 관측된다** — 그래서 이 절은 이제 그 수를 세지 않는다.
- **유도 방식 분류(재설계로 바뀌지 않았다)**: ⓐ 픽스처 연역 6건(A1-1~A1-5, A1-8) · ⓑ 런타임 유도 10건(A1-0, A1-6, A1-7, A2-1~A2-3, A3-2, A4-1, A4-2, A5-2) · **ⓒ 하드코딩 2건(A3-1, A5-1)**. 재설계가 바꾼 것은 **계수 지점과 대조**이고 기대값의 출처는 그대로다. ⓒ 2건은 이제 전역 검색이 아니라 **요소 지목 + 등호**로 재므로 항진명제·동적 문구 경로가 **둘 다 닫혔다** — 「다른 출현은 전부 주석이다」라는 grep 근거에 더는 의존하지 않는다.
- 이 문서는 **문서를 절 제목으로, 코드를 `파일:심볼`로** 가리킨다. 인용한 줄은 전부 작성 중 직접 읽어 확인했다.
