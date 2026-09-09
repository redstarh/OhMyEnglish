# 5차수 브라우저 다리 — 판정 요약 (압축본)

> ⛔ **2026-09-09 압축.** 회차 1~5차 시도의 서술·프리플라이트 출력·재현 절차를 지웠다 —
> **전문은 git 이력에 있다**(`git show 744bb07:tests/harness/runs/2026-09-09-run-5-browser.md`,
> 원본 1282줄). 남긴 것은 **판정 표와 그 근거 한 줄씩**이다.
> 이유: 정리된 이력을 매 세션 context 로 올리지 않는다 (사용자 지시 2026-09-09).
> 요약 정본은 [2026-09-09-run-5.md](2026-09-09-run-5.md) 이고 이 파일은 **단정별 상세**만 갖는다.

## 회차 6개 — 어댑터 모드와 판정

| 시도 | 회차 id | 어댑터 | 결과 |
|---|---|---|---|
| 1차 | (열지 못함) | stub | `BLOCKED` — 프리플라이트 P5. 백엔드가 낡은 코드를 돌리고 있었다(소스 34건 중 16건이 프로세스보다 새로움) |
| 2차 | `8bc59725` | `stub` | `PASS` 5 · `BLOCKED` 12 · C1 부분 |
| 3차 | `bcafc8ba` | `stub_unresponsive` | **11건 전부 `PASS`** |
| 4차 | `3d7ddd94` | `stub` | A1-6 본 단정 `PASS`(계측 `startedSessionId` 유도) |
| 5차 | `cb2f4e19` | `stub` | 라이트 모드 결과 화면 5상태 — **네 항목 `PASS`** |
| 6·7차 | 실물 | `nova` | 실물 세션 2건. 상세는 요약 정본 |

## A1 합산 — 여덟 건 `PASS` · `A1-7` 만 `BLOCKED`

`A1-0`·`A1-1`·`A1-2`·`A1-3`·`A1-4`·`A1-5`·`A1-6`·`A1-8` = `PASS`. 각 단정의 **음성 대조가 실제로
FAIL 을 냈다** — `recv.final`·`partial`·`audio` 6·6·3 → **0·0·0** · `started.count` 3 → **0** ·
URL 이 `/results/<uuid>` → `/` · 그 세션 `utterances` 6행 → **0행**(전체 114 불변).
**`A1-7` 만 `BLOCKED`** 이고 사유는 화면 결함이 아니라 **표본 구성**이다 — 스텁 세션이 32 ms
캡처 프레임 1건이 만들어지기도 전에 끝난다(`elapsed 0.035s`). 3차의 `stub_unresponsive` 가
`sent.audio` **313** 을 낸 것이 그 진단을 뒷받침한다.

## C2·C3·C4·C5

- **C2** `PASS` 3건 — 실행체 단정 **56건 전건 통과**·exit 0. 라이트 muted `rgb(89,89,89)` ≠
  다크 `rgb(154,154,154)` · fg 라이트 `rgb(23,23,23)` ≠ 다크 `rgb(237,237,237)`. **두 모드를 다
  돌렸다** — 한 모드면 `A2-3 미평가`(FAIL)다.
- **C3·C4** — 실행체 단정 **57건 전건 통과**·exit 0. 5상태 라벨이 모드에 무관하고, 교정 카드
  위계가 라이트(라벨 17.93:1 대 이유 **7:1**)·다크(16.91:1 대 7.04:1) 양쪽에서 성립한다.
  ⚠️ **`F-1` 회귀 없음** — 1차수 `F-1` 은 다크 확정 전사문 **1.05:1** 이었고 이번 다크 최저값이
  **7.04:1** 이다. 대비 AA 는 라이트 15행·다크 15행 전건 통과(`[AA!]` 0건).
- **C5** `PASS` 2건 — 4 outcome 이 같은 `p[aria-live="polite"]` 에서 매번 바뀌며
  `PRONUNCIATION_BADGE` 와 등호 일치하고 sentinel 은 4회 전부 0건. ⚠️ **대조 ①이 오염됐다**
  (라운드트립 20,635 ms > 창 10,000 ms 를 우회로 성립시켰다) → `TASK-49`.
- **A4-2** 는 이 회차들에서 `BLOCKED` 였고 **실물 세션이 표본을 만들어 해소됐다**(`C3f`).

