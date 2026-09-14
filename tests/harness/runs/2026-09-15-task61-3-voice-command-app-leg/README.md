# 회차 — `TASK-61.3`: 브라우저 레그에서 「Oh My English, 종료」가 실제로 도는가

세션 `ohmyenglish-65` · 2026-09-15 KST · 계약 정본 결정 102 · 구현은 `TASK-61.1`(Done) ·
비용 승인 결정 40 · 절차 정본 `tests/harness/browser_leg.md`

> 무엇을 재는가: 단위 테스트가 확인한 것은 **어댑터가 tool 을 받으면 무엇을 하는가**이고, 이 회차가
> 재는 것은 **실물 Nova 가 그 tool 을 부르는가**임. 그 둘은 다른 물음이라 하나로 다른 하나를 대신하지
> 않음(결정 50 의 「스파이크만으로 닫지 않는다」와 같은 규율).

---

## 0. 상한과 해석 규칙 — 돌리기 전에 적음

### 스택

| 무엇 | 값 |
|---|---|
| DB | 검증 전용 `ohmyenglish_t613`(마이그레이션 024) · 계획·발음 패턴을 심지 않음 |
| 백엔드 | `:8012` · 래퍼 `/tmp/t613_app.py`(CORS origin 만 `:3001` 로 돌림) · `VOICE_ADAPTER=nova` · `WORKER_ENABLED=false` |
| 프론트 | 사본 `/tmp/fe-t613`(`:3001`) · 픽스처를 사본의 `public/harness/` 에 둠 |
| 브라우저 | 전용 Chrome `:9333` · fake media stream |
| 드라이버 | `p_app_path.py --port 9333 --url http://localhost:3001/ --wav <명령>,<확인>` — 모드를 주지 않는 일반 세션 |
| 공유 자원 | 공유 dev DB · `:3000` · `:8002` · 다른 세션의 Chrome(`:9222`)을 건드리지 않음 |

### 픽스처 — 이 회차에서 만들었음

macOS TTS 로 만들고 16kHz·모노로 변환했음(생성 명령을 그대로 적음 — 다시 만들 수 있어야 함):

```bash
say -v Samantha -o /tmp/x.aiff "Oh My English, end the session."   # vc01_cmd_en
say -v Samantha -o /tmp/x.aiff "Yes, please end it now."           # vc02_yes_en
say -v Yuna     -o /tmp/x.aiff "오 마이 잉글리시, 학습 종료할게."   # vc03_cmd_ko
say -v Yuna     -o /tmp/x.aiff "네, 종료해 주세요."                 # vc04_yes_ko
say -v Samantha -o /tmp/x.aiff "I want to end the meeting early tomorrow."  # vc05_nocmd_en
afconvert -f WAVE -d LEI16@16000 -c 1 /tmp/x.aiff tests/harness/fixtures/voice/<id>.wav
```

⚠️ 이것은 **명령을 또박또박 말한 음성**임 — 학습자의 발음 오류를 재는 픽스처가 아니므로 Qwen TTS
(`gen_pq_fixtures.sh`)를 쓰지 않았음. 재는 것이 「알아듣는가」이지 「발음이 나쁜가」가 아님.

### 팔 셋과 상한

| 팔 | 흘리는 픽스처 | 무엇을 재는가 |
|---|---|---|
| ARM-A | `vc01_cmd_en` → `vc02_yes_en` | 영어 명령이 tool 로 오고 확인을 거쳐 세션이 닫히는가 |
| ARM-B | `vc03_cmd_ko` → `vc04_yes_ko` | 한국어 명령이 같은 경로를 타는가 (결정 102 ④) |
| ARM-C | `vc05_nocmd_en` 하나 | 표지가 없는 발화가 명령으로 실행되지 «않는» 것 (반대 방향) |

상한: Nova **4세션**(팔 셋 + 예비 1) · Claude 0회(계획을 만들지 않음). 중간에 늘리지 않음.

### 해석 규칙

