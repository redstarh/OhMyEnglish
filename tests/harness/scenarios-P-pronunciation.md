# P계층 — 발음 오류 교정 (4차수 신설)

> 캡틴 지시(2026-08-26): "음성으로 테스트할 때 **잘못된 발음으로 대답할 경우 교정해주는
> 루틴이 있는지** 테스트하고, 없으면 수정한다. 정확한 음성과 약간 잘못된 발음이 있는 음성을
> **함께** 준비해서 테스트한다."
>
> 이 파일이 P계층의 정본이다. 결과는 `runs/2026-08-26-run-4.md`에 기록하고 향후 통합테스트에
> 반영한다.

---

## 1. 실측한 현재 구현 상태 (2026-08-26, 코드 직접 확인)

| 자산 | 상태 | 근거 |
|---|---|---|
| 분석 워커의 발음 카테고리 | **금지** — 프롬프트가 "쓰지 마라"고 명시 | `app/backend/app/services/analysis.py:48` `UNJUDGEABLE_CATEGORY = "pronunciation_intonation"`, 같은 파일 `:108` |
| 카테고리 열거에는 존재 | `pronunciation_intonation`이 유효값 | `app/backend/app/models/analysis.py:43` |
| Nova 대화 중 교정 규칙 | **있다. 단 발음 특화가 아니다** — "한 턴에 최대 1회 교정, 학습자 말을 인용하고 자연스러운 교정을 준 뒤 다시 말하게 한다" | `app/backend/app/audio_gateway/nova.py:77` `SYSTEM_PROMPT` rule 4 |
| 발음 전용 지시문 | **0건** — `SYSTEM_PROMPT`에 발음/억양 단어가 없다 | 같은 파일 grep |
| 제품 요구 | 오류 분류에 `발음/억양` **포함** | `docs/PRD.md:89`, `docs/requirements-summary.md:47` |
| 제품 비범위 | "공인 발음 시험 수준의 **음소 단위 채점**"은 MVP 이후 | `docs/PRD.md:39` |
| 복습 과제 매핑 | `pronunciation_intonation → shadowing` 의도만 문서화, 구현 0건 | `scenarios-E-agent-learning.md` L3 |

**요약**: 발음 오류를 **패턴으로 기억하는 경로는 의도적으로 없다**(전사문 텍스트만 받는
워커가 판정할 수 없다 — 설계서 §6.1 D1). 반면 **대화 중 교정 루틴은 존재하지만 발음을
겨냥하지 않는다**. 즉 "루틴이 있는지"의 답은 **문법 교정은 있고 발음 교정은 없다**다.

---

## 2. 사전 실측 (4차수 개시 전 확보) — 시나리오 설계의 전제

`spike_nova_protocol.py`로 Nova에 직접 왕복시켰다(앱 경로 아님, 어댑터 개입 없음).
**세 케이스 모두 `PASS`로 왕복은 성립했다.** 문제는 전사문의 내용이다.

| 픽스처 | 입력 오디오가 실제로 발음한 것 | Nova ASR 전사문 | agent 응답 |
|---|---|---|---|
| `p1a.wav` | "I think I found three very useful videos." (정확) | `i think i found three very useful videos.` | `That's great to hear. Those videos can be a valuable resource for improving your English.` |
| `p1m.wav` | "I **sink** I **pound** **sree** **bery** useful **bideos**." (음소 치환) | `i think i found three very useful videos.` ← **원문으로 복원됨** | `That's great to hear. Those videos can be a valuable resource for improving your English.` ← **p1a와 한 글자도 다르지 않다** |
| `p1k.wav` | 같은 문장을 한국어 음성(`Yuna`)이 읽음 (강한 한국어 억양) | `아이싱크 아이파운드 쓰리 베리 유스풀 비디오즈` ← **한글로 전사됨** | `Sorry, that part sounds a bit unclear. Could you please repeat or clarify your request?` |

원자료: `runs/2026-08-26-P-preflight/P-preflight-nova-asr.json` (세 케이스 요약 + `p1k` 이벤트
71건. `audioOutput`의 base64는 바이트 수만 남겼다).

### 여기서 확정된 것 3개

1. **약한 발음 오류는 전사문 경로에서 완전히 소실된다.** ASR 언어모델이 문맥으로 복원해
   버리므로 `utterances.transcript`에 흔적이 0이다. 전사문을 입력으로 받는 분석 워커는
   **원리적으로** 발음 오류를 볼 수 없다 — 금지 카테고리 설정이 실측으로도 옳았다.