## 스크린샷 규약

5차 시도의 10장은 md5 가 전부 다르고 프레임 하단에 `STAMP <pathname> | <ISO 시각>` 띠가 있어
**세션 id 가 화면 안에** 남는다. 그 띠는 `main` **밖**이라 측정을 오염시키지 않는다
(`stampInsideMain: false`). 4차수 교훈 5 가 요구한 것이 처음으로 구조적으로 충족됐다.
⚠️ 이 회차 **밖**에서 바이트 동일 3건을 발견해 적어 두었다 — `c2-dark.png` ·
`c2-selftest-failure.png` · `c2-selftest2-failure.png` 가 md5 `b2c5daa5…` 로 셋 다 같다
(2026-09-06 생성 · 이 회차가 만든 파일이 아니라 원인을 조사하지 않았다).

## 이 회차들이 찾은 문서·계측 결함 — 전부 고쳤다

① P5 실패 시 재기동 주체가 문서에 없었다(절차 불능) → §2 에 규약. ② 기동 명령의
`--log-level warning` 이 P5 의 신원 확인과 모순이었다 → `info` + `/tmp/omy-backend.log`.
③ 한 회차로 두 어댑터 모드를 판정할 수 없다 → §2 에 규약(호출자가 모드를 명시). ④ A1-6 의
유도가 계측에 없었다 → `instrument.js` 에 `startedSessionId`. ⑤ fetch 캐시가 낡은 계측을
먹였고 sha256 대조가 잡았다 → §10-3 에 `{cache:'no-store'}`. ⑥ C5 에 실행체가 없다 → `TASK-49`.

---

# 8차 시도 — P8 렌더 · P7 재캡처 · N11 · P11

> HEAD **`0fdb975`** · 백엔드 pid **5506** · `VOICE_ADAPTER=stub` · `WORKER_ENABLED=false`
> (`ps -Eww` 로 확인) · **워커를 켜지 않았음** · 실물 호출 **0회** · 계측(`instrument.js`) 미사용.
> 프리플라이트 통과(P5 `pid 5506 · 기동 27:15 전 · 소스 34건 → 통과` · P1 `{"status":"ok"}` ·
> P6 `200` · P8 `pytest 0건`). `H-AT` ③-1 대응: 배경 프로세스를 `ps -axo pid,etime,command` 로
> 확인했고 **이 회차가 띄운 것은 0개**(CORS 서버 불필요 · 권한 스크립트는 즉시 종료).

| 항목 | 판정 | 근거 |
|---|---|---|
| **P8** 렌더 | **`PASS`** | `pronunciation_intonation` 카드가 다른 카테고리와 동일하게 렌더 |
| **P8** 기계 키 누출 | **`PASS`** | `an_as_a` 가 DOM **0건** — `api/results.py:95` 계약 지켜짐 |
| **P7** 재캡처 | **`PASS`** | 두 장 md5 서로 다름 |
| **N11** 마이크 거부 | **`PASS`** | `사유: microphone_permission_denied` + 음성 대조 성립 |
| **P11** 발음 복습 도달 | **구조적 관측 불가** | 그 화면이 프론트에 **없음**(FAIL 아님 — 기준선 고정) |

## P8 — `910404ab-b166-4d7e-95d7-eec867e408ba` 렌더

API 에서 유도한 기대값과 DOM 을 등호로 대조했음:

| 단정 | 관측 |
|---|---|
| `main` 첫 직계 `<p>` | `확정` (status `final`) |
| 접두 `원문:` / `교정문:` | **1개 / 1개** |
| 카드 수 · 카드 `<p>` 수 | **1** · **3** (`strongs` = `["원문:","교정문:",null]`) |
| 카드 본문 | `원문: an action plan` · `교정문: a action plan` |
| 라벨 없는 셋째 `<p>` == API `reason` | **`true`** (`「an」을 「a」로 발음했습니다 — 모음 앞에서는 an 을 씁니다.`) · 비어 있지 않음 |
| 화면 깨짐·빈 화면 | 없음 (`mainOuterHTML` 정상) |