| 결과 | 읽는 법 |
|---|---|
| ARM-A 에서 `voice_command` 프레임이 `requested`·`confirmed` 둘 다 오고 세션이 닫힘 · `utterances` 에 `voice_command` + `command_confirmation` | AC#1 충족 |
| `requested` 만 오고 `confirmed` 가 안 옴 | 코치가 둘째 호출을 하지 않은 것 ⇒ 프롬프트 규율의 결함 후보로 보고하고 AC 를 닫지 않음 |
| tool 이 아예 안 옴 | 명령을 알아듣지 못한 것 ⇒ 전사문을 먼저 읽어 **표지가 어떻게 전사됐는지** 가름. 결함 후보로 보고 |
| `requested` 에서 세션이 닫힘 | ⛔ 심각 — 확인 절차가 실사용에서 무력화된 것. 코드 결함으로 보고 |
| ARM-C 에서 세션이 닫히거나 `voice_command` 가 저장됨 | ⛔ 심각 — 오인식. AC#3 실패로 보고 |
| ARM-B 의 한국어 전사가 표지로 인식되지 않음 | 관측값으로 적고 AC#2 를 「인식되지 않음」으로 판정(결함 후보) — 결정 102 ④를 지키려면 후속이 필요함 |
| `session_failed` | 환경 고장이라 판정하지 않음 |

⚠️ 표본 1 로 비율을 말하지 않음. 각 팔이 답하는 것은 「한 번이라도 그렇게 되는가」임.
⚠️ `TASK-65` 의 함정을 기억함 — 파일이 아니라 **순서**가 ASR 언어를 정함. ARM-B 는 한국어를 첫
발화로 주므로 그 조건을 만족함.

---

## 1. 쓴 것 — 상한을 넘기지 않았음

Nova **4세션**(ARM-A · ARM-A2 · ARM-C · ARM-B) · Claude **0회** · `session_failed` 0.
⚠️ ARM-A 가 대기 부족으로 판정을 못 내 **예비 1회를 ARM-A2 로 썼음** — 그래서 정확히 상한 4 임.

| 팔 | 세션 | 흘린 것 | 코치 오디오 | 세션이 닫혔나 |
|---|---|---|--:|---|
| ARM-A | `9c304d56` | 명령만(둘째가 안 흘렀음) | **0** | 아니오(드라이버가 눌러 닫음) |
| ARM-A2 | `9b2a9b8f` | 명령 → 확인 | **0** | **예 — tool `confirmed` 가 닫았음** |
| ARM-C | `20b6fb28` | 표지 없는 발화 하나 | 68 | 아니오 |
| ARM-B | `85fa4736` | 한국어 명령 → 확인 | **0** | **예 — tool `confirmed` 가 닫았음** |

## 2. 확인된 것 셋

1. **실물 Nova 가 제어 tool 을 부른다.** 네 팔 모두에서 `voice_command` 행이 남았음 — 그 행은 tool 이
   실어 온 `heard` 로만 생기므로 tool 도착의 직접 증거임. ⇒ 결정 46 의 수단(전사문 패턴이 아니라 tool)이
   실사용에서 성립함.
2. **`confirmed` 가 세션을 닫고 `command_confirmation` 이 남는다.** ARM-A2·ARM-B 에서 세션이
   `completed` 로 닫혔고 확인 발화가 그 유형으로 저장됐음.
3. **한국어 명령이 같은 경로를 탄다**(결정 102 ④). ASR 이 표지를 `오마이잉글리시` 로 **붙여** 적었고
   앱의 판정이 공백을 지워 비교하므로 잡혔음 — 그 정규화가 실측으로 값을 했음.

## 3. ⛔ 결함 다섯 — 재현 절차와 함께

| # | 결함 | 관측 | 심각도 |
|--:|---|---|---|
| D1 | **같은 발화가 두 번 저장된다.** 전사문 경로(표지 판정)와 tool 경로(`heard`)가 각각 적음 | ARM-A2·ARM-B 에 `voice_command` 행이 **2건**씩(구두점만 다름) | HIGH |
| D2 | **확인 답이 `learning` 으로도 저장된다** — 분석기가 「네 종료해주세요」를 교정 대상으로 본다 | ARM-A2 `yes please end it now.` · ARM-B `네 종료해주세요` 가 `learning` 으로 남음 | HIGH |
| D3 | **코치가 확인 질문을 소리로 말하지 않는다.** tool 만 부르고 발화가 0 임 | ARM-A·A2·B 에서 `audio: 0` — 학습자는 무엇을 확인해야 하는지 듣지 못함 | HIGH |
| D4 | **명령으로 분류된 발화에 `final` 프레임을 보내지 않는다** — 화면에 아무 줄도 남지 않고 학습자는 접수됐는지 알 수 없다 | ARM-A2·ARM-B 의 화면 줄이 **빈 배열**이고 드라이버도 그 발화를 못 봤음(첫 final 대기가 상한까지 갔음) | HIGH |
| D5 | **모델이 표지 없이도 명령으로 읽는다.** 앱은 tool 을 그대로 신뢰한다 | ARM-C: `i want to end the meeting early tomorrow.` 에 코치가 *"Oh My English, I hear you want to end the meeting early. Is that right? Please say yes to confirm."* 로 답하고 tool 을 불렀음(`voice_command` 행이 남음) | HIGH |

