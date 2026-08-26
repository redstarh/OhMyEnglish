# Handoff — 자동 테스트 하네스 (4차수 진입용)

> 테스트 하네스 작업의 연속성만 담당한다. 제품·구현 정본은 `handoff/HANDOFF.md`,
> 수정 세션의 판단 근거는 `handoff/HANDOFF-fix-session.md`이며 **둘 다 다른 세션 소유라
> 건드리지 않는다.**
> 최종 갱신 2026-08-26 09:40 · 대상 커밋 **`204d8a1` 이후** · **다음 할 일: 4차수 시작**
> **4차수 범위가 캡틴 지시로 확장됐다 — P계층(발음 교정)·M계층(학습 반영) 신설.** §3 참조.

---

## 1. 지금 상태 — 3차수 완료, 앱 결함 0건

| 항목 | 상태 |
|---|---|
| 루프 | **4/10 차수 사용.** 되돌려 보낼 결함이 없어 일시 종료 |
| **4차수 P·M (2026-08-26 완료)** | ✅ P1~P7 · M0 · M1. **신규 앱 결함 0건** — 최우선 위험 P5가 clean. 기록 `runs/2026-08-26-run-4.md` |
| **5차수에 남은 것** | N6~N13 · B1~B4 전량 · 라이트/다크 5상태 · 회귀(A1·A2·E4·E5·E6·D1·D2) · P8 · `tests/harness/**` ruff 6건 |
| **F-1** 다크모드 색상 위계 역전 (HIGH) | ✅ 수정·검증 완료 (2차수) |
| **F-2** `target_form` 불일치 (MEDIUM) | ✅ 수정·검증 완료 (3차수, 패턴 일반형) |
| **Nova 2 Sonic 실연동** | ✅ **앱 경로로 관통 (AC1 충족)** — 3차수 N5 |
| 미해결 앱 결함 | **없음.** 관찰 1건만 남음(O-1, LOW — 아래 §4) |
| 게이트 | `241 passed`(skip/xfail 0) · ruff · format · ty 전부 clean |
| DB | **baseline 정확 복원** — 세션 2 · 패턴 1 · `frequency` 2 · `harness_runs` 4행 |
| 스택 | 백엔드 `:8002` baseline(`--log-level warning`, **스텁 모드**) · 프론트 `:3000` · podman `ohmy-pg` |
| 미커밋 | `.claude/settings.json`(untracked) — 수정 세션이 배경작업 워크트리 격리를 끄려고 추가. **지우지 마라**, "워크트리 금지" 제약이 이것에 의존한다 |

## 2. 차수별 기록 (전부 git 추적)

| 문서 | 내용 |
|---|---|
| `tests/harness/runs/ROUNDS.md` | **원장** — 차수별 상태·10차수 상한·회귀 중점 규칙 |
| `runs/2026-08-26-run-1.md` | 1차수 — 판정 17건, 발견 7건(F-1·F-2·F-3 게이트해소 등) |
| `runs/2026-08-26-run-2.md` | 2차수 — F-1 검증, E4/E5/E6 신규, 신규결함 0 |
| `runs/2026-08-26-run-3.md` | 3차수 — F-2 검증, **N5 실음성 왕복**, 신규결함 0 |
| `docs/ops/2026-08-26-test-harness.html` | 절차 정본(12절) |
| `docs/ops/2026-08-26-test-harness-report.html` | 1차수 리포트(스크린샷 임베드) |
| `tests/harness/scenarios-N-real-voice.md` | Nova 계약·실측·남은 시나리오 **정본** |
| `tests/harness/scenarios-E-agent-learning.md` | E계층(구현됨)·L계층(미구현) 시나리오 |

---

## 3. 남은 일 — **수정 왕복이 아니라 테스트 커버리지 확장**

> **2026-08-26 갱신**: 아래 **묶음 P·M은 4차수에서 실행 완료**(`runs/2026-08-26-run-4.md`).
> 캡틴이 4차수 범위를 P·M으로 한정했으므로 **묶음 ①②③④는 5차수 몫**이다. 절차·명령은 그대로 쓴다.

