# 수정 세션 작업 지시 — 3차수 (Nova 실연동 + F-2)

> 테스트 세션(`claude_air_5-49:0.0`)이 작성. **완료 후 그 세션에 보고하면 3차수 회귀 테스트가
> 돌아간다.** 합격 판정은 테스트 세션이 한다 — 자기 수정을 스스로 통과시키지 않아도 된다.
> 작성 2026-08-26 · 기준 커밋 `832b258`

## 먼저 읽을 것

| 문서 | 왜 |
|---|---|
| `tests/harness/scenarios-N-real-voice.md` | **이 작업의 명세다.** 공식 문서 대조 + 실측 결과 + 고쳐야 할 곳이 전부 있다 |
| `tests/harness/spike_nova_protocol.py` | **동작이 확인된 참조 구현.** 이벤트 시퀀스·프레임 크기·송수신 순서를 여기서 가져온다 |
| `tests/harness/runs/2026-08-26-N1/N1-nova-protocol.json` | Nova가 실제로 돌려준 이벤트 원자료 |
| `handoff/HANDOFF-test-harness.md` | 현재 상태와 환경 제약 |
| `docs/design/2026-08-24-first-vertical-slice-design.md` §7 | 포트 확장 원칙(수정 금지, 읽기만) |

## 환경 제약 (반드시)

1. **워크트리를 새로 만들지 않는다.** 테스트 스택이 `/Users/redstar/MyProject/OhMyEnglish`를
   직접 서빙한다(프론트 `:3000`, 백엔드 `:8002`). 다른 워크트리에서 고치면 테스트가 수정 전
   코드를 검증한다. 부득이 썼다면 보고 전에 `design/first-vertical-slice`로 병합하고 보고에 적어라.
2. **`.env` 편집 금지.** 자격증명이 들어 있다. 플래그는 환경변수로만 넘긴다.
3. **DB 조작 금지.** `harness_*` 테이블은 테스트 세션 소유다.
4. **수정 금지 경로**: `tests/harness/**` · `docs/design/**` · `docs/ops/2026-08-26-test-harness*.html`
5. **백엔드 파이썬을 고쳤으면** `--reload`가 없어 실행 중 프로세스에 반영되지 않는다 →
   보고에 **"백엔드 소스 변경 있음"** 을 명시해라(테스트 세션이 재기동한다).
6. **작업을 두 덩이로 나눠 커밋해라** — 태스크 1과 2는 무관한 변경이다.

---

## 태스크 1 — F-2: `target_form`을 패턴 수준 일반형으로 (작은 것 먼저)

**배경.** 1차수 F-2에서 교정 카드의 `target_form`이 표시된 `original_span`/`correction`과
**다른 문장**을 가리키는 것이 관측됐다. 2차수에서 조건이 특정됐다 —
**occurrence가 2개 이상이고 서로 다른 `target_form`을 가진 패턴에서만** 발생한다.

실측 예 (E1 세션):

| pattern_key | occ | original_span | correction | 패턴의 target_form |
|---|--:|---|---|---|
| `verb_tense_past_simple_yesterday` | 2 | `Yesterday I go` | `Yesterday I went` | **`and presented`** |
| `word_order_embedded_question` | 1 | `I know not why` | `I don't know why` | `I don't know why` |

원인은 두 값이 **독립적으로 선택**되는 것이다 — `services/results.py:125`가 대표 occurrence를
`distinct on`으로 고르고, `:133`은 `ep.target_form`을 **패턴 테이블**에서 가져온다.
패턴 upsert(`services/analysis.py`의 `_UPSERT_PATTERN_SQL`)는 `set target_form =
excluded.target_form`으로 **마지막 분석이 이긴다**.

**캡틴 결정: 선택지 B — 패턴 수준의 일반화된 형태로 만든다.** 스키마를 바꾸지 않는다.

근거: 문장별 교정형은 **이미 `error_occurrences.correction`에 있다**. `target_form`을
문장별로 만들면 같은 값을 두 번 저장하는 것이고, 컬럼이 패턴 테이블에 있는 이유가 없어진다.
`target_form`이 따로 존재할 값이 있으려면 **"이 패턴을 연습할 때 익힐 형태"** 여야 한다 —
문장을 넘어서는 것이다. 이 값은 나중에 복습 기능(L계층)이 연습 목표로 쓴다.

### 해야 할 일