2. **agent도 발음을 지적하지 않았다.** 음성을 직접 듣는 speech-to-speech 모델인데도 응답이
   정확 발음 케이스와 완전히 동일했다. `SYSTEM_PROMPT`에 발음 지시가 없으므로 예상된 결과다.
3. **강한 억양은 ASR의 언어 판별을 뒤집는다** — 영어 문장이 한글 전사문이 된다. 이 전사문이
   분석 워커에 들어가면 무슨 일이 벌어지는지가 **미검증이고, 실제 결함 후보다**(§4 P5).

### 이 실측의 한계 (기록해 둔다)

- `p1m`은 **원어민 음성이 다른 단어를 정확히 발음한 것**이다. 한국인이 /θ/를 /s/로 낼 때의
  중간값·불안정성은 재현하지 않는다.
- `p1k`는 **한국어 TTS가 영문자를 읽은 것**이다. 한국인이 영어를 말하는 것보다 억양이 과하다.
  "강한 억양" 상한 케이스로만 쓴다.
- 실제 캡틴 육성은 이 둘 **사이**에 있다. 따라서 P계층은 실물 마이크 1회로 보정해야 하며,
  그 전까지 판정은 "픽스처 기준"임을 명시한다.

---

## 3. 픽스처 — 정확/오류 쌍 (준비 완료)

같은 문장을 **발음만 바꿔** 3판씩 만들었다. 문장은 **문법적으로 완전히 옳다** — 그래야
분석 결과에 나오는 오류가 전부 발음 때문임을 단정할 수 있다.

```
tests/harness/fixtures/voice/
  p1a.wav  2.54s  "I think I found three very useful videos."                    (정확, Samantha)
  p1m.wav  2.49s  "I sink I pound sree bery useful bideos."                      (음소 치환: θ→s, f→p, v→b)
  p1k.wav  3.05s  같은 문장, 한국어 음성 Yuna                                     (강한 한국어 억양)
  p2a.wav  2.96s  "I finished the report and shared the results with my team."   (정확, Samantha)
  p2m.wav  3.04s  "I pinished the leport and shaled the lesults wis my team."    (f→p, r→l, θ→s)
  p2k.wav  3.79s  같은 문장, 한국어 음성 Yuna                                     (강한 한국어 억양)
```

전부 **16kHz · 16bit · mono WAV**(Nova 입력 규격). 재생성:

```bash
say -v Samantha -o /tmp/f.aiff "<문장>"      # 정확·음소치환판
say -v Yuna     -o /tmp/f.aiff "<문장>"      # 한국어 억양판
afconvert -f WAVE -d LEI16@16000 -c 1 /tmp/f.aiff p1a.wav
```

발음 오류는 **한국인 학습자의 전형적 치환**을 골랐다: /θ/→/s/, /f/→/p/, /v/→/b/, /r/↔/l/.
`p2`는 학습자의 목표 도메인(업무 보고) 문장이라 실사용에 가깝다.

---

## 4. 시나리오

전제: 백엔드 `VOICE_ADAPTER=nova`, 픽스처를 `app/frontend/public/harness/`에 임시 배치.
브라우저 주입 스크립트는 `handoff/HANDOFF-test-harness.md` §5의 N5 검증본을 재사용한다.

