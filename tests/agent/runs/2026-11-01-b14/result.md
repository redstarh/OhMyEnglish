# 회차 2026-11-01-b14 — 음성 종료 확인 절차 실제 Nova 확인 (`TASK-303` AC3)

HEAD 는 `0b32ea9` 임. 회차 시작(05:08 UTC)과 끝(05:47 UTC) 모두 같았음.
`app/backend/app` · `app/frontend/{app,lib,components}` 에서 14:05 KST 이후 바뀐 소스는 0건임.
시험 서버(pid 51493)는 14:07:22 KST 에 기동했음. 그 시각은 확인 대상 커밋 `f33ec27`(13:13) · `4dc472c`(13:23) 뒤임.

## 먼저 알릴 것

1. 이 회차는 전용 런처 없이 서브에이전트로 돌았음. 그래서 OS 샌드박스 보장이 없었고 정의 §1-1 규칙만 지켰음. 쓰기는 이 폴더와 `/private/tmp/_b14-*` 뿐이었고 임시 파일은 지웠음.
2. 호출자 지시에 따라 커밋·원장 갱신·결함 등록·서버 재기동을 하지 않았음.
3. 공유 판정: :8002 와 :3000 은 남의 것이므로 건드리지 않았음. 회차 중 다른 클라이언트가 :8002 에 `POST /api/course/days/1/progress` 를 계속 보냈음(서버 로그). 이 회차 판정에는 영향이 없음.
4. 세션 입구가 b10 과 다름. `TASK-304` 뒤 홈의 `start-session`(Start speaking)은 코치 세션이 아니라 문장 연습을 엶(`app/page.tsx` 주석). 그래서 More practice 의 `practice-free_talk`(`source=additional`)로 코치 음성 세션을 열었음.
5. 화면 알림은 b10 의 `session-overlay` 가 없어져 `session-panel` 안의 `p[aria-live]` 로 읽었음(`app/SessionChat.tsx` 의 `Notice`).
6. 입력은 macOS `say`(Samantha) 합성음이고 헤드리스 Chrome 의 가짜 장치로 넣었음. 사람 목소리와 물리 마이크로는 재지 않았음.

## 입력 설계 — 「Yes.」를 두 번 둔 이유

`_hold_unrequested_confirmation` 은 요청 없이 온 `confirmed` 를 실행하지 않음. 대신 화면에 `requested` 를 보내고 모델에 `confirmation_required` 를 돌려줌. b10 에서 모델은 3/3 로 말로만 묻고 「Yes.」 뒤에 바로 `confirmed` 를 불렀음. 그래서 수정판에서는 첫 「Yes.」가 보류되고 코치가 다시 물을 것으로 봤음. 따라서 S1·S2 입력에 「Yes.」를 14초 간격으로 두 번 넣었음. 배치는 `evidence/audio-compose.txt` 에 있음.

| 입력 | 배치(초) |
|---|---|
| `in-end2yes.wav` (S1·S2) | e1 9.0 · e2 23.9 · "Hey, end the lesson." 39.1 · "Yes." 50.4 · "Yes." 64.9 |
| `in-lapse.wav` (S3) | e1 9.0 · "Hey, end the lesson." 23.9 · e4 37.2 · e3 54.7 · 80초에 End lesson 버튼 |

## 실제 세션 — 3개 (상한 5)

| 세션 | id | 입력 | 끝난 방식 | 양성 대조(관측 수단 동작) |
|---|---|---|---|---|
| S1 | `ef4ed5ea` | `in-end2yes.wav` | 음성 종료 68.9초 | `final` 학습자 5 · 코치 4 수신 · 오디오 프레임 351 수신 |
| S2 | `35183362` | `in-end2yes.wav`(재현) | 음성 종료 68.9초 | `final` 학습자 5 · 코치 4 수신 · 오디오 프레임 371 수신 |
| S3 | `9feb8af1` | `in-lapse.wav` | 버튼 종료 81.6초 | `final` 학습자 4 · 코치 4 수신 · 같은 수단이 `end requested` 를 잡은 뒤 `cancelled` 도 잡음 |

