# 문장 연습 실시간 따라 말하기 표시 설계

> 2026-11-14 · `TASK-317` · 사용자 결정(2026-11-14): 말하는 동안 실시간으로 표시함("말이 끝난 직후"가 아님)
> 대상: 홈 「Today's practice」와 Day 화면이 함께 쓰는 `components/course/SentencePractice.tsx`

## §1. 문제와 원인

- 요구: 표시된 문장을 읽는 동안, 말하는 내용이 화면에 바로 나와야 함.
- 현재 흐름: TTS로 읽어 줌 → 고정된 창(`spokenMs + 1000ms`) 동안 녹음 → PCM 전체를 HTTP로 보냄 → Nova 전사 전용 스트림으로 전사 → 판정.
- 측정된 원인 셋(`TASK-317` 메모):
  - ① 학습자 final이 하나도 오지 않으면 `transcribe.py`의 `_TIMEOUT_S` 30초를 다 기다린 뒤 빈 값을 돌려줌. 시도 간격 약 37초가 이것으로 설명됨.
  - ② 녹음 창이 고정이라 늦게 읽거나 천천히 읽으면 문장 중간에서 잘림(`we walk where we`).
  - ③ 결과는 판정이 끝난 뒤에만 보이므로 말하는 동안 화면에 아무것도 없음.
- ⛔ 설계를 막는 사실: Nova의 사용자 전사에는 부분 전사가 없음(`nova.py` 첫머리 실측 3번 · `port.py` 첫머리). 코치 화면의 회색 부분 전사(`partialLine`)는 코치 발화의 SPECULATIVE 블록임. 학습자 발화는 끊어 읽는 자리마다 final 한 블록으로만 옴.
  - 그래서 Nova 스트림으로는 낱말이 말하는 대로 나오지 않음. 10낱말 안팎의 한 문장은 말을 멈춘 뒤 final 하나로 올 가능성이 큼.

## §2. 구조 선택지

| 안 | 내용 | 말하는 동안 글자 | Nova 호출 | 새 의존 | 복잡도 |
|---|---|---|---|---|---|
| A. Nova WS 스트리밍 | 새 `/ws/course/readback?key=` 엔드포인트. 마이크 프레임을 실시간으로 보내고 `speech_start`/`speech_end`와 학습자 final을 화면에 넘김. 서버가 final을 모아 판정함 | ✕ 끊어 읽는 자리마다만 나옴. 사이에는 「듣고 있어요」만 보임 | 시도마다 1회(지금과 같음) | 없음 | 중간 |
| B. 혼합 | 표시는 Web Speech, 판정은 A의 Nova 스트림 | ○ | 시도마다 1회 | 없음 | 높음 |
| **C. Web Speech 단독(권장)** | 브라우저 `SpeechRecognition`(`interimResults`)으로 표시하고 말 끝도 감지함. 확정 문장을 텍스트로 서버에 보내고, 서버는 `compare_readback`으로 판정해 저장함 | ○ | 0회 | 브라우저 기능 | 낮음 |
| D. Amazon Transcribe Streaming | 서버에서 진짜 부분 전사를 받음 | ○ | 0회(Transcribe 과금) | 새 AWS 서비스 · SigV4 자격증명 경로 · SDK | 높음 |

- A: 사용자가 고른 「실시간」을 채우지 못함. ⛔ `/ws/session`은 다시 쓰지 않음. 그 엔드포인트는 `learning_sessions` 행을 만들고 코치 지시문과 분석 job을 붙임.
- B: 화면에 두 전사기의 결과가 차례로 보임(회색 글자 다음에 다른 판정 문장). 비용과 구현이 둘 다 남음.
- D: 결정 131이 「새 AWS 서비스 의존과 자격증명 경로가 늘어남」으로 이미 물린 길임. Bedrock bearer 토큰은 Transcribe에 쓸 수 없음.
- **권장: C.** 근거는 셋임.
  - ① 실시간 요구를 채우는 가장 짧은 길임.
  - ② 이 칸은 이미 브라우저 음성 합성(`lib/speech.ts`)에 기대고 있음. 같은 계열의 기능임.
  - ③ 이 흐름에서 Nova 호출과 30초 대기가 통째로 없어짐.
- **더 단순한 대안(명시)**: 실시간 표시를 포기하고 지금의 HTTP·Nova 판정을 유지함. 고정 창만 말 끝 감지로 바꾸고 서버 상한만 줄임(§4·§7-⑥). 사용자가 이미 물린 안이라 권장하지 않음. 다만 C가 0단계에서 막히면 이 안으로 내려감.

