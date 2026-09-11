# 회차 기록 — 테스트 진행 상태 탐침. **판정: 재기동으로 구성이 갈리고 실행 가능 집합이 뒤바뀜**

> **임무는 조사·판정이고 시나리오 실행이 아님.** 팀리드 지시로 ⑴ 테스트가 어디까지 진행됐는가
> ⑵ 추가 테스트를 지금 진행할 수 있는가 둘만 답함. 다회차 스윕은 돌리지 않았음.
>
> ⛔ **이 회차의 Nova 실물 호출은 0회임.** DB 쓰기 0건 · 백엔드 재기동 0회(이쪽이 하지 않음) ·
> 원장 변경 0건 · 앱 코드 변경 0건. 관측은 전부 읽기 왕복(HTTP GET · psql SELECT · ps · lsof)임.
>
> ⛔ **회차 중간에 `:8002` 가 재기동됐음.** 이 문서는 **두 구간**을 담고 경계가 §8 임.
> **2026-09-10 16:27:44 KST 이후의 `:8002` 관측만 새 코드(`adf462c` 이상) 기준임.**
> §2~§7 은 **이전 프로세스(pid 7990)** 에 대한 것이고 §8 이후가 **새 프로세스(pid 25563)** 임.

---

## 1. 환경 — 이 턴에 직접 재서 얻음

| 항목 | 값 | 어떻게 얻었나 |
|---|---|---|
| 조사 구간 | 2026-09-10 16:24~16:33 KST | `date` |
| HEAD | `b6b3b7d` · `origin` 과 동기 · 미커밋 0건(이 기록 제외) | `git rev-parse --short HEAD` · `git status --short --branch` |
| 회차 중 소스 변경 | **0건** (`app`·`tests`·`scripts`·`backlog` 에서 최근 3시간 내 변경 파일 0) | `find … -newermt '-180 minutes'` |
| DB `:5432` | postgresql@17 `started` · `ohmyenglish` 접속 OK | `brew services list` · `psql` |
| 프론트 `:3000` | pid **37650** `next-server (v16.3.2)` · 기동 **2026-09-06 10:21:13**(4일 6시간 전) · `/` **200** | `lsof` · `ps -o lstart` · `curl` |
| CDP `:9222` | **살아 있음** — `Chrome/152.0.7977.65` · Protocol 1.3 | `curl /json/version` |
| `:5173` | **이 리포가 아님** — `StockNews/frontend` 의 vite | `ps -p 36190` |
| 단위 테스트 게이트 | ⛔ **이 턴에 돌리지 않았음** — 다른 세션(`ohmyenglish-e4`)이 점유 중이라 지시로 금지됨 | — |

⚠️ **인용값과 직접 측정값을 가름.** 게이트 수치(`pytest` 900 passed 등)는
`handoff/HANDOFF-implementation.md` ⑥ 의 기록값이고 **내가 돌린 것이 아님.**

