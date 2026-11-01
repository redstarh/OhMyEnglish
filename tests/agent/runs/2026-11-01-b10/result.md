# 회차 2026-11-01-b10 — 영어 음성 명령 실물 확인 · 결과 화면의 한국어 (`TASK-300`)

HEAD `5944ae7` 임. 회차 시작(10:36)과 끝(11:23) 모두 같았음. `app/backend/app` · `app/frontend/app` · `app/frontend/lib` 에서 10:35 이후 바뀐 소스는 0건임.

## 먼저 알릴 것

1. 이 회차는 전용 런처 없이 서브에이전트로 돌았음. 그래서 OS 샌드박스 보장이 없었고 정의 §1-1 규칙만 지켰음. 쓰기는 이 폴더와 `/private/tmp/_b10-*` 뿐이었고 임시 파일은 지웠음. 커밋·원장 갱신·결함 등록은 호출자 지시에 따라 하지 않았음.
2. 공유 판정: :3000 과 :8002 는 남의 것이므로 재기동·종료하지 않았음. 회차 중 10:55~11:14 에 중단이 있었음. 그 사이 호출자가 백엔드를 사용자 스택으로 바꿨다가 다시 테스트 스택으로 돌렸음(새 pid 기동 11:14:39 · `VOICE_ADAPTER=nova` · DB `ohmyenglish_course_paid`). 따라서 S1~S4 는 10:35:52 기동판에서, S5·S6 는 11:14:39 기동판에서 잼. 코드는 둘 다 `5944ae7` 임.
3. S4 드라이버는 중단 때 결과 대기 도중 종료됐음. 그래서 `SESSION-s4.json` 이 없음. 프레임(`frames-s4.jsonl`)과 DB 행은 남아 있음. S4 세션은 4분 뒤 드라이버의 「End lesson」 버튼으로 닫혔음.
4. 입력은 macOS `say`(영어 Samantha · 한국어 Yuna) 합성음임. 헤드리스 Chrome 156 의 가짜 장치로 넣었음. 사람 목소리와 물리 마이크로는 재지 않았음.
5. 전 백엔드 프로세스(82922)의 로그 끝에 Claude 분석 `AccessDeniedException`(IAM user)이 있었음. 이번 기동판들에서는 분석 34건이 모두 `done` 이었음.

## 실제 세션 수 — 6개 (상한 6)

격리 DB `learning_sessions` 가 24 → 30 이 됐음(`paiddb-start.json` · `paiddb-end.json`).

| 세션 | id | 입력 | 끝난 방식 |
|---|---|---|---|
| S1 | `5b998a1d` | 영어 오류 3문장 → "Hey, end the lesson." → "Yes." | 음성 종료 69초 |
| S2 | `786f0e90` | 영어 오류 2문장 → 「헤이, 학습 종료.」 → 「네.」 | 음성 종료 55초 |
| S3 | `fa3bd93a` | "Hey, pause the lesson." → 정지 중 발화 → "Hey, continue the lesson." → 종료 + "Yes." | 음성 종료 93초 |
| S4 | `7a18a111` | 「헤이, 일시 정지.」 → 정지 중 발화 → 「헤이, 학습 계속.」 → 「헤이, 학습 종료.」 → 「네.」 | 버튼 종료(4분) |
| S5 | `645c7116` | S3 와 같은 파일(재현) | 음성 종료 92초 |
| S6 | `c7482f05` | S4 와 같은 파일(재현) | 버튼 종료 150초 |

## 인식 대상 명령 (코드에서 정리함)

- 정본은 `app/backend/app/models/voice_command.py` 임. 명령은 `end` · `show_report` · `next_question` · `start_additional` · `pause` · `resume` 여섯이고 확인을 타는 것은 `end`·`start_additional` 둘임.
- 표지(wake word)는 앱이 판정함. 공백·문장부호를 지우고 맨 앞이 `ohmyenglish` · `오마이잉글리시` · `오마이잉글리쉬` · `hey` · `헤이` · `해이` 중 하나여야 함.
- 어떤 명령인지는 Nova 가 `request_session_control` tool 로 고름(`audio_gateway/nova.py` 규칙 12~14). 확인 답에는 표지가 필요 없음. `requested` 뒤의 사용자 발화 1건을 확인 답(`command_confirmation`)으로 분류함.
- 근거 수단은 세 가지임. 서버 WS 프레임(`voice_command` · `voice_command_ignored` · `session_ended`), 덮개 안내 문구, DB `utterances.utterance_type` 임. 관측 수단은 매 세션에서 `final` 프레임과 S2 의 `end requested` 를 실제로 잡았음. 그래서 「프레임 0건」을 관측 불능이 아니라 실제 부재로 읽었음.