**기계 키 누출 검사 — 3중으로 쟀고 전부 0**: `documentElement.innerHTML` 에 `an_as_a` **부재** ·
`body.innerText` 에 **부재** · leaf 요소 계수 **0**. `pattern_key`(`pronunciation_an_as_a`)와
`category`(`pronunciation_intonation`) 도 `innerText` 에 **부재**. → **결함 없음.**
⚠️ API 는 `target_form: "an_as_a"` 를 실제로 실어 보냈음(직접 확인) — 즉 **화면이 그것을 버리는
것**이고 「API 가 안 보내서 0건」이 아님. 그 구별이 이 단정의 판별력임.

## P7 — 4차수의 「바이트 동일」을 닫음

| 파일 | md5 · 크기 | 교정 수 |
|---|---|--:|
| `.harness/evidence/r8-p7-e0c5e580-2corr.png` | `ab278df4e8dbdcb429a334a45dda303a` · 146 kB | **2** |
| `.harness/evidence/r8-p7-6225ddaf-1corr.png` | `25947c1a23a33c219ce1fe9a13f9a721` · 97 kB | **1** |

**md5 가 서로 다름** → 「같은 캡처를 두 이름으로 저장」이 배제됨. 크기도 49 kB 차이임.
5차 시도의 **`STAMP` 띠**를 그대로 썼음 — `main` **밖**(`document.body`)에 붙여 측정 대상을
오염시키지 않았고 두 세션 모두 `stampInsideMain: false` 를 확인했으며 회차 끝에 지워
`stampRemoved: true` 를 확인했음. **`r8-p7-e0c5e580-2corr.png` 를 직접 열어 봤음** — 카드 2개
(`and present the project's details` · `go to office`)와 하단 노란 띠
`STAMP /results/e0c5e580-dfc0-4793-b02d-54cf4346c3c5 | 2026-09-08T23:33:57.625Z` 가 보였음.

## N11 — 마이크 권한 거부. ⚠️ CDP 명령 하나로는 부족했음

| 단계 | 관측 |
|---|---|
| **음성 대조**(거부 전) | `microphone_permission_denied` **부재** · `사유: ` `<p>` **0개** · `연결에 실패했습니다` **부재** · 버튼 `학습 시작` |
| CDP `Browser.setPermission` | ⛔ `audioCapture` → **`Invalid PermissionDescriptor name`**. `microphone` 으로 바꿔 `{}` 성공 |
| 클릭 후 | **권한 대화상자가 떴음** — `setPermission denied` 가 그것을 억제하지 못했음 |
| `dialog::dismiss` 뒤 | `사유: microphone_permission_denied` `<p>` **1개** · `연결에 실패했습니다.` **있음** · 버튼 `다시 시도` · URL 이 `/` 에 남음 |
| 권한 원복 | `Browser.resetPermissions` → `{}` |

**판정 `PASS`** — 거부 경로가 `microphone_permission_denied` 화면을 냈고 **음성 대조가 성립**했음
(거부하지 않은 회차에 그 문구가 없었음). 증거: `.harness/evidence/r8-n11-mic-denied.png`
(md5 `7877378d9d4b26744feb9c2be6ee85e0` — 위 두 장과도 다름).

⚠️ **절차에 남길 실측 둘**: ① `Browser.setPermission` 의 descriptor 이름은 **`microphone`** 이고
`audioCapture`(그쪽은 `Browser.grantPermissions` 의 `PermissionType`)가 아님 ② **`denied` 를
걸어도 대화상자가 뜸** — 그래서 `dialog::dismiss` 가 필요했음. §11 이 적어 둔
「계측을 걸지 않은 경로에서는 대화상자가 뜬다」와 일치하고, **CDP 거부만으로 대화상자를 건너뛸
수는 없었음.** ⛔ **`e0c5e580` 세션과 그 job 을 건드리지 않았음.**

## P11 — 「구조적 관측 불가」. 기준선으로 고정함

**재료는 DB 에 실재함**(읽기만 했음):

| 무엇 | 값 |
|---|---|
| 발음 패턴 | `pronunciation_an_as_a` · `pronunciation_intonation` · `frequency 2` · `next_review_at 2026-09-04 13:51:26+00`(**기한 지남**) |
| 발음 `review_tasks` | **1건** — `pending` · `task_type rephrase` · `review_stage 1` · `due_at 2026-09-04`(**기한 지남**) |
| `review_tasks` 카테고리 분포 | `article 6` · `preposition 3` · `verb_tense 2` · `word_order 2` · `business_expression 1` · **`pronunciation_intonation 1`** |

