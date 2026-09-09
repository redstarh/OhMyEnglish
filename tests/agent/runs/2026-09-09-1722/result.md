# 회차 2026-09-09 17:22 — 사용자 여정 3건 (J1·J2·J3)

## 0. 이 회차의 조건 — 먼저 읽어야 판정을 읽을 수 있음

**공유 인스턴스임.** 다른 Claude 세션(`ohmyenglish-e4`)이 같은 리포·같은 백엔드·같은 DB 로 동시에
작업 중임을 직접 확인함. §2-6 규칙 3개를 적용했고 그 사실을 아래에 적음.

| 항목 | 실측값 |
|---|---|
| 회차 시각 | 2026-09-09 17:18 ~ 17:27 KST |
| 착수 시 HEAD | `07c9ab1` |
| **회차 중 HEAD 가 3번 움직임** | `07c9ab1` → `3ce3e62`(17:20) → `d752a75`(17:26) |
| 측정 대상 코드 | **`d2fa24d`** — 백엔드 pid 17729 가 17:09:56 에 기동했고 `--reload` 가 없음 |
| 그 3개 커밋의 app 변경 | **0건** (`git show --stat` 로 확인) → 측정은 현재 HEAD 의 app 코드와 동일 |
| 백엔드 | `127.0.0.1:8002` pid 17729 · `VOICE_ADAPTER=stub` · 회차 중 재기동 없음 |
| 프론트 | `:3000` 응답 200 · `.env.local` 에 `NEXT_PUBLIC_API_BASE=http://localhost:8002` |
| 분석 워커 | **꺼져 있음**(지시대로 켜지 않음) → 새 세션은 `analyzing` 에 머무름. 결함이 아니라 회차 조건임 |
| 테스트 원장 | 착수 시 **0건** — 이 회차가 기준선임. 회귀 판정을 한 척하지 않음 |

**전제 재검증 결과 — 착수 지시와 어긋난 것 1건 없음.** 지시가 준 전제 3개(`:8002` 기동 · pid 17729 ·
`VOICE_ADAPTER=stub`)를 각각 `lsof -ti:8002` · `ps -p 17729` · `/health` 응답으로 그 자리에서 확인함.

---

## 1. 판정표

| 시나리오 | 판정 | 근거 요지 |
|---|---|---|
| **J1** 학습 시작 → 3턴 관통 → 결과 화면 도달 | **PASS** (AC 4/5, 1건 차단) | 프레임 19개를 32ms 안에 전부 관측. 발화 6행 저장. 결과 조회 200 |
| **J2** 결과 화면 문구가 사람이 읽을 수 있게 나옴 | **PASS** (AC 4/4) | 상태 5종 전부와 발음 카드 3장을 실물로 열어 문구 대응 완료. 실물 호출 0회 |
| **J3** 존재하지 않는 세션 uuid 조회 | **FAIL** (AC 4/4 관측 완료, 결함 2건) | API 는 404 로 옳게 응답하나 **화면이 사용자에게 `결과 API가 404을 반환했습니다` 를 보여주고 2초마다 영구 재시도함** |

⚠️ **J3 의 AC 는 4/4 체크됐지만 판정은 FAIL 임.** AC 가 「무엇을 보는지 적는다」라는 관측 과제이고,
관측 결과가 사용자에게 나쁘기 때문임 — AC 충족과 여정 판정을 섞지 않음.

---

## 2. J1 — 학습 시작에서 결과 화면까지 (TS-1)

### 만든 세션 2건 — ⛔ 직접 지우지 않았음

| session_id | 생성 시각 (KST) | 생성 시각 (UTC, DB) | 상태 | 발화 | 왜 2건인가 |
|---|---|---|---|---|---|
| `df49c4b1-69d4-4dc5-ad53-f01d8261f456` | 2026-09-09 17:23:46 | `2026-09-09 08:23:46.559342+00` | `completed` | 6행 | **1차 드라이버가 죽어 생긴 것** — 아래 참조 |
| `47aec3e6-ce9a-4892-9bf3-ef80c05ac7d9` | 2026-09-09 17:24:53 | `2026-09-09 08:24:53.464839+00` | `completed` | 6행 | 2차 드라이버 — 판정 근거가 이것임 |