## 명령별 결과

| 명령 | 언어 | 결과 | 근거 |
|---|---|---|---|
| 종료 + 확인 | 영어 "Hey, end the lesson." → "Yes." | 세션 종료 3/3 · 단 `requested` 단계 0/3 | S1·S3·S5: `final voice_command "hey, end the lesson."` → 코치 "Do you want to end today's session?" → `final learning "yes."` → `voice_command end confirmed` → `session_ended`. 확인 대기 안내는 0/3 표시됨(`overlayNotes`) |
| 종료 + 확인 | 한국어 「헤이, 학습 종료.」 → 「네.」 | 1/3 | S2: `"헤이! 학습 종료!"`(voice_command) → `end requested` → 안내 「Do you want to end? Say "네"…」 → `"네!"`(command_confirmation) → `end confirmed` → 종료. S4: 전사가 `"hey, how's it going?"` 이었고 tool 이 없었음. S6: 전사가 `"hey, i have a question."` 이었고 tool 이 없었음 |
| 일시 정지 | 영어 "Hey, pause the lesson." | 2/2 | S3·S5: `pause requested` · 안내 「Paused. I'm not recording now. Say "헤이, 학습 계속"…」 · 정지 중 학습 발화는 저장 0건(DB 에 없음) |
| 일시 정지 | 한국어 「헤이, 일시 정지.」 | 0/2 | S4: 전사가 `"hey, you should change it."` 이었고 모델이 **`end requested`** 를 불렀음(다른 명령). S6: 전사가 `"hey, it's changji."` 이었고 tool 이 없었음 |
| 계속 | 영어 "Hey, continue the lesson." | 서버 재개 2/2 · 화면 1/2 | S3: **`resume confirmed`** 로 와서 화면에 「Paused」 가 남음(D2). S5: `resume requested` 이고 안내가 지워짐. 두 번 모두 다음 학습 발화가 `learning` 으로 저장됐음 |
| 계속 | 한국어 「헤이, 학습 계속.」 | 0/2 | S4: `"hey, how's it going?"` · S6: `"hey, i'm still here. what's up?"`. 둘 다 tool 이 없었음 |

요약: 영어 명령은 시험한 셋(종료·정지·계속)이 모두 서버 동작을 일으켰음(7/7). 한국어 명령은 6번 중 1번만 인식됐음. 실패 5번은 모두 Nova ASR 이 한국어를 영어 문장으로 적은 것임. 다만 영어 쪽에서 단계(`requested`/`confirmed`) 갈림이 화면 결함 둘(D1·D2)을 만들었음.

## 결과 화면 (`/results/<id>`) 관찰

스크린샷:
- `evidence/RESULTS-s1-reload.png` — 교정 카드 2 · Today's lesson · Today's mistakes 4 (새로 고친 뒤)
- `evidence/RESULTS-s5.png` — 가장 완전한 판: 「Today's drill was shorter than planned.」 · 교정 2 · 총평 · 오늘의 실수 5
- `evidence/SESSION-s2-results-noreload.png` · `SESSION-s3-results-noreload.png` — 새로 고치지 않은 결과 화면. 총평 칸이 없음(D3)
- 세션 덮개: `SESSION-s2-1-voice_command-end-requested.png`(확인 대기 안내) · `SESSION-s3-2-voice_command-resume-confirmed.png`(재개 뒤에도 Paused)

영어 UI 문구: `Your results` · `Done`/`Checking...` · `You finished today — N scenes` · `You said:` · `Better:` · `Today's lesson` · `You did well` · `Work on next` · `You said` · `Today's mistakes` · `N times today` · `Practice this` · `← Home` · `History →`.

남은 한국어 — S5 화면의 한글 줄 11개를 API 필드와 하나씩 대조했음. **11/11 이 백엔드 값이고 UI 상수에서 온 한국어는 0줄임.**