되돌려 보낼 결함이 없으므로 `claude_air_3-14`에 전달하지 않는다. 내가 돌린다.
**단 P5·P6에서 결함이 나오면 그때 왕복을 연다** (분기 조건은 `runs/ROUNDS.md` §4차수 범위 확장).

### 묶음 P — 발음 교정 루틴 (캡틴 지시로 신설, **최우선**)

정본: `tests/harness/scenarios-P-pronunciation.md`. 픽스처 6개는 **생성 완료**
(`p1a/p1m/p1k` · `p2a/p2m/p2k` — 같은 문장을 발음만 바꾼 쌍, 16kHz/16bit/mono).

개시 전 Nova 직접 왕복으로 이미 확정한 것: **약한 발음 오류는 ASR이 원문으로 복원해 전사문에
흔적이 0**이고(`p1m` = `p1a` 전사문 동일), **강한 억양은 한글로 전사된다**. agent는 두 경우
모두 발음을 지적하지 않았다.

| # | 이번에 확인할 것 |
|---|---|
| **P5** ⚠️ | **최우선.** 한글 전사문(`p1k`)으로 만든 발화를 분석 워커에 넣는다 — findings 0건 `done`인가, 금지 카테고리 `pronunciation_intonation`을 쓰려다 검증 실패 → **5회 재시도 후 `failed`**인가(W7), 엉뚱한 문법 오류를 발명하는가. 뒤 둘이면 **결함** |
| P6 | 문법적으로 옳은 문장(`p1m`/`p2m`)이 `error_patterns`에 패턴을 만드는가 — 만들면 **오탐** |
| P1·P2 | 정확/오류 쌍의 전사문을 **문자 단위 비교**해 앱 경로에서도 오류가 소실되는지 확정 |
| P3 | agent가 발음을 지목하거나 다시 말하게 요구하는가 (판정 기준은 P계층 문서 §6-1) |
| P4 | 한글 전사문이 화면 렌더를 깨지 않는가 |
| P7·P8 | 정확/오류 세션 결과 화면 대조(스크린샷 2장) · `pronunciation_intonation` 직접 주입 내성 |

### 묶음 M — 오류가 이후 학습에 반영되는가 (캡틴 지시로 신설)

정본: `tests/harness/scenarios-E-agent-learning.md` M계층. **지금 실행 가능한 것은 M0·M1**이고
목적은 "없음을 증거로 고정"이다 — 통합테스트에서 뒤집히면 활용 링크가 붙었다는 뜻이다.

| # | 이번에 확인할 것 |
|---|---|
| **M0** | `inject_errors.py --scenario E1`로 패턴 7개를 쌓고 **새 세션**을 연다 → ① `scenario_id`가 이전 세션과 동일(고정 첫 행, `sessions.py:29` `limit 1`) ② agent 첫 발화가 축적 패턴을 언급하지 않음 ③ `review_tasks` 0행 ④ `next_review_at` 전부 null |
| **M1** | `u1` → 새 세션 → `u2`(같은 `article` 패턴) → `frequency` 2로 오르지만 두 세션의 agent 발화가 구별되지 않음. **두 세션 발화를 나란히 기록**해 대조 증거로 남긴다 |

### 묶음 ① Nova 시나리오 중 **아직 실행하지 않은 것** (정본: `scenarios-N-real-voice.md` §4)

> ⚠️ **"Nova가 안 된다"는 뜻이 아니다.** Nova 연동은 3차수 N5에서 앱 경로로 관통이
> 확인됐다 — 브라우저 마이크 → AudioWorklet raw PCM → WS → Nova ASR → 화면 + DB 저장 +
> job 등록까지 실물로 한 바퀴 돌았고 AC1이 충족됐다.
> 아래는 **수정 세션이 구현했다고 보고했지만 테스트 세션이 아직 시험해 보지 않은** 항목이다.
> 즉 "코드는 있고 검증이 없는 상태"다.