두 세션 모두 `mode=speaking` · `drill_turns_expected=20` · 종료 시각이 시작 +9~18ms.

### ⛔ 1차 드라이버가 자기 관측을 버렸음 — 내 결함이고 앱 결함이 아님

1차 드라이버(`/tmp/j1_driver.py`)는 `session_started` 를 받은 뒤 오디오를 보내려다
`ConnectionClosed` 로 터져 **그때까지 모은 프레임 전부를 잃었음.** 원인은 스텁 어댑터가 픽스처 3턴을
32ms 안에 소진하고 세션이 스스로 끝나는 것(`app/backend/app/audio_gateway/session.py:245` `_relay` —
「먼저 끝나는 쪽에서 세션을 마친다」)임.

**이것을 「0건 관측」으로 결함에 올리지 않았음**(§7-7). 2차 드라이버(`/tmp/j1_driver2.py`)에서
모든 전송을 관용하고 어떤 경로로 끝나도 수집분을 출력하게 고친 뒤 전부 관측됐음.

### 관측한 프레임 — 사용자 브라우저가 받는 것과 같은 것

증거: `evidence/TS-1-ws-frames.json` (프레임 19개 전문)

```
 0.025  session_started  session_id=47aec3e6-ce9a-4892-9bf3-ef80c05ac7d9
 0.026  FINAL [agent] seq=1  'What do you usually do after work?'
 0.026  partial [user] 'I usually' → 'I usually go to'
 0.027  FINAL [user]  seq=2  'I usually go to gym after work.'
 0.027  audio  b64_len=8592
 0.028  FINAL [agent] seq=3  'What do you usually do on weekends?'
 0.029  partial [user] ×2 → FINAL [user] seq=4 'I usually go to office by subway.'
 0.029  audio  b64_len=8592
 0.030  FINAL [agent] seq=5  'What do you need to do tonight?'
 0.030  partial [user] ×2 → FINAL [user] seq=6 'I need to finish my homework tonight.'
 0.031  audio  b64_len=8592
 0.032  session_ended  session_id=47aec3e6-...
 0.077  (클라이언트의 end_session 전송이 ConnectionClosedOK 로 실패)
```

### AC 판정

| AC | 판정 | 증거 |
|---|---|---|
| #1 `session_started` 도착 · session_id 가 uuid | ✅ | `t=0.025`, `47aec3e6-ce9a-4892-9bf3-ef80c05ac7d9` |
| #2 3턴의 agent/user final 6개가 순서대로 | ✅ | seq 1~6 이 agent·user 교대. `FIXTURE_TURNS`(`app/backend/app/audio_gateway/fixtures.py:19-23`)와 문자열 일치 |
| #3 `end_session` **후** `session_ended` 도착 | ⛔ **차단됨** | `session_ended` 가 `t=0.032` 에 이미 도착했고 내 `end_session` 은 `t=0.077` 에 닫힌 소켓을 만남. 아래 설명 |
| #4 그 id 로 결과 조회 200 · status 실려 옴 | ✅ | `HTTP=200` · `{"status":"analyzing","partial_failure":false,"pronunciation":[]}` |
| #5 그 status 가 화면에 한국어로 | ✅ | `analyzing` → `분석 중` (`app/frontend/app/results/[sessionId]/page.tsx:23`, 렌더 `:157`) |

**AC#3 이 차단된 이유 — 앱 결함이 아님.** 스텁 어댑터는 이벤트 스트림을 32ms 에 소진하므로
「사용자가 종료 버튼을 누를 시점에 아직 살아 있는 세션」이라는 **전제를 세울 수 없음.**
`VOICE_ADAPTER` 변경이 금지돼 있어 이 회차에서 종료 버튼 경로는 관측 불가임 → `실패` 가 아니라
`차단됨` 임(§7-4).

⚠️ **닫힌 소켓에 종료를 보내는 것이 사용자에게 오류로 보이지는 않음.** 프론트의
`SessionSocket.send` 는 `readyState === WebSocket.OPEN` 을 먼저 보고 조용히 버림
(`app/frontend/lib/ws.ts:133-137`) — 내 드라이버만 예외를 봤음.

### 사용자가 실제로 보는 화면 (소스 대조)