| # | 시나리오 | 단정 | 상태 |
|---|---|---|:--:|
| **P1** | 정확 발음 기준선 (`p1a`, `p2a`) — 앱 경로 | 전사문이 문장과 일치. 분석 findings **0건**(문법적으로 옳으므로). agent가 발음을 언급하지 않는다 | 미실행 |
| **P2** | 음소 치환 (`p1m`, `p2m`) — 앱 경로 | 전사문을 `p1a`/`p2a`와 **문자 단위로 비교**한다. 사전 실측대로 동일하면 **"앱은 발음 오류를 인지하지 못한다"가 앱 경로에서도 확정**된다 | 미실행 |
| **P3** | agent의 발음 교정 여부 (`p1m`, `p2m`) | agent 전사문·오디오에 발음 관련 언급(예: "the *th* sound")이 있는가. **기대: 없다.** 있으면 루틴이 존재하는 것이므로 그 근거를 기록한다 | 미실행 |
| **P4** | 강한 억양 (`p1k`, `p2k`) — 앱 경로 | 전사문이 한글이 되는가(사전 실측 재현). 화면 렌더가 깨지지 않는가. agent가 재요청("unclear")하는가 | 미실행 |
| **P5** | **한글 전사문의 분석 처리** ⚠️ | P4의 세션을 종료해 job을 돌린다. Claude가 한글 전사문에 대해 ① findings 0건으로 `done`인가 ② 금지 카테고리 `pronunciation_intonation`을 쓰려다 검증 실패 → **5회 재시도 후 `failed`**인가(AC W7 경로) ③ 엉뚱한 문법 오류를 발명하는가. **②·③이면 결함이다** | 미실행 |
| **P6** | 발음 오류의 오탐 (`p1m`+`p2m` 종단) | 문법적으로 옳은 문장인데 `error_patterns`에 패턴이 생기는가. 생기면 **오탐**이고 `frequency`를 오염시킨다 | 미실행 |
| **P7** | 정확/오류 쌍의 결과 화면 대조 | `p1a` 세션과 `p1m` 세션의 결과 화면이 동일한가. 학습자 관점에서 "잘못 말했는데 아무 피드백이 없다"가 재현되는가 (스크린샷 2장) | 미실행 |
| **P8** | `pronunciation_intonation` 주입 내성 | `inject_errors.py`로 그 카테고리를 **직접** 주입해 저장·조회·렌더가 깨지지 않는지 본다. 저장 경로 자체는 카테고리를 차별하지 않아야 한다 | 미실행 |

**P5가 4차수 P계층의 최우선이다.** 나머지는 "없음을 확인"하는 성격인데 P5만 **동작하는
코드가 실패할 수 있는 경로**다.

---

## 5. "없으면 수정한다"의 범위 — 3단계로 나눈다

캡틴 지시는 "없으면 수정"이지만 발음 교정에는 성질이 다른 세 층이 섞여 있다. 4차수 결과에
따라 아래로 분기한다. **③은 PRD 비범위와 충돌하므로 캡틴 결정 없이 착수하지 않는다.**

| 층 | 내용 | 조건 | 처리 |
|:--:|---|---|---|
| **①** | **결함 수정** — P5에서 job이 `failed`로 수렴하거나 P6에서 오탐 패턴이 생기면 | 실측으로 확인되면 | 4차수 수정 왕복을 연다(`claude_air_3-14`). O-1(선행 개행)도 함께 묶는다 |
| **②** | **프롬프트 수준 발음 교정** — `SYSTEM_PROMPT`에 "발음이 불명확하면 한 턴에 1회, 해당 소리를 짚어 다시 말하게 한다"를 추가 | P3에서 교정이 없음이 확인되면 | 작고 범위 안이다(rule 4의 확장). **단 기능 신설이므로 캡틴 승인 후** 수정 세션에 전달 |
| **③** | **발음 오류의 패턴 기억** — 음소 단위 채점·`pronunciation_intonation` 패턴 저장·shadowing 과제 | — | **PRD:39 비범위**. 게다가 전사문 경로로는 원리적으로 불가(§2-1)라서 오디오를 워커까지 보내는 아키텍처 변경이 필요하다. **캡틴 결정 사항** |

②를 넣으면 **1·2차수에서 검증한 C2(부분 전사문 UI)와 A1 프레임 계약은 영향받지 않는다**
(프롬프트만 바뀐다). 다만 agent 발화가 늘어나 `utterances` 행 수 기대값이 바뀌므로 E계층
단정을 델타로 유지해야 한다.

---

## 6. 판정 불가 / 캡틴 결정 대기

1. **"교정해줬다"의 판정 기준.** agent가 "Try saying *think* with your tongue between your
   teeth"라고 말하면 교정이다. 그런데 "Sorry, that sounds unclear. Could you repeat?"는
   교정인가 회피인가 — **P4에서 실제로 나온 응답이다.** 기준을 정해야 P3을 단정할 수 있다.
   → 제안: **틀린 소리를 지목하거나 다시 말하게 요구하면 교정으로 본다.** 단순 재요청은 아니다.
2. **실물 마이크 보정 1회.** §2의 한계 때문에 픽스처만으로는 캡틴 육성의 발음을 대표하지
   못한다. 캡틴이 `p1`/`p2` 문장을 직접 읽어 주면 P2·P4의 판정을 실물로 고정할 수 있다.
3. **픽스처 상주 배치.** P계층은 WAV 6개가 프론트에서 fetch 가능해야 한다. 3차수처럼 매번
   `public/harness/`에 복사·제거할지, 상주시킬지(프로덕션 번들 오염) 결정이 필요하다.