| # | 코드 상태 | 미확인 사항(=이번에 확인할 것) | 준비물 |
|---|---|---|---|
| **N6** | `InterruptionEvent` + 프론트 오디오 큐 비움이 구현돼 있다 | agent 발화 중 실제로 끼어들면 **1초 안에 출력이 멈추는가**, `interrupted` 프레임이 오는가, 큐가 비워지는가 | agent가 말하는 동안 두 번째 WAV를 주입해야 한다 — `recv.audio`가 늘기 시작한 시점에 `u2.wav`를 `start()` |
| **N7** | 구현과 무관(같은 경로의 반복) | **1턴만 확인했다.** 여러 턴에서 `sequence_no`가 단조 증가하고 사용자 발화마다 job 1건이 붙는가 | `u1`→`u2`→`u3` 순차 주입 |
| **N8** | 분석 파이프라인은 이미 검증됨 | 병합은 지금까지 **주입 경로**(`inject_errors.py`)로만 확인했다. **실음성으로 만든 발화 2개**가 같은 `article` 패턴으로 병합되고 `frequency` +2가 되는가 | `u1`+`u2` |
| **N11** | `microphone_permission_denied` 화면이 존재한다 | `getUserMedia`가 실제로 reject됐을 때 그 화면이 뜨는가 | shim에서 `throw`만 하면 된다 |
| **N12** | 방어 코드가 있다 | 잘못된 샘플레이트·깨진 프레임에 세션이 **조용히 죽지 않는가** | A2의 실물판 |
| **N13** | `NOVA_ENDPOINTING_SENSITIVITY` 환경변수가 있다 | HIGH/LOW로 바꿨을 때 **발화 종료 감지 시점이 실제로 달라지는가** | N-1 실측: MEDIUM에서 약 480ms |

**4차수에서 일부러 빼는 2건** (`scenarios-N-real-voice.md` §4에는 있다):

| # | 왜 뺐나 |
|---|---|
| **N9** 세션 롤오버 | Nova 스트림 상한이 **8분**이다(SDK docstring). 경계를 시험하려면 8분 넘게 실음성 세션을 유지해야 해 시간·비용이 크다 — 별도 실행으로 돌린다 |
| **N10** 무응답형 자격증명 실패 | 일부러 잘못된 키를 넣어야 하는데 그러면 **`.env` 편집 금지** 제약에 걸린다. 환경변수로 덮어쓰는 우회는 가능하니 그 방식으로 할지 캡틴에게 확인한 뒤 별도로 돈다 |

### 묶음 ② 3차수에서 대체 커버한 것 전량 재확인

3차수는 B1~B4를 "변경이 그 경로를 안 건드린다"는 판단으로 E6·A2·B5로 대체했다.
**그 판단을 4차수에서 검증한다** — B1(`no_utterances`) · B2(`analyzing` + 수렴) ·
B3(`final`) · B4(`partial_failure`) 전량, 그리고 라이트/다크 5상태 화면.

### 묶음 ③ 회귀

A1 · A2 · E4 · E5 · E6 · D1 · D2 + 프론트 `npx tsc --noEmit`

### 묶음 ④ O-1을 다른 결함과 묶어 전달 (결함이 더 나오면)

4차수에서 새 결함이 나오면 O-1(선행 개행)을 함께 넣어 4차수 수정 지시를 만든다.
**O-1 단독으로는 왕복을 열지 않는다** — LOW이고 사용자 영향이 없다.

---

## 4. 남은 관찰과 캡틴 결정