`session_ended` 수신 → `terminalHandledRef` 세움 → `goToResults(event.session_id)` →
`router.push('/results/47aec3e6-...')` (`app/frontend/app/page.tsx:156-160`, `:92-98`).
결과 화면 최초 폴링이 `analyzing` 을 받으므로 사용자가 보는 것은 두 줄임:

```
학습 결과            ← page.tsx:145
분석 중              ← page.tsx:157 + STATUS_LABEL.analyzing (:23)
```

교정·발음·드릴 문구는 **하나도 그려지지 않음**: `corrections` 키가 응답에 없고(`showCorrections`
false, `:129`), `pronunciation` 이 `[]`(`:204`), `drill` 키가 없음(`:140-141`). 워커가 꺼져 있어
이 상태가 계속되는 것이고, 이 회차의 조건임.

---

## 3. J2 — 결과 화면 문구 (TS-2) · 실물 호출 0회

보존 세션 6개를 **읽기만** 했고(`GET` 만), 여기에 발음 시도가 있는 세션 2건을 더해 열었음.

### 관측 수단이 신호를 잡을 수 있음을 먼저 증명함 (§7-7)

같은 `curl` 드라이버로 **HTTP 200 과 상태 5종 전부**를 잡았음. 즉 「0건」이 나왔다면 그것은
관측 불가가 아니라 실제 부재였을 것임.

| session_id | HTTP | status | 응답 키 |
|---|---|---|---|
| `6225ddaf-90a8-43af-9aa8-e003921c75eb` | 200 | `final` | corrections, partial_failure, pronunciation, status |
| `210233be-ecaa-4409-a1af-8b7016cfe7e9` | 200 | `analyzing` | partial_failure, pronunciation, status |
| `b2f0d169-3d90-431b-b842-cce21125052a` | 200 | `partial_failure` | + corrections(`[]`) |
| `d127dece-d1d1-4329-802d-9b8fd1067388` | 200 | `no_utterances` | partial_failure, pronunciation, status |
| `76d9ef31-0d1b-4c50-b906-f16ee438080e` | 200 | `connection_failed` | partial_failure, pronunciation, status |
| `e0c5e580-dfc0-4793-b02d-54cf4346c3c5` | 200 | `final` | + **drill** `{observed:2, expected:20}` |
| `bbfc3908-639c-4f1e-a565-fdbd74e0a420` | 200 | `final` | + pronunciation 3건(전부 `nova_tool`) |
| `7b43ce56-b400-4c0d-942f-7987756d2129` | 200 | `final` | + pronunciation 1건 |

증거: `evidence/TS-2-results-<uuid>.json` 8개.

### 상태 5종이 전부 한국어 문구로 매핑됨

`app/frontend/app/results/[sessionId]/page.tsx:22-28` → 렌더 `:157`

| API status | 화면 문구 |
|---|---|
| `analyzing` | 분석 중 |
| `final` | 확정 |
| `partial_failure` | 부분 실패 |
| `connection_failed` | 연결 실패 |
| `no_utterances` | 분석 대상 없음 |

### 가장 내용이 많은 화면을 실제로 조립함 — `bbfc3908`

응답 본문(`evidence/TS-2-results-bbfc3908-639c-4f1e-a565-fdbd74e0a420.json`)을 프론트 소스에
대응시키면 사용자가 보는 것은 이것임:

```
학습 결과                                                       ← :145
확정                                                            ← :157 + :24
원문: will plan on action plan                                  ← :186
교정문: will make an action plan                                 ← :189
'plan on'은 계획 명사와 어울리지 않아요. 계획을 세운다고
말할 때는 make an action plan처럼 씁니다.                        ← :193
원문: action plan
교정문: an action plan
action plan은 셀 수 있는 단수 명사이므로 앞에 an을 붙여요.
발음                                                            ← :206 + :43
  시범 문장   I am going to have a meeting.                     ← :210 + :44
  내 발화     i'm going to have a meeting.                      ← :212 + :45
  ✓ 좋아요                                                      ← :223 + :54
  시범 문장   I will talk about architecture.
  내 발화     i will talk about architecture.
  ✓ 좋아요
  시범 문장   I will plan an action plan.
  내 발화     대답 없이 끝났어요        ← spoken_form=null → :220 + :48
  다시 연습해요                        ← outcome=incorrect → :55 (danger 색 :63)
```