S4·S5 는 돌리지 않았음. S1~S3 의 판정 항목에 실패나 불확실이 없어 호출자의 재현 조건에 걸리지 않았음.

## 관측 순서

S1 (S2 도 같은 순서 · 초는 S1 기준, 괄호는 S2)

| 초 | 프레임 | 내용 |
|---|---|---|
| 43.05 (43.01) | `final` user `voice_command` | "hey, end the lesson." |
| 45.86 (44.10) | `final` agent | "Do you want to end today's session? …" — tool 없이 말로 물음 |
| 53.46 (53.44) | `final` user `learning` | "yes." |
| 54.03 (54.04) | `voice_command end requested` | 요청 없는 `confirmed` 를 서버가 보류해 보낸 프레임. 로그 「요청 없이 온 확정 'end' 을 실행하지 않고 확인 대기로 받았다」 |
| 56.53 (55.96) | `final` agent | "I need your confirmation again. Do you want to end today's session? …" |
| 68.00 (67.92) | `final` user `learning` | "yes." |
| 68.59 (68.54) | `voice_command end confirmed` | |
| 68.93 (68.87) | `session_ended` | 결과 화면으로 이동함 |

S3

| 초 | 프레임 | 내용 |
|---|---|---|
| 26.52 | `final` user `voice_command` | "hey, end the lesson." |
| 27.10 | `voice_command end requested` | 이번에는 모델이 직접 `requested` 를 부름 |
| 28.75 | `final` agent | "Do you want to end today's session? Please say yes or no." |
| 41.15 | `final` user `learning` | "last week i finished the test report and i sent it to my teacher." (e4) |
| 44.04 | `final` agent | "Good! You said the sentence correctly. …" — tool 없음 |
| 58.68 | `voice_command end cancelled` | e3 의 `final` 과 같은 순간. 로그 「확인 대기 'end' 이 답을 받지 못하고 지나갔다」 |
| 58.70 | `final` user `learning` | "my manager say the project is late, so we has a meeting." (e3) |
| 61.81 | `final` agent | e3 교정 |
| 81.60 | `session_ended` | 80초에 End lesson 버튼으로 닫음 |

## 판정

| # | 항목 | S1 | S2 | S3 | 근거 |
|---|---|---|---|---|---|
| ① | `end requested` 가 `confirmed` 보다 먼저 옴 | 통과 | 통과 | — | `frames-s1.jsonl` · `frames-s2.jsonl` (54.0초 requested → 68.6초 confirmed) · 서버 로그 `backend-log-s1s2.txt` |
| ② | 확인 대기 안내가 화면에 뜸 | 통과 | 통과 | 통과 | DOM `overlayNotes` · `shotNotes`(「Do you want to end? Say "Yes." to end. It has not ended yet.」) · 스크린샷 `SESSION-s{1,2,3}-1-voice_command-end-requested.png` |
| ③ | 코치가 확인을 물음 | 통과 | 통과 | 통과 | 코치 `final` 2회(S1·S2: 처음 질문 + 「I need your confirmation again」) · 1회(S3) |
| ④ | `end confirmed` → `session_ended` | 통과 | 통과 | — | 프레임 · `learning_sessions.status=completed` · 화면 경로 `/results/<id>` |
| ⑤ | 「yes.」 가 `command_confirmation` 이고 분석 job 없음 | 통과 | 통과 | — | `db-s1-utterances.json` · `db-s2-utterances.json`: 7번·9번 「yes.」 모두 `command_confirmation` · job 0건. 프레임에는 `learning` 으로 왔음(저장 뒤 고쳐 씀 · 설계대로) |
| ⑥ | e1·e2 가 `learning` 이고 분석됨 | 통과 | 통과 | — | `db-s{1,2}-final-utterances.json`: 1번·3번 `learning` · `analyze_utterance done` · `results-api-s{1,2}-final.json`: status `final` · 교정 2건(`i go to the office` → `I went …` · `i am work at it company` → `I work at an IT company`). 분석 완료는 05:47 UTC 로 늦었음 — 관찰 O1 |
| S3-① | `end cancelled` 프레임 | — | — | 통과 | `frames-s3.jsonl` 58.68초 · 서버 로그 `backend-log-s3.txt` |
| S3-② | 그 뒤 확인 안내가 지워짐 | — | — | 통과 | DOM `overlayNotes` 의 58.5초 빈 값 · `shotNotes` 59.6초 `[]` · `noticesBeforeButton []` · 스크린샷 `SESSION-s3-2-voice_command-end-cancelled.png` |
| S3-③ | e4·e3 가 `learning` 이고 분석 job 이 걸림 | — | — | 통과 | `db-s3-final-utterances.json`: 1번·5번·7번 `learning` · 모두 `analyze_utterance done` · `results-api-s3-final.json`: 교정 2건(`we has a meeting` · `i meet my manager`). e4 는 전사가 이미 바르게 적혀 교정이 없음(O4) |
| S3-④ | 세션이 닫히지 않음 | — | — | 통과 | `cancelled` 뒤 `session_ended` 는 버튼을 누른 80초 뒤(81.6초)에만 옴 · `endedByServer false` · 스크린샷에서 대화가 이어짐 |

