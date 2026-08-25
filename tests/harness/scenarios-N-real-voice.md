# N계층 — 실제 음성 발화 테스트: 가능성 검토와 준비

**검토 결론(2026-08-26): 실음성 발화 테스트는 지금 불가능하다.** 자격증명은 열렸지만
앱에 Nova 경로가 없다. 아래는 무엇이 막혀 있고, 무엇이 이미 준비됐고, 어떤 순서로
풀어야 하는지다.

---

## 1. 지금 불가능한 이유 — 블로커 3개 (순차적)

### B-1 · Nova 어댑터가 존재하지 않는다

`app/backend/app/audio_gateway/factory.py`가 아는 구현은 둘뿐이다 — `stub`,
`stub_unresponsive`. 설정값에 `nova`가 없고 그런 이름의 모듈도 없다. 즉
**앱을 통과하는 실음성 경로가 아예 없다.** 브라우저에서 마이크를 켜도 스텁 픽스처
3문장이 돌아온다(1회차 C1에서 실측 — 무슨 소리를 넣어도 전사문은 같다).

### B-2 · Nova Sonic 이벤트 프로토콜이 구현되지 않았다

`scripts/spike_nova_bidirectional.py`가 스스로 명시한다 —
*"Nova Sonic은 클라이언트가 전체 초기화 시퀀스(`sessionStart` → `promptStart` →
`contentStart` …)를 보내기 전까지 아무 이벤트도 내보내지 않는다. 그 프로토콜 구현은
Phase 2의 몫이다."*

SDK가 스키마를 주지 않는다. `aws-sdk-bedrock-runtime` 0.10.0의 양방향 입력은
**불투명한 bytes 하나**다:

```python
InvokeModelWithBidirectionalStreamInputChunk(
    value=BidirectionalInputPayloadPart(bytes_=json.dumps(event).encode())
)
```

`models.py`에 `AudioInput*`·`SessionStart*` 같은 타입이 없다(실측 확인). 이벤트 JSON의
구조는 **AWS 공식 문서에서 확인해야 한다** — 추측으로 구현하면 무응답으로 실패하고
(설계서 §4.2), 그 실패는 자격증명 문제와 구별되지 않는다.

### B-3 · 오디오 포맷 계약이 어디에도 없다 — 그리고 불일치 가능성이 크다

| 지점 | 현재 상태 |
|---|---|
| 브라우저가 보내는 것 | **`audio/webm;codecs=opus`** — 1회차 F-3에서 실측(33프레임·158,132 B) |
| 포트가 약속하는 것 | `bytes`뿐. `port.py`는 포맷을 계약에 넣지 않았다 |
| 스텁이 내보내는 것 | 16 kHz·16 bit·mono PCM WAV — **스텁 자체 규격**이라고 `fixtures.py`가 명시("Nova Sonic의 실제 출력 형식은 Phase 2에서 실측해 확정한다") |
| Nova가 요구하는 것 | **이 저장소 어디에도 문서화돼 있지 않다.** `voice-architecture.md`·`nova-sonic-claude-architecture.md`·설계서 전부 포맷 언급 없음 |

브라우저의 컨테이너·코덱(webm/opus)과 실시간 스트리밍 STT가 통상 요구하는 raw PCM은
같지 않다. **변환이 필요한지, 어디서 하는지(브라우저 `AudioWorklet` 원시 PCM 캡처 vs
서버 트랜스코딩)가 미정이고, 이것이 포트 계약을 건드릴지도 미정이다.**

---

## 2. 이미 준비된 것