**전부 사람이 읽을 수 있는 문구임.** 영어 문장은 시범·발화 원문이라 영어인 것이 옳음.

`e0c5e580` 은 `drill{observed:2, expected:20}` 을 받고 화면에 **숫자를 그리지 않고**
`오늘은 드릴이 계획보다 짧았어요.` 한 문장만 그림(`:39`, 조건 `:141`, 렌더 `:164`) — 설계 계약대로임.

`b2f0d169`(`partial_failure`, corrections `[]`, pronunciation `[]`)는
`부분 실패` + `일부 발화는 분석하지 못했다 — 재시도되지 않습니다`(`:30`, 렌더 `:159`) +
`표시할 교정이 없습니다.`(`:173`) 를 그림.

### 기계 키가 사용자 눈에 노출되지 않음 — 확인함

응답에 실려 오는 기계 키 중 화면에 **글자로 나오는 것은 0건**임. JSX 의 보간 지점을 전부 열거해
확인했음: `original_span`·`correction`·`reason`(`:186`·`:189`·`:193`),
`attempt.target_form`·`attempt.spoken_form`·`outcomeLabel(outcome)`(`:211`·`:220`·`:223`), 그리고
상수 문구뿐임.

| 기계 키 | 어떻게 처리됨 |
|---|---|
| `pattern_key` | React `key` 로만 쓰임(`:177`) — DOM 텍스트가 아님 |
| `category` · correction 의 `target_form` · `occurrences` | **아예 렌더되지 않음** |
| `signal_source` | 분기 조건으로만 쓰임(`:208`) |
| `outcome` 원값 | `OUTCOME_LABEL` 로 치환됨(`:53-57`, `:84`) |
| `target_sound` | **API 응답에 애초에 없음**(`app/backend/app/api/results.py:94-106`) |

⚠️ **관측하지 못한 화면 1건을 밝힘**: `signal_source != "nova_tool"` 인 발음 행(`관찰된 신호` 카드,
`:229-234`)은 DB 전체에 데이터가 없어(`pronunciation_attempts` 의 `signal_source` 가 전부
`nova_tool`) 실물로 열지 못했음. 그 카드의 판정은 **소스 대조뿐**임.

---

## 4. J3 — 존재하지 않는 세션 uuid (TS-3) · **FAIL · 결함 2건**

증거: `evidence/TS-3-error-path.txt` · `TS-3-404-body.json` · `TS-3-404-headers.txt` · `TS-3-422-body.json`

### API 는 옳게 응답함

```
GET /api/sessions/00000000-0000-4000-8000-000000000000/results
→ HTTP/1.1 404 Not Found
  content-type: application/json
  {"detail":"session not found"}
```

랜덤 uuid 3건으로 재현함 — 3/3 이 같은 404·같은 본문임(간헐 아님).
uuid 형식이 아닌 입력(`not-a-uuid`)은 **422** 이고 본문은 FastAPI 의 기계 오류 배열임
(`{"type":"uuid_parsing","loc":["path","session_id"],"msg":"Input should be a valid UUID, invalid character: found \`n\` at 1","input":"not-a-uuid",...}`).

### 사용자가 보는 화면 — 여기서 갈림

`app/frontend/lib/api.ts:94-96` 이 `Error` 를 던지고, 결과 화면이 `:114-119` 에서 그 메시지를
`fetchError` 로 세우며, `:149-153` 이 그것을 **danger 색으로 그대로 그림**:

```
학습 결과                              ← page.tsx:145
결과 API가 404을 반환했습니다            ← :151 + lib/api.ts:95  (빨간색)
```

그리고 `:118` 이 **2초 뒤 다시 폴링을 걸음.** 404 는 영구 오류인데 종료 조건이 없음 —
`TERMINAL_STATUSES`(`:15-20`)는 **성공 상태 5종만** 담고 있고, catch 분기의 주석(`:117`)은
「네트워크 오류는 terminal 이 아니다」를 전제하지만 **404 는 네트워크 오류가 아님.**

---

## 5. 결함 — ⛔ 고치지 않았음. 수정 제안만 적음

⚠️ **대상의 작업 원장(`backlog/`)에 등록하지 못했음** — 이 회차는 「작업 원장을 고치지 마라 ·
커밋하지 마라」로 지시받았음. §8 의 대체 절차대로 여기에 남기고 그 사실을 보고함.
등록 주체는 이 회차를 부른 세션임.

