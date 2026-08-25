# N계층 — 실제 음성 발화 테스트: 검토와 준비

**결론 갱신 (2026-08-26 N-0·N-1 완료): 실음성 왕복이 실제로 성공했다.**
Nova 2 Sonic이 우리 합성 음성을 알아듣고 텍스트와 음성으로 답했다. 남은 것은
**앱에 붙이는 일**이고, 그 과정에서 **프론트엔드를 두 곳 고쳐야 한다는 것이 확정됐다.**

| 단계 | 상태 |
|---|---|
| **N-0** 공식 문서로 이벤트 스키마·오디오 포맷 확정 | ✅ 완료 |
| **N-1** 프로토콜 스파이크 — 실음성 → 전사문 왕복 | ✅ **PASS** |
| N-2 브라우저 입력 포맷 경로 | ⏸ 결론 나옴(변경 필요) — 구현은 수정 세션 몫 |
| N-3 브라우저 출력 재생 경로 | ⏸ 결론 나옴(변경 필요) |
| N-4 Nova 어댑터 구현 | 미착수 |

---

## 1. N-1 실측 결과 — 실음성 왕복 PASS

입력: `fixtures/voice/u1.wav` (1.92초, "I usually go to gym after work.")
스크립트: `spike_nova_protocol.py` · 원자료: `runs/2026-08-26-N1/N1-nova-protocol.json`

```
[userSpeechStart]  inputAudioOffsetMs=0
[completionStart]
[userSpeechEnd]    inputAudioOffsetMs=1920, inputAudioDetectionOffsetMs=2400
[contentStart] TEXT  USER/{"generationStage":"FINAL"}
[textOutput]         'i usually go to gym after work.'      ← 픽스처와 일치
[contentEnd]   TEXT  stopReason=PARTIAL_TURN
[contentStart] TEXT  ASSISTANT/{"generationStage":"SPECULATIVE"}
[textOutput]         'That's a great routine.'
[contentEnd]   TEXT  stopReason=PARTIAL_TURN
[contentStart] AUDIO ASSISTANT
[audioOutput]  × 17  총 44,800B = 1.4초 (16kHz·16bit·mono 기준)
[contentEnd]   AUDIO stopReason=END_TURN
[completionEnd]      stopReason=END_TURN
```

관측 이벤트 집계: `usageEvent 12` · `userSpeechStart 1` · `completionStart 1` ·
`userSpeechEnd 1` · `contentStart 3` · `textOutput 2` · `contentEnd 3` ·
`audioOutput 17` · `completionEnd 1`

### 이 실행에서 확정된 것 5가지

1. **오디오 입력은 raw LPCM이다.** `mediaType: "audio/lpcm"`, `sampleRateHertz` 8000|16000|24000,
   `sampleSizeBits: 16`, `channelCount: 1`, `audioType: "SPEECH"`, `encoding: "base64"`.
   WAV 헤더를 벗겨 보내야 한다(`wave.readframes`). 프레임은 **32ms = 1,024바이트**(16kHz).
2. **오디오 출력도 raw LPCM이다 — 컨테이너가 없다.** 17개 청크의 앞 4바이트가 `RIFF`가 아니라
   PCM 샘플이었다(`b'+\x00,\x00'` 등). 청크 크기는 2,528~6,400B로 일정하지 않다.
3. **무음 프레임이 없으면 전사문이 오지 않는다.** 첫 시도에서 오디오 직후 바로
   `contentEnd`/`sessionEnd`를 보냈더니 `userSpeechStart`만 오고 끝났다. 발화(1,920ms) 뒤에
   무음을 이어 보내자 `inputAudioDetectionOffsetMs=2400`에서 `userSpeechEnd`가 떴다 —
   **약 480ms의 무음이 endpointing을 발동시켰다.** 실제 마이크는 사람이 말을 멈춘 뒤에도
   무음을 계속 흘리므로 그 조건을 재현해야 한다.
4. **`await_output()`은 초기화 이벤트를 보내기 전에는 반환하지 않는다.** HTTP 응답 헤더 자체가
   오지 않기 때문이다(실측: 20초 타임아웃). **전송과 수신을 동시에 시작해야 한다.**
5. **문서에 없는 이벤트 2개가 온다** — `userSpeechStart`, `userSpeechEnd`. 공식 출력 이벤트
   목록에 없지만 발화 경계를 알려주는 신호다. 파서가 미지 이벤트를 만나도 죽지 않아야 한다.

### Nova 2와 v1의 차이 (문서 대조)

- `sessionStart`에 **`turnDetectionConfiguration.endpointingSensitivity`**(HIGH/MEDIUM/LOW)가
  추가됐다 — **AC2 barge-in 민감도가 여기서 정해진다.**