| 화면 자리 | 출처 필드 | 예 |
|---|---|---|
| 교정 카드의 이유 줄 | `/api/sessions/<id>/results` `corrections[].reason` | 「work는 일반동사이므로 am과 함께 쓰지 않고 'I work at ~'이라고 말합니다.」 |
| Today's lesson → You did well | `summary.went_well[]` | 「자기 직업과 일하는 곳을 영어로 먼저 꺼내 말하며…」 |
| Today's lesson → Work on next | `summary.weak_points[].point` (`quote` 는 영어 원문) | 「과거 시점을 나타내는 말(yesterday)을 쓰면서도…」 |
| Today's mistakes 의 이유 줄 | `/api/daily-summary` `patterns[].example.reason` | 「we는 복수 주어이므로 has가 아니라 have를 씁니다.」 |

- `target_form` 의 한국어 자리 표시(예: `Yesterday + 주어 + 동사 과거형` · `주어 + 현재형 동사 (be동사 없이) / I work at + 직장`)는 두 API 에 실려 있음. 하지만 결과 화면은 그 필드를 그리지 않으므로 이 화면에서는 보이지 않았음. 설계서 §6 의 예상 2 는 이 화면 기준으로는 해당 없음. `Practice this` 이동 뒤 화면은 보지 않았음.
- 세션 덮개(결과 화면 밖)에는 UI 상수의 한국어가 실제로 보였음. 「Say "헤이, 학습 계속" to go on.」(S3·S5)과 「Say "네" to end.」(S2)임.
- 관찰: S5 교정의 `Better: i met my manager` 는 소문자로 시작함. Today's mistakes 에 같은 오류 `i am software tester` 가 교정이 다른 두 카드(`I am a…` · `I'm a…`)로 나뉘어 나옴. S5 총평의 You did well 이 음성 명령 사용(「수업을 멈추고… 영어로 직접 요청해서」)을 학습 성과로 칭찬함.

## 새 결함 (재현 절차 · 등록하지 않음 — 제안만)

### D1. 영어 종료 명령에서 확인 대기 안내가 뜨지 않고 확인 답 「yes.」가 학습 발화로 저장·분석됨 — 3/3
- 재현: 대화 세션 시작 → "Hey, end the lesson." → 코치가 "Do you want to end today's session?" 라고 물음 → "Yes."
- 기대: `voice_command end requested` 가 오고 확인 대기 안내가 보이며, "yes." 가 `command_confirmation` 으로 저장됨(한국어 S2 가 그렇게 동작함)
- 실제: `requested` 프레임 0건이고 곧바로 `end confirmed` 가 옴. 안내 0회. "yes." 는 `utterance_type=learning` 임(S1 9번 · S3 12번 · S5 12번). 그래서 분석 job 에 들어갔음. S5 의 "yes." job `122ff508` 은 1차 출력이 검증에서 거부되어(`extra_forbidden`) 2회 시도됐음.
- 증거: `evidence/frames-s1.jsonl` · `frames-s3.jsonl` · `frames-s5.jsonl` · `SESSION-s1.json` 의 `overlayNotes: []`
- 제안: `confirmed` 가 `requested` 없이 오는 경우를 앱이 판정해야 함. 그 직전의 사용자 final 을 확인 답으로 재분류하거나 분석 대상에서 빼는 방안이 있음. 확인 절차(결정 102 ③)가 앱에 관측되지 않는 점도 함께 봐야 함 — 이번에는 코치가 말로 물었으므로 실제 확인은 있었음.

### D2. 영어 재개가 `confirmed` 단계로 오면 화면이 「Paused」를 계속 보임 — 1/2(간헐)
- 재현: "Hey, pause the lesson." → 10초 → "Hey, continue the lesson."
- 실제(S3): `resume confirmed` 를 받았음. 서버는 재개해서 다음 발화 "yesterday i go…" 를 `learning` 으로 저장했음. 하지만 화면은 상단 안내 「Paused. I'm not recording now…」와 하단 「Paused」를 세션 끝까지 유지했음. 프런트 `page.tsx` 는 `pause`/`resume` 을 `stage === "requested"` 일 때만 반영함. 서버 `audio_gateway/session.py` 의 제어 처리부는 `PAUSE_COMMANDS` 이면 단계와 무관하게 `_apply_pause` 를 부름.
- S5 에서는 `resume requested` 로 와서 정상이었음.
- 증거: `evidence/SESSION-s3-2-voice_command-resume-confirmed.png` · `frames-s3.jsonl` · `SESSION-s3.json` `overlayNotes`
- 제안: 화면과 서버가 같은 규칙(단계 무관)으로 정지 상태를 옮겨야 함.

### D3. 결과 화면이 총평(Today's lesson)을 새로 고치기 전까지 보이지 않음 — 2/3(시점 의존)
- 재현: 세션을 음성으로 끝냄 → 자동 이동한 결과 화면을 새로 고치지 않고 50초 봄
- 실제: S2·S3 에서 착지 때 status 는 `final`(S3 는 `analyzing` → 곧 `final`)이었고 화면은 폴링을 멈췄음. API 의 `summary` 는 착지 후 15초(S2)·18초(S3)부터 있었음. 하지만 화면에는 48초까지 끝내 나타나지 않았음. S5 는 분석이 15초 걸려 폴링이 이어졌으므로 나타났음. S1 은 요약 기록이 종료 18초 뒤(01:43:46 UTC)이고 분석 완료는 1초 뒤(01:43:29)였음.
- 원인 후보(미확정): `shouldKeepPolling` 은 `final` 에서 멈추고, 총평은 `summarize_session` job 이 따로 씀(`services/results.py` 주석 `TASK-62`).
- 증거: `evidence/SESSION-s2.json` · `SESSION-s3.json` 의 `summaryWatchNoReload`(각 행 = [초, 화면에 있음, API 에 있음, status])
- 제안: 총평이 비어 있는 동안은 폴링을 이어 가야 함.

### D4. 확인 질문 뒤 학습자가 확인하지 않고 말하면 그 학습 발화가 확인 답으로 저장되어 분석에서 빠짐 — 1/1
- 재현(S4): 「헤이, 일시 정지.」가 "hey, you should change it." 으로 전사됨 → 모델이 `end requested` 를 부르고 "Do you want to end today's session?" 라고 물음 → 학습자가 "yesterday i go to the office and i meet my manager." 라고 말함
- 실제: 그 문장이 `command_confirmation` 으로 저장됐음(S4 5번). 모델은 `cancelled` 를 부르지 않았음. 확인 대기 안내 「Do you want to end?…」는 화면에 남았음(`SESSION-s4-1-voice_command-end-requested.png`).
- 제안: 확인 답 분류에 최소 조건(짧은 긍정·부정)을 둘지 검토해야 함. 오인식된 명령을 물리는 경로도 검토해야 함.

## 관찰 (결함으로 올리지 않음)

- 한국어 명령의 ASR: S4·S6 에서 Yuna 합성음 「헤이, …」 5개가 모두 영어 문장으로 전사됐음. S2 에서는 같은 목소리의 「헤이, 학습 종료」·「네」가 한글로 정확히 전사됐음. 그 차이의 원인은 가리지 못했음. 표지 「hey」는 매번 살아서 그 발화들이 `voice_command` 로 저장되어 분석에서 빠졌음(결정 116 이 알고 받은 대가와 같은 기전).
- 정지 중 코치 발화: S3(42초)·S5(47초) 모두 정지 중 학습 발화 뒤에 코치가 말했음. S5 에서는 그 발화를 인용하며 교정했음. 프롬프트 규칙 13 은 정지 중 침묵을 요구함. 저장은 0건으로 계약대로였음.
- 코치와 화면의 안내 불일치: 코치는 "Please say "yes" to confirm."(S2·S5)이라 말하고 화면은 「Say "네" to end.」라고 보임. S2 는 「네」로, S5 는 "yes" 로 모두 종료됐음.
- 드릴 미달 경고 「드릴 exchange 미달 — 관측 1건 / 기대 16건」이 결과 조회 폴링마다 반복 기록됨(S2). 짧은 시험 세션이라 미달 자체는 예상된 일임.

## AC3 에 대한 근거

영어 명령은 시험한 세 가지가 모두 서버 동작을 일으켰음. 같은 조건의 한국어는 1/6 이었음. 따라서 화면 안내를 영어 명령으로 바꾸는 근거는 이 회차로 생겼음. 단, D1·D2 의 단계 갈림이 있으므로 안내만 바꾸면 영어 종료의 확인 대기 안내는 여전히 뜨지 않음. 문구 변경은 대상 프로젝트의 몫이고 이 회차에서는 하지 않았음.

## dev DB 대조 (AC4)

| | learning_sessions | utterances | course_day_progress | course_attempts |
|---|---|---|---|---|
| 회차 시작 10:36 (`devdb-start.json`) | 18 | 144 | 0 | 0 |
| 재개 기준선(호출자 통보 · 사용자가 11:10 에 세션 1개 시작) | 19 | 144 | 0 | 0 |
| 회차 끝 11:22 (`devdb-end.json`) | 19 | 144 | 0 | 0 |

끝 값이 재개 기준선과 같음. 18 → 19 는 사용자의 11:10 세션임(`sessions_max_started 02:10:38 UTC`). 이 회차는 dev DB 에 읽기 전용 연결(`default_transaction_read_only = on`)만 썼음.

## 만든 데이터 (격리 DB · 남겨 둠)

- `learning_sessions` +6 · `utterances` 120 → 203 · 분석 job 34건 모두 `done` · `llm_calls` 5 → 46
- 정리: Chrome 은 모두 `TaskStop` 으로 종료했고 :9337 은 비어 있음. `/private/tmp/_b10-*` 는 지웠음. :3000·:8002 는 그대로임.

## 파일

- 드라이버: `session.mjs` · `results.mjs` · `lib.mjs` · `chrome.sh` · `db.py` · `compose.py` · `synth.sh`
- 음성: `audio/raw-*.wav`(조각 12) · `audio/in-s*.wav`(입력 4) · 배치는 `evidence/audio-compose.txt`
- 증거: `evidence/frames-s*.jsonl`(서버 프레임 · 오디오 제외) · `SESSION-s*.json` · `results-api-s*.json` · `RESULTS-*.png/json` · `daily-summary-end.json`

## 덧붙임 (작업 세션 · 2026-11-01)

- 입력 음성 `audio/*.wav` 는 저장소에 넣지 않았음(합계가 크고 `synth.sh`·`compose.py` 로 다시 만들 수 있음). 지운 파일의 sha256 은 아래와 같음.

    75e0aa2978f922874bc3b53048e4a05a2ef498cbdb29498a77dc48c5c8bf1b77  audio/in-s1-en-end.wav
    6b4ccee78be0460497577fe8e9fadcd384367cdeafa411d47d7437c57b0ada91  audio/in-s2-ko-end.wav
    5ed2ac968f4a9379d7c2aaa4128ace5dd8918cc958b47c932ba22213571a90b4  audio/in-s3-en-pause.wav
    8732191f12ab6db8e01a1394e2b2b5a68fc48fe2b4947c8f629fd75a7bfa99b8  audio/in-s4-ko-pause.wav
    d571dcb16144ecc913981e5ff33f283a9e05d261b03f48f959592680b7616f0b  audio/raw-cmdend.wav
    2a7317a545c80f4a3775c129116b4dcd85550de29d442e06b3cacc0bccbd09ba  audio/raw-cmdpause.wav
    1efbb7c0de142d484667ee0ae537f9048ec032d7b67a733479f93e891cdf4c45  audio/raw-cmdresume.wav
    6b6cdda2dad0f4784e437c268b6655d01233f8471837232e95b3bf9208b6f551  audio/raw-e1.wav
    6c7e4615b0bb7d9e0a8ce86310a1d0a7e933543befc19d8c134362a10af28692  audio/raw-e2.wav
    51c9a2cb2a635233582f25c780484adb1bae82a90995a2a7e7d84bd217a6ad23  audio/raw-e3.wav
    b0bb958e5bb7d7593c3aa3f42abec65832cdb75be8b2924f8b275ada62f84d43  audio/raw-e4.wav
    013dac0cf7057edaaa94dc83b679ea1039be96380e7c644cc48392be4964e354  audio/raw-koend.wav
    4e7282f588f08ee99585cbf364d0e7adea165c1d588efccce730c69a010545b2  audio/raw-kopause.wav
    9586d839c83f131943a6fefa2ea9fbf3b7774fa449de2e555efa594842dfa2e0  audio/raw-koresume.wav
    1a69fdf41946072857935cefc67431dee9cdc08900e0b736f07c6dcdfc798a4d  audio/raw-koyes.wav
    b9220ca4f8e7a1dbc6f188aec3232dd3760c52fe6d2c802bb22124331f980fd9  audio/raw-yes.wav