요약: 판정 18칸 가운데 통과 18 · 실패 0 · 불확실 0 임. ⑥은 05:37 에는 job 이 `pending` 이라 불확실이었음. 워커가 다시 돈 뒤 05:47 에 다시 재서 통과로 올렸음(`evidence/jobs-poll.txt`).

## 결함

이 회차에서 확인 대상(`TASK-303` 수정)의 새 결함은 찾지 못했음.

## 관찰 (결함으로 올리지 않음 · 판단은 호출자 몫)

### O1. 분석 워커가 job 1건에서 멈췄고 로그에 아무것도 남기지 않음
- 실측: 격리 DB 에 02:47 UTC 이후의 job 이 쌓여 있었음(회차 시작 무렵 `pending` 241건). 워커는 서버 기동(05:07:23) 뒤 10분간 112건을 오래된 순서로 처리했음.
- 05:27:32 에 `analyze_utterance` job `acca56b0` 를 잠근 뒤로는 job 을 하나도 잠그지 않았음(05:34:35 측정 · `running` 1 · `pending` 126). 그 job 의 `llm_calls` 행은 없고 마지막 analysis 호출 기록은 05:27:32.044 임.
- `BEDROCK_READ_TIMEOUT` 은 120초이지만 그보다 오래 `running` 이었음. 서버 로그에는 그 사이 경고·예외가 한 줄도 없음.
- 워커는 동시성 1의 단일 루프임(`workers/analysis_worker.py` 머리말). 그래서 호출 1건이 끝나지 않으면 대기열 전체가 멈춤. lease 만료 회수도 같은 루프가 하므로 이 경우에는 동작하지 않음.
- 그 job 은 05:36:03 측정에서 `done` 이었고 워커가 다시 돌았음(마지막 잠금 05:36:02). 정지는 약 8분 30초였음.
- 영향: 이 회차의 job 13건은 05:47:15 에야 모두 `done` 이 됐음(`evidence/jobs-poll.txt`). 결과 화면은 S1 에서 241초 동안 `analyzing` 이었음(`SESSION-s1.json`).
- 원인 미확정임. 재현과 원인 조사는 하지 않았음. 증거: `jobs-recent-locked-s1.json` · `jobs-rate-s1.json` · `jobs-poll.txt`.
- 제안: Bedrock 호출에 전체 시간 상한이 있는지 확인해야 함. 120초 읽기 상한은 청크 사이 간격에만 걸릴 수 있음. 멈춘 동안 로그가 비어 있는 것 자체도 진단을 막았음.

### O2. 보류 경로에서 학습자는 「Yes.」를 두 번 말해야 함
- S1·S2 에서 모델은 두 번 다 말로만 물었음(tool 없음). 첫 「Yes.」는 보류되어 `requested` 가 되었고 코치가 다시 물었음. 확인 안내가 처음 뜬 시점은 첫 「Yes.」 뒤(53.9초)임 — 코치가 처음 물은 시점(44~46초)에는 화면 안내가 없었음.
- 설계 의도(`_hold_unrequested_confirmation` 독스트링)와 같은 동작임. 사용자 경험으로는 확인을 두 번 받는 셈이므로 기록함.

