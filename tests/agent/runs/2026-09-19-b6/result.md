# B6 회차 — TS-21 · TS-29 · TS-34 (실물 Nova 마지막 배치)

> 2026-09-19 07:16~07:35 UTC · 대상 `/Users/redstar/MyProject/OhMyEnglish` ·
> 브랜치 `design/first-vertical-slice` · **HEAD `a34a143` (회차 전후 같음)**
> 회차 디렉터리 `tests/agent/runs/2026-09-19-b6/` · 증거 `evidence/`

## §1. 환경과 전제 재검증

| 항목 | 값 (이 회차에 직접 쟀음) |
|---|---|
| HEAD (착수) | `a34a143fb921fdd019565c74eea0eb894dcf270c` · 짧게 `a34a143` |
| HEAD (회차 끝) | `a34a143` — **움직이지 않았음** |
| 작업 트리 | 착수 시 미커밋 2건(`ts-23`·`ts-25` 원장 파일) 뿐이고 대상 소스는 무변경 |
| 백엔드 | 착수 시 `:8002` 에 **스텁**으로 떠 있었음(pid 57857) → 내려서 `VOICE_ADAPTER=nova`(pid 61566) → 회차 끝에 **`VOICE_ADAPTER=stub` 로 되돌려 띄웠음**(pid 92720) |
| 프런트 | `:3000` pid 98298 — 호출 세션 소유. 손대지 않았고 회차 끝에도 살아 있음 |
| 브라우저 | 전용 Chrome 153.0.8010.50 — `--remote-debugging-port=9333 --user-data-dir=/tmp/chrome-b6 --use-fake-device-for-media-stream --use-fake-ui-for-media-stream --autoplay-policy=no-user-gesture-required`. 회차 끝에 닫았음(`:9333` 무주인) |
| DB | homebrew `:5432` `ohmyenglish` · `current_schema()` = `ohmyenglish` |
| 워커 | 끝까지 켜지 않았음(`WORKER_ENABLED=false`) |

### 재검증에서 어긋난 전제 셋

1. ⛔ **`TASK-75` 는 미해결이 아니라 `Done` 임**(2026-09-10 04:30 UTC). 착수 지시가 그것을
   미해결로 인용했고, 인용의 출처인 Phase 1 완료 선언문
   (`docs/design/2026-08-25-first-slice-acceptance-criteria.md:169`)이 지금도
   *"발음 코칭이 지금 어떤 프롬프트 조건에서도 일어나지 않는다"* 로 적혀 있음.
   **이 회차의 실측은 그 문장과 반대임** — 발음 전용 모드에서 tool 이 도착해 시도 1건이 기록됐음(§7).
   ⇒ 결함 `TASK-238` 로 등록함.
2. ⛔ **스텁 어댑터로는 쉐도잉 화면에 닿을 수 없음.** TS-29 본문의 전제 정정 노트는 「503 으로도
   같은 ok:false 화면에 닿으므로 그쪽이 더 싸다」고 적었는데, 스텁 세션은 **0.021~0.023초**에
   끝나 패널이 뜨기 전에 결과 화면으로 넘어감(3회 재현 · `evidence/01-stub-round-note.md`).
   503 은 HTTP 로만 관측됨. ⇒ 404 갈래를 실물 세션 «안»에서 만드는 쪽으로 바꿨음.
3. ⚠️ **`p_readback_leg.py` 의 로드 대기가 직전 문서에 즉시 만족함.** `Page.navigate` 직후
   `document.readyState === 'complete'` 를 보면 **바뀌기 전 문서**의 complete 에 걸림 —
   실제로 `about:blank` 에 마이크 대체를 심고 새 문서가 그것을 지운 상태를 관측했음.
   이 회차의 드라이버는 **위치와 버튼이 실제로 뜰 때까지 센** 뒤에 심음.

### 격리