- `contentStart` role에 `SYSTEM_SPEECH`가 추가되고, TEXT의 `interactive: true`로
  음성 세션 중 텍스트 입력(cross-modal)이 가능하다.
- `voiceId` 목록이 늘었다(`olivia`·`tina`·`carolina`·`leo`·`kiara`·`arjun` 등).
- 오디오 설정 값 자체는 v1과 동일하다.

---

## 2. 앱에 붙일 때 고쳐야 할 것 — 확정

### N-2 · 프론트엔드 오디오 캡처를 바꿔야 한다 (입력)

현재 프론트는 `MediaRecorder`로 **`audio/webm;codecs=opus`**를 만든다(1차수 F-3에서
33프레임·158KB 실측). Nova는 **raw LPCM**을 요구한다. **둘은 호환되지 않는다.**

| 선택 | 방법 | 평가 |
|---|---|---|
| **A** | 브라우저에서 `AudioWorklet`(또는 `ScriptProcessor`)로 **원시 PCM 캡처** → 16kHz 리샘플 → base64 | 서버 의존성 없음, 실시간에 맞다. **권장** |
| B | 서버에서 webm/opus → LPCM 트랜스코딩 | ffmpeg 의존성 추가 + 지연. 실시간 대화에 불리 |

`MediaRecorder`의 250ms 타임슬라이스도 Nova의 32ms 케이던스와 맞지 않는다 —
A를 택하면 이 문제도 함께 사라진다.

### N-3 · 프론트엔드 오디오 재생을 바꿔야 한다 (출력)

현재 코드는 `new Blob([bytes], {type:"audio/wav"})` + `new Audio(url)`로 재생한다
(`app/frontend/app/page.tsx`의 `playAudioFrame`). 지금 동작하는 이유는 **스텁이 헤더가 유효한
WAV를 보내기 때문**이다. Nova 출력은 헤더가 없어 **그대로는 디코드에 실패한다.**

| 선택 | 방법 |
|---|---|
| **A** | `AudioContext`로 PCM을 직접 큐에 넣어 재생 — barge-in 시 큐를 비울 수 있어 **권장** |
| B | 청크마다 WAV 헤더를 붙여 `new Audio()` 유지 — 간단하지만 barge-in 중단이 어렵다 |

barge-in은 "이미 받았지만 아직 재생 안 한 오디오를 버리는 것"이 핵심이라(공식 문서)
**A가 사실상 필수다.**

### N-4 · 포트 확장이 필요하다

현재 포트는 `TranscriptEvent(kind='partial'|'final', text, speaker)` + `bytes`뿐이다.
Nova는 여기에 매핑되지 않는 신호를 준다:

| Nova 신호 | 포트에 없는 것 |
|---|---|
| `userSpeechStart` / `userSpeechEnd` | 발화 경계 이벤트 |
| `contentEnd.stopReason = INTERRUPTED` | **barge-in 통보** — 클라이언트가 오디오 큐를 비울 근거 |
| `generationStage: SPECULATIVE` vs `FINAL` (ASSISTANT) | agent 텍스트의 예고/확정 구분 |
| `usageEvent` | 토큰 사용량 |

AC 문서가 예고한 "포트는 Phase 2에서 **확장**된다"가 그대로 필요하다.

### ⚠️ AC U1의 "부분 전사문 회색 표시"에 대응하는 데이터가 없다

**사용자 ASR은 `generationStage: FINAL` 한 블록으로만 온다.** N-1에서 `textOutput`이
사용자 발화당 1건이었고 중간 전사문은 없었다. `SPECULATIVE`는 **ASSISTANT 텍스트**에
쓰인다.

즉 스텁이 만들어 온 "사용자 부분 전사문이 자라다가 확정된다"는 화면 거동은
**Nova 실연동에서 재현되지 않는다.** 선택이 필요하다:

1. 사용자 부분 전사문 UI를 **버린다** — 대신 `userSpeechStart`~`userSpeechEnd` 구간에
   "듣고 있어요" 상태를 보여준다.
2. ASSISTANT의 `SPECULATIVE` 텍스트를 부분 전사문 자리에 쓴다 (의미가 달라진다).
3. 그대로 두고 실연동에서는 부분 전사문이 안 나오는 것을 수용한다.

**캡틴 결정 사항이다.** 1차수·2차수에서 검증한 C2(회색→검정 전환)는 **스텁 거동의 검증이며
실연동 거동이 아니라는 것**을 기록해 둔다.

---

## 3. 재현 가능한 음성 입력 — 준비 완료