1. **분석 프롬프트를 고쳐라** — Claude가 `target_form`을 **문장별 교정문이 아니라 패턴의
   일반형**으로 내게 한다. 예: `go to office` → `go to the office`(문장형)가 아니라
   `go to the + 장소 명사` 또는 `the + 특정 장소`처럼 재사용 가능한 형태.
   프롬프트에 **좋은 예/나쁜 예를 함께 넣어라** — 형식만 말하면 모델이 문장을 그대로 넣는다.
2. **같은 패턴의 재분석이 값을 흔들지 않게 하라.** 기존 `pattern_key` 목록을 프롬프트에
   주입하는 §5.6 계약이 이미 있으니, **기존 `target_form`도 함께 주입해 재사용을 우선**하게
   하는 것이 자연스럽다(`_EXISTING_PATTERNS_SQL`이 이미 `target_form`을 select한다).
3. **`database-schema.md`의 `target_form` 설명을 갱신해라** — "패턴 수준의 일반화된 목표 형태,
   문장별 교정은 `error_occurrences.correction`이 담당"임을 명시.
4. 단위 테스트를 추가해라 — occurrence가 2개인 패턴에서 `target_form`이 어느 한 occurrence의
   `correction`과 같아지지 **않는** 것을 가짜 Claude 응답으로 확인.

**하지 말 것**: 마이그레이션 002를 만들지 마라. 컬럼 이동은 이번 결정이 아니다.

---

## 태스크 2 — Nova 2 Sonic 실연동

프로토콜은 이미 실증됐다(N-1 PASS). **참조 구현이 `spike_nova_protocol.py`에 있으니 이벤트
스키마를 다시 추측하지 마라.**

### 2-1. 포트 확장 (`app/backend/app/audio_gateway/port.py`)

현재 포트는 `TranscriptEvent(kind='partial'|'final', text, speaker)` + `bytes`뿐이다.
Nova가 주는 신호 중 매핑할 곳이 없는 것들을 **확장**한다 (설계서 §7이 예고한 확장이다):

| Nova 신호 | 필요한 것 |
|---|---|
| `userSpeechStart` / `userSpeechEnd` (`inputAudioOffsetMs`) | 발화 경계 이벤트 |
| `contentEnd.stopReason = "INTERRUPTED"` | **barge-in 통보** — 클라이언트가 오디오 큐를 비울 근거 |
| ASSISTANT `generationStage`: `SPECULATIVE` vs `FINAL` | agent 텍스트의 예고/확정 구분 |

**제약**: 확장이 `session.py`의 상위 로직(세션 수명·저장·job 등록)에 파급되지 않아야 한다.
그것이 G3의 목표였고, 스텁으로 검증된 그 로직은 **가능하면 손대지 마라**.
`StubVoiceAdapter`도 새 이벤트 타입을 만족시켜야 한다(스텁은 계속 쓰인다).

### 2-2. Nova 어댑터 (`app/backend/app/audio_gateway/nova.py` 신규)

`spike_nova_protocol.py`에서 가져올 것:

- 이벤트 시퀀스: `sessionStart`(+`turnDetectionConfiguration`) → `promptStart` →
  `contentStart`(TEXT/SYSTEM) → `textInput` → `contentEnd` → `contentStart`(AUDIO/USER,
  `interactive: true`) → `audioInput`* → `contentEnd` → `promptEnd` → `sessionEnd`
- 오디오 규격: `audio/lpcm`, 16000Hz, 16bit, mono, `audioType: SPEECH`, `encoding: base64`,
  프레임 **32ms = 1024바이트**
- **`await_output()`은 초기화 이벤트를 보내기 전에 반환하지 않는다** → 송수신을 **동시에**
  시작해야 한다 (실측: 먼저 기다리면 20초 타임아웃)
- **미지 이벤트에 죽지 마라** — `userSpeechStart`/`userSpeechEnd`는 공식 출력 이벤트 목록에
  없다. 파서는 모르는 이벤트를 로그만 남기고 넘겨야 한다
- 자격증명은 **`app.config`를 그대로 쓴다**(F5 단일 이음새). 어댑터가 직접 키를 읽지 마라

주의할 것:
- **무음 프레임은 어댑터가 만들지 않는다.** 스파이크는 WAV가 끝나면 프레임이 끊겨서 무음을
  넣어야 했지만, 실제 마이크는 사용자가 말을 멈춘 뒤에도 계속 흐른다. 다만 **사용자가 종료를
  누르면 프레임이 끊기므로** 그때 endpointing이 발동하지 않을 수 있다 — `contentEnd`를 보내
  명시적으로 닫아라