공유로 전제하고 시작했으나 회차 중 다른 주체는 관측되지 않았음 — `:8002` 는 내가 소유했고,
`git log` 는 `a34a143` 에서 움직이지 않았고, `find app/backend/app -newermt` 로 잡힌 최근 변경이
없었음. 프런트 `:3000` 만 호출 세션 소유라 건드리지 않았음.

## §2. 판정표

| 시나리오 | 판정 | AC 체크 | 근거 |
|---|---|---|---|
| **TS-21** A3 음성 세션 왕복(실물 Nova) | **통과** | #1 #2 #3 #4 (4/4) | §5 |
| **TS-29** A11 낭독 판정 | **차단됨** | #1 #2 (2/3) | §6 · AC#3 문면이 설계 계약과 어긋남 |
| **TS-34** A16 발음 코칭 | **차단됨** | #1 #4 (2/4) | §7 · AC#2 원인 미확정 · AC#3 writer 0곳 |

- **새로 실패**: 0건. 세 시나리오 모두 이 회차가 첫 실행이라 회귀 비교의 기준선임.
- **차단**: TS-29 AC#3 · TS-34 AC#2 · TS-34 AC#3.
- **등록한 결함**: `TASK-235` · `TASK-236` · `TASK-237` · `TASK-238`(작업 원장 ID).

## §3. 착수 시 상태 — 회귀 기준선

```
TS-21 - A3 · 음성 세션 왕복 (실물 Nova) — 실제 음성 1회차     In Progress · AC 0/4
TS-29 - A11 · 낭독 판정 — recordings 조회와 readback          In Progress · AC 0/3
TS-34 - A16 · 발음 코칭 — mode=pronunciation 실시간 판정       In Progress · AC 0/4
```

세 시나리오 전부 이 회차가 처음 실행함 ⇒ **회귀 판정의 대상이 없고 이 회차가 기준선임.**
원자료는 `evidence/00-baseline.txt`.

## §4. 실물 세션과 비용 — 승인 범위 3회를 전부 씀

| 회차 | 시나리오 | 세션 ID | mode | 지속 | Nova 호출 |
|---|---|---|---|---|---|
| R1 | TS-29 (+TS-21 보조) | `4ec9240c-5ae2-4c0a-9b8f-12ef498a3e07` | shadowing | 07:25:22 → 07:26:08 | **2** |
| R2 | TS-21 | `8c1a4e8b-35f2-45fc-af97-d12f4a9ca748` | speaking | 07:27:49 → 07:28:03 | **1** |
| R3 | TS-34 | `d5497eaf-4e7f-4a8c-89a1-5bcc488c063c` | pronunciation | 07:30:53 → 07:32:21 | **1** |

**`llm_calls` 증가분 — 회차 전 34 → 회차 뒤 38 (`+4`), 그 중 `purpose='nova'` 20 → 24 (`+4`).**
Claude 계열(`vocab`·분석)은 0건 증가 — 워커를 켜지 않았음.

| 호출 시각(UTC) | 입력 토큰 | 출력 토큰 | 무엇 |
|---|---|---|---|
| 07:25:47.643 | 903 (음성 508 · 글 395) | 93 (음성 23 · 글 70) | R1 낭독 전사 — 설계서 §6-1 의 B 팔(897/92)과 오차 범위 |
| 07:26:08.437 | 216 (음성 150 · 글 66) | 0 | R1 쉐도잉 세션의 Nova 스트림(코치가 말할 거리가 없었음) |
| 07:28:03.218 | 2,569 (음성 213 · 글 2,356) | 311 (음성 234 · 글 77) | R2 말하기 세션 1턴 |
| 07:32:21.483 | 1,142 | 847 | R3 발음 전용 모드 2턴 |

⚠️ **3회를 넘기지 않았음.** 넘길 근거가 생긴 자리는 TS-34 AC#2 하나이고(§7-2) 돌리지 않고
보고로 넘김.

⚠️ 스텁 예비 회차 3건은 Bedrock 호출 0건이었고 남긴 job 아홉을 teardown 으로 걷었음.