### §2-1. 0단계 측정 게이트(구현 전)

- G1 Nova: 짧은 WAV 1~2개를 전사 전용 모드로 흘려 학습자 SPECULATIVE 블록이 오는지 셈(`tests/harness/spike_nova_protocol.py` 방식 · Nova 호출 1~2회).
  - 오면 A가 실시간을 채움. 판정을 서버가 갖고 스텁으로 시험할 수 있는 A로 바꿔 사용자에게 다시 물음.
  - 안 오면 C로 감.
- G2 Chrome: 시험용 Chrome(CDP)에서 `webkitSpeechRecognition`이 `network` 오류 없이 도는지 확인함. `--use-file-for-fake-audio-capture` WAV가 인식기에 들어가는지도 확인함.
  - ⚠️ Google API 키가 없는 Chromium 빌드에서는 인식기가 `network` 오류로 끝남.
  - 들어가지 않으면 자동 실물 검증 대신 사용자가 직접 말해 확인함(§8-③).
- G3 사용자 결정: Chrome의 Web Speech는 소리를 Google 서버로 보냄(Safari는 Apple). 이 점을 사용자에게 물어 승인받음. 승인이 없으면 A 또는 더 단순한 대안으로 감.

## §3. 권장안 흐름(C)

- `run()` 한 문장의 흐름:
  1. ① Listen: `speak()`로 읽어 줌. 이 단계는 바뀌지 않음.
  2. ② Say it: 읽기가 끝난 뒤 인식기를 시작함. ⛔ 읽는 동안에는 켜지 않음(스피커 소리가 전사됨). `onaudiostart`가 온 뒤에 단계 표시와 안내를 「듣는 중」으로 바꿈. 켜지는 데 걸리는 0.3~0.5초 동안 첫 낱말이 잘리지 않게 하려는 것임.
  3. 결과가 올 때마다 확정 부분과 미확정 부분을 화면에 갱신함(§6).
  4. 말 끝 감지(§4) → `stop()` → 남은 final을 기다림(상한 1초).
  5. ③ Check: 확정 문장을 `POST /api/course/sentences/{key}/attempts/text`로 보냄. 서버가 판정·저장해 `{transcript, words, attempts}`를 돌려줌.
  6. 결과를 보임 → 자동 모드면 1.5초 뒤 다음 문장으로 감. 이 부분은 지금과 같음.
- 새 모듈 `lib/speechRecognition.ts`:
  - `listen({ signal, expectedWords, maxMs, onUpdate }) → Promise<ListenOutcome>`
  - `ListenOutcome = { kind: "heard", text } | { kind: "silent" } | { kind: "denied" } | { kind: "unavailable" } | { kind: "aborted" }`
  - 인식기는 시도마다 새로 만듦. 설정은 `lang="en-US"`, `continuous=true`, `interimResults=true`.
  - ⚠️ `continuous=false`는 첫 쉼에서 끝나므로 쓰지 않음. 「중간에 잘림」이 같은 모양으로 돌아옴.
- 마이크: `ensureMic`는 권한을 먼저 받는 자리로 남김. 인식기를 쓸 때는 PCM을 모으지 않음(`recordRef`를 비운 채 둠). 이 브라우저에 인식기가 없을 때만 지금처럼 PCM을 모음(§7-⑥).

## §4. 녹음을 언제 끝내는가 — 고정 창 대신 말 끝 감지

- ⚠️ 아래 수치는 이 설계가 새로 정한 값임(근거 문서 없음). 실물 측정으로 고침.
- `QUIET_MS = 1500`: 마지막 결과(확정·미확정 모두) 뒤로 이만큼 조용하고 확정 부분이 있으면 끝냄.
- 늦게·천천히 읽는 학습자 보호: 확정 낱말 수가 원문 낱말 수의 60% 미만이면 조용함 기준을 `QUIET_LONG_MS = 3000`으로 늘림. 이것이 `we walk where we` 같은 잘림을 막는 장치임.
- `NO_SPEECH_MS = 5000`: 시작한 뒤 결과가 하나도 없으면 「안 들렸어요」로 끝냄. Chrome 자체의 `no-speech` 오류도 같은 갈래로 받음.
- `maxMs = max(8000, spokenMs × 3)`: 아무리 길어도 이 시간에 멈춤. 멈추면 그때까지의 결과로 판정함.
- 확정 부분이 없고 미확정 부분만 있는 채로 끝나면, `stop()` 뒤 1초 안에 온 final을 씀. 그래도 없으면 마지막 미확정 문장을 전사로 씀. 빈 값보다 낫다는 판단임.
- 학습자에게 보이는 것:
  - 단계 줄: `Sentence N / M · ② Say it`. 남은 초 표시는 없앰(끝이 정해져 있지 않음).
  - 녹음 막대: 같은 4px 자리에서, 줄어드는 막대 대신 맥박처럼 깜빡이는 막대(`omy-course-listen`)를 보임. 말 끝을 감지하면 바로 `③ Check`로 바뀜.
  - 새 버튼은 없음. 「Try again」·「Next」·「Back」은 그대로 둠.