| 항목 | 상태 | 증거 |
|---|---|---|
| SigV4 자격증명 | **열림** | 스파이크 재실행 PASS (2026-08-26). 음성 대조군도 정상 거부(`ValidationException`) |
| 양방향 스트림 수락 | **확인** | `amazon.nova-2-sonic-v1:0` 스트림 20초 유지, 4xx 없음 |
| 이벤트 1개 전송 메커니즘 | **확인** | `sessionStart`(`inferenceConfiguration`: maxTokens 256·topP 0.9·temperature 0.7)를 보내도 거부되지 않았다 |
| 브라우저 마이크 캡처 | **확인** | F-3 — 실제 Opus 프레임 33개·158 KB를 열린 WS로 전송 |
| 포트 계약 | **확정** | `start` / `send_audio(bytes)` / `events() -> TranscriptEvent | bytes` / `close` |
| 세션 상위 로직 | **전부 검증됨** | 수명주기·저장·job 등록·결과 판정을 스텁으로 관통(1회차 A·B·C계층). **어댑터만 갈아 끼우면 된다** |
| 재현 가능한 음성 입력 | **준비 완료** | `fixtures/voice/u{1,2,3}.wav` — 아래 §3 |

---

## 3. 재현 가능한 음성 입력 — 준비 완료

실음성 테스트의 최대 난점은 **"같은 발화를 다시 넣을 수 없다"**는 것이다. 사람이 마이크에
말하면 매번 달라져 단정을 쓸 수 없다. 그래서 고정 문장을 미리 합성해 뒀다.

```
tests/harness/fixtures/voice/
  u1.wav   1.92s  "I usually go to gym after work."                                   (article 오류)
  u2.wav   2.16s  "I usually go to office by subway."                                 (같은 패턴 → 병합 확인용)
  u3.wav   3.66s  "Yesterday I go to the client meeting and present the project status." (verb_tense 2건)
```

전부 **16 kHz · 16 bit · mono WAV**. 생성 방법(재생성 가능):

```bash
say -v Samantha -o /tmp/x.aiff "<문장>"
afconvert -f WAVE -d LEI16@16000 -c 1 /tmp/x.aiff u1.wav
```

문장은 스텁 픽스처와 E계층 주입 문장에서 가져왔다 — **실음성 경로가 열렸을 때 기대 결과를
이미 알고 있다는 뜻이다**(u1·u2는 한 패턴으로 병합, u3는 `verb_tense` 2건).

### 브라우저에 주입하는 방법 (기법은 1회차에서 이미 검증됨)

F-3에서 `getUserMedia`를 오실레이터 합성 스트림으로 대체하는 데 성공했다. 같은 자리에
**WAV를 디코드해 흘리면** 매번 같은 발화를 마이크처럼 넣을 수 있다:

```js
const ctx = new AudioContext();
const buf = await ctx.decodeAudioData(await (await fetch('/fixtures/u1.wav')).arrayBuffer());
const src = ctx.createBufferSource(); src.buffer = buf; src.loop = false;
const dest = ctx.createMediaStreamDestination(); src.connect(dest);
navigator.mediaDevices.getUserMedia = async () => { await ctx.resume(); src.start(); return dest.stream; };
```

주의: `fetch`가 되려면 WAV가 프론트엔드에서 서빙되는 경로에 있어야 한다
(`app/frontend/public/`로 복사하거나 base64로 인라인). **앱에 테스트 자산을 심는 것이므로
캡틴 승인이 필요하다** — 대안은 base64 문자열을 `eval` 페이로드에 실어 보내는 것이다.

---

## 4. 착수 순서 — 어댑터를 쓰기 전에 알아야 할 것

각 단계는 **다음 단계의 전제**다. 순서를 건너뛰면 무응답 실패를 디버그할 근거가 없다.

