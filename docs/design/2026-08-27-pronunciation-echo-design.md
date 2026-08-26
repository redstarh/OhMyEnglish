# 발음 시범·재발화 설계서 (Pronunciation Echo)

- 작성: 2026-08-27
- 트랙: **A (풀)** — 새 서브시스템, 어댑터 포트 확장, 새 테이블
- 상태: **초안 — 검토 전**
- 요구사항: `docs/PRD.md` **v1.1 §10** (R10-1~8, AC10-1~5) · `docs/requirements-summary.md` v1.1 `발음 교정 학습`
- 선행 실측: `tests/harness/runs/2026-08-26-run-4.md` §P계층(부재 확정) · `tests/harness/runs/2026-08-27-P-tooluse-spike/`(전송 수단 실증)
- 캡틴 승인 이력: 발음 판정 주체 = Nova + 결정론 보조 신호 / 기록 = Nova 이벤트 확장 / 교정 예산 = B안(일반 세션 문법 우선 + 발음 집중은 추가 학습 분리) — 3건 모두 2026-08-27 대화형 승인

---

## 1. 범위

**한 문장**: 학습자가 발음을 틀렸을 때 Agent가 **올바른 발음으로 그 문장을 다시 읽어주고**, 따라 말한 결과를 **기록해 다음 학습에 쓰이게** 한다.

### 범위에 넣지 않는 것

음소 단위 점수·발음 등급·원어민 유사도(`PRD.md:39` 비범위). 오디오를 분석 워커로 보내는 채점 파이프라인. 쉐도잉 콘텐츠(YouTube·클립) 수집 — `shadowing_items`는 별도 단계다.

### 요구사항 #2와의 관계

이 설계는 **기록까지** 담당하고, 그 기록을 **다음 세션 계획에 쓰는 것**은 `2026-08-25-learning-coach-agent-design.md`(§11 R11-9)가 담당한다. 두 설계의 접합면은 `error_patterns`의 `pronunciation_intonation` 행 하나다 — 그 이상 결합하지 않는다.

---

## 2. 스파이크 결과 — 이 설계의 전제 (2026-08-27 실측)

`spike_nova_protocol.py --wav p1m.wav --tools`를 1회 돌렸다. 원자료: `tests/harness/runs/2026-08-27-P-tooluse-spike/P-tooluse-nova-events.json`(git 추적).

입력은 `p1m.wav` — 같은 문장을 음소 치환해 발음한 것(θ→s, f→p, v→b. 실제 발음 `I sink I pound sree bery useful bideos.`).

### 관측된 이벤트 순서

```text
userSpeechStart → userSpeechEnd
contentStart(TEXT, role=USER, FINAL) → textOutput 'i think i found three very useful videos.'
contentStart(TOOL, role=TOOL) → toolUse → contentEnd(stopReason=TOOL_USE)
contentStart(TEXT, ASSISTANT) → textOutput 'Great! Let\'s work on that sentence.
                                            Say this after me: "I think I found three very useful videos."'
contentStart(AUDIO, ASSISTANT) → audioOutput ×81            ← 올바른 발음 시범 음성
contentStart(TEXT, ASSISTANT) → textOutput 'Now you repeat that sentence for me.'
contentStart(AUDIO, ASSISTANT) → audioOutput ×20 → contentEnd(END_TURN)
completionEnd
```

### 확정된 것 6개