### O3. 프레임의 `utterance_type` 은 고쳐 쓴 뒤의 값을 반영하지 않음
- 「yes.」 두 건이 프레임에는 `learning` 으로 왔고 DB 에는 `command_confirmation` 으로 남음. 설계서가 말한 「일단 learning 으로 저장하고 고쳐 씀」과 같음. 화면이 그 값을 쓰는 곳이 있다면 어긋날 수 있음. 이 회차에서는 화면 쪽 사용처를 찾지 않았음.

### O4. Nova ASR 이 e4 의 문법 오류를 고쳐 적음
- 입력 「Last week I finish the test report and I send it to my team.」이 「last week i finished the test report and i sent it to my teacher.」로 전사됐음. 코치는 「You said the sentence correctly」라고 답함. 오류가 전사 단계에서 사라져 분석 대상이 되지 못함. 이번 확인 대상과 무관함.

### 시험하지 않은 갈래
- 「보류로 세운 확인 대기」(S1·S2 의 경로)가 답 없이 만료되는 경우는 재지 않았음. S3 의 만료는 모델이 직접 `requested` 를 부른 경로였음. 두 경로가 같은 `_pending_confirmation` 을 쓰므로 같게 동작할 것으로 보이나 실측은 아님.

## DB 대조

| DB | 시점 | learning_sessions | utterances | course_attempts | analysis_jobs | 근거 |
|---|---|---|---|---|---|---|
| dev `ohmyenglish` | 시작 05:08 | 22 | 145 | 11 | 83 | `devdb-start.json` |
| dev `ohmyenglish` | 끝 05:47 | 22 | 145 | 11 | 83 | `devdb-end.json` |
| 격리 `ohmyenglish_course_paid` | 시작 05:08 | 99 | 617 | 7 | 492 | `paiddb-start.json` |
| 격리 `ohmyenglish_course_paid` | 끝 05:47 | 102 | 643 | 7 | 505 | `paiddb-end.json` |

- dev DB 는 끝 값이 시작 값과 같음. 이 회차는 dev DB 에 읽기 전용 연결(`default_transaction_read_only = on`)만 썼음.
- 격리 DB 증가분은 이 회차의 세 세션과 맞음. 세션 +3 · 발화 +26(S1 9 · S2 9 · S3 8) · job +13(S1 4 · S2 4 · S3 5) 임. `llm_calls` 62 → 410 은 대부분 회차 전부터 쌓인 job 을 워커가 처리한 몫임.
- 만든 데이터는 격리 DB 에 남겨 두었음.

## 정리

- Chrome 3개는 모두 `TaskStop` 으로 종료했고 :9337 은 비어 있음.
- `/private/tmp/_b14-*` 는 지웠음.
- :3000·:8002 는 그대로임.
- 회차 끝에 작업 원장에 미추적 파일 `backlog/tasks/task-310 - …-2026-11-01-14-07.md` 가 보였음. 이 회차가 만든 것이 아님.

## 파일

- 드라이버: `session.mjs` · `lib.mjs` · `chrome.sh` · `db.py` · `compose.py` · `synth.sh`(b10 에서 복사) · `q.sh`(세션별 DB 조회 · 새로 씀)
- b10 대비 바꾼 곳: `session.mjs` 의 입구(`practice-free_talk`) · 알림 관측 대상(`session-panel p[aria-live]`) · 스크린샷 시점 알림 기록(`shotNotes`) · 대기 시간 환경 변수(`WATCHMS` · `WAITMS`)
- 음성: `audio/raw-*.wav` · `audio/in-end2yes.wav` · `audio/in-lapse.wav` · 배치 `evidence/audio-compose.txt`
- 증거: `evidence/frames-s{1,2,3}.jsonl` · `SESSION-s{1,2,3}.json` · `run-s{1,2,3}.txt` · `db-s{1,2,3}-*.json`(세션 직후) · `db-s{1,2,3}-final-*.json` · `results-api-s{1,2,3}-final.json`(분석 완료 뒤) · `jobs-poll.txt` · `backend-log-s1s2.txt` · `backend-log-s3.txt` · 스크린샷 `SESSION-s*-*.png` · `RESULTS-s*.png`