## §5. TS-21 — A3 음성 세션 왕복 (통과 · AC 4/4)

**수단**: `tests/harness/p_app_path.py --port 9333 --wav u1.wav`(전용 Chrome · `instrument.js`
sha256 `cbc19fb6…b55ac` 대조 통과). 픽스처 `u1.wav` 1.923초 · 16kHz · mono.
원자료 `evidence/09-r2-app-path.json` · 화면 `evidence/09-r2-session.png`·`09-r2-results.png` ·
DB `evidence/10-r2-post-db.txt`.

### AC#1 — 실물 어댑터로 세션 1회가 열려 사용자 음성에 음성 응답이 돌아옴 ✅

`session_started` 1 · `speech_start` 1 · `speech_end` 1 · `partial` 3 · `final` 2 ·
**`audio` 115** · `session_ended` 1. 화면 줄 둘이 실제로 렌더됐음:

- `답변: i usually go to gym after work.` ← 픽스처가 말한 문장의 전사
- `질문: I see. You usually go to the gym after work. Can you tell me one thing you need at work today? …`

⇒ 사용자 음성이 전사되고 코치가 글과 **음성 프레임 115건**으로 답했음. `session_failed` 0건.

### AC#2 — 그 발화의 전사가 DB 에 남음 ✅

`learning_sessions` 1행(`status=completed` · `mode=speaking` · `started_via=ui`) ·
`utterances` 2행:

| seq | speaker | type | transcript |
|---|---|---|---|
| 1 | user | learning | `i usually go to gym after work.` |
| 2 | agent | learning | `I see. You usually go to the gym after work. …` |

### AC#3 — 회차가 만든 세션이 teardown 으로 걷혔음 ✅

`teardown_session.py --session-id` 를 **6건**에 돌렸음(실물 3 + 스텁 예비 3).
원자료 `evidence/15-teardown.txt`. 회차 뒤 계수기가 착수 값으로 되돌아왔음
(`evidence/16-post-teardown-counters.txt`):

| 표 | 착수 | 회차 끝 |
|---|--:|--:|
| `learning_sessions` | 27 | **27** |
| `utterances` | 175 | **175** |
| `analysis_jobs` | 111 | **111** |
| `pronunciation_attempts` | 7 | **7** |

⚠️ teardown 이 손대지 않는 자리 둘을 따로 확인해 지웠음 — R3 이 **새로 만든**
`error_patterns` 1행(`pronunciation_th_as_t`)과 그것을 가리키는 `review_tasks` 1행.
둘 다 이 회차가 만든 행이고(created_at 07:32:21) 지운 뒤 발음 패턴 전수가 착수 상태
(`pronunciation_an_as_a` 1행 · freq=2)와 같음.

### AC#4 — llm_calls 증가분을 회차 전후로 세어 비용 근거를 남김 ✅

§4 의 표가 그것임. 회차 전 `evidence/00-baseline.txt`·`03`·`08`·`11`, 회차 뒤 `07`·`10`·`13`·`16`.
⚠️ `llm_calls` 는 비용 기록이라 teardown 으로 지우지 않았음 — 지우면 비용을 복원할 수 없음.

## §6. TS-29 — A11 낭독 판정 (차단됨 · AC 2/3)

**수단**: `/tmp/b6_rb2.py`(사본 `evidence/driver-b6_rb2.py`). `p_readback_leg.py` 의 JS 상수와
도우미를 **import 해서 그대로** 쓰고, 한 세션 안에서 낭독을 두 번 태워 성공 갈래와 404 갈래를
함께 봄. 픽스처 `public/harness/readback.wav` 14.895초 · 16kHz · 끝 2초 RMS 0.0(침묵 확인).
클립은 세션이 고르는 첫 행 `00000000-…-0201`(45낱말)이고 픽스처와 같은 글임.
원자료 `evidence/04-r1-readback-two-legs.json` · 화면 `04-r1-leg1.png`·`04-r1-leg2.png` ·
판정 본문 `06-r1-leg1-judgment.json`.