## §5. 판정과 저장 — 두 번 전사하지 않음

- 새 경로 `POST /api/course/sentences/{key}/attempts/text`. 본문은 `{"transcript": str}`(앞뒤 공백을 지우고 최대 400자 · 발명한 수치이며 가장 긴 문장은 61자).
  - 키가 없으면 404, 모양이 틀리거나 길이를 넘으면 422.
  - ⛔ `transcriber_available` 검사를 하지 않음. Nova를 부르지 않으므로 `VOICE_ADAPTER=stub`에서도 200임.
  - 픽스처가 만든 문장이 아니라 실제 학습자 발화이므로 결정 131이 막은 오염(`factory.py` 주석)이 생기지 않음.
- 서비스: `services/course.py`에 `record_text_attempt(pool, course, user_id, key, transcript)`를 둠. `compare_readback`·삽입·횟수 읽기를 맡음. 기존 `record_attempt`는 전사한 뒤 이 함수를 부르게 바꿔, 삽입하는 자리를 하나로 둠.
- 전사 정본: 브라우저가 확정한 문장 하나. 서버는 다시 전사하지 않음.
  - ⚠️ 서버는 이 텍스트가 실제 소리에서 왔는지 검증하지 않음. 단일 사용자 로컬 앱이라 받아들임.
- 시도 횟수:
  - 빈 전사도 시도로 셈. 문법 코스 설계서 §4의 「전사가 비어도 시도로 셈」을 그대로 따름. `silent`이면 빈 문자열을 보냄.
  - `denied`·`unavailable`·`aborted`이면 보내지 않음. 시도로 세지 않음.
  - 결함 수정: 지금은 응답이 오기 전에 Next를 누르면 화면이 `counts`를 고치지 않음(서버에는 기록됨). 이제 `signal.aborted`여도 `setCounts`는 적용함. 문장 키 단위라 다른 문장을 덮지 않음. 결과 표시만 버림.
- 진도 저장(`save()`)과 `completedCount` 규칙은 바꾸지 않음.

## §6. 표시 — 고정 `course-result-slot` 안에서

- 카드(B)와 결과 자리의 크기는 바꾸지 않음(리디자인 설계서 §3 · `TASK-310`).
- ② Say it 단계:
  - 결과가 오기 전: 지금 안내문 「I'm listening. Say it, and you will see it below.」를 그대로 둠.
  - 결과가 오면: `You're saying:` 뒤에 확정 부분은 보통 색, 미확정 부분은 `var(--foreground-muted)` 기울임꼴로 붙여 보임(`data-testid="course-live"` · 미확정은 `course-live-interim`).
  - 글이 넘치면 이 자리 안에서만 스크롤함. 갱신할 때마다 맨 아래로 내림(`scrollTop = scrollHeight`).
- ③ Check 뒤: 실시간 줄을 지우고 기존 `Spoken`(낱말별 밑줄·취소선)으로 바꿈. `course-transcript`·`data-verdict`는 그대로 둠.
- 안내(`course-notice`)는 지금처럼 같은 자리를 나눠 씀.

## §7. 실패 갈래

| 갈래 | 감지 | 화면 | 시도 기록 |
|---|---|---|---|
| ① 말 없음 | `NO_SPEECH_MS` 또는 `no-speech` | `NOTICE.unheard` | 빈 전사로 1회 |
| ② 마이크 거부 | `ensureMic` 실패 또는 `not-allowed` | `NOTICE.mic` · 단계 `idle` | 안 함 |
| ③ 인식 서비스 실패 | `network` · `service-not-allowed` · `audio-capture` | `NOTICE.unavailable` | 안 함 |
| ④ Back·Next·Close·영상 재생·언마운트 | `cancelRun` → `signal` abort → `recognition.abort()` | 단계 `idle`, 안내 지움 | 안 함 |
| ⑤ 판정 POST 실패 | `fetch` 실패·5xx | `NOTICE.unavailable` | 서버가 못 썼으면 없음 |
| ⑥ 인식기 없는 브라우저(Firefox) | `SpeechRecognition` 미정의 | 실시간 줄 없이 지금 경로(PCM POST)를 씀. 다만 녹음 창은 §4의 상한을 씀 | 지금 규칙 |