| # | 내용 | 상태 |
|---|---|---|
| **O-1** (LOW) | agent 전사문에 **선행 개행**이 들어간다. Nova가 `'\nWhat time do you…'`를 보내고 `save_final_transcript`가 그대로 저장한다. agent 발화라 job이 없어 분석에는 안 들어가고 화면 렌더도 정상 — 지금은 무해 | 4차수에 묶어 전달 |
| **L계층(복습 기능)** | `next_review_at`·`mastery_score`·`review_tasks`·`summarize_session` 전부 **앱 코드에 참조 0건**. 캡틴 결정 5건이 선행 필요 (`scenarios-E-agent-learning.md` §L계층) | 캡틴 결정 대기 |
| **음성 픽스처 배치** | 3차수에는 `app/frontend/public/harness/u1.wav`로 **임시 배치 후 제거**했다. 4차수는 **WAV 9개**가 필요하다(`u1~u3` + 발음 쌍 `p1a/p1m/p1k/p2a/p2m/p2k`) — 매번 배치/제거하거나 캡틴이 상주 배치를 승인할 수 있다 | 캡틴 판단(사전승인 범위) |
| **발음 픽스처의 한계** | `p*m`은 원어민이 다른 단어를 정확히 발음한 것, `p*k`는 한국어 TTS가 영문자를 읽은 것이다. 캡틴 육성은 그 사이에 있어 **실물 마이크 1회 보정**이 필요하다 — 제품 게이트 1(E2E-S 마이크)과 한 번에 처리 가능 | 캡틴 판단 |
| **`tests/harness/**` ruff 6건** | `inject_errors.py`(I001·E501) · `measure_contrast.py`(E501) · `spike_nova_protocol.py`(I001) · `ws_session.py`(E501·UP041). 게이트 범위 밖이지만 **내 소유 파일이라 4차수에 정리한다** | 내 작업 |
| **`.claude/settings.json` 커밋 여부** | 배경작업 워크트리 격리 해제. 하네스가 의존한다 | 캡틴 판단 |

---

## 5. 4차수 시작 절차 (그대로 실행)

```bash
cd /Users/redstar/MyProject/OhMyEnglish

# ① 스택 신원 — :8000 은 StockAgent다. version 키가 있으면 잘못된 포트다.
curl -s localhost:8002/health          # {"status":"ok"} 여야 한다
curl -so /dev/null -w '%{http_code}\n' localhost:3000

# ② 낡은 프로세스 함정 (1차수에 실제로 물렸다 — 23시간 낡은 코드)
#   ⚠️ mtime 검사는 **백엔드에만** 의미가 있다(--reload 없음).
#      프론트는 Next dev가 HMR로 재컴파일하므로 소스가 프로세스보다 새로워도 최신일 수 있다
#      — 2026-08-26 실측: 프론트 프로세스는 23시간 낡았지만 번들은 최신이었다(오탐).
ps -o lstart= -p $(lsof -nP -iTCP:8002 -sTCP:LISTEN -t)
find app/backend/app -newermt '<위 시각>' -name '*.py'
#   결과가 있으면 백엔드를 재기동하고 시작한다
grep -rl 'localhost:8002' app/frontend/.next/dev >/dev/null && echo '프론트 번들 API base OK'
#   비면 .env.local 반영이 안 된 것 → 프론트 재기동(NEXT_PUBLIC_API_BASE=http://localhost:8002)

# ③ 회차 열기 — run_id.txt 오염 주의 (2번 재발했다. grep 고정 필수)
podman exec -i ohmy-pg psql -U ohmy -d ohmyenglish -tAc \
  "insert into harness_runs (git_commit, note) values ('$(git rev-parse --short HEAD)','round#4 coverage') returning id" \
  | grep -oE '[0-9a-f-]{36}' | head -1 > .harness/run_id.txt

# ④ 패턴 baseline (teardown 복원 기준) — 3차수 것이 남아 있으니 새로 뜬다
podman exec -i ohmy-pg psql -U ohmy -d ohmyenglish -c \
  "drop table if exists harness_pattern_baseline;
   create table harness_pattern_baseline as select id, pattern_key, frequency, last_seen_at
     from error_patterns where user_id='00000000-0000-0000-0000-000000000001';"

# ⑤ 이 세션의 주소를 기록 (수정 세션이 회신할 곳 — 세션마다 바뀐다!)
tmux display-message -p '#{session_name}:#{window_index}.#{pane_index}' > .harness/caller_pane.txt
```