| # | 발견 | 설계에 미치는 영향 |
|---|---|---|
| **F1** | **`promptStart.toolConfiguration`이 받아들여진다.** 거부되지 않았고 `toolUse` 이벤트가 `contentStart(type=TOOL, role=TOOL)` … `contentEnd(stopReason=TOOL_USE)`로 감싸여 도착했다. `inputSchema.json`은 **JSON 문자열**이어야 한다 | R10-2(결과 기록)의 전송 수단이 **존재한다.** 설계가 구조화 이벤트로 갈 수 있다 |
| **F2** | **지시하면 Nova가 실제로 교정한다.** 문장 전체를 올바른 발음으로 다시 읽어주고("Say this after me: …") 따라 말하기를 요구했다 | **4차수의 "Nova는 발음을 지적하지 않았다"는 능력 부재가 아니라 지시 부재였다.** 개입 지점이 `nova.py:77` 한 곳이라는 판단이 실측으로 확인됐다. R10-1이 프롬프트만으로 성립한다 |
| **F3** ⚠️ | **Nova는 재발화 *전에* tool을 부른다.** `spoken_form: "[awaiting user repetition]"`, `outcome: "pending"`. 즉 tool 호출 1건 ≠ 판정된 시도 1건 | 시도를 **2단계 생명주기**로 모델링해야 한다(§3.2). 단일 호출을 결과로 저장하면 전부 미판정으로 쌓인다 |
| **F4** ⚠️ | **Nova가 스키마 enum을 어겼다.** 스키마는 `correct\|incorrect\|unclear`인데 `pending`을 냈다 | ① 계약에 `pending`을 **정식 값으로 포함**한다(모델이 자연히 내는 값을 거짓으로 만들지 않는다) ② tool 페이로드를 **신뢰하지 않고 검증**한다 — Phase 1 W7 방식 재사용 |
| **F5** | **ASR은 여전히 원문을 복원했다.** `p1m` 전사문이 `i think i found three very useful videos.`로, 4차수와 동일 | R10-3(전사문 경로는 발음을 판정하지 않는다)이 재확인됐다. **tool 호출이 유일한 구조화 기록원이다** |
| **F6** ⚠️ | **`toolResult`를 돌려보내지 않았는데 세션이 `END_TURN`으로 정상 종료했다** | 이번 1회 관측이다. 다중 턴에서도 안전한지는 **미검증** → §9 미결 1 |

### 이 스파이크가 바꾼 것

4차수는 "발음 교정 루틴이 없다"까지 확정했고, 캡틴 결정은 "수정 보류, 기록만"이었다. 그때의 판단 근거 중 하나가 **"speech-to-speech 모델인 Nova도 발음을 지적하지 않았다"**였는데, 스파이크가 그것이 **프롬프트 부재의 결과**임을 보였다. 부재의 성질이 "능력 없음"에서 "지시 없음"으로 바뀌었고, 그래서 이 기능의 비용 추정이 크게 내려간다.

---

## 3. 구조와 데이터 흐름

### 3.1 판정은 Nova가, 보조 신호는 Gateway가

| 담당 | 하는 일 | 왜 |
|---|---|---|
| **Nova (판단)** | 발음이 틀렸는가, 어떤 소리가 문제인가, 시범 문장, 재발화가 맞았는가 | 오디오를 직접 듣는 유일한 구성요소다. 전사문에는 흔적이 0이다(F5) |
| **Gateway (결정론)** | 보조 신호 2개 감지, tool 페이로드 검증, 시도 생명주기 관리, 저장 | 놓침이 조용히 일어나면 안 된다. 회귀 테스트가 가능해야 한다 |
| **분석 워커** | **관여하지 않는다** | `services/analysis.py:48`이 이 카테고리를 산출하지 않는 것은 옳다(F5) |

**보조 신호 2개** (R10-4) — Gateway가 확정 USER 전사문에서 결정론적으로 판정한다.

| 신호 | 감지 방법 | 4차수 근거 |
|---|---|---|
| `korean_transcript` | 확정 USER 전사문에 한글 음절이 섞였다 | `p1k`가 `아이싱크 아이파운드 쓰리 베리 유스풀 비디오즈`로 전사됐다 |
| `agent_reprompt` | Nova가 재요청 취지의 발화를 냈다 | `p1k`에서 `I'm sorry, I didn't catch that clearly…`가 실제로 나왔다 |