- ⑥ 경로에서도 30초 빈 대기를 없앰. `transcribe.py`의 상한을 녹음 길이에 맞춤: `min(30, 녹음 초 + 10)`(발명한 수치).
  - 오디오를 다 보낸 뒤 2초 안에 `SpeechBoundaryEvent(speaking=True)`가 한 번도 오지 않으면 바로 빈 값으로 끝냄.
  - ⚠️ 쉐도잉 낭독 판정도 같은 함수를 씀. 긴 클립은 30초 상한이 그대로 남도록 `min`으로 둠.
- Nova 자격증명 만료: 권장 경로에는 해당하지 않음. ⑥ 경로에서는 지금처럼 503 → `NOTICE.unavailable`(`TASK-288`).

## §8. 시험 계획(실패하는 테스트 먼저)

- 백엔드 pytest. 격리된 `ohmyenglish_test` DB를 씀(`tests/conftest.py`가 다시 만듦). dev DB에는 닿지 않음.
  - `tests/integration/test_course_api.py`:
    - 텍스트 시도가 낱말별 판정과 `attempts=1`을 돌려주고 `course_attempts`에 한 행을 남기는가.
    - `VOICE_ADAPTER=stub`에서도 200인가. `create_transcriber`를 예외를 던지는 대역으로 바꿔 「부르지 않음」을 못 박음.
    - 빈 전사도 200이고 시도로 세는가.
    - 없는 키는 404, 400자 초과·필드 누락은 422인가.
    - 기존 PCM 경로의 테스트가 그대로 통과하는가(삽입 함수를 하나로 합친 회귀 확인).
  - `tests/unit/test_readback_transcribe.py`(⑥ 경로):
    - 말 시작이 없는 대역에서 `timeout_s`까지 기다리지 않고 빈 값을 내는가.
    - 상한이 녹음 길이를 따르는가.
- 프런트엔드: 단위 시험 도구가 없음(`package.json`). 브라우저 시나리오로 잼.
  - 새 드라이버 `tests/harness/p_course_live_transcript.py`(또는 `tests/agent` 방식의 `.mjs`)를 둠. `addInitScript`로 가짜 `SpeechRecognition`을 심어 미확정·확정·오류 이벤트를 각본대로 냄.
  - 이 방식은 Google에 의존하지 않고 결정적임.
  - 시나리오:
    - ① POST 전에 미확정 글자가 `course-live`에 보임.
    - ② 확정 뒤 조용해지면 POST가 1번 나가고, 판정이 보이고, `Try`가 1 오름.
    - ③ 낱말 4개 다음에 2초 쉬고 나머지를 말해도 잘리지 않음.
    - ④ 말이 없으면 6초 안에 「안 들렸어요」가 나옴.
    - ⑤ `not-allowed` 오류면 마이크 안내가 나오고 POST가 없음.
    - ⑥ `network` 오류면 「판정 불가」 안내가 나옴.
    - ⑦ 듣는 중에 Next를 누르면 `abort` 호출이 있고 POST는 없음.
    - ⑧ 1400·390 폭에서 `course-card` 상자 크기가 idle·듣는 중·긴 미확정·결과 네 상태에서 같음.
  - 여기에 `npm run lint` · `tsc --noEmit`을 더함.
  - 구현할 사람은 `app/frontend/AGENTS.md`에 따라 `node_modules/next/dist/docs/`를 먼저 읽음.
- 실물 검증:
  - ① 0단계 G1(Nova 1~2회) · G2(Chrome 인식기).
  - ② 시험용 스택에서 가짜 오디오 WAV로 실시간 글자를 확인함. b16 회차 규약을 따름: 백엔드 `:8002` + 격리 DB `ohmyenglish_course_paid` + CDP Chrome `:9401`/`:9402`. 프런트는 별도 worktree에서 `next dev -p 3002`(`NEXT_PUBLIC_API_BASE=http://localhost:8002`)로 띄움. ⛔ 서버는 내 셸에서 띄우지 않고 `launchctl submit` 으로 띄움(사용자 지시).
  - ③ AC #4: 사용자가 자기 화면에서 한 번 읽어 확인함. 이 단계는 사람이 함.