### D1 · 결과 화면이 사용자에게 HTTP 상태 코드를 그대로 보여줌 — 심각도 HIGH

- **재현 (3단계)**: ① 백엔드를 띄움 ② 브라우저로 `/results/00000000-0000-4000-8000-000000000000`
  을 엶 ③ 화면을 봄
- **기대**: 학습자 언어의 안내 — 예 「그 학습 결과를 찾을 수 없습니다」
- **실제**: `결과 API가 404을 반환했습니다` (빨간색). `API`·`404` 가 그대로 노출됨
- **영향**: 결과 화면에는 홈으로 가는 인앱 링크가 없음(`app/frontend/app/page.tsx:233` 이
  그 사실을 명시함) → 학습자가 이 화면에서 브라우저 조작 없이 빠져나갈 수단이 없음
- **증거**: `evidence/TS-3-error-path.txt` · `app/frontend/lib/api.ts:95` ·
  `app/frontend/app/results/[sessionId]/page.tsx:116`·`:151`
- **HEAD**: 측정 대상 코드 `d2fa24d` (현재 HEAD `d752a75` 와 app 동일)
- **시나리오**: TS-3
- **제안**: `fetchSessionResults` 가 상태 코드를 구분해 던지고(404 = 「없는 세션」),
  화면이 그 종류별로 학습자 문구를 고르게 함. 상태 코드 문자열을 화면 문구로 쓰지 않음

### D2 · 영구 오류(404)를 2초마다 무한 재시도함 — 심각도 MEDIUM

- **재현 (2단계)**: ① `/results/<없는 uuid>` 를 엶 ② 네트워크 탭을 봄 —
  `GET .../results` 가 2초마다 끝없이 반복됨
- **기대**: 영구 오류에서 폴링을 멈춤
- **실제**: `TERMINAL_STATUSES` 는 성공 상태만 담고, catch 분기(`:118`)가 **모든** 예외에
  재시도를 걸음. 404·422 도 재시도 대상이 됨
- **증거**: `app/frontend/app/results/[sessionId]/page.tsx:15-20`·`:111-119`
- **시나리오**: TS-3
- **제안**: 4xx 를 terminal 로 분류함. 주석(`:117`)이 전제한 「네트워크 오류」와 「응답이 4xx」를
  갈라야 그 주석의 근거가 성립함

### D3 · 오류 문구의 조사가 대부분의 상태 코드에서 틀림 — 심각도 LOW (어법)

- `결과 API가 ${response.status}을 반환했습니다` 에서 조사가 `을` 로 하드코딩됨
  (`app/frontend/lib/api.ts:95`)
- 404(사백사)·422(사백이십이)는 모음으로 끝나 조사가 **`를`** 임. `을` 이 맞는 것은 500(오백) 류임
- **제안**: D1 을 고치면 이 문장 자체가 사라짐. D1 과 함께 처리함

### D4 · 한 문장에 문체 두 개가 섞임 — 심각도 LOW (문체)

- `일부 발화는 분석하지 못했다 — 재시도되지 않습니다`
  (`app/frontend/app/results/[sessionId]/page.tsx:30`)
- 앞은 해라체(`못했다`), 뒤는 합쇼체(`않습니다`)임. 같은 화면의 다른 문구는 전부
  `~어요`·`~습니다` 로 통일돼 있음(`:39`·`:48`·`:54-56`·`:173`)
- **관측 경로**: `b2f0d169`(`partial_failure`) 를 열면 이 문장이 실제로 그려짐
- **제안**: `분석하지 못한 발화가 있습니다 — 재시도되지 않습니다` 로 통일함

---

## 6. 지키지 못한 것 · 밝혀 둘 것

### 쓰기 경계 — 정의 규칙만으로 유지됐음

⚠️ **이 회차는 서브에이전트 호출이라 전용 런처(`~/.claude/test-agent/run.sh`)의 OS 샌드박스
보장이 없음.** `cwd` 가 리포 루트이고 `allowUnsandboxedCommands: false` 도 걸려 있지 않음.
즉 쓰기 경계는 **규칙 준수만으로** 유지됐고 OS 가 막아 준 것이 아님.