보조 신호는 **판정을 대체하지 않는다.** 신호가 떴는데 `toolUse`가 오지 않으면 — Nova가 놓친 경우 — Gateway가 `outcome='unclear'`, `signal_source='<신호명>'`인 시도 1건을 기록한다. 그것이 다음 세션 계획에 "발음이 안 들린 적이 있다"를 전달하는 유일한 경로다.

`agent_reprompt`는 문구 매칭이라 취약하다 — 그래서 이 신호는 **기록에만** 쓰고 개입 트리거로는 쓰지 않는다(§9 미결 2).

### 3.2 시도 생명주기 — F3에 대한 답

Nova가 두 시점에 tool을 부를 수 있고(시범 시점 / 판정 시점) 두 번째가 오지 않을 수도 있다. 그래서 Gateway가 상태 기계를 갖는다.

```text
toolUse(outcome=pending)          → pronunciation_attempts INSERT (outcome='pending')
toolUse(outcome=correct|incorrect|unclear)
                                  → 같은 세션의 최신 pending 행을 UPDATE
                                     (없으면 새 행을 그 outcome으로 INSERT)
세션 종료 시 pending 행이 남아 있으면 → outcome='unclear'로 수렴시킨다
```

**마지막 규칙이 이 설계의 핵심 방어다.** `pending`을 영구히 남기면 "판정되지 않은 시도"가 조용히 쌓여 숙련도 계산을 왜곡한다. 학습자가 대답하지 않고 세션을 끝낸 것도 정보이므로 `unclear`로 남긴다 — 없는 일로 만들지 않는다.

`outcome='incorrect'`가 되는 순간 `error_patterns`에 `pronunciation_intonation` 행을 upsert한다(§4.3). **임계값을 두지 않는다** — 문법 오류도 1회에 패턴이 생기므로 같은 규약이다(`PRD.md:90`).

### 3.3 교정 예산 — 캡틴 승인 B안

`agent-system-prompt.md:19`가 "한 턴에 최대 1~2개 교정"을 정해 두었다. 발음이 들어오면 문법과 예산을 다툰다.

| 세션 종류 | 발음 개입 | 근거 |
|---|---|---|
| **일반 Speaking 세션** | 보조 신호가 떴을 때만 즉시 개입. 그 밖에는 문법 우선 | 안 들리는 일은 드문데 매 턴 예산을 뺏기면 핵심 루프가 흔들린다 |
| **추가 학습 `발음 집중`** | 주 활동. 시범·재발화를 반복한다 | `PRD.md:75`에 추가 학습 메뉴가 이미 있다. h-doc의 쉐도잉 요구와 맞는다 |

구현 위치는 **지시문 가변부**다 — 학습 코치 설계서 §5.2가 만드는 그 자리에 "오늘 발음 개입 모드"를 한 줄 얹는다. 두 설계가 같은 통로를 쓰고 새 통로를 만들지 않는다.

### 3.4 지연 — 사용자 대기 경로에 추가 호출이 없다

| 경로 | 추가 비용 |
|---|---|
| 발음 판정 | **0** — Nova가 대화 턴 안에서 한다. 별도 호출이 아니다 |
| 시범 음성 | **0** — Nova의 기존 `audioOutput`이다 |
| 기록 | DB INSERT/UPDATE 1회. 음성 경로를 막지 않는다(`PRD.md:112` 유지) |
| 보조 신호 감지 | 확정 전사문 1건에 대한 정규식 1회 |

**Claude 호출이 추가되지 않는다.** 이 설계는 `PRD.md:111`의 모델 분리(Nova=실시간, Claude=분석)를 그대로 따른다.

---

## 4. 상세 기능 정의

### 4.1 Nova 지시문 — 발음 규칙 (R10-1)

`nova.py:77` `SYSTEM_PROMPT`의 **고정부**에 발음 규칙을 넣고, 개입 강도는 가변부(§3.3)가 정한다. 스파이크에서 실효를 확인한 문구를 기준으로 한다.