- ⛔ 사용자 스택(`:3000`·`:8002`·dev DB `ohmyenglish`)은 띄우거나 끄거나 쓰지 않음. 진행 중인 회차가 있으면 백엔드를 바꾸지 않음(`TASK-317` 메모).

## §9. 바꿀 파일

- `app/frontend/components/course/SentencePractice.tsx`: `run()`의 repeat·judge 단계, 실시간 표시, 횟수 적용 수정.
- `app/frontend/lib/speechRecognition.ts`(새 파일): 인식기 감싸기, 말 끝 감지, 타입 선언.
- `app/frontend/lib/api.ts`: `postCourseTextAttempt`.
- `app/frontend/app/globals.css`: `omy-course-listen` 맥박 막대(`prefers-reduced-motion`이면 멈춤).
- `app/backend/app/api/course.py`: 텍스트 시도 경로.
- `app/backend/app/services/course.py`: `record_text_attempt` 추출.
- `app/backend/app/models/course.py`: 본문 모델과 최대 길이.
- `app/backend/app/audio_gateway/transcribe.py`: ⑥ 경로의 상한과 「말 없음」 조기 종료.
- `tests/integration/test_course_api.py` · `tests/unit/test_readback_transcribe.py` · 새 하네스 드라이버.
- `docs/design/2026-10-26-grammar-course-design.md` §4: 「읽은 시간 + 1초 녹음」과 「`create_transcriber`를 그대로 씀」 규칙이 바뀌었음을 적음.

## §10. 위험과 비용

- 비용: 권장 경로에서 문장 연습의 Nova 호출이 0이 됨. 지금은 시도마다 스트림 1개를 엶. 0단계 G1은 1~2회. ⑥ 경로는 지금과 같음.
- 개인정보: Chrome 인식은 소리를 Google로 보냄. 사용자 결정이 필요함(G3).
- 브라우저 의존: Firefox에는 인식기가 없음(⑥ 경로). Safari는 `continuous`·`interim`의 동작이 다를 수 있음. 실물로 1회 확인함.
- 전사기 차이: Google 전사는 Nova와 다르게 낱말을 합치거나 고쳐 적음. 같은 날 기록 안에서 전사 출처가 섞임. 출처 열(`course_attempts.transcriber`)은 이 범위에서 더하지 않음. 마이그레이션이 공유 dev DB에 닿기 때문임. 필요하면 따로 task를 만듦.
- ASR 복원: 브라우저 인식도 잘못 발음한 낱말을 원문으로 고쳐 적을 수 있음. 지금 Nova와 같은 한계임(4차수 P2 실측).
- 자동 시험 한계: 가짜 인식기 시험은 화면 로직만 재고, 인식 품질은 재지 못함. 품질은 실물 확인 ②③이 맡음.
- 말 끝 수치: §4 수치는 발명한 값임. 늦게 읽는 사람이 1.5~3초 넘게 쉬면 잘릴 수 있음. 실측으로 고침.
- 결정 131과의 관계: 쉐도잉 낭독 판정의 전사 경계는 그대로 둠. 문법 코스만 전사 출처가 바뀜.

## §11. 사용자에게 물을 것

1. Chrome 인식이 소리를 Google로 보내는 것을 받아들이는가(G3).
2. 「말 없음」을 지금처럼 시도로 셀 것인가.
3. 0단계 G1에서 Nova가 학습자 부분 전사를 보내면 A로 바꿀 것인가.

### §11-1. 사용자 결정 (2026-11-14 · AskUserQuestion)

- G3: Web Speech 를 씀. Chrome 이 소리를 Google 로 보내는 것을 받아들임. → 권장안 C 로 감.
- 말 없음: Try 횟수에 세지 않음. → §5 의 「빈 전사도 시도로 셈」과 §7 ① 의 「빈 전사로 1회」를 뒤집음. `silent` 이면 서버에 보내지 않고 「안 들렸어요」만 보임.
  - ⚠️ 뒤집은 규칙: 문법 코스 설계서(`2026-10-26-grammar-course-design.md`) §4 의 「전사가 비어도 시도로 셈」. 구현 때 그 문서에도 번복을 적음.
- 질문 3(Nova 재측정 후 A 로 바꿀지)은 묻지 않았음 — G3 승인으로 C 가 정해져 0단계 G1 은 생략함. G2(시험 Chrome 의 인식기 동작)는 구현 전에 잼.