```
tests/harness/fixtures/voice/
  u1.wav   1.92s  "I usually go to gym after work."                                   (article 오류)
  u2.wav   2.16s  "I usually go to office by subway."                                 (같은 패턴 → 병합 확인용)
  u3.wav   3.66s  "Yesterday I go to the client meeting and present the project status." (verb_tense 2건)
```

전부 **16kHz · 16bit · mono WAV** = Nova 입력 규격과 정확히 일치. 재생성:

```bash
say -v Samantha -o /tmp/x.aiff "<문장>"
afconvert -f WAVE -d LEI16@16000 -c 1 /tmp/x.aiff u1.wav
```

문장은 스텁 픽스처·E계층 주입 문장에서 가져왔으므로 **기대 분석 결과를 이미 알고 있다**
(u1·u2는 한 패턴으로 병합, u3는 `verb_tense` 2건). N-1에서 u1의 ASR이 픽스처와 일치함을
확인했다.

### 브라우저에 주입하는 방법

1차수 F-3에서 `getUserMedia`를 합성 스트림으로 대체하는 데 성공했다. WAV를 디코드해 흘리면
매번 같은 발화를 마이크처럼 넣을 수 있다:

```js
const ctx = new AudioContext();
const buf = await ctx.decodeAudioData(await (await fetch('/fixtures/u1.wav')).arrayBuffer());
const src = ctx.createBufferSource(); src.buffer = buf;
const dest = ctx.createMediaStreamDestination(); src.connect(dest);
navigator.mediaDevices.getUserMedia = async () => { await ctx.resume(); src.start(); return dest.stream; };
```

**주의 (1차수 H-1)**: 클릭은 반드시 CDP 실제 입력으로 한다 — `eval` 안의 `element.click()`은
user activation을 만들지 않아 `ctx.resume()`이 멈춘다.
`fetch`가 되려면 WAV가 프론트엔드에서 서빙돼야 하므로 `app/frontend/public/`에 두거나
base64로 인라인한다(캡틴 사전 승인 범위).

---

## 4. 어댑터가 생긴 뒤 돌릴 시나리오

| # | 시나리오 | 단정 | 대응 AC |
|---|---|---|---|
| **N5** | 실음성 1턴 왕복 | `u1.wav` 주입 → 확정 전사문이 **실제 발화 내용과 일치**(픽스처가 아니라) → `utterances` 저장 → job 등록 | AC1 |
| **N6** | barge-in | agent 발화 중 오디오 입력 → **1초 안에** 출력 중단 + `stopReason=INTERRUPTED` 통보 + 클라이언트 오디오 큐 비움 | AC2 |
| **N7** | 실음성 3턴 완주 | `sequence_no` 단조, 각 사용자 발화에 job 1건 | AC12 |
| **N8** | 실발화 → 실분석 결합 | `u1`+`u2` → 같은 `article` 패턴 병합, `frequency` +2 (E계층 단정을 실음성으로 재현) | AC3·AC4 |
| **N9** | 세션 롤오버 | 스트림은 **8분**이 상한이다(SDK docstring) — 그 경계에서 세션이 이어지거나 깨끗히 닫힌다 | §7 Boundary |
| **N10** | 무응답형 자격증명 실패 | 잘못된 키로 10초 상한이 실물에서도 동작하는가 | §4.2 실계측 |
| **N11** | 마이크 권한 거부 | `getUserMedia` reject → `microphone_permission_denied` 화면 | U1 실패 경로 |
| **N12** | 포맷 불일치 방어 | 잘못된 샘플레이트/코덱을 보냈을 때 조용히 죽지 않고 실패를 통보하는가 | §7 Boundary |
| **N13** | endpointing 민감도 | `HIGH`/`MEDIUM`/`LOW`로 발화 종료 감지 시점이 달라지는가 (N-1 실측: MEDIUM에서 약 480ms) | AC2 튜닝 |

`N10`~`N12`는 1차수 A2(깨진 프레임 내성)·B5(무응답 타임아웃)가 스텁으로 메커니즘을 이미
검증한 항목이다 — 실물에서 같은 방어가 작동하는지만 확인한다.

## 5. 남은 캡틴 결정

1. **사용자 부분 전사문 UI를 어떻게 할까** — 위 §2 마지막 (선택 3개)
2. **음성 픽스처를 `app/frontend/public/`에 둘까** — 사전 승인 범위지만 프로덕션 번들에 테스트
   자산이 들어가는 것이라 기록해 둔다
3. **Nova 어댑터 구현을 누가 할까** — 작성자≠검증자 원칙상 수정 세션(`claude_air_3-14`)