담을 것: ① 어떤 소리가 틀렸는지 짚는다 ② **문장 전체**를 올바른 발음으로 다시 읽어준다 ③ 따라 말하도록 요구한다 ④ 재발화를 듣고 판정한다 ⑤ 두 시점(시범·판정)에 tool을 부른다 ⑥ 한 턴 1~2회 교정 상한을 넘지 않는다.

⚠️ **문구는 발명값이다.** 스파이크가 검증한 것은 "지시하면 한다"이고, 최종 문구의 효과는 실물 1회로 확인해야 한다(§9 이월).

### 4.2 tool 계약 (R10-2)

`report_pronunciation_coaching` — Nova가 부르고 Gateway가 받는다.

| 필드 | 타입 | 비고 |
|---|---|---|
| `target_form` | string | 올바른 발음으로 읽어준 문장. **필수** |
| `spoken_form` | string | 학습자가 어떻게 들렸는지. 시범 시점에는 placeholder일 수 있다(F3) |
| `target_sound` | string | 문제가 된 소리의 재사용 가능한 키(예: `th_as_s`). `pattern_key` 생성의 재료 |
| `outcome` | enum | `pending` \| `correct` \| `incorrect` \| `unclear`. **`pending`은 F4 실측을 반영해 정식 값이다** |

**검증 규칙 (F4 대응)** — 페이로드를 신뢰하지 않는다.

- `outcome`이 열거값 밖이면 `unclear`로 **강등**하고 원문을 로그에 남긴다. 세션을 깨뜨리지 않는다 — 1차수 I-5에서 모델 출력에 엄격 검증을 걸었다가 발화가 5회 재시도 끝에 `failed`가 된 전례가 있다.
- `target_form`이 비면 그 tool 호출을 **버린다**(시범이 없는 시범 기록은 의미가 없다).
- `target_sound`가 비면 `pattern_key` 생성을 건너뛰고 시도만 기록한다.

### 4.3 패턴 연결 (R10-6 → R11-9)

`outcome='incorrect'`일 때 `error_patterns`를 upsert한다.

- `category = 'pronunciation_intonation'`
- `pattern_key = 'pronunciation_' || target_sound` (기존 §5.6 규약: 기존 키 재사용 우선, 신규만 생성)
- `frequency`는 기존 규약대로 occurrence 수 재계산이 아니라 **시도 수 기준**으로 센다 — 발음 시도는 `error_occurrences`를 만들지 않기 때문이다. 이 차이를 스키마 문서에 명시한다.
- `next_review_at`은 학습 코치 설계서 §4.1의 갱신 주체가 다룬다. 이 설계는 값을 쓰지 않는다.

### 4.4 오디오 (R10-7)

시범 음성과 학습자 재발화 오디오를 **저장하지 않는다.** 남는 것은 `target_form`(텍스트)과 판정이다. `PRD.md:107`의 opt-in 미저장 정책이 그대로 유지되고, 이 설계는 그 정책을 건드리지 않는다.

---

## 5. 스토리보드

### 5.1 일반 세션 — 보조 신호가 떴을 때 (S1~S7)

| 스텝 | 화면 | 음성 | 저장 |
|:--:|---|---|---|
| **S1** | 전사문 영역에 회색 "듣고 있어요" | 학습자: *"I sink I pound sree bery useful bideos."* | — |
| **S2** | 확정 전사문이 일반 텍스트로 굳는다 | — | `utterances`(user, learning) |
| **S3** | **발음 배지**가 그 전사문 옆에 붙는다 — `발음 교정 중` | Agent: *"Let's work on that sentence."* | `pronunciation_attempts` INSERT (`pending`) |
| **S4** | 시범 문장이 **큰 글씨로 강조**되고 재생 표시가 돈다 | Agent: *"Say this after me: **I think I found three very useful videos.**"* | — |
| **S5** | `따라 말해보세요` 안내 + 마이크 활성 표시 | Agent: *"Now you repeat that sentence for me."* | — |
| **S6** | 학습자 전사문이 시범 문장 **바로 아래 나란히** 표시된다 | 학습자 재발화 | `utterances` |
| **S7** | 배지가 결과로 바뀐다 — `좋아요` / `다시 연습할 거예요` / `잘 안 들렸어요` | Agent: 한 문장 피드백 | 같은 행 UPDATE (`correct`/`incorrect`/`unclear`) |