실제로 쓴 곳은 3곳뿐임:

| 경로 | 무엇 |
|---|---|
| `tests/agent/runs/2026-09-09-1722/**` | 이 문서와 증거 14개 |
| `tests/agent/backlog/tasks/**` | TS-1·TS-2·TS-3 (`backlog` CLI 로만 조작) |
| `/tmp/j1_driver.py` · `/tmp/j1_driver2.py` · `/tmp/_j3_*.json` | 드라이버와 임시 캡처 |

대상 소스·설정·테스트·마이그레이션·`.env`·작업 원장(`backlog/`)을 **하나도 건드리지 않았음.**
커밋하지 않았음.

### 금지 항목 자체 점검

| 금지 | 지켰는가 |
|---|---|
| 보존 세션 6개를 지우거나 고치지 마라 | ✅ `GET` 만 함. `UPDATE`·`DELETE` 0회 |
| 워커를 켜지 마라 | ✅ 켜지 않았음 |
| 백엔드를 기동·재기동·종료하지 마라 | ✅ pid 17729 가 회차 시작·끝에 동일 |
| `VOICE_ADAPTER` 를 바꾸지 마라 | ✅ 읽지도 쓰지도 않았음 |
| `pytest` 를 돌리지 마라 | ✅ 돌리지 않았음 |
| DB 에 쓰지 마라 · SELECT 만 | ⚠️ **`psql` 은 `SELECT` 만 씀.** 다만 허용된 J1 세션 생성이 앱을 통해 `learning_sessions` 2행 · `utterances` 12행 · 분석 job 을 만들었음. 그 이상은 없음 |
| 만든 세션을 직접 지우지 마라 | ✅ 지우지 않았음. §2 에 id 와 생성 시각을 적었음 |
| 브라우저를 쓰지 마라 | ⚠️ **Chrome·Orca 는 쓰지 않았음.** 다만 `curl http://127.0.0.1:3000/` 를 **1회** 호출해 프론트 기동만 확인했음(응답 200). 화면 문구 판정은 지시대로 소스 대조로만 했음 |
| 쓰기는 `tests/agent/` 아래에만 | ✅ 위 표대로 |

### 이 회차가 재지 않은 것

- 하네스가 이미 재는 것(프레임 수 단정·전이 계수·전사문 위계)은 다시 재지 않았음
- 종료 버튼이 세션을 끝내는 경로(J1 AC#3) — 스텁으로 전제를 세울 수 없어 `차단됨`
- `관찰된 신호` 발음 카드 — DB 에 해당 데이터가 0건이라 소스 대조만 함
- 실물 Nova 호출 0회

---

## 7. 원장 상태

착수 시 0건(기준선). 회차 끝 상태:

| ID | 제목 | 상태 | AC |
|---|---|---|---|
| TS-1 | J1 · 학습 시작에서 3턴 관통 후 결과 화면 도달 | `Blocked` | 4/5 (#3 차단) |
| TS-2 | J2 · 결과 화면 상태 문구 | `Done` | 4/4 |
| TS-3 | J3 · 존재하지 않는 세션 uuid | `In Progress` | 4/6 (#5·#6 미충족) |

⛔ **AC 설계를 마감 중에 고쳤음 — 근거를 남김.** 원래 TS-3 의 AC 4건은 전부 관측 과제
(「기록함」·「확정함」·「적음」)여서 다 체크되면 끝난 것처럼 보였으나 판정은 FAIL 이었음.
게이트(G2: In Progress 인데 AC 전부 체크)가 그 어긋남을 잡았고, 원인은 **통과 조건 AC 가
빠진 내 AC 설계 결함**임. D1·D2 가 참이 되는 조건을 AC#5·#6 으로 **추가**했음 —
기대값을 낮춘 것이 아니라 올린 것임(§7-6 을 어기지 않음). 그 둘이 체크될 때 TS-3 이 닫힘.

⚠️ **이 테스트 원장을 다른 회차가 동시에 쓰고 있음.** 마감 시점에 내가 만들지 않은
`TS-4`~`TS-7` 이 나타났음. `TS-1`~`TS-3` 은 온전하나, 같은 접두사 원장을 여러 회차가
공유하고 있다는 사실을 알고 써야 함.