### Nova 모드 실행 (N6~N13)

```bash
# 백엔드를 nova 모드로. 픽스처를 프론트에서 fetch 가능하게 임시 배치.
mkdir -p app/frontend/public/harness && cp tests/harness/fixtures/voice/*.wav app/frontend/public/harness/
lsof -nP -iTCP:8002 -sTCP:LISTEN -t | xargs kill; sleep 3
cd app/backend && VOICE_ADAPTER=nova nohup .venv/bin/uvicorn app.api.main:app --port 8002 \
  --log-level info > ../../.harness/backend-nova.log 2>&1 &
#   N13은 NOVA_ENDPOINTING_SENSITIVITY=HIGH|MEDIUM|LOW 를 함께 준다

# 끝나면 반드시 baseline 복구 + 픽스처 제거
rm -rf app/frontend/public/harness
cd app/backend && nohup .venv/bin/uvicorn app.api.main:app --port 8002 --log-level warning >/dev/null 2>&1 &
```

### N5에서 검증된 브라우저 주입 스크립트 (그대로 재사용)

`use_browser` `navigate http://localhost:3000` → 아래 `eval` → **`click` 액션으로 클릭**
(→ `eval` 안의 `.click()`은 user activation이 없어 `ctx.resume()`이 멈춘다, 1차수 H-1)

```js
(async () => {
  const ctx = new AudioContext({ sampleRate: 16000 });
  const buf = await ctx.decodeAudioData(await (await fetch('/harness/u1.wav')).arrayBuffer());
  const dest = ctx.createMediaStreamDestination();
  window.__omy = { sent: 0, sentBytes: 0, recv: {}, texts: [] };
  navigator.mediaDevices.getUserMedia = async () => {
    await ctx.resume();
    const src = ctx.createBufferSource(); src.buffer = buf; src.connect(dest); src.start();
    return dest.stream;                    // WAV 뒤로는 무음이 흘러 endpointing이 발동한다
  };
  const send = WebSocket.prototype.send;
  WebSocket.prototype.send = function (d) {
    try { const m = JSON.parse(d); if (m.type === 'audio') { window.__omy.sent++; window.__omy.sentBytes += atob(m.data||'').length; } } catch (e) {}
    return send.call(this, d);
  };
  const om = Object.getOwnPropertyDescriptor(WebSocket.prototype, 'onmessage');
  Object.defineProperty(WebSocket.prototype, 'onmessage', { configurable: true,
    get() { return om.get.call(this); },
    set(fn) { om.set.call(this, (ev) => {
      try { const m = JSON.parse(ev.data);
        window.__omy.recv[m.type] = (window.__omy.recv[m.type]||0)+1;
        if (m.type==='final'||m.type==='partial') window.__omy.texts.push(`${m.type}/${m.speaker}: ${m.text}`);
      } catch (e) {}
      return fn(ev); }); } });
  return 'ready';
})()
```

**N6(barge-in)은 이 스크립트를 확장해야 한다** — 첫 WAV가 끝나고 agent가 말하기 시작한 뒤
(`recv.audio`가 늘기 시작한 시점) 두 번째 `BufferSource`를 `start()`해서 끼어들게 만든다.

### 실행 스크립트

```bash
cd app/backend
.venv/bin/python ../../tests/harness/ws_session.py --scenario <이름> [--junk --send-audio 3] [--timeout 20]
.venv/bin/python ../../tests/harness/inject_errors.py --scenario E1|E3|E4|E5|E6 [--wait 120]
.venv/bin/python ../../tests/harness/measure_contrast.py --shot-prefix <경로>   # 다크/라이트 대비
.venv/bin/python ../../tests/harness/spike_nova_protocol.py [--wav u3.wav]      # Nova 직접 왕복
```