**S3의 배지가 이 기능의 유일한 새 UI 요소다.** 전사문 영역·마이크 상태·재생 표시는 이미 있는 것을 쓴다.

### 5.2 결과 화면 — 4차수가 드러낸 공백을 메운다

4차수 P7에서 정확 발음 세션과 오류 발음 세션의 결과 화면이 **똑같이 "표시할 교정이 없습니다."** 였다. 학습자 관점에서 "잘못 말했는데 아무 피드백이 없다"가 바로 이 화면이다.

| 영역 | v1.1에서 추가 |
|---|---|
| 교정 카드 목록 | 문법 교정 카드 아래에 **발음 카드**가 붙는다 — 시범 문장, 어떤 소리였는지, 결과 |
| 빈 상태 문구 | 발음 시도가 있으면 "표시할 교정이 없습니다."를 **쓰지 않는다** |
| 다음 복습 | 발음 패턴도 복습 목록에 나타난다(학습 코치 설계 담당) |

### 5.3 추가 학습 `발음 집중` (§3.3)

`PRD.md:75`의 추가 학습 선택 패널에 항목 하나를 더한다. 진입하면 S3~S7이 주 활동으로 반복되고, 문법 교정은 억제된다. 문장은 학습자의 **누적 발음 패턴**에서 고른다(없으면 폴백 뱅크).

---

## 6. 스키마 변경

### 6.1 새 테이블 1개

**`pronunciation_attempts`** — 발음 시범 1회와 그 재발화 결과.

| 컬럼 | 타입 | 비고 |
|---|---|---|
| `id` | uuid | PK, `default gen_random_uuid()` |
| `session_id` | uuid | FK → `learning_sessions`, **not null** |
| `utterance_id` | uuid | FK → `utterances`, **nullable** — 시범을 유발한 발화. 보조 신호만으로 만든 행은 연결될 발화가 없을 수 있다 |
| `pattern_id` | uuid | FK → `error_patterns`, nullable — `target_sound`가 있고 `incorrect`일 때 연결된다 |
| `target_form` | text | not null. 올바른 발음으로 읽어준 문장 |
| `spoken_form` | text | nullable — 시범 시점에는 아직 없다(F3) |
| `target_sound` | text | nullable — `pattern_key` 생성 재료 |
| `outcome` | text | CHECK `in ('pending','correct','incorrect','unclear')` |
| `signal_source` | text | CHECK `in ('nova_tool','korean_transcript','agent_reprompt')` — 이 행이 무엇 때문에 생겼는지 |
| `created_at` / `resolved_at` | timestamptz | `resolved_at`은 `pending`을 벗어난 시각. nullable |

**`pattern_attempts`(학습 코치 설계 §8.1)와 합치지 않는 이유**: 그 테이블은 `unique(pattern_id, utterance_id)`로 "패턴이 있는 발화의 재발화"를 세는데, 발음 시도는 ⓐ 패턴이 아직 없을 수 있고 ⓑ tool 호출이 발화가 아니며 ⓒ `target_form`·`signal_source`처럼 그 테이블에 자리가 없는 필드를 갖는다. 억지로 합치면 두 컬럼이 대부분 null인 테이블이 된다.

### 6.2 인덱스

`(session_id, outcome)` — 세션 종료 시 `pending` 행을 찾는 경로(§3.2)가 유일한 뜨거운 조회다.

### 6.3 CHECK 확장 없음 · 컬럼 추가 없음

`error_patterns.category`의 `pronunciation_intonation`은 **이미 CHECK에 있다**(001, `models/analysis.py:43`). 이 설계는 그 값을 처음 **사용**하는 것이고 스키마를 넓히지 않는다.