- **스트림 상한은 8분이다**(SDK docstring: "The response is returned in a stream that remains
  open for 8 minutes"). 세션 롤오버는 이번 범위가 아니지만 **상한에 닿았을 때 조용히 죽지 말고
  세션을 닫고 통보**해라
- `factory.py`에 `nova` 값을 추가한다. 분기는 그 함수 **한 곳에만** 둔다(G3)

### 2-3. 프론트엔드 입력 — `MediaRecorder`를 버려야 한다

현재 `app/frontend/app/page.tsx`는 `MediaRecorder`로 `audio/webm;codecs=opus`를 250ms마다
만든다. **Nova는 raw LPCM을 요구하므로 호환되지 않는다.**

`AudioWorklet`(또는 최소한 `ScriptProcessor`)으로 **원시 PCM을 16kHz·16bit·mono로 캡처**해
32ms(1024바이트) 단위로 base64 인코딩해 보낸다. `AudioContext({sampleRate: 16000})`으로
리샘플을 브라우저에 맡기는 것이 가장 단순하다.

> 참고: 1차수 F-3에서 `MediaRecorder` 경로로 33프레임·158KB가 실제로 전송됨을 확인했다 —
> **전송 배선 자체는 살아 있고, 인코딩만 바꾸는 것이다.**

### 2-4. 프론트엔드 출력 — `new Audio()`를 버려야 한다

현재 `playAudioFrame`은 `new Blob([bytes], {type:"audio/wav"})` + `new Audio(url)`이다.
지금 동작하는 이유는 **스텁이 헤더가 유효한 WAV를 보내기 때문**이고, Nova 출력은 헤더가 없다
(실측: 17청크의 앞 4바이트가 `RIFF`가 아닌 PCM 샘플).

`AudioContext`로 PCM을 직접 큐에 넣어 재생해라. **barge-in이 "이미 받았지만 아직 재생 안 한
오디오를 버리는 것"이므로 큐를 직접 쥐고 있어야 한다** — 이것이 `new Audio()`를 못 쓰는 진짜
이유다. `INTERRUPTED` 통보를 받으면 큐를 비운다.

### 2-5. 부분 전사문 UI — 캡틴 결정 반영

**Nova는 사용자 부분 전사문을 주지 않는다.** 사용자 ASR은 `generationStage: FINAL` 한 블록으로만
온다(실측). 그래서 지금의 "회색 부분 전사문이 자라다가 확정된다"는 화면 거동은 실연동에서
재현되지 않는다.

**캡틴 결정: 선택지 ① — `userSpeechStart`~`userSpeechEnd` 구간에 "듣고 있어요" 상태를 보여준다.**
회색 부분 전사문 자리를 그 표시로 대체한다. **스텁 모드에서는 기존 부분 전사문 거동을 유지해라** —
1·2차수 회귀(C2)가 그것을 검증하고 있다.

색은 **반드시 테마 토큰**(`var(--foreground-muted)` 등)을 쓴다. 인라인 하드코딩은 1차수 F-1의
재발이다(다크모드에서 대비 1.05:1이 났던 그 문제).

---

## 완료 조건

```bash
cd app/backend
.venv/bin/pytest -q          # 실패 0, skip/xfail 0 (현재 기준선 206)
.venv/bin/ruff check .
.venv/bin/ruff format --check .
ty check
cd ../frontend && npx tsc --noEmit    # 프론트 타입 확인
```

TDD로 진행해라 — Nova 어댑터는 실제 호출 없이도 이벤트 시퀀스와 파싱을 가짜 스트림으로
테스트할 수 있다. **실물 왕복 1회 확인은 테스트 세션이 한다**(N5~N13 시나리오).

## 보고

끝나면 **한 줄로** 이 명령을 실행해라. `claude_air_5-49:0.0`은 셸이 아니라 tmux 페인 주소이고
그 안에 테스트 세션(다른 Claude Code)이 대화형으로 돌고 있다 — 보낸 텍스트는 그 세션의 사용자
프롬프트가 된다. `Enter`는 별도 인자여야 하고, 줄바꿈에서 조기 전송되니 한 줄로 붙여라.

```
tmux send-keys -t claude_air_5-49:0.0 '3차수 수정완료 태스크1(F-2)=<한줄> 태스크2(Nova)=<한줄> 커밋=<해시들> 백엔드소스변경=있음/없음 게이트=<pytest수>passed/ruff/format/ty/tsc 재테스트요청' Enter
```

**막히면 멈추고 보고해라.** 특히 스키마 변경이 필요하다고 판단되면 **고치지 말고 근거를
보고**해라 — 1차수 F-2에서 그렇게 한 판단이 옳았다.

이 왕복은 **최대 10차수**까지만 진행한다(현재 3차수 시작).