### AC#1 — 녹음이 저장된 뒤 판정 요청이 성공 갈래를 냄 ✅

세션 화면이 `['클립 듣기','따라 읽기','학습 종료']` 로 열리고, 낭독 뒤
`['클립 듣기','따라 읽기','내 낭독 듣기','낭독 판정 보기','학습 종료']` 로 바뀌었음.
「낭독 판정 보기」가 만든 요청이
`POST /api/sessions/4ec9240c-…/recordings/df3aa791-7764-4177-9b5b-541f05b58ce7/readback` 이고
응답이 **200 · 낱말 45개**였음:

- `match` **44** · `missing` **1**(`coffee.`)
- 화면도 같게 렌더 — 낱말 44개는 평문색, `coffee.` 하나만 `line-through` + `rgb(255,138,138)`,
  범례 「밑줄은 다르게 읽은 낱말이고 취소선은 빠뜨린 낱말이에요.」가 함께 떴음
- 저장된 전사: `i usually wake up at seven. … then i make a cup of. after that, …`
- `utterances.readback_transcript` 에 그 글이 남았음(`evidence/07-r1-post-db.txt`)

⚠️ 빠진 낱말 하나는 **설계서 §6-1 이 이미 ASR 한계로 귀속해 둔 자리와 같음**
(`a cup of coffee` → `a cup of.`). 두 팔이 같은 자리를 놓쳤다는 그 회차의 근거와 일치하므로
앱 결함으로 올리지 않았음.

### AC#2 — audio_url 이 없으면 판정이 404 이고 화면이 「지금은 낭독 판정을 쓸 수 없어요.」 를 냄 ✅

같은 세션의 둘째 낭독(`72983775-c54a-43ef-b485-a68af655c09e` · 회차가 만든 행)의
`audio_url` 을 `null` 로 지우고(갱신 1행) 판정을 눌렀음.

- **화면**: `지금은 낭독 판정을 쓸 수 없어요.` — 낱말은 0개 (`evidence/04-r1-leg2.png`)
- **HTTP**: 같은 주소에 `curl -X POST` 로 다시 물어 **404 · `{"detail":"readback not found"}`**
  (`evidence/05-r1-leg2-404-status.txt`·`-body.txt`)
- ⚠️ 이 갈래는 전사가 아직 없을 때만 성립함 — 전사가 있으면 `load_recording` 을 부르지 않으므로
  `audio_url` 을 지워도 캐시된 판정이 돌아옴. 그래서 **성공 갈래를 먼저** 태우고 **다른 발화**로
  404 를 만들었음.
- ⚠️ 관측력 증명: 같은 수단(`section p` 판독)이 성공 갈래에서 범례와 전사문을, 실패 갈래에서
  안내 문구를 각각 잡았음 ⇒ 「0건」이 수단의 눈먼 자리에서 온 것이 아님.

### AC#3 — 판정 결과가 성공·실패·판정 불가 가운데 하나로 기록됨 (PRD §10) ❌ 체크하지 않음

**구현이 기대와 다르게 동작한 것이 아니고 AC 문면이 문서화된 계약과 어긋남.**

- 설계서 `docs/design/2026-09-18-read-aloud-judgment-design.md` §5 가
  *"판정 확정 (2026-09-18 · `TASK-211`): 연결하지 않음. **v1 유예가 아니라 결론임**"* 으로
  낭독 판정을 `pronunciation_attempts` 에 **잇지 않기로 확정**했음. 근거 셋 가운데 하나가
  *"낱말 대조는 낱말을 낼 뿐 소리를 내지 못함"* 임.
- 실제 기록 형태는 낱말마다 `match`·`missing`·`different` 셋이고, 그 세션의
  `pronunciation_attempts` 는 **0행**이었음(`evidence/07-r1-post-db.txt`).
- PRD §10 의 성공·실패·판정 불가는 **재발화**(R10-2)의 값역이고 낭독 판정의 값역이 아님.