**그런데 그것을 보여줄 화면이 없음.** 프론트 라우트가 **2개뿐**임 —
`app/page.tsx` · `app/results/[sessionId]/page.tsx`(`find app -name page.tsx`). API 클라이언트도
`results` 와 `next-plan` **둘만** 호출함(`lib/api.ts`). 복습 과제 목록·히스토리 화면이 **0개**임.
→ **`FAIL` 이 아니라 「구조적 관측 불가」**. 소유자는 `TASK-3`·`TASK-10` 임.

⚠️ **곁가지로 하나 더 관측했음(화면 밖 사실이므로 판정에 넣지 않음)**: 화면이 생겨도 **계획
경로로는 도달하지 않음** — 최신 `session_plans` 의 `focus_pattern_ids` 가
`article_missing_before_noun` · `business_expression_verb_noun_collocation` **둘뿐**이고 기한이
지난 발음 패턴이 **빠져 있음.** idle 화면의 추천 이유 한 줄도 `a/an` 을 말하지만 그것은 그 두
문법 패턴에서 온 것임. **왜 빠졌는지는 백엔드 로직이고 이 회차 범위가 아님.**

## DB — 이 회차는 세션을 만들지 않았음. ⚠️ 그런데 baseline 대비 2개 표가 **줄었음**

**§8 정의 drift 쿼리 출력**:

```
select count(*) from harness_pattern_baseline b join error_patterns p on p.id = b.id
 where p.frequency <> b.frequency or p.last_seen_at is distinct from b.last_seen_at;
→ 0
```

| 표 (쿼리) | 회차 baseline | 회차 끝 |
|---|--:|--:|
| `learning_sessions` (`where user_id='0…001'`) | 15 | **14** |
| `error_patterns` (`where user_id='0…001'`) | 9 | 9 |
| `review_tasks` (전체) | 15 | 15 |
| `pronunciation_attempts` (전체) | 5 | **4** |

⛔ **줄어든 두 건은 내가 지운 것이 아님.** 이 회차는 **세션을 0건 만들었고**(창 안 세션 0 —
N11 거부 경로는 DB 에 세션을 만들지 않음) **`delete` 를 한 번도 돌리지 않았음.**
사라진 것을 특정했음: **7차 시도의 실물 2차 세션 `9664afd1-3747-4bc4-aaf2-94bb60dc7cfb` 가
0건**이고, 남은 `pronunciation_attempts` 4행은 전부 옛 세션(`bbfc3908`·`7b43ce56`)의 것임.
즉 **이 회차 창(23:33:03 이후) 안에서 다른 주체가 그 세션을 teardown 했음.**
⚠️ 그 세션은 브리프의 **보존 목록 6개에 없었으므로** 규약 위반은 아니나, 7차 브리프가
*"teardown 하지 마라"* 고 지시해 남긴 세션이었음 — **호출자가 알아야 할 사실이라 적음.**

**보존은 전부 지켜졌음**: 보존 세션 **6개 생존**(`C3f` 포함) · **`910404ab` 생존**(호출자 소유이므로
지우지 않았음) · **drift 0**.

## 내가 확인하지 못한 것

- **`9664afd1` 을 누가 왜 지웠는지** — 내 회차 밖이라 조사하지 않았음.
- **P11 의 계획 경로 누락 원인** — 백엔드 로직이고 범위 밖임.
- **P8 카드의 다크·라이트 대비** — 이 회차는 렌더 구조와 기계 키 누출만 쟀음(대비는 5차 시도가
  5상태에서 이미 쟀고 이 세션은 그 다섯에 없음).

---

# 9차 시도 — N6 · N13 · B-2. **세션 1건으로 합쳤음**

## ⛔ 보존할 세션 — `e6206514-fca4-4be1-b2fc-7c57a8c82e8c`