### 6.4 마이그레이션 번호

학습 코치 설계서가 `002_learning_coach.sql`을 예약했다. 이 설계는 **`003_pronunciation_echo.sql`**로 쌓는다 — 두 설계의 구현 순서가 바뀌어도 파일명 추적(`migrate.py`)이 그대로 동작한다.

### 6.5 스키마 문서 정합화 (모순 2 해소)

`database-schema.md:137`이 "`pronunciation_intonation` — 텍스트 전사문만 다루는 첫 슬라이스 워커는 산출하지 않음"이라 적었다. **거짓이 아니지만 범위 한정 서술이다** — 이 설계가 산출 주체를 정하므로 단계 표기를 갱신한다: *워커는 산출하지 않는다(전사문에 흔적이 0). Nova tool 경로가 산출한다.*

같은 취지로 `2026-08-25-first-slice-acceptance-criteria.md:108`과 `2026-08-24-first-vertical-slice-design.md:229`에도 "그 판단은 Phase 1 범위에 대한 것"임을 명시한다. **두 문서의 원래 문장을 부정하지 않는다** — 당시 진술은 옳았다.

---

## 7. 4 Lenses 검증

### Contract

- **tool 핸들러**: 입력은 검증되지 않은 Nova 페이로드. 출력은 `pronunciation_attempts` 0 또는 1행. **예외를 세션 바깥으로 던지지 않는다** — 발음 기록 실패가 대화를 끊으면 안 된다.
- **시도 행 불변조건**: `target_form`은 비지 않는다. `outcome='pending'`인 행은 **세션 종료 시점에 존재하지 않는다**(§3.2가 수렴시킨다). `resolved_at`은 `outcome != 'pending'`일 때만 non-null.
- **보조 신호 감지**: 확정 USER 전사문 1건 → 신호 0~2개. **부작용이 없다**(순수 함수).
- **포트**: 새 이벤트는 `AdapterEvent` 유니온에 더해지고, 기존 4종의 의미를 바꾸지 않는다.

### Boundary

- **타입 경계**: Nova tool `content`는 **JSON 문자열**로 온다(실측). 파싱 실패·열거값 위반·필수 필드 누락을 전부 방어한다(§4.2). F4가 실제로 위반을 냈으므로 가정이 아니라 관측이다.
- **시스템 경계**: `toolConfiguration`은 `promptStart`에만 실린다 — 세션 중간에 tool을 바꿀 수 없다. 그래서 발음 모드 전환은 tool 목록이 아니라 **지시문**으로 한다(§3.3).
- **시간 경계**: 시범(S3)과 판정(S7)이 **다른 턴**에 있다. 그 사이 세션이 끊기면 `pending`이 남고 §3.2가 수렴시킨다.
- **학습/명령 경계**: 발음 시도는 `utterance_type='learning'` 발화에서만 만든다 — `voice_command` 발화는 분석 대상이 아니다(Phase 1 §6.2 D4 규약 계속).
- **모드 경계**: 스텁 어댑터는 tool 이벤트를 **만들지 않는다**. 스텁 모드 화면에 발음 배지가 끼어들면 1·2차수 C2 검증이 바뀐다 — 수정 세션이 3차수에 세운 "스텁은 새 이벤트를 흘리지 않는다" 원칙을 그대로 따른다.

### Failure

- **tool이 오지 않음**: 보조 신호가 떴다면 `unclear` 행을 남긴다. 신호도 없으면 아무 일도 없다 — 정상이다.
- **tool이 두 번째로 오지 않음**: `pending`이 세션 종료 시 `unclear`로 수렴한다. **이것이 이 설계에서 가장 자주 밟힐 경로다**(F3).
- **페이로드가 깨짐**: 강등 또는 폐기(§4.2). 세션은 계속된다.
- **패턴 upsert 실패**: 시도 행은 남고 `pattern_id`가 null이다. 기록이 통째로 사라지는 것보다 낫다.
- **부분 실행**: 시도 INSERT와 패턴 upsert를 **한 트랜잭션**에 둔다. 절반만 반영된 상태를 만들지 않는다.
- **Nova가 발음을 과잉 교정**: 교정 예산 상한(§3.3)이 프롬프트에만 있어 **코드로 강제되지 않는다.** 이 설계의 약점이다 — §8 D5 참조.