⇒ 통과로도 실패로도 올리지 않고 결함 `TASK-235` 로 넘겼음(전례 `TASK-231`).

## §7. TS-34 — A16 발음 코칭 (차단됨 · AC 2/4)

**수단**: `/tmp/b6_pron.py`(사본 `evidence/driver-b6_pron.py`) — `tests/harness/ws_session.py` 의
`run()` 을 그대로 부르는 얇은 래퍼임. 래퍼를 둔 이유는 그 파일의 `main()` 이 관측을
`.harness/evidence/` 에 쓰는데 그 경로가 이 에이전트의 쓰기 경계 밖이기 때문임.
호출: `--mode pronunciation --wav p2k.wav,p2a.wav --silence-ms 12000 --timeout 120`.

픽스처 선택 근거: `p2k.wav`(같은 문장을 한국어 음성 `Yuna` 가 읽은 강한 억양판)를 **첫 발화**로
줬음 — `scenarios-P-pronunciation.md` §3.2 가 요구하는 순서임. 둘째 `p2a.wav` 는 같은 문장의
정확 발음판이고 「따라 말하기」 자리를 채우려고 12초 간격을 두고 흘렸음.

⛔ **브라우저가 아니라 WS 레그를 쓴 이유**: `p_app_path.py` 는 「학습 시작」만 누르므로
`mode=pronunciation` 진입을 만들지 못하고, 화면의 「발음 집중」 버튼으로 몰려면 그 드라이버를
고쳐야 함(§1-1 이 금지함). `ws_session.py --mode` 가 리포가 이 측정을 위해 가진 수단임
(`TASK-86` 이 같은 이유로 만들었음). ⇒ **배지 화면(A5-1·A5-2)은 이 회차의 사거리 밖임.**

원자료 `evidence/12-r3-pronunciation-frames.json` · DB `evidence/13-r3-post-db.txt`.

### §7-1. AC#1 — 발음 오류에 대해 올바른 발음 시범이 돌아옴 ✅

프레임 집계: `session_started` 1 · `speech_start` 2 · `final` 5 · `speech_end` 2 ·
**`pronunciation` 1** · `partial` 5 · **`audio` 294** · `session_ended` 1.

- 첫 발화(강한 억양)의 전사가 **한글**로 왔음 — `아이피니시트더리포트엔쉐어드더리절치위드마이팀`
- 코치가 소리를 지목하고 문장 전체를 다시 읽고 따라 말하기를 요청했음:
  - `The sound I need you to focus on is the "th" sound at the beginning of words like "the" and "this."`
  - `In English, this "th" is voiced, which means your voice box should be vibrating…`
  - `Please repeat: I finished the report and shared the results with my team.`
- 음성 프레임 294건이 함께 왔음 ⇒ 글만이 아니라 소리로도 시범했음
- DB 에 시도 1행이 생겼음: `signal_source=nova_tool` · `target_sound=th_as_t` ·
  `sound_check=matched` · `target_form` = 시범 문장 전체

⇒ PRD AC10-1(문장 전체를 다시 읽고 따라 말하기를 요청)이 실제로 충족됐음.
⛔ **이것은 착수 지시가 예상한 「미동작」과 반대 방향의 관측임** — §1 의 전제 셋 ①.

### §7-2. AC#2 — 따라 말한 결과가 성공·실패·판정 불가 가운데 하나로 기록됨 ⚠️ 체크하지 않음

행은 생겼고 값도 값역 안임(`outcome='incorrect'`). 그런데 **그 값이 재발화의 판정이 아님**:

| 관측 | 값 |
|---|---|
| `outcome` | `incorrect` |
| `spoken_form` | **`null`** |
| `resolved_at` | `2026-09-19 07:32:21.491263+00` = **세션 종료 시각과 같음** |
| 둘째 `pronunciation` 프레임 | **오지 않았음** (그 type 은 1건뿐) |
| 학습자의 재발화 | 실제로 있었음 — `utterances` seq 2 `i finished the report and shared the results with my team` |