**D5 에서 세션이 닫히지 않은 이유가 이 설계의 값어치다** — 확인이 오지 않았으므로 앱이 닫지 않았음.
⇒ 결정 102 ③(음성 확인)이 **오인식을 실제로 막았음.** 그것이 이 회차의 가장 값어치 있는 관측임.
⚠️ 그러나 D5 는 「확인만 있으면 된다」로 읽히지 않음 — 학습자가 무심히 「yes」라고 답하면 닫힌다.
표지 판정을 **앱이 tool 에도 적용**해야 한다는 것이 D5 의 요구임.

**재현 절차**(넷 다 같음): 위 §0 스택을 세우고 해당 팔의 픽스처로 `p_app_path.py` 를 돌린 뒤
`utterances` 를 `order by created_at` 으로 읽고 화면 줄과 `recv.audio` 를 함께 본다.

⚠️ **표지의 ASR 이 불안정하다** — ARM-A 는 `all my english`, ARM-A2 는 `oh my english` 로 왔음
(같은 픽스처 · 2회 중 1회 실패). 즉 앱의 표지 판정만으로는 영어 명령을 절반 놓친다.
그럼에도 D5 가 요구하는 「tool 에도 표지를 요구한다」와 이 관측이 **충돌한다** — 표지가 전사문에서
깨지면 정상 명령까지 막힌다. ⇒ 이 상충은 다음 태스크가 결정으로 다뤄야 함(§5).

## 4. 판정

| AC | 판정 |
|---|---|
| `TASK-61.3` AC#1(영어 종료 명령이 확인을 거쳐 세션을 닫는다) | **충족** — ARM-A2 가 관측했음 |
| AC#2(한국어 명령의 전사문을 관측하고 인식되는지 판정한다) | **충족** — 인식됨(`오마이잉글리시`). ARM-B 가 관측했음 |
| AC#3(명령이 아닌 학습 발화로 세션이 닫히지 않는다) | **충족** — ARM-C 에서 닫히지 않았음. ⚠️ 다만 모델이 그것을 명령으로 읽은 것은 D5 로 남김 |
| AC#4(회차 기록·정리) | 충족 — 이 문서와 §6 |

⇒ **`TASK-61.3` 은 닫는다. 결함 다섯은 새 태스크로 남긴다** — 회차의 판정과 결함의 처리를 같은
태스크에 섞지 않는다(원장 규약).

## 5. 다음 태스크에 넘기는 판단 하나

D1·D2·D4 는 구현 결함이라 고치면 되고, **D3·D5 는 판단이 앞에 있음**:

- D3: 코치가 말하지 않는 것을 프롬프트로 고칠지(먼저 말하고 그 다음 tool 을 부르게 함), 아니면 앱이
  확인 문구를 내보낼지(TTS 가 아니라 화면 문구). 후자는 결정 102 ③의 「음성 확인」을 좁힘.
- D5: tool 에도 표지를 요구하면 오인식을 막지만, 표지의 ASR 이 불안정해(2회 중 1회) **정상 명령까지
  막는다.** 둘 다 대가가 있어 사용자 판단이 필요함.

## 6. 정리와 무변경 확인 — 직접 돌려 얻은 값

| 무엇 | 확인 |
|---|---|
| `:9333` · `:3001` · `:8012` | 전부 HTTP `000` |
| 검증 전용 DB | `drop database ohmyenglish_t613` 완료 · 남은 DB 는 `ohmyenglish` · `_smoke` · `_test` 뿐 |
| `/tmp` 사본 | `fe-t613` · `chrome-t613` · `t613_app.py` · `vc_tts` 삭제 |
| 공유 dev DB | 회차 전후가 같음 — `17 · 7 · 9 · 6 · 128 · 15` · `schema_migrations` 22 |
| 다른 세션의 Chrome | `:9222` 가 여전히 200 |
| 리포에 더한 것 | 픽스처 다섯(`tests/harness/fixtures/voice/vc0*.wav`) — 생성 명령을 §0 에 적었음 |
| 실물 사용 | Nova 4세션 · Claude 0회 |