⛔ **원장의 AC 는 `backlog task view <ID> --plain` 을 직접 돌려 확인했음** — SessionStart 브리핑을
인용하지 않았음. 브리핑은 네 태스크의 미충족 AC 를 태스크 구분 없이 한 목록으로 내므로 귀속이 섞임.
확인 결과 `TASK-86` 은 AC 가 **3개**(#1 체크 · #2 실물 왕복 최소 2회 · #3 우회로 유지)이고,
「결정 49 를 유지할지 뒤집을지 받는다 · toolChoice 강제 금지」는 **`TASK-78` AC#4** 임.

---

# 구간 A — 재기동 전 프로세스 (pid 7990)

## 2. 판정 — 이전 프로세스는 낡은 코드였음 (응답으로 확정)

| 항목 | 값 |
|---|---|
| pid | **7990** |
| 기동 | **≈09:00:43 KST** (`etime` 7시간 23분 51초 · 16:24:34 시점) |
| 플래그 | `VOICE_ADAPTER=stub_unresponsive` · `WORKER_ENABLED=false` · `--log-level info` |
| `/health` | 200 |

`handoff/HANDOFF-implementation.md` ④-1 의 서술이 **그 시점에 참이었음.** 코드가 아니라 **응답으로**
판정했음.

```
GET http://localhost:8002/api/sessions/d127dece-…/results  → HTTP 200
  keys: ['partial_failure', 'pronunciation', 'status']   ← 3개
  status: no_utterances · awaiting_analysis 존재: False

GET http://localhost:8002/api/sessions/76d9ef31-…/results  → HTTP 200
  keys: ['partial_failure', 'pronunciation', 'status']   ← 3개
  status: connection_failed · awaiting_analysis 존재: False
```

`app/backend/app/api/results.py:124` 가 그 키를 싣는데 응답에 없었음. 시간 순서도 일치함 — 도입 커밋
`64b8b58` 이 **09:30:20 KST** 이고 프로세스 기동이 **≈09:00:43 KST** 임.
**낡은 소스의 범위**: `64b8b58` 이후 백엔드 커밋 전건. `--reload` 가 없어 반영되지 않았음.

⚠️ **팀리드가 전한 「약 4시간 39분 낡음」과 값이 다름** — 그쪽은 최신 백엔드 커밋 `adf462c`(13:39:55)
기준이고 이쪽은 `awaiting_analysis` 도입 커밋 `64b8b58`(09:30:20) 기준임. **둘 다 맞고 재는 기준이
다름.** 낡음의 하한을 정하는 것은 후자이고(그 커밋부터 이미 반영되지 않았음), 낡음의 폭을 정하는
것은 전자임.

## 3. 프론트는 최신이었음 — 스택이 갈라져 있었음

프론트가 낡았을 것으로 의심해 세 방향으로 쟀고 **반증됐음.**

| 시도 | 결과 | 판정 |
|---|---|---|
| dev 전용 엔드포인트 `/__nextjs_original-stack-frame` · `/_next/webpack-hmr` | 둘 다 **404** | 낡음의 정황으로 보였음 |
| `.next/` 최종 갱신 | 2026-09-10 **07:47** (프론트 변경 커밋 09:30 보다 이름) | 낡음의 정황으로 보였음 |
| ⛔ **서빙 중 번들에서 문자열 탐색** | `/results/<uuid>` HTML 의 chunk 12개를 받아 grep → **HIT** `/_next/static/chunks/_0_c79j_._.js` 에 `awaiting_analysis` 있음 | **프론트는 최신임** |

⛔ **앞의 두 정황을 판정 근거로 쓰지 않았음** — 서빙되는 것을 직접 읽는 것이 정본이고 그것이 앞의
둘을 뒤집었음. 「빌드 산출물 mtime」과 「실제로 서빙되는 코드」는 다름.

### 3.1 갈라진 결과 — `no_utterances` 회복 경로가 그 구간에 죽어 있었음

`app/frontend/app/results/[sessionId]/page.tsx:71-78`:

```ts
export function shouldKeepPolling(status, awaitingAnalysis): boolean {
  if (!TERMINAL_STATUSES.has(status)) return true;
  if (status === "no_utterances") return awaitingAnalysis;   // ← 키가 없으면 undefined
  return false;
}
```

최신 프론트가 낡은 백엔드에게 그 키를 묻고 `undefined` 를 받아 falsy → **재확인이 한 번도 일어나지
않는 상태였음.** `TASK-77`(3회 재확인)과 `TASK-79`(응답 계약)가 만든 회복 경로가 **둘 다** 없었음.

⛔ **앱 결함으로 등록하지 않음** — 배포 불일치의 산물이고 재기동으로 해소됨(§8 이 그것을 확인함).
⛔ **관측한 것이 아님** — 응답(§2)과 소스를 조합한 논리 판정이고 화면 폴링을 직접 세지 않았음.

## 4. 이전 구간의 어댑터가 앱 경로 시나리오를 결정했음

`VOICE_ADAPTER=stub_unresponsive` 는 `app/backend/app/config.py:74` 가 *"연결 실패 시나리오
E2E-S 6 을 코드 수정 없이 재현"* 용으로 적은 모드임.

⛔ **`browser_leg.md` 의 규약이 이 회차에 그대로 적용됐음**: *"재기동의 주체는 검증자가 아니라
호출자다. 검증자는 재기동하지 않고 `BLOCKED` 로 보고하며, 보고에 낡은 소스의 개수와 프로세스 기동
시각을 넣는다."* — §2 가 그 둘을 적었고 **재기동은 `ohmyenglish-e4` 가 했음.**

## 5. 워커를 켤 수 없는 이유 (두 구간에 공통)

`analysis_jobs` 에 **`pending` 이고 `available_at <= now()` 인 job 이 7건** 있음
(`plan_next_session` 4 · `analyze_utterance` 3 — 이 턴에 직접 셈).

`runs/2026-09-10-task81-pronunciation-focus.md` §2 가 지목한 위험이 유효함 — 워커든 `claim_one`
이든 부르면 그 7건이 먼저 집혀 보존 세션이 파괴되고 Bedrock 비용이 나감(`H-AT`).

⚠️ **`analyze_utterance` pending 3건의 `session_id` 가 NULL 임**(직접 조회). 그래서 그 job 들이 어느
세션 것인지 원장 조회로는 가려지지 않음 — 이 사실 자체를 적어 둠.

## 6. DB 기준선 — 이 턴에 직접 센 값

| 표 | 지금 | 인계된 기준선 | 판정 |
|---|--:|--:|---|
| `learning_sessions` | 13 | 13 | 일치 |
| `utterances` | 120 | 120 | 일치 |
| `pronunciation_attempts` | 4 | 4 | 일치 |
| `error_occurrences` | 24 | 24 | 일치 |
| `analysis_jobs` | 49 | 49 | 일치 |
| `error_patterns` | **10** | 9 | 어긋남 — `TASK-84` 소유(P6 산출물) |
| `review_tasks` | **17** | 15 | 어긋남 — `TASK-84` 소유 |
| `session_plans` | 2 | — | 인계된 기준선에 없음 |

⚠️ 어긋난 둘은 `handoff` ⑥ 이 이미 *"회귀가 아니라 다른 갈래의 P6 산출물"* 로 적어 둔 것과 일치함.
**새로운 어긋남 0건임.**

## 7. 마지막 실물 회차 — 무엇을 관측하고 무엇을 못 봤나

마지막 Nova 실물 호출은 **2026-09-10 13:38:29 KST** 임
(`.harness/evidence/P-tooluse-prompt-rule10-nova-protocol-p2k+p2a-20260910T043829Z.json` mtime).
`TASK-86` 규칙 10 리마인더 8회의 마지막 회차임.

### 7.1 ⛔ 스파이크 1회 소요를 실측했음 — **약 41초**

그 8회 산출 파일 mtime 간격임(연속 5건): `13:35:43 → 13:36:24 → 13:37:06 → 13:37:47 → 13:38:29`
= **41 · 42 · 41 · 42 초.** 픽스처 길이(`p2k` 3.79s + `p2a` 2.96s)와 `--silence-ms 1600` 기본값이
하한을 만들고 나머지는 Nova 왕복임. ⚠️ **파일 mtime 에서 유도한 값이고 스톱워치가 아님.**

### 7.2 자격증명은 그 시각에 유효했음 — 지금은 미확인

`spike_nova_protocol.py:351` 이 `prepare_bedrock_credentials(settings)` 를 부르고
`app/backend/.env` 에 `AWS_ACCESS_KEY_ID`·`AWS_SECRET_ACCESS_KEY` 쌍이 있음(키 이름만 확인).
13:38 에 성공적으로 돌았으므로 **그 시각에 유효했음.** ⛔ **지금 유효한지는 재지 않았음** —
확인에 유료 호출이 필요하고 이번 임무 범위 밖임.

---

# 구간 B — 재기동 후 프로세스 (pid 25563) · **2026-09-10 16:27:44 KST 이후**

## 8. 새 기준선 — 이 턴에 직접 재서 얻음

⛔ **이 시각 이후의 `:8002` 관측만 새 코드 기준임.**

| 항목 | 값 | 어떻게 |
|---|---|---|
| pid | **25563** | `lsof -ti:8002` |
| 기동 | **2026-09-10 16:27:44 KST** (`etime` 04:48 · 16:32:32 시점) | `ps -o lstart` |
| 플래그 | **`VOICE_ADAPTER=nova`** · `WORKER_ENABLED=false` · `--log-level info` | `ps eww` |
| `/health` | **200** | `curl` |

팀리드가 전한 값과 **일치함** — 그리고 이쪽이 직접 재서 확인했음.

### 8.1 응답 스키마가 늘었음 — **이쪽이 직접 확인했음**

팀리드 전달에서 이 항목은 「`ohmyenglish-e4` 보고 · 이쪽 미확인」이었음. 직접 재서 채움.

| 세션 | 응답 키 수 | `status` | `awaiting_analysis` |
|---|--:|---|---|
| `d127dece` | **4** | `no_utterances` | **`True`** |
| `76d9ef31` | 4 | `connection_failed` | `False` |
| `b2f0d169` | 5 | `partial_failure` | `False` |
| `210233be` | 4 | `analyzing` | `False` |
| `e0c5e580` | 6 | `final` | `False` (교정 2건) |

**회귀가 아니라 `64b8b58` 의 반영임.** §2 의 3개 → 4개로 늘었고 §3.1 의 갈림이 해소됐음.

---

## 9. 가설 판정 — 팀리드가 준 셋을 각각 확인·반증함

### 9.1 가설 1 — ⛔ **반증됨.** `WORKER_ENABLED=false` 는 `TASK-78` AC#3 을 막지 않음

AC#3 이 요구하는 셋(`pronunciation_attempts` 행 · `error_patterns` 패턴 · `next_review_at`)이
**전부 세션 경로의 한 연쇄 안에서** 만들어짐. 워커를 지나지 않음. 호출 연쇄를 직접 읽어 확인했음.

```
audio_gateway/session.py:319  record_attempt(...)          ← 진입점이 세션임 (워커 아님)
  services/pronunciation.py:202  _insert_attempt()         → pronunciation_attempts 행
  services/pronunciation.py:217  link_pattern()            → error_patterns upsert
  services/pronunciation.py:226  refresh_review()
    services/review.py            recompute()              → next_review_at
```

근거 문장 셋(전부 소스에서 직접 읽음):

- `services/pronunciation.py:12` — *"incorrect가 되면 → error_patterns 연결 (**경로 불문**)"*
- `services/pronunciation.py:218` — *"판정 **경로 불문**으로 복습 상태를 다시 계산한다"*
- `services/review.py:3` — *"`next_review_at`에 값을 넣는 코드는 이 모듈뿐이다. **세션·워커는
  배선만 한다**"*

그리고 `resolve_dangling`(`session.py:216`)도 세션 경로에서 불리고 내부에서 `link_pattern`(:356) ·
`refresh_review`(:360)를 부름 — 세션 종료 시 미해결 시도도 워커 없이 처리됨.

⛔ **그러면 AC#3 의 실제 장벽은 워커가 아니라 tool 도착임.** `TASK-78` Implementation Notes 가
*"워커를 켜지 않았고(H-AT) tool 이 오는 앱 회차를 얻지 못해 종단을 시작할 입력이 없었다"* 로 **둘을
한 문장에 적어** 원인이 섞여 보였음. 실측하면 뒤쪽만 남음.

⚠️ **단정 범위**: `link_pattern` 은 `outcome='incorrect'` 일 때만 패턴을 upsert 함
(`pronunciation.py:499-504` 주석). 즉 종단이 성립하려면 tool 이 **판정 호출까지** 와야 함 —
규칙 10 이 요구하는 두 번째 호출임. 그것도 워커 문제가 아니라 tool 내용 문제임.

### 9.2 가설 2 — **결론은 대체로 맞고 기전이 다름.** 워커 OFF 가 근거가 아님

`results.py:403-414` 를 직접 읽었음. `awaiting_analysis` 가 계산되는 분기가 **하나뿐**임.

```python
if counts["total"] == 0:                      # ← job 이 «아예 0건» 일 때만
    analyzable = await conn.fetchval(_ANALYZABLE_UTTERANCES_SQL, …)
    return SessionResult(status="no_utterances", …, awaiting_analysis=analyzable > 0)
```

주석이 *"**여기가 그 조건이 성립할 수 있는 유일한 분기다** — 아래 규칙 3·4·5 는
`counts["total"] > 0` 이므로 정의상 거짓이다"* 로 그것을 못박음.

⛔ **그래서 「워커 OFF 의 무한 지연」이 `awaiting_analysis=True` 를 만들지 않음.** 워커가 꺼져도
정상 경로로 새 세션을 돌리면 job 이 **생성되므로** `counts["total"] > 0` 이 되고 `status='analyzing'`
(규칙 3)이며 `awaiting_analysis=False` 임. 그리고 `analyzing` 은 `TERMINAL_STATUSES` 에 없어
`shouldKeepPolling` 이 **첫 줄에서** true 를 반환함 — `TASK-79` 가 고친 자리를 **지나가지 않음.**

⚠️ **그런데 앞 조각을 지금 관측할 수 있다는 결론 자체는 맞음. 근거가 다름**: `d127dece` 가 이미
`awaiting_analysis=True` 를 내놓고 있음(§8.1). 그 세션은 **user 발화 3건인데 `analyze_utterance`
job 0건**(직접 조회)이고 그것이 종료 flush 실패 재현본임. **워커 상태와 무관한 정적 표본임.**

| AC#2 의 조각 | 지금 가능한가 | 무엇이 필요한가 |
|---|---|---|
| 앞 — 「폴링이 조기에 멈추지 않는가」 | **가능함** | `d127dece` 를 브라우저 레그로 열어 폴링을 셈. ⛔ **계측 신설이 선행됨** — 하네스에 `awaiting_analysis` 를 재는 코드가 **0건**(`grep` 확인) |
| 뒤 — 「회복 뒤 화면이 교정을 표시하는가」 | **불가능함** | job 을 되살릴 주체가 워커의 `flush_ended_sessions` 뿐이고, 켜면 §5 의 pending 7건이 집혀 보존 세션이 파괴됨 |

⛔ **AC 를 두 조각으로 나누는 것은 원장 변경이라 이쪽이 하지 않음** — 문면이 「화면이 교정을 놓치지
않는 것을 관측한다」로 뒤 조각을 포함하므로, 앞 조각만 닫으면 문면을 좁히는 것임. 판정만 냄.

### 9.3 가설 3 — ⛔ **확인됨.** `stub_unresponsive` 의존 시나리오가 지금 성립하지 않음

`browser_leg.md` 에서 직접 세어 확인했음. 그 문서 §2 가 이미 열거해 둠(`:121-122`):
*"C1 의 음성 대조 6건과 C2 3건·C5 2건은 `stub_unresponsive` 를 요구하고 **A1-4 본 단정은 `stub`**
을 요구한다."*

개별로 확인한 것:

| 단정 | 그 어댑터를 요구하는 자리 | 종류 |
|---|---|---|
| A1-1 | `:313` — `recv.final` **0** | 음성 대조 |
| A1-4 | `:316` — 대조 ① **0**. 본 단정은 **`stub`** 요구 | 음성 대조 + 본 단정 |
| A1-6 | `:324` — URL 이 `/` 에 남고 `voice_adapter_connect_timeout` | 음성 대조 |
| A1-8 | `:326` — `utterances` **0행** | 음성 대조 |
| **A1-7** | `:489` — **본 단정임.** `stub.py:70` 의 `await asyncio.Event().wait()` 가 영원히 끝나지 않아 **경쟁 프레임 0인 주입 창**이 열림. 창은 유한함 — `session.py:53 CONNECT_TIMEOUT = 10.0` | **본 단정** |
| C3d | `:694` — 보존 세션 `76d9ef31` 의 `connection_failed` 근거 | 표본 근거 |

⛔ **A1-7 은 음성 대조가 아니라 본 단정이 그 어댑터를 요구함** — 다른 모드로 대체할 수 없음.
⛔ **`browser_leg.md` §2 의 규약이 그대로 걸림**: *"한 회차는 어댑터 모드 하나만 판정한다 — 두 모드가
필요하면 회차를 두 번 연다."* 2026-09-09 5차수에서 `BLOCKED` 12건의 대부분이 이 하나에서 나왔음.

⚠️ **`ROUNDS.md` 가 A1-7 을 `BLOCKED` 로 둔 사유는 어댑터가 아니라 「표본 구성」임** — 별건이고
어댑터를 되돌려도 그 사유는 남음.

---

## 10. ⛔ 재기동이 만든 가장 큰 변화 — `TASK-81` AC#4 가 지금 실행 가능해짐

`p_app_path.py` 의 docstring `:21` 이 *"⛔ 어댑터는 `VOICE_ADAPTER=nova` · `WORKER_ENABLED=false`
여야 한다(`H-AS`·`H-AT`)"* 를 요구하고 **지금 구성이 정확히 그것임.** 선행 조건 전건을 직접 확인했음.

| 선행 조건 | 상태 | 확인 방법 |
|---|---|---|
| 백엔드 `nova` + `WORKER_ENABLED=false` | 갖춰짐 | `ps eww -p 25563` |
| 백엔드가 최신 코드 | 갖춰짐 | 응답 키 4개 (§8.1) |
| 프론트 `:3000` 최신 | 갖춰짐 | 번들 grep (§3) |
| CDP `:9222` | 갖춰짐 | `Chrome/152.0.7977.65` |
| 픽스처가 프론트에서 서빙됨 | 갖춰짐 | `GET /harness/p2k.wav` **200 · 125,446B** · `p2a.wav` **200 · 98,710B** |
| 회차 개설 (`.harness/browser_run_id.txt`) | **갱신 필요** | 지금 값은 2026-09-09 14:38 의 `6454e5c1-…` |

**소요 상한**: `p_app_path.py` 의 타임아웃 기본값 합이 회차당 약 **129초**
(`--walk-timeout-ms 45000` + `--settle-timeout-ms 60000` + `--end-timeout-ms 20000` +
`--result-settle-ms 4000`). 실제로는 세션이 먼저 끝나면 짧아짐.

⚠️ **그러나 코칭 빈도 13% 가 그대로 걸림** — 앱 경로 1회로는 코칭 도착을 판정할 수 없음.

---

## 11. (나) 추가 실행 가능한 시나리오 — **필요 구성별**

지금 구성은 **`VOICE_ADAPTER=nova` · `WORKER_ENABLED=false` · 최신 코드**임.

| # | 시나리오 | 소유 태스크·AC | 필요 `VOICE_ADAPTER` | 필요 `WORKER_ENABLED` | 지금 가능? | 대략 소요 |
|--:|---|---|---|---|---|--:|
| A | 코칭 회차에서 tool 도착 확인 (스파이크 직결) | `TASK-86` AC#2 | **무관** — `:8002` 를 지나지 않음 | 무관 | **가능** | 코칭 2건까지 약 15회 = **약 10분** |
| B | 빈도 표본 보강 | `TASK-87`(간접) | 무관 | 무관 | 가능하나 **판정 불가** — 목표치 미결 | 15회당 약 10분 |
| C | 「코칭이 나는 조건」 판별 4팔 | `TASK-78` AC#2 연장 | 무관 | 무관 | **가능** | 4팔 × 8회 = **약 22분** |
| D | 앱 경로 코칭 확인 (`p_app_path.py`) | **`TASK-81` AC#4** | **`nova`** | `false` | **가능 — 재기동으로 열렸음** | 회차당 상한 약 129초 |
| E | 종단: tool → `pronunciation_attempts`→`error_patterns`→`next_review_at` | `TASK-78` AC#3 | `nova` | **`false` 로 충분함**(§9.1) | **가능** — 단 **tool 이 오는 앱 회차**가 입력임 | D 를 반복해 tool 1건 확보 + 종단 조회 수 분 |
| F | 지연 시나리오 **앞 조각**(폴링이 조기에 멈추지 않는가) | `TASK-79` AC#2 앞 | 무관 | 무관 | **가능하나 계측 신설 선행** | 계측 신설이 지배함 |
| G | 지연 시나리오 **뒤 조각**(회복 뒤 표시) | `TASK-79` AC#2 뒤 | 무관 | **`true` 필요** | **불가** — 보존 세션 파괴 · 승인 대기 | — |
| H | A1-7 주입 창 · C1 음성 대조 6 · C2 3 · C5 2 | 별건(5차수 잔여) | **`stub_unresponsive`** | `false` | **불가 — 재기동 필요** | — |
| I | A1-4 본 단정 | 별건 | **`stub`** | `false` | **불가 — 재기동 필요** | — |

⛔ **D·E 와 H·I 를 한 회차에 담을 수 없음.** 어댑터가 재기동으로만 갈리고 재기동은 호출자 몫임.
⛔ **A·B·C 는 전부 Nova 유료 호출임.** 이번 임무는 실행하지 않았고 비용만 냈음.

**순서 제안 하나**: D 를 먼저 돌리면 그 산출이 E 의 입력이 됨(tool 이 온 앱 회차). 반대 순서는 성립
하지 않음. 그리고 A 와 D 는 **경로가 달라 서로를 대체하지 않음** — A 는 스파이크 직결이고 D 는 앱
경로임. `TASK-81` AC#4 가 *"스파이크만으로 닫지 않는다"* 를 명시함.

## 12. (다) 막힌 것 — 세 부류

| 부류 | 무엇 | 누가 풂 |
|---|---|---|
| **재기동 대기** | H(`stub_unresponsive` 계열) · I(`stub`) | 호출자(`ohmyenglish-e4`) |
| **승인 대기** | G(워커 ON — 보존 세션 파괴와 비용을 감수하는 판단) | 캡틴 |
| **사람의 결정** | `TASK-87` AC#1 목표 빈도 · `TASK-78` AC#4 결정 49 · `TASK-84` AC#1 발음 기원 구별 · `TASK-87`↔`TASK-86` 의존 방향 | 캡틴/사용자 |
| **표본 부족** | A(코칭 13%) · D(같은 이유) | 시간·비용만 있으면 풀림 |
| **자산 부재** | F(계측 신설) | 테스트 갈래 |

## 13. 태스크별 — 무엇이 관측됐고 무엇이 미관측인가

⚠️ 「관측된 것」 중 실물 왕복 수치는 전부 이전 세션의 것이고 **내가 돌린 것이 아님.** 정본은
`runs/2026-09-10-task81-pronunciation-focus.md` · `runs/2026-09-10-task75-rule9-rule11-replacement.md` ·
`runs/2026-09-10-decision50-tool-rate.md` 임.

| 태스크 | 상태·AC | 관측된 것 | **미관측** | 지금 구성에서 |
|---|---|---|---|---|
| `TASK-79` | In Progress 2/3 | AC#1·AC#3 — 상수를 없애고 응답 계약으로 닫았음. **키가 실제로 응답에 있음을 이 회차가 확인했음**(§8.1) | AC#2 | 앞 조각 가능(계측 신설 선행) · 뒤 조각 불가(워커) |
| `TASK-81` | In Progress 3/4 | AC#1·AC#2·AC#3 — 실물 왕복 28회. 결과는 「코칭 도착하지 않음」이고 원인이 고친 두 층이 **아님** | AC#4 | **가능 — 선행 조건 전건 갖춰짐**(§10) |
| `TASK-86` | In Progress 1/3 | AC#1 — 규칙 10 의 *"right after you have modeled the sentence"* 를 **반증으로 답했음**. 리마인더 8회는 **판정 불가**(코칭 0회) | AC#2. AC#3 은 부작위라 마감 때 확인 | 가능 — 표본 비용이 장벽 |
| `TASK-87` | To Do 0/2 | 빈도 실측 약 **13%** | AC#1·AC#2 | 목표치 결정 대기 |
| `TASK-78` | In Progress 2/4 · **타 세션** | AC#1·AC#2 | AC#3 · AC#4 | **AC#3 이 워커 없이 가능함**(§9.1 — 이 회차의 발견) · AC#4 는 사용자 |
| `TASK-84` | Awaiting Decision 0/2 · **타 세션** | 관측 완료 | AC#1·AC#2 | 사람의 판정 대기 |

## 14. 정리 대조

- Nova 실물 호출 **0회** · DB 쓰기 **0건**(SELECT 만) · 원장 변경 **0건** · 앱 코드 변경 **0건**
- 재기동 **0회** — `:8002` 재기동은 `ohmyenglish-e4` 가 했고 이쪽은 결과를 직접 재서 확인만 했음
- 회차 중 HEAD 불변 — 시작 `b6b3b7d` · 끝 `b6b3b7d`
- 프론트 pid 37650 · CDP Chrome 152 그대로 살아 있음 — 내가 띄운 것이 아니고 닫지 않음
- 임시 파일 전건 삭제함(`/tmp/_health.json` · `/tmp/_res_*.json` · `/tmp/_front.html` ·
  `/tmp/_res_page.html` · `/tmp/_chunks.txt`). ⚠️ 증거로 옮길 것이 없음 — 판정에 쓴 값을 본문이 적었음