`services/pronunciation.py` 의 `resolve_dangling` 이 *"세션에 남은 `pending` 을 `incorrect` 로
수렴시키고 `spoken_form` 을 비운다 — 재발화를 실제로 못 들었으므로"* 를 계약으로 적었음.
⇒ 기록된 `incorrect` 는 **「대답을 못 했다」로 수렴된 값**이고, 학습자는 정확히 따라 말했는데
그것이 실패로 남았음.

⛔ **원인을 단정하지 않음.** 내 수단이 배제하지 못하는 갈래가 있음 — `ws_session.py` 는
*"보내면서 받지 않는다"* 가 계약이라 **코치의 턴이 끝나기를 기다리지 않고** 재발화를 흘림.
12초 간격을 뒀지만 코치의 시범이 그보다 길었는지 이 수단으로는 가릴 수 없음(모든 프레임의 `t` 가
32.728 로 뭉쳐 도착 시각을 잃음). 그러므로 이것은 **「앱이 재발화를 판정하지 않는다」가 아니라
「이 회차가 재발화 판정을 관측하지 못했다」**임.
실물 3회 상한을 이미 다 썼으므로 재현을 돌리지 않고 결함 `TASK-236` 으로 넘기고 보고함.

⚠️ 관측력 증명: 같은 수단이 `pronunciation` 프레임을 **1건 잡았음** ⇒ 그 신호에 눈먼 것이 아님.
즉 「둘째가 오지 않았다」는 관측 자체는 신뢰할 수 있고, 가릴 수 없는 것은 **왜** 오지 않았는지임.

### §7-3. AC#3 — 전사문에 한글이 섞인 경우와 되물음이 신호로 기록됨 (PRD §10.2) ❌ 체크하지 않음

**두 조건이 이 회차에서 실제로 둘 다 발생했는데 기록은 0건임.**

| 보조 신호 | 이 회차에서 일어났는가 | 기록됐는가 | 왜 |
|---|---|---|---|
| ① 전사문에 한글 | **일어남** — `아이피니시트더리포트…` | **0행** | `korean_transcript` writer 를 **지웠음** — `services/pronunciation.py` 머리말: *"보조 신호 경로를 지웠다(`TASK-78.1` · 결정 120 · 결정 50 ③)… 51세션에서 입력을 한 번도 받지 못했고(0/51)"* |
| ② 코치의 되물음 | **일어남** — `Please repeat: …` | **0행** | `agent_reprompt` 는 **값역에만 두고 만들지 않음** — `models/pronunciation.py:32` · `db/migrations/003` · `services/review.py:256`(*"`TASK-24` 는 `agent_reprompt` 를 만들지 않는다로 2026-09-09 에…"*) |

확인 방법: 그 세션의 `pronunciation_attempts` 에서 `signal_source in ('korean_transcript','agent_reprompt')`
가 **0행**, 리포 전체 grep 으로 두 값을 «쓰는» 코드가 0곳(읽는 쪽과 값역만 남아 있음).

⚠️ 이것은 AC 문면의 오류가 아님 — **PRD R10-4 가 지금도 그 기록을 요구함**(판정 우선순위 ②가 ③보다
셈). 즉 PRD 와 캡틴 결정(120 · `TASK-24`)이 갈려 있고 어느 쪽이 정본인지 사람이 정해야 함.
⇒ 결함 `TASK-237`.

### §7-4. AC#4 — 미동작이면 무엇이 어디서 끊기는지 증거와 함께 적음 ✅

끊기는 자리를 셋으로 갈라 적었음:

1. **끊기지 않는 구간** — 진입 → 지시문 선택 → 억양 발화 → tool 도착 → 시도 기록 → 패턴 연결.
   `mode=pronunciation` 으로 열린 세션(`learning_sessions.mode='pronunciation'`)에서 tool 이
   1/1 도착했고 `error_patterns` 에 `pronunciation_th_as_t` 가 새로 생기며 복습 예정일
   (2026-09-20)까지 붙었음.