### Dependency

- **초기화 순서**: 003 마이그레이션 → 지시문 갱신 → 어댑터 tool 설정. 순서를 바꾸면 tool 이벤트가 저장될 곳이 없다.
- **읽기 전 갱신**: 학습 코치의 계획 생성이 발음 패턴을 읽으려면 시도가 먼저 기록돼야 한다. 두 설계의 접합면이 `error_patterns` 한 곳인 이유다(§1).
- **`session_id` 의존**: 시도는 세션 없이 존재할 수 없다(not null). 세션 종료 기록보다 먼저 쓰인다.
- **단독 테스트 가능성**: tool 핸들러와 보조 신호 감지는 **Nova 없이** 단위 테스트한다 — 페이로드를 픽스처로 만든다. 스파이크가 남긴 실제 페이로드를 그 픽스처의 원본으로 쓴다(`P-tooluse-nova-events.json`).

---

## 8. 이 설계의 약점 (D5)

1. **교정 예산이 코드로 강제되지 않는다.** "한 턴 1~2회"는 프롬프트 규칙이고 Nova가 어길 수 있다. 관측 수단은 있다(시도 행 수) — 세션당 시도가 비정상적으로 많으면 로그 경보로 잡는 것을 이월한다.
2. **`agent_reprompt` 신호가 문구 매칭이다.** Nova 문구가 바뀌면 조용히 놓친다. 그래서 기록 전용이고 트리거로 쓰지 않는다(§3.1).
3. **판정 품질을 회귀 테스트할 수 없다.** Nova 판정은 비결정적이라 자동 테스트는 "규칙이 전달됐고 이벤트 스키마가 맞다"까지다. 실제 교정이 학습자에게 맞는지는 실물 1회 판정이 필요하다 — 이미 대기 중인 캡틴 게이트(실물 마이크)와 묶는다.
4. **픽스처가 합성음이다.** `p1m`은 원어민이 다른 단어를 정확히 발음한 것이라 한국인의 중간값·불안정성을 재현하지 않는다(4차수 §한계). 캡틴 육성 1회로 보정해야 일반화된다.

---

## 9. 수용 시나리오

**PS1 — tool 전송 경로가 관통한다**
Given `toolConfiguration`이 실린 세션에서, When Nova가 `report_pronunciation_coaching`을 부르면, Then Gateway가 `pronunciation_attempts` 1행을 만든다. (스파이크가 이미 Nova 쪽 절반을 실증했다.)

**PS2 — 시범이 문장 전체를 담는다** (AC10-1)
Given 발음 개입이 일어났을 때, Then `target_form`이 **문장**이고 단어 조각이 아니다. 화면에 강조 표시된다.

**PS3 — 재발화 결과가 남는다** (AC10-2)
Given 시범 후 학습자가 다시 말했을 때, Then 같은 행이 `correct|incorrect|unclear` 중 하나로 UPDATE되고 `resolved_at`이 채워진다.

**PS4 — pending이 남지 않는다** (§3.2 핵심 방어)
Given 학습자가 재발화 없이 세션을 종료했을 때, Then 그 행이 `unclear`로 수렴하고 `pending` 행이 **0개**다.

**PS5 — 한글 전사문이 신호로 기록되고 파이프라인이 죽지 않는다** (AC10-3)
Given 강한 억양으로 전사문이 한글이 되었을 때, Then `signal_source='korean_transcript'` 시도가 남고 분석 job은 4차수 P5와 동일하게 `done`·findings 0으로 수렴한다.