### 정리 (반드시) — 3단계 + 대조

```bash
# teardown 직전 스윕 (브라우저 레그는 자동 등록 훅이 없다 — 1차수 F-7)
# 그다음 README §정리의 3단계: 세션 삭제(cascade) → frequency/last_seen_at 재계산 →
#   baseline에 없던 0-occurrence 패턴 삭제
# 마지막에 세션 2 · 패턴 1 · frequency 2 로 돌아오는지 반드시 대조한다
```

---

## 6. 반복하지 말 것 (실측된 함정)

| # | 함정 | 대응 |
|---|---|---|
| H-1 | `eval` 안의 `element.click()`은 **user activation을 만들지 않아** `AudioContext.resume()`이 멈춘다 → 화면이 `마이크 권한 요청 중`에서 정지 | 클릭은 플러그인 `click` 액션(CDP 실제 입력)으로만 |
| H-2 | `psql -tAc "insert … returning id"`가 `INSERT 0 1`을 함께 출력해 `run_id.txt`를 오염시킨다 (**2회 발생**) | `grep -oE '[0-9a-f-]{36}' \| head -1` 고정 |
| H-3 | 브라우저 레그 세션이 부기에서 누락 | teardown **직전** 시간창 스윕 |
| H-4 | 공유 dev DB에서 `frequency` 절대값 단정은 반드시 실패 | 델타로 단정 |
| H-5 | 스텁은 지연 0으로 재생 → 브라우저가 오디오 프레임을 못 보내고 전사문 DOM도 안 잡힌다 | 마이크 측정은 B5(무응답 10초) 창에서, 렌더 관측은 이벤트 도착 스로틀로 |
| H-6 | `prefers-color-scheme`은 페이지에서 못 바꾼다 | CDP `Emulation.setEmulatedMedia` (`measure_contrast.py`) |
| H-7 | Nova는 **초기화 이벤트 전에 HTTP 응답 헤더조차 안 보낸다** → `await_output()`을 먼저 부르면 타임아웃 | 송수신 동시 시작 |
| H-8 | Nova는 **무음 프레임이 없으면 전사문을 안 준다** | 마이크는 계속 흐르므로 앱 경로에선 자동. 스크립트로 넣을 때만 무음을 이어 보낸다 |
| H-9 | 백엔드는 `--reload`가 없다 | 소스가 바뀌면 반드시 재기동 |
| H-10 | Bash 툴은 호출마다 cwd가 리셋될 수 있다 | `cd <절대경로> &&` 또는 절대경로 |

## 7. 세션 간 왕복 규약

- **페인 주소는 세션마다 바뀐다.** 3차수까지는 테스트=`claude_air_5-49:0.0`,
  수정=`claude_air_3-14:0.0`이었다. 새 세션에서는 `tmux display-message`로 자기 주소를
  다시 얻고, 수정 세션 주소도 `tmux list-panes -a`로 다시 확인한다.
- 수정 세션(`claude_air_3-14`)은 **agents 관리 화면**이다. 입력창에 텍스트를 넣으면 새 작업이
  생성된다(`enter to create`). 진행 중 작업에 덧붙이려면 `space`로 답장창을 열고 **대상이
  맞는지 상태 문구로 확인한 뒤** 타이핑, 푸터가 `enter to send`로 바뀐 것을 보고 Enter.
- **전달은 파일 경로로 지목한다** — 3차수처럼 지시서를 `tests/harness/`에 쓰고 한 줄로 가리킨다.
- **10차수 상한.** 상한에 닿으면 오류가 남아도 캡틴에게 보고하고 멈춘다.
- 역할 분리: 테스트 세션은 앱 코드를 수정하지 않고, 수정 세션은 자기 수정을 합격 판정하지 않는다.
  단 `tests/harness/**`는 테스트 세션 소유이므로 그 안의 오류는 내가 고친다(3차수 `ty` 2건).