> `completed` · `2026-09-08 23:50:40.775476+00` → `23:51:28.656045+00` · **teardown 하지 않았음**
> (호출자 소유). 백엔드 pid **55492** · `VOICE_ADAPTER=nova` · `WORKER_ENABLED=false` ·
> `NOVA_ENDPOINTING_SENSITIVITY=LOW`(`app/backend/.env:27`) · HEAD **`0fdb975`**.
> 프리플라이트 통과(P5 `pid 55492 · 기동 03:56 전 · 소스 34건 → 통과`) · 계측 sha256 `cbc19fb6…`
> 일치(`{cache:'no-store'}`) · **워커 켜지 않았음** · `H-AT` ③-1 대응으로 배경 프로세스를
> `ps -axo pid,etime,command` 로 확인했음(CORS 서버 1개 → 회차 끝에 종료 · 8899 `000`).
> **브리프가 목표한 3세션을 1세션으로 줄였음** — `u1.wav` 1턴(B-2 · N13) 뒤 agent 발화 중
> `u2.wav` 를 끼워 barge-in(N6).
> 증거: `runs/2026-09-09-run-5-live/frames-e6206514.json` · `…/transcripts-repr-e6206514.txt`.

| 항목 | 판정 |
|---|---|
| **N6** ① 1초 안에 출력 중단 | **`PASS`** — **338 ms** |
| **N6** ② `INTERRUPTED` 통보 | **부분** — 앱 계층 `interrupted` 프레임 1건 확인 · **Nova 원본 `stopReason` 은 앱 경로에서 관측 불가** |
| **N6** ③ 클라이언트 오디오 큐 비움 | **`PASS`** — `stop()` **20회 동시 호출** + `when` 이 3.967 → **0** 으로 낙하 |
| **N13** endpointing 민감도 | **`BLOCKED`** — 필요한 필드가 앱 경로에 없음(아래) |
| **B-2** 대조군 | **`PASS`** — 전사문이 N5 기대와 등호 일치 · 발음 개입 **0건** |

## N6 — barge-in. 셋 중 둘 `PASS`, 하나 부분

`§5` 의 확장 지시 그대로 **`recv.audio` 가 늘기 시작한 시점**에 두 번째 `BufferSource` 를
`start()` 했음: barge-in **@31,169 ms**(agent audio **4건** 수신 후).

| 단정 | 관측 | 판정 |
|---|---|---|
| ① 1초 안에 출력 중단 | `interrupted` 프레임 **@31,507 ms** · 첫 `stop()` **@31,507 ms** → **barge-in 부터 338 ms** | **`PASS`**(< 1,000 ms) |
| ② `stopReason=INTERRUPTED` 통보 | 프론트가 받은 `interrupted` 프레임 **1건**. ⛔ Nova 원본 `stopReason` 문자열은 **프레임에 없고**(`ws.ts` 의 `interrupted` 는 payload 가 `type` 뿐) **백엔드 로그에도 0건**(`grep -c stopReason` → **0** · `INTERRUPTED` → **0**) | **부분** |
| ③ 오디오 큐 비움 | `stop()` 호출 **20회가 전부 `at: 31507`**(인자 없음) — `dropQueuedAudio()` 가 스케줄된 노드를 한꺼번에 멈춤. 그리고 `started.calls` 의 `when` 이 **3.967 → 0** 으로 떨어짐(`afterRecvAudio: 4` 지점) = `nextStartTime = 0` 의 효과 | **`PASS`** |

**계측 지점을 확정했음**: `stop` 소유자는 **`AudioScheduledSourceNode.prototype`**(§11-2 실측
재확인 — `AudioBufferSourceNode` 에는 없음). 그 후킹이 이 회차에 새로 더한 관측 지점이고
`when` 낙하가 **큐 비움의 독립 증거**임(계수만으로는 「멈췄다」와 「비웠다」를 못 가름).

⚠️ **`interrupted` 뒤에도 세션이 이어졌음** — 2턴이 정상 완주하고 `session_ended` 가 왔음
(`final` 4 · `audio` 106). 7차의 곁가지 관측(끼어들어도 죽지 않음)이 **의도된 barge-in 에서도
유지됨.**

## N13 — `BLOCKED`. ⛔ **`MEDIUM` 재기동 요청을 철회함**

**필요한 값이 앱 경로에 없음.** `nova.py:_offset_ms` 가 읽는 것은 **`inputAudioOffsetMs`** 하나이고
(직접 읽어 확인) N-1 이 「MEDIUM 에서 약 480 ms」의 근거로 쓴 **`inputAudioDetectionOffsetMs` 는
프레임에도 백엔드 로그에도 0건**(`grep -c` → 0). 즉 **감지 지연이 노출되지 않음.**