**PS6 — 깨진 페이로드에 세션이 살아남는다** (F4)
Given `outcome`이 열거값 밖이거나 JSON이 깨진 tool 호출이 왔을 때, Then `unclear`로 강등되거나 폐기되고 **세션은 계속된다**. 예외가 대화를 끊지 않는다.

**PS7 — 발음 오류가 패턴이 된다** (AC10-2·R10-6)
Given `outcome='incorrect'`이고 `target_sound`가 있을 때, Then `error_patterns`에 `pronunciation_intonation` 행이 생기고 `pattern_id`가 연결된다.

**PS8 — 스텁 모드가 무손상이다**
Given `VOICE_ADAPTER=stub`일 때, Then tool 이벤트가 발생하지 않고 발음 배지가 화면에 나타나지 않으며 1·2차수 C2 판정이 그대로 재현된다.

**PS9 — 결과 화면이 발음 카드를 보인다** (§5.2)
Given 발음 시도가 있는 세션의 결과 화면에서, Then 발음 카드가 표시되고 "표시할 교정이 없습니다."가 **나오지 않는다**.

**PS10 — 교정 상한을 넘지 않는다** (AC10-4)
Given 한 턴에 문법과 발음 오류가 함께 있을 때, Then 개입 합계가 2건을 넘지 않는다. **비결정적이므로 단정이 아니라 관측으로 기록한다**(§8-1).

### 9.1 실물 검증 (자동 판정 불가)

**PS-live** — 실제 Nova로 발음 세션 1회. 단정: 시범 음성이 실제로 올바른 발음이고, 재발화 판정이 사람의 판단과 어긋나지 않는다. **캡틴 육성 1회를 함께 쓴다**(§8-4).

---

## 10. 이월과 미결

### 이월

| 항목 | 사유 |
|---|---|
| 발음 패턴 → 쉐도잉 과제 생성 | `shadowing_items`는 별도 단계. 이 설계는 패턴까지만 만든다 |
| 세션당 발음 시도 수 경보 | §8-1. 관측 수단은 생기므로 임계값만 나중에 |
| 실물 마이크 보정 | 캡틴 게이트와 묶임 |
| `p2` 쌍(업무 보고 문장) 검증 | 하네스 5차수 백로그 |

### 미결 — 캡틴 확인 필요

1. **`toolResult`를 돌려보내야 하는가.** F6에서 안 보냈는데 세션이 정상 종료했지만 **1회 관측**이다. 다중 턴에서 Nova가 응답을 기다리며 멈추는지 확인이 필요하다. **기본안: 보내지 않는다**(관측된 거동을 따르고, 멈춤이 재현되면 그때 추가). 확인 방법은 `--tools`에 2턴 주입을 더하는 것이다.
2. **`agent_reprompt` 신호를 유지할 가치가 있는가.** 문구 매칭이라 취약하다(§8-2). `korean_transcript` 하나만으로 충분할 수 있다. **기본안: 유지하되 기록 전용.**
3. **발음 `pattern_key`의 값역.** `target_sound`를 Nova가 만들면 키가 흩어질 수 있다(`th_as_s` vs `theta_to_s`). 문법 패턴과 같은 §5.6 규약(기존 키 주입 + 재사용 우선)을 쓰면 완화되지만, 소리 목록을 우리가 열거해 고정하는 안도 있다. **기본안: §5.6 규약 재사용.**

---

## 11. 다음 단계

1. 이 설계서 검토 → 승인
2. `superpowers:writing-plans`로 구현 계획 (학습 코치 설계와 **함께** 계획한다 — 접합면이 `error_patterns` 한 곳이라 순서 제약이 약하다)
3. 003 마이그레이션 → tool 핸들러 → 보조 신호 → 지시문 → 화면 순으로 TDD
4. PS8(스텁 무손상)을 먼저 통과시킨다 — 기존 판정을 깨지 않는 것이 선행 조건이다
5. PS-live 1회 + 하네스 5차수에 P계층 시나리오 추가