2. **끊기는 자리 ①** — 재발화 판정. 시도가 `pending` 으로 열린 뒤 닫는 tool 이 오지 않아
   종료 수렴이 `incorrect` 로 덮었음(§7-2). 원인 미확정.
3. **끊기는 자리 ②** — 보조 신호 둘의 writer 가 코드에 0곳임(§7-3). 이것은 미구현이 아니라
   **지우기로 결정된 것**이라 회차가 고칠 자리가 아님.

`TASK-75` 와의 연결: 그 태스크는 **`Done`**(2026-09-10)이고 「규칙 9·11 이 발음을 막는다」를
발음 전용 모드 신설(`docs/design/2026-09-12-pronunciation-mode-design.md`)로 풀었음.
이 회차의 관측이 그 해소를 뒷받침함 — 그러므로 **이 영역의 남은 문제는 `TASK-75` 가 아니라
위 2·3번**임. 착수 지시가 `TASK-75` 를 미해결로 인용한 것은 Phase 1 선언문의 낡은 문장에서
왔고 그것이 결함 `TASK-238` 임.

## §8. 등록한 결함

| ID | 현상 | 시나리오 |
|---|---|---|
| `TASK-235` | 낭독 판정 AC 문면이 「성공·실패·판정 불가 기록」을 요구하나 설계가 그 연결을 하지 않기로 확정했음 | TS-29 AC#3 |
| `TASK-236` | 학습자가 따라 말했는데 재발화가 판정되지 않고 종료 수렴으로 `incorrect`·`spoken_form=null` 이 기록됨 | TS-34 AC#2 |
| `TASK-237` | PRD R10-4 의 보조 신호 둘(한글 전사·되물음)을 기록하는 writer 가 0곳임 | TS-34 AC#3 |
| `TASK-238` | Phase 1 완료 선언문이 「발음 코칭은 어떤 조건에서도 일어나지 않는다」를 그대로 두어 낡은 전제가 전파됨 | TS-34 (§1 전제 ①) |

⛔ 코드는 한 줄도 고치지 않았음. 넷 다 제안만 본문에 적었음.

## §9. 정리

- 띄운 프로세스: nova 백엔드(pid 61566) → `TaskStop` 으로 내리고 `lsof` 로 무주인 확인 →
  **스텁으로 다시 띄웠음**(pid 92720 · `/health` `{"status":"ok"}` · readback 가드 503 확인).
- 전용 Chrome(`:9333`) 닫았음. 프런트(`:3000` pid 98298)는 호출 세션 소유라 살려 뒀음.
- teardown 6건(실물 3 + 스텁 3) · 회차가 만든 `error_patterns`·`review_tasks` 각 1행 삭제.
- 되돌리지 못한 것 하나: **`llm_calls` 4행** — 비용 기록이라 남겨야 함.
- 임시 파일: 드라이버 둘을 `evidence/driver-*.py` 로 옮겨 남겼음. `/tmp` 캡처는 회차 산출물이
  아니라 버림.

## §10. 다음 회차로 넘기는 것

1. **TS-34 AC#2 재현** — 코치의 턴이 끝난 뒤에 재발화를 흘리는 수단이 필요함.
   `p_app_path.py` 의 `--next-wait-ms`·`--quiet-ms` 가 그 박자를 이미 갖고 있으나 그 드라이버는
   `mode=pronunciation` 진입을 만들지 못함 ⇒ **진입을 「발음 집중」 버튼으로 여는 드라이버**가
   선행함(대상 리포의 개발 몫).
2. **발음 배지 화면(A5-1·A5-2)** 은 이 회차가 WS 레그를 썼으므로 보지 못했음.
   `c5_pronunciation_badge.py` 가 그 수단임.
3. **TS-29 AC#3 · TS-34 AC#3** 은 사람의 결정이 선행함 — 결정이 나면 AC 문면을 고치고 다시 잼.