이 회차가 얻은 값(LOW):

| 무엇 | 값 |
|---|--:|
| `speech_start.offset_ms` | 0 · 3,880 |
| `speech_end.offset_ms` | **1,920** · 5,920 |
| `u1.wav` 길이 | **1,920 ms** — `speech_end - speech_start` 와 **정확히 같음** |
| `u1` 재생 → `speech_end` 프레임 도착(벽시계) | 2,846 ms |

⛔ **그 값은 발화 끝 오프셋이고 감지 지연이 아님.** 민감도를 바꿔도 발화 끝은 그대로이므로
**`MEDIUM` 으로 재기동해도 같은 이유로 못 잼** → **재기동 요청을 철회함.**
⚠️ **표본이 이미 흔들린 것도 함께 적음**: 같은 `u1.wav`·같은 `LOW` 에서 **7차 회차는
`speech_end.offset_ms` 가 2,520** 이었고 이번은 **1,920** 임. 두 값이 갈리므로 이 필드로
모드를 비교하면 **모드 차이와 회차 흔들림을 구별할 수 없음.**
→ 닫으려면 **백엔드가 `inputAudioDetectionOffsetMs` 를 실어 보내야** 하거나
`spike_nova_protocol.py`(Nova 직접 왕복)로 재야 함. **후자는 앱 경로가 아님.** 둘 다 이 회차
범위 밖이므로 고치지 않았음.

## B-2 — 대조군. 기준선 유지

| 단정 | 관측 |
|---|---|
| 전사문이 실제 발화와 일치 | seq1 = `'i usually go to gym after work.'` — N5 기대(`u1.wav` = "I usually go to gym after work.")와 **등호 일치** (`== True`) |
| 발음 개입 | agent 2턴 전사문에 `pronounc`·`sound`·`발음`·`accent` **0건** |
| 저장·job | `utterances` 4행(user 2 · agent 2) · `analyze_utterance` **2건 `pending`**(사용자 발화 수와 일치) · `plan_next_session` 1건 |

**「학습 반영 부재」 기준선이 유지됨** — 발음 개입이 없는 일반 대화에서 3차수 N5 와 같은 결과임.
⚠️ **agent 문구는 회차마다 다름**(비결정적): 7차의 같은 WAV 응답은
`That's good to hear. Can you tell me what you did yesterday? …` 였고 이번은
`That's a good habit! Can you tell me what you want to do this weekend?` 임. **부류는 같음**
(내용 질문 + 시범 요청) — **문구 등호로 대조하지 않았고**, 대조한 것은 **사용자 전사문**과
**발음 언급 부재**임.

## DB — teardown 하지 않았음 · drift 0

**§8 정의 drift 쿼리 출력 = `0`**
(`select count(*) from harness_pattern_baseline b join error_patterns p on p.id = b.id where p.frequency <> b.frequency or p.last_seen_at is distinct from b.last_seen_at`)

| 표 | 회차 baseline | 회차 후 (**그대로 둠**) |
|---|--:|--:|
| `learning_sessions` (`where user_id='0…001'`) | 13 | **14** (+1 = 이 세션) |
| `error_occurrences` (전체) | 24 | **24** (워커 꺼짐 → 분석 미실행) |

**보존 세션 6개 생존.** 프로세스: pid **55492** 동일 · 플래그 동일 · `/health` `{"status":"ok"}`.
⚠️ 회차 시작 시 baseline 이 브리프가 알려 준 값(`learning_sessions` 13 · `error_occurrences` 24 ·
drift 0 · 보존 6)과 **일치했음** — 사전 통보가 대조를 성립시켰음.

## 내가 확인하지 못한 것

- **Nova 원본 `stopReason=INTERRUPTED`** — 앱 경로가 그 값을 버림. `spike_nova_protocol.py` 가
  소유(N-1 기록에 `stopReason=END_TURN` 이 있음).
- **N13 의 모드 간 비교** — 위 이유로 `LOW` 값조차 회차마다 흔들림.
- **`interrupted` 뒤 큐가 「완전히」 비었는지** — `stop()` 20회와 `when` 낙하로 **비움 동작**은
  확인했으나 **잔여 노드 0개**를 직접 세지는 못했음(`scheduled` Set 은 앱 내부 상태임).