| # | 작업 | 산출물 / 판정 |
|---|---|---|
| **N-0** | AWS 공식 문서에서 **이벤트 스키마와 오디오 포맷을 확정**한다 (코드 아님, 문서 작업) | 초기화 시퀀스 각 이벤트의 JSON 구조, 입력 오디오 인코딩·샘플레이트·프레임 크기, 출력 이벤트 종류. **이것 없이 구현 착수 금지** (CLAUDE.md: 공식 문서 미확인 추측 금지) |
| **N-1** | **프로토콜 스파이크** — `u1.wav`를 초기화 시퀀스와 함께 밀어넣어 **전사문 이벤트를 실제로 받는다** | 부분/확정 전사문 이벤트 원문 로그. 이게 되면 어댑터를 쓸 수 있다. 실패하면 N-0으로 되돌아간다 |
| **N-2** | **입력 포맷 경로 결정** — 브라우저 webm/opus → Nova 입력 | 선택지 ① 브라우저에서 `AudioWorklet`으로 raw PCM 캡처(프론트 변경) ② 서버에서 트랜스코딩(ffmpeg 의존성 추가) ③ Nova가 opus를 받는다면 무변환. **N-0의 답에 따라 결정된다** |
| **N-3** | **출력 경로 확인** — Nova 오디오 응답을 브라우저가 재생 가능한가 | 스텁은 헤더 유효한 WAV를 보내 브라우저가 `new Audio()`로 재생했다(1회차 C1). Nova 출력이 raw PCM이면 **헤더를 붙이거나 `AudioContext`로 재생해야 한다** — 프론트 변경 여부가 여기서 갈린다 |
| **N-4** | 어댑터 구현 + `factory.py`에 `nova` 추가 | 포트 4개 메서드. 세션 상위 로직은 무변경이어야 한다(G3의 목표) |

---

## 5. 어댑터가 생긴 뒤 돌릴 시나리오

| # | 시나리오 | 단정 | 대응 AC |
|---|---|---|---|
| **N5** | 실음성 1턴 왕복 | `u1.wav` 주입 → 확정 전사문이 **실제 발화 내용과 일치**(스텁처럼 픽스처가 아니라) → `utterances`에 저장 → job 등록 | AC1 |
| **N6** | barge-in | agent 발화 중 오디오 입력 → **1초 안에** agent 출력이 끊긴다 | AC2 |
| **N7** | 실음성 3턴 완주 | 세션 하나에서 3턴, `sequence_no` 단조, 각 사용자 발화에 job 1건 | AC12 |
| **N8** | 실발화 → 실분석 결합 | `u1`+`u2` 주입 → 같은 `article` 패턴으로 **병합**, `frequency` +2. E계층 단정을 실음성 입력으로 재현 | AC3·AC4 |
| **N9** | 세션 롤오버 | Nova 스트림 수명 경계에서 세션이 이어지거나 깨끗히 닫힌다 | §7 Boundary |
| **N10** | 실제 자격증명 실패 거동 | 잘못된 키로 무응답형 실패를 재현 — 10초 상한이 실물에서도 동작하는가 | §4.2 실계측 |
| **N11** | 마이크 권한 거부 | `getUserMedia` reject → `microphone_permission_denied` 화면 (계측 없이 실브라우저에서 거부 시뮬레이션) | U1 실패 경로 |
| **N12** | 포맷 불일치 방어 | 잘못된 샘플레이트/코덱 프레임을 보냈을 때 세션이 조용히 죽지 않고 실패를 통보하는가 | §7 Boundary |

**N10~N12는 이번 회차의 A2(깨진 프레임 내성)와 B5(무응답 타임아웃)가 스텁으로 이미 메커니즘을
검증한 항목이다** — 실물에서 같은 방어가 작동하는지만 확인한다.

---

## 6. 캡틴 결정이 필요한 것

1. **N-0의 문서 확인을 누가 하는가** — 공식 문서 조사는 웹 접근이 필요하다.
2. **테스트 자산을 앱에 넣을지** — 음성 픽스처를 `app/frontend/public/`에 두면 `fetch`가
   간단해지지만 프로덕션 번들에 테스트 자산이 들어간다. 대안(base64 인라인)은 지저분하지만
   앱을 오염시키지 않는다.
3. **실물 마이크 1회 확인 시점** — F-3로 프레임 전송은 자동 검증됐으므로, 남은 것은 OS 권한
   대화상자와 실제 장치·스피커다. Nova 연동 후에 한 번에 확인하는 것이 효율적이다.
