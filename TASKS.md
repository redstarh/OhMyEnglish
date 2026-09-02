# TASKS — 전체 작업 계획과 진행 상태

> **이 파일의 역할**: 프로젝트의 **모든 작업 갈래와 그 진행 상태**를 한곳에서 본다.
> "무엇이 남았나 / 무엇을 놓쳤나"의 정본이다.
>
> **읽는 방법**: 세션 시작 시 **자기 갈래의 표 한 줄**만 본다. 전체를 읽을 필요가 없다.
> 세부 절차·코드는 각 행이 가리키는 계획서에 있다.
>
> **handoff와의 차이**: `handoff/**`는 "지금 어디까지 왔고 다음 한 걸음이 무엇인가"만 담는다
> (짧게 유지). 이 파일은 **전체 지도와 상태**를 담는다. 둘이 겹치면 이 파일이 상태의 정본이다.
>
> **갱신 시점**: 태스크 상태가 바뀔 때(착수/완료/차단). 커밋과 같은 리듬.
>
> 최종 갱신 **2026-09-01** (I절 신설 — 실물 마이크 1회에서 나온 결함) · 브랜치 `design/first-vertical-slice`
>
> 갈래: **A**(§10 발음) · **B**(캡틴 결정) · **C**(§11 학습 코치) · **D**(하네스) · **E**(비차단) · **F**(전역 규약 정리) · **G**(결정 후속) · **H**(En-Coach 공유 DB) · **I**(실물 마이크 결함)

---

## 상태 기호

`✅` 완료 · `🔨` 진행 중 · `⏭` 대기 · `⛔` 차단(선행조건 있음) · `⏸` 캡틴 결정 대기

---

## A. 요구사항 v1.1 §10 — 발음 시범·재발화

계획: `docs/design/2026-08-27-pronunciation-echo-plan.md` (⚠️ 머리말의 **"구현 후 정정" 표**를
먼저 읽어라 — 본문 코드 블록 일부가 낡았다)
설계: `docs/design/2026-08-27-pronunciation-echo-design.md` (계약의 정본: §3.1a·§3.2·§6.1)
연속성: `handoff/HANDOFF.md` (2026-08-30 단일화 — 갈래별 handoff는 폐기)

| # | 태스크 | 상태 | 커밋 | 착수 전 필수 |
|--:|---|:--:|---|---|
| 1 | 003 마이그레이션 `pronunciation_attempts` | ✅ | `f7b8ccc` | — |
| 2 | tool 페이로드 검증 모델 | ✅ | `a0eff8e` | — |
| 3 | 포트 확장 `PronunciationEvent` | ✅ | `e6833c9` | — |
| 4 | 시도 생명주기 서비스 (+004 정렬 키) | ✅ | `ed91363` `582eef6` `aa1fcfe` | — |
| 5 | Nova 어댑터 tool 연결 + 지시문 규칙 | ✅ | `b31227a` `1a8c908` | — |
| 6 | 세션 배선 · 전사문 신호 · 종료 수렴 (+005 제약) | ✅ | `0025301` | — |
| 7 | 패턴 연결 (`error_patterns` upsert) | ✅ | `21ebf80` `43ab5f7` | 3건 전건 해소 — A-1 |
| **8** | **결과 화면 발음 카드 + 세션 화면 배지 (백엔드+프론트)** | **✅ 완료** — 결과 카드 `9b7985f` / 세션 배지 A-5. **2026-09-01 실물 마이크에서 캡틴이 배지를 눈으로 확인**("발음 교정 배지가 뜬 경우가 있었고, 교정도 잘 해줬어") | `9b7985f` + A-5 | 전건 해소 |
| 9 | 하네스 5차수 P9~P12 시나리오 | ⏭ | — | A-3(실물 검증 포함) |

### A-1. Task 7 착수 전 필수 3건 — ✅ 전건 해소 (`21ebf80` + `43ab5f7`)

해소 방식: ① `record_attempt`가 `async with conn.transaction():`을 직접 연다(savepoint로
합성). **`resolve_dangling`도 같다** — Task 7이 수렴을 `1+3N` 문장으로 만들어 호출자에게
맡길 수 없게 됐다(`43ab5f7`, 리뷰 MEDIUM-3) ② 적용 조건을 `link_pattern`의 **SQL `where`**에
두어 판정·수렴 두 경로가 같은 한 줄을 쓴다 ③ `target_form`은 **정규화한 `target_sound`**로
채운다(예: `th_as_s`).

⚠️ ③은 **뒤집힌 결정이다.** `21ebf80`은 "시도의 시범 문장"을 넣었고 리뷰 HIGH-2가 반박해
`43ab5f7`이 정정했다 — `docs/database-schema.md:120`이 이 컬럼을 "일반화된 목표 형태,
**문장이 아니다**"로 정의하고 근거가 관측된 결함(1차수 F-2)이다. 시범 문장은 이미
`pronunciation_attempts.target_form`에 있다. **문장으로 되돌리지 마라.**

T0 기록: 신규 7건 중 **5건이 red**였다(⑯⑰은 부재를 단정해 부모 커밋에서도 green — 함정 H-M).
`43ab5f7`의 ㉗은 트랜잭션을 임시 제거해 red를 실제로 관측했다.

아래 원문은 근거로 남긴다.

1. **`record_attempt`가 자기 트랜잭션을 열어야 한다.** 지금은 호출자의 것을 쓰고, Task 6의
   호출자는 `pool.acquire()`(autocommit)다. 설계서 §7 Failure가 "시도 INSERT와 패턴 upsert를
   한 트랜잭션에"를 요구하므로 그대로 두면 부분 실행이 생긴다(패턴 `frequency`만 +1 되거나
   시도의 `pattern_id`가 null). 대응은 `async with conn.transaction():` —
   `services/utterances.py:13-17`이 같은 결론을 문서화한다.
2. **패턴 생성은 경로 불문이다.** 판정으로 `incorrect`가 된 행뿐 아니라 **종료 수렴으로
   `incorrect`가 된 행도** 패턴을 만든다(설계서 §3.2, 캡틴 결정). 경로별 예외를 만들지 않는다.
3. **`error_patterns.target_form`이 not null이다.** 계획에 쓴 upsert가 그대로면 실패한다.

### A-2. Task 8 착수 전 캡틴 결정 — 판정↔시범 짝짓기에 상관키가 없다

판정 UPDATE가 `session_id` + 최신 대답기다림만 보고 **판정의 `target_form`을 버린다**. Nova가
A를 시범한 뒤 B의 판정을 보내면 한 행에 `target_form=A` + `spoken_form=B의 발화`가 어긋난 채
남는다. 계획 위반이 아니라 설계서 §3.2가 "최신순 매칭"만 규정한 **설계 공백**이다
(Task 4 코드리뷰 HIGH, 실측 재현).

✅ **결정 (2026-08-29): (b) 최신순 수용.** 설계서 **§8 D5-5**가 근거의 정본이다 —
(a) `and target_form = $N` 술어는 폐기했다(관측 증거 0 + 문자열 재렌더로 "대답 없음"이 늘는
새 실패 모드). 빈도는 5차수 P9~P12 관측 대상이고, 실제로 나타나면 `target_sound` 기준으로
다시 본다. **뒤집으려면 이 근거를 반박해야 한다.**

또한 Task 8은 응답에 **`signal_source`도 실어야 한다** — 신호 행의 `target_form`은 문장이 아니라
설명 문구라서 구분 없이 렌더하면 "이렇게 발음하세요"로 보인다. `incorrect`인데 `spoken_form`이
null인 행은 **대답 없이 끝난 시도**다.

✅ **결정 (2026-08-30) — 발음 카드는 기계 키를 표시하지 않는다.** 근거의 정본은 설계서
**§10 미결 4**다. 카드는 **시도 행만** 쓴다(시범 문장 · 들린 발음 · 판정)이고, 패턴의
`target_form`(= `btrim(target_sound)`, 예 `th_as_s`)은 **응답에도 화면에도 넣지 않는다.**
구성 단위는 **시도 1건 = 1카드**(`attempt_seq` 순) — 소리별로 묶지 않는다(묶으면 소리 라벨을
발명해야 한다). ⚠️ **2026-09-01 갱신 — 관측된 키가 3건 생겼다**(`am_as_i_m`·`w_as_vw`·`an_as_a`).
표시 사전·`_as_` 분해 규칙은 **더 이상 전부 발명값이 아니지만**, 관측 키에 **음소 치환이 하나도
없어서** §10이 의도한 "발음"과 어긋나는지가 먼저다 → **I-2**. 표본 3건이라 판정은 유보하고,
반복 오류 강조는 마이크 세션을 더 돌린 뒤 §10 미결 3과 함께 다시 본다.

✅ **A-2 후단 2건 해소** (`9b7985f`) — 응답에 `signal_source`를 싣고 프론트가 신호 행을
"관찰된 신호"로 따로 렌더한다 · `incorrect` + `spoken_form` null은 "대답 없이 끝났어요"로
렌더한다. 브라우저 실측으로 확인했다(대조군 포함).

### A-5. 세션 화면 발음 배지 — ✅ 완료 (2026-09-01, 실물 마이크로 확인)

**구현**: `app/frontend/lib/ws.ts`의 `ServerEvent`에 `pronunciation` variant 추가 +
`app/frontend/app/page.tsx`의 `switch`에 분기와 pill 렌더. 문구는 **새로 만들지 않고**
결과 화면 카드(`results/[sessionId]/page.tsx:44-48`)의 어휘를 그대로 썼다 — 같은 판정을 두 화면이
다른 말로 부르면 학습자가 다른 것으로 읽는다. `pending`만 이 화면에 있는 상태이고 문구는
스토리보드 03b(`:108`)를 따랐다. `target_sound`는 렌더하지 않는다(§10 미결 4).

**검증**: G-4 실물 마이크 1회(2026-09-01). 캡틴 관측 — "발음 교정 배지가 뜬 경우가 있었고,
교정도 잘 해줬어." 같은 세션에서 `pronunciation_attempts` **3행**이 처음으로 기록됐다
(그전까지 0행). 프론트 게이트 `tsc`·`eslint` 각각 exit 0.

⚠️ **같은 세션에서 별개 결함 1건이 나왔다 — I절 참조.**

<details><summary>이전 서술 (배지 미구현 시절의 착수 안내)</summary>

**백엔드는 이미 프레임을 방송한다** (`app/audio_gateway/session.py:254-261`, Task 6):
`{"type": "pronunciation", "outcome", "target_form", "target_sound"}`. 프론트가 그 타입을
모르는 것이 전부다 — `app/frontend/lib/ws.ts`의 `ServerEvent` union에 없고(`:18-27`),
`app/page.tsx`의 `switch (event.type)`에 분기가 없다(`:66-102`). 그래서 nova로 띄워도
화면에 아무 표시가 없다.

고칠 자리 2곳: ① `ServerEvent`에 variant 추가 ② `page.tsx`에 분기 + 배지 렌더.
시각 규약은 `docs/storyboard.html` 03b — 사용자 버블에 `🔊 발음 교정 중` pill, 판정 후
`✓ 좋아요` pill.

⚠️ **프레임이 `target_sound`(기계 키)를 실어 보낸다.** 설계서 §10 미결 4 결정에 따라
**화면에 렌더하지 않는다.** 프레임에서 필드를 빼는 것은 별개 판단이라 여기서 하지 않았다 —
결과 응답과 달리 이 프레임은 이미 있던 계약이고, 지우면 나중에 관측 도구가 쓸 값을 잃는다.

**검증 수단**: 스텁 어댑터는 이 프레임을 내지 않고(PS8: 스텁 무손상), 프론트에 테스트
프레임워크가 없고(`package.json`에 test 스크립트 0개), 하네스 `ws_session.py`는
**클라이언트**로 붙으므로 서버→클라이언트 프레임을 주입할 수 없다.

✅ **결정 (2026-08-30, 캡틴): 실물 마이크 1회(G-4)에 묶는다.** 폐기한 두 안 —
스텁에 프레임 주입 스위치를 신설하는 것은 **테스트 전용 경로를 생산 코드에 심는 지출**이고,
프론트 테스트 프레임워크 도입은 **새 의존성**이다. 어느 쪽이든 마이크 1회는 여전히
필요하다(판정 품질 A-3 · 픽스처 보정 §8-4) — 그 한 번에 실시간 표시까지 함께 본다.

**그래서 A-5는 G-4 앞에 코드를 올려둔다**: 지시문이 확정된 뒤(G-1·G-3) 배지를 구현해
놓고, 마이크 세션에서 배지 · 판정 품질 · 픽스처를 한 번에 관측한다. **Task 8은 그때까지
열어둔다.**

</details>

### A-3. 실물 Nova 왕복 — ✅ **1회 완료** (2026-09-01), tool 스키마 대조만 남았다

✅ **실물 마이크가 동작한다.** 세션 `bbfc3908` `completed` 3분 28초 · 발화 51건 ·
`pronunciation_attempts` **3행** 최초 기록 · 발음→패턴 연결 동작. 기록은
**`tests/harness/runs/2026-09-01-mic-1.md`**(다음 마이크 세션이 그대로 쓸 절차 포함).
캡틴 판정 — "교정도 잘 해줬어". **"왕복 0회"라는 이전 서술은 폐기됐다.**

⚠️ **다만 아래 스키마 대조는 이 세션에서 하지 않았다** — Task 9가 계속 소유한다.


**남은 것은 이것 하나다** — 앱이 보내는 tool 스키마가 스파이크가 보낸 것과 다른데, 마이크 세션은
발음 경로가 **동작함**을 보였을 뿐 두 스키마를 **대조하지는 않았다**:

| | 스파이크 | 앱 |
|---|---|---|
| 필드 / required | 3개 / 3개 | **4개**(+`target_sound`) / **2개** |
| `outcome` enum | `correct`·`incorrect`·`unclear` | **+`pending`** |
| 시스템 프롬프트 | 5문장 전용 | 규칙 **10개** 전문 |

즉 실증된 것은 **봉투 모양**까지다(`toolConfiguration`→`toolSpec`→`inputSchema.json`이 문자열).
**닫는 방법**: `spike_nova_protocol.py`의 `_PRONUNCIATION_TOOL_SCHEMA`를 앱 상수로 바꿔 1회 왕복한다.
**Task 9(5차수 P9)가 이 확인을 포함해야 한다.**

### A-4. 의도적 미충족 (요구사항 대비)

| 요구사항 | 상태 |
|---|---|
| R10-4 보조 신호 2개 | **절반만.** `korean_transcript`만 만든다. `agent_reprompt`(되묻기 문구 감지)는 **캡틴 결정으로 만들지 않는다** — 문구 매칭이라 케이스가 불어난다. 미충족 구간의 크기는 5차수 관측 대상 |
| R10-5 · R10-8 교정 예산 | **프롬프트로만.** 코드 강제 없음(설계서 §8 D5-1). 그리고 지시문 규칙 8이 설계서 §3.3보다 넓다 — ⏸ **B-2** |

---

## B. 캡틴 결정 — **전건 종결 (2026-08-30)**

B-1~B-10이 모두 결정됐다. **결정은 여기, 결정에서 생긴 작업은 G절**이다.
결정문은 캡틴의 말을 그대로 옮기고, 내가 해석한 부분은 "해석"으로 표시했다 —
해석이 틀리면 그 줄만 고치면 된다. 뒤집으려면 근거를 반박해야 한다.

| # | 항목 | 언제까지 |
|--:|---|---|
| B-1 | ~~**판정↔시범 상관키**~~ → **✅ 결정 (2026-08-29): (b) 최신순 수용.** `target_form` 술어를 더하지 않는다 — 실물 Nova 왕복 0회라 이 순서가 일어나는 증거가 없고, 문자열 일치는 모델의 미세한 재렌더에 빗나가 "대답 없음" 행을 늘리는 **새 실패 모드**를 만든다. 빈도는 5차수 관측(P9~P12). 근거는 설계서 §8 D5-5 | ~~Task 8 전~~ 완료 |
| B-2 | **교정 예산 범위** (발음 개입이 문법 교정과 예산을 다툰다) → **✅ "문법 교정을 우선으로 하여 결정."** 설계서 §3.3의 원안이 확정됐다 — 일반 세션에서 발음 개입은 **보조 신호가 떴을 때만**이고 그 밖에는 문법이 우선이다. 지금 `SYSTEM_PROMPT` 규칙 8이 무조건이라 코드가 결정과 어긋난다 → **G-1** | 종결 |
| B-3 | **교정 상한 문구 불일치** (`agent-system-prompt.md:19` "one **or two**" ↔ `nova.py` 규칙 4 "At most **one**") → **✅ "일상 회화 우선으로 결정."** _해석_: 교정이 잦으면 회화가 끊기므로 **한 턴 최대 1개**(코드 쪽)를 정본으로 삼고 요구사항 문서를 코드에 맞춘다 → **G-2** | 종결 |
| B-4 | **발음 `pattern_key` 값역** (§5.6 키 주입 기제가 Nova 경로에 없다) → **✅ "Nova 경로를 필요한 곳에 모두 사용가능하도록 설정. 설계, 코드에 반영."** 즉 문법 워커에만 있는 기존 키 주입을 **Nova 지시문에도** 만든다 → **G-3** | 종결 |
| B-5 | **실물 마이크 1회 + 발음 픽스처 보정** → **✅ "요청하면 진행하겠슴."** 캡틴 대기가 아니라 **내가 요청할 차례다** — 절차·픽스처·확인 항목을 준비해 한 세션에 둘을 함께 닫도록 요청한다 → **G-4** | 종결 |
| B-6 | **M계층 반영 단위** (오류가 대화에 닿는 경로가 0개) → **✅ "오류가 발생할 시나리오를 가정하여 설계 구성."** A(시나리오 선택) 갈래를 채택한다 — 학습자의 약점 패턴이 실제로 튀어나올 상황을 시나리오로 구성해 넣는다 → **G-5** | 종결 |
| B-7 | **Phase 1 완료 선언** → **✅ "미완료 항목은 수정하거나, 추가 테스트 수행."** 선언을 미루지 않고 **미충족 3건(W-live 1회 · E2E-S 1회 · 실물 마이크)을 채운다** → **G-6** | 종결 |
| B-8 | `pending_learning_utterances` 앱 미사용 → **✅ "죽은 코드는 삭제."** → **G-7** | 종결 |
| B-9 | `.claude/settings.json` 커밋 여부 → **✅ "커밋하지 마."** untracked로 둔다. **지우지도 않는다** — 하네스의 워크트리 금지가 이 파일에 의존한다. 후속 작업 없음 | ✅ 완결 |
| B-10 | **문법 프롬프트에 발음 패턴이 새어 들어가 `frequency`를 두 writer가 번갈아 덮는다** → **✅ "두번 틀리면 두번 입력 가능하도록 SQL 생성, 필요시 반복 컬럼 생성, 단순한 모델링으로 해."** _해석_: 한 컬럼을 두 경로가 다투게 두지 말고, **재발을 있는 그대로 세는** 단순한 모델로 바꾼다(필요하면 컬럼을 나눈다) → **G-8**. ✅ **2026-08-31 해석 확정** — 캡틴 "두 번 틀리면 두 번 틀린 것으로 기록". 세는 방식만 구속하고 저장 구조는 지정하지 않으므로 **(나) 경로 분리**로 확정했다(스키마 변경 0). 근거는 G-8 절 | 종결 |

**이전에 결정된 것**(근거는 설계서 §3.1·§3.2·§8·§10): `toolResult` 미회신 / `agent_reprompt`
미구현 / 대답 없음 = `incorrect` 일관 처리 / 종료 기록·수렴 한 트랜잭션 / 판정↔시범은 최신순
수용(B-1) / 패턴 `target_form`은 일반형(문장 금지).

---

## G. 결정에서 생긴 후속 작업 (2026-08-30 신설)

B절 결정이 만든 작업이다. **어느 것도 아직 착수하지 않았다.**

| # | 무엇 | 어디를 고치나 | 트랙 | 선행 |
|--:|---|---|:--:|---|
| **G-1** | 발음 개입을 좁힌다 (B-2) | `audio_gateway/nova.py` 지시문 규칙 8 | A | ✅ `efc6264` — **문구로 좁혔다.** 우리 신호(한글 전사문)는 전사 후 서버가 보는 것이라 Nova가 볼 수 없어, "알아듣기 어려울 만큼 무너졌을 때만 · 그 밖에는 문법 우선"으로 옮겼다(2026-08-30 캡틴 선택) |
| **G-2** | 교정 상한을 **한 턴 1개**로 통일 (B-3). 요구사항 문서를 코드에 맞춘다 | `docs/agent-system-prompt.md:19` 한 줄 → 한 줄 (⚠️ 이 파일은 줄 단위 인용 대상 — 함정 H-H) | C | ✅ **2026-09-03** — "one or two" → "**at most one**". `git diff -U0`이 `@@ -19 +19 @@`(순수 한 줄 교체)임을 확인해 살아 있는 인용 `:33`·`:47`이 안 밀린 것을 증명했다. 되돌린 이력: 첫 시도가 `@@ -19 +19,2 @@`로 두 줄이 되어 즉시 원복했다 |
| **G-3** | Nova 지시문에 **학습자의 기존 `target_sound` 주입** (B-4) | `services/pronunciation.load_known_sounds`(신설) → `nova.build_system_prompt` → `factory` | A | ✅ `efc6264` — 문법 쪽 조회를 **재사용하지 않았다**(카테고리 필터 부재가 G-8의 뿌리라 건드리면 그 판단을 미리 정한다). 통로는 팩토리 하나이고 넘기는 것은 조립된 문구가 아니라 **데이터**다 |
| **G-4** | 실물 마이크 세션 (B-5). 절차·픽스처·확인 항목을 준비해 한 세션에 마이크 1회 + 픽스처 보정 + **A-5 실시간 배지**를 함께 닫는다 (2026-08-30 결정 — A-5의 유일한 검증 경로다). ✅ **2026-08-31 캡틴 승인: "마이크 테스트 필요하면 진행해"** — 요청 단계는 끝났고 남은 것은 실행이다 | `tests/harness/scenarios-P-pronunciation.md`에 실행용 체크리스트 | D | **A-5 구현이 선행이다** (G-1·G-3은 `efc6264`로 해소). 배지 없이 마이크를 쓰면 같은 세션을 두 번 써야 한다 |
| **G-5** | §11 M계층을 **시나리오 선택** 갈래로 설계 (B-6). 약점 패턴이 실제로 튀어나올 상황을 시나리오로 구성한다. **고칠 자리는 이미 특정돼 있다** — `services/sessions.py:29`가 `_CREATE_SESSION_SQL` 안에서 `(select id from learning_scenarios order by created_at, id limit 1)`로 **항상 같은 시나리오**를 고른다(2026-08-30 확인). 그것을 "추천 한 건"으로 바꾸는 작은 변경이다. 반영이 시나리오 문구 수준으로 거칠다는 한계는 알고 채택했다. ⚠️ **B갈래 기각 근거는 사실이 아니었다** (2026-08-30 `efc6264`로 확인): "지시문 주입은 `port.start()` 인자 확장이 필요하다"고 적혀 있었지만, 실제 이음매는 `audio_gateway/factory.create_voice_adapter`이고 **포트 계약을 건드리지 않고** 주입할 수 있다. G-3이 그 통로를 이미 만들었으므로 비용은 이미 지불됐다 — **B갈래를 다시 검토해야 한다.** A갈래(시나리오 선택) 채택 자체가 틀렸다는 뜻은 아니고, 기각 사유가 사라졌다는 뜻이다 | `docs/design/2026-08-25-learning-coach-agent-design.md`에 결정 반영 → 구현 계획. 남은 미결 5건은 `tests/harness/scenarios-E-agent-learning.md` L계층·M계층 §캡틴 결정 | A | — |
| **G-6** | Phase 1 미충족 3건을 채운다 (B-7) — **W-live 1회 · E2E-S 1회 · 실물 마이크** | AC 문서 `:145-154`의 6항목 대조 | A/D | G-4 |
| **G-7** | `pending_learning_utterances` **삭제** (B-8). 참조가 없는지 확인 후 함수와 그 테스트를 함께 제거 | `services/utterances.py` | B | ✅ **2026-09-03** — 앱 참조 **0곳** 직접 확인 후 함수 + 테스트 2건(35줄) 삭제. `_SELECT_COLUMNS`·`UtteranceRow`·`_to_utterance`는 `save_final_transcript`가 계속 쓰므로 남겼다. **AC W6 증거는 잃지 않았다** — 계획서가 "W6의 검증 대상은 enqueue 조건"이라고 이미 적어 두었고 그 테스트는 그대로다. `ANALYZED_*` 상수 주석의 세 번째 소비자 서술도 함께 정정 |
| **G-8** | `frequency` 이중 writer 해소 (B-10) — **(나) 경로 분리로 확정**(2026-08-31 캡틴: "두 번 틀리면 두 번 틀린 것으로 기록"). 발음 키가 문법 프롬프트에 실리지 않게 카테고리 필터를 더해 충돌 자체를 없앤다. **스키마 변경 0 · 006 마이그레이션 불필요** | `services/analysis.py` `_EXISTING_PATTERNS_SQL`에 카테고리 필터 | **B** | ✅ **완료 2026-09-03** — `and category <> $2`(값은 기존 상수 `UNJUDGEABLE_CATEGORY`, 발명 0). red 먼저 관측했고 **뮤테이션으로 재확인**: 필터를 `($2::text is not null)`(항상 참)로 바꾸면 AssertionError로 red다. 스키마 변경 0 · 006 불필요. 해석 확정 근거는 아래 G-8 절 |

### G-8 착수 전 확인할 것 — 지금 무엇이 문제인가

한 `error_patterns` 행의 `frequency`를 **두 곳이 서로 다른 규약으로** 덮는다.

| writer | 세는 것 | 코드 |
|---|---|---|
| 문법 분석 | `error_occurrences` **행 수** | `services/analysis.py` `_RECOUNT_PATTERN_SQL` |
| 발음 연결 | `pronunciation_attempts` **행 수** | `services/pronunciation.py` `_RECOUNT_PATTERN_FROM_ATTEMPTS_SQL` |

지금은 키가 겹치지 않아 사고가 안 났다(신규 문법 키는 그 카테고리가 프롬프트에서 금지됨 —
`analysis.py:49`). **재사용 경로만** 구멍이다: `_EXISTING_PATTERNS_SQL`(`analysis.py:188`)에
카테고리 필터가 없어 발음 키가 문법 프롬프트에 실리고, 모델이 그것을 글자 그대로 재사용하면
한 행을 두 writer가 번갈아 덮는다.

캡틴 결정("두 번 틀리면 두 번 입력 · 필요시 반복 컬럼 · 단순한 모델링")을 만족하는 안 2개:

- **(가) 컬럼을 나눈다** — `error_patterns`에 발음 전용 카운터를 두고 각 writer가 자기 것만 만진다. 006 마이그레이션 1개. 조회는 두 값을 더한다
- **(나) 경로를 나눈다** — 발음 키가 문법 프롬프트에 실리지 않게 필터 한 줄을 더해 충돌 자체를 없앤다. 스키마 변경 0

✅ **결정 (2026-08-31, 캡틴): "두 번 틀리면 두 번 틀린 것으로 기록."** → **(나) 경로를 나눈다**로 확정.

_해석의 근거_: 캡틴 문구는 **세는 방식(재발을 있는 그대로 기록한다)을 구속하고, 저장 구조를
지정하지 않는다.** (가)·(나) 둘 다 이 요구를 만족한다 — 두 writer 모두 이미 행 수를 다시 세는
방식(`_RECOUNT_*_SQL`)이고, 재발 1건은 `error_occurrences` 또는 `pronunciation_attempts`의
**행 1개**로 이미 남는다. 즉 "두 번 기록"은 지금도 참이며 버그는 **한 행을 두 writer가 덮는 것**이다.
그렇다면 남는 판단 기준은 B-10이 함께 말한 **"단순한 모델링"**이고, (나)는 컬럼도 마이그레이션도
늘리지 않는다. "필요시 반복 컬럼 생성"의 **"필요시"** 조건이 성립하지 않는다.

_되돌리기 비용도 (나)를 가리킨다_: (나)는 필터 한 줄이라 철회가 싸고, (가)는 마이그레이션이라
한 번 적용하면 되돌리기 어렵다. 해석이 어긋났다면 (나)를 걷어내고 (가)로 가는 비용이 그 반대보다 작다.

⚠️ **이 해석이 캡틴 의도와 다르면 말해 달라** — (가)로 바꾸는 데 드는 것은 006 마이그레이션 1개다.

---

## C. 요구사항 v1.1 §11 — 이력 기반 추천 학습 루틴

설계: `docs/design/2026-08-25-learning-coach-agent-design.md` (**정본 승격**, 미결 3건 종결)

| 단계 | 상태 | 비고 |
|---|:--:|---|
| 계획 문서 작성 | ⏭ | **첫 걸음.** §12.1의 **2슬라이스 분해**가 채택됐다 |
| 슬라이스 1 — 데이터 유실 정지 | ⏭ | `suggested_contexts` 저장 · `pattern_attempts` · 복습 스케줄 갱신(§4.1) · 만성 지표 쿼리(§6.1) |
| 슬라이스 2 — 계획 생성·반영 | ⏭ | 지시문 가변부(§5.2)가 여기서 생긴다 → B-2와 묶인다 |

**착수 전 실측 (2026-08-27 확인)**: 테이블 `session_plans`·`learner_notes`·`pattern_attempts`
**전부 없음** / 컬럼 `next_review_at`·`mastery_score`·`review_tasks`·`current_level`·
`self_difficulty`·`impact_score`·`suggested_contexts` **앱 참조 0곳** / `sessions.py:29`는 여전히
고정 시나리오 1개 / `port.py` `start()`에 인자가 없어 지시문을 넘길 자리가 없다.

⚠️ **착수 전 필수 — 달력 날짜를 `current_date`로 구하지 않는다** (함정 **H-S**, 2026-08-31 실측).
공유 DB 세션 타임존이 UTC라서 UTC 자정~09:00(KST) 구간에는 `current_date`가 KST 날짜보다
하루 이르다. 복습 주기(1·3·7일) · `next_review_at` · 일일 계획이 전부 이 칸에 걸린다 —
`AT TIME ZONE`으로 변환하고 tz의 SoT는 `users.timezone` 컬럼이다(기본값 `Asia/Seoul`, 아직
앱이 읽지 않는다). `ALTER DATABASE … SET TimeZone`은 En-Coach와 공유하는 DB라 금지다.
전역 규약은 `~/.claude/CLAUDE.md` "DB 시각·날짜 규약", En-Coach 쪽 정책은
`~/MyProject/En-Coach/docs/operations/timezone-policy-handoff.md`.

✅ **해소 (2026-09-03, D-6)** — 거짓 서술 2건을 고쳤다: AC 문서와 Phase1 계획서가 `impact_score`를
"컬럼만 존재" 목록에 넣고 있었다(둘 다 **한 줄 → 한 줄** 교체 — `@@ -N +N @@` 확인). 학습 코치
설계서의 `suggested_contexts` AC에는 "이 컬럼은 아직 없다 · 슬라이스 1이 006으로 신설한다"를 못 박았다.
나머지 언급은 이미 정확했다(연기·영구 제외·작업 항목). 아래는 그 판정의 원래 기록이다.

⚠️ **착수 전 필수 — 문서가 없는 컬럼을 있는 것처럼 말한다** (2026-09-01 중간 점검 실측,
`docs/consistency-audit-2026-09-01.html` D-6). **`impact_score`·`suggested_contexts`는 실제 DB에
컬럼이 없다** — 마이그레이션 참조 각 **0건**이고 `information_schema`에도 없다. 그런데 설계서
**4개·2개 파일**이 이 컬럼을 전제로 서술한다. 위 "착수 전 실측"의 "앱 참조 0곳"과는 **상태가 다르다** —
`next_review_at`·`mastery_score`·`self_difficulty`·`users.current_level`은 **컬럼이 있고 앱만 안 쓰는**
것이라 바로 쓸 수 있지만, 이 둘은 **006에서 신설해야 한다.** 설계서를 믿고 쓰면 그 자리에서 깨진다.

✅ **해소 (2026-09-03, D-5)** — `docs/database-schema.md`에 `pronunciation_attempts`(003~005 반영,
CHECK 2개·인덱스 2개·`attempt_seq` 함정·**frequency 두 번째 writer** 포함)와 `schema_migrations`
(러너가 만드는 표) 정의 섹션을 넣었다. **`### 아직 SQL에 없는 테이블` 앞**에 삽입해 `git diff -U0`이
`@@ -218,0 +219,48 @@`(순수 삽입)임을 확인했다 — 살아 있는 줄 인용의 최대값이 `:161`이라 하나도
밀리지 않았다. dev DB에만 있는 `harness_*` 3표가 앱 스키마가 아니라는 것도 함께 적었다.
⚠️ 그 확인 중에 **원래부터 깨져 있던 인용 2건**을 발견했다(`database-schema.md:111`·`:161`은 각각
`created_at` 행과 다른 줄을 가리킨다) — 내가 만든 것이 아니고 이번에 고치지 않았다. 아래는 원래 기록이다.

⚠️ **스키마 문서도 뒤처져 있다**(같은 점검 D-5). `docs/database-schema.md`가 정의한 표는 **8개**인데
우리 표는 **10개**다 — `pronunciation_attempts`(003~005가 만든 §10 핵심 표)와 `schema_migrations`의
정의 섹션이 없고 "아직 SQL에 없는 테이블" 목록에도 없다. §11이 `error_patterns`를 만지므로
그 문서를 근거로 쓰기 전에 채운다.

**순서 권고**: §10 Task 7·8 → §11 슬라이스 1 → §11 슬라이스 2.
슬라이스 1을 앞세우는 근거: `suggested_contexts`는 모델이 산출해도 지금 **버려지고 소급이
불가능하다**. 늦어질수록 잃는 것이 쌓인다.

---

## D. 테스트 하네스 — 차수 원장

원장: `tests/harness/runs/ROUNDS.md`(차수·5차수 범위의 정본) · 연속성: `handoff/HANDOFF.md`
**4/10 차수 사용. 미해결 앱 결함 0건.**

| 차수 | 상태 | 범위 |
|---|:--:|---|
| 1~3 | ✅ | 기본 흐름 · Nova 실음성 왕복(N-0·N-1·N5) · 회귀 |
| 4 | ✅ | P계층(발음 부재 확정) · M계층(학습 반영 부재 확정) · 신규 결함 0건 |
| **5** | ⏭ | 미실행 Nova N6·N7·N8·N11·N12·N13 / B1~B4 재확인 + 라이트·다크 5상태 / 회귀 A1·A2·E4·E5·E6·D1·D2 + 프론트 `npx tsc --noEmit` / P8 + `p2` 쌍 + P7 재캡처 / **신규 P9~P12**(Task 9) / `tests/**` ruff 6건·format 4건 정리 |

**5차수가 반드시 포함해야 하는 관측 3건**: A-3(실물 tool 스키마) · A-4의 미충족 구간 크기 ·
B-2의 대조군(발음 개입 없는 일반 대화 1턴이 3차수 N5와 같은가).

**일부러 빼는 것**: N9(세션 롤오버 — 8분 이상 실음성 필요, 시간·비용) ·
N10(무응답형 자격증명 실패 — `.env` 편집 금지 제약).

---

## E. 비차단 후속

| 항목 | 비고 |
|---|---|
| `tests/**` ruff 6건 · format 4건 | 전부 `tests/harness/*`. **선언된 게이트 밖이다**(함정 H-L) — 5차수 정리 |
| WS 엔드포인트 origin 미검증 | `api/ws.py`에 origin 참조 0건. localhost 단일 사용자라 수용 |
| `botocore` 재시도 미설정 | 스로틀 중복 과금 — Phase 2 운영 관찰 |
| AWS access key 로테이션 | 대화 기록을 경유한 키다. `docs/ops/iam-setup-nova-sigv4.md` §6 |
| 추적 체크리스트 HTML (캡틴 요청) | 요구사항 상세 기능 ↔ 설계·구현 대조표. 구현 후 |
| 이연 minor 33건 | 전건 "병합 전 필수 아님" triage 완료 |
| **O-1** (LOW) agent 전사문에 **선행 개행** | Nova가 `'\nWhat time do you…'`를 보내고 `save_final_transcript`가 그대로 저장한다. agent 발화라 분석 job이 없고 화면 렌더도 정상 — 지금은 무해. 4차수에서 두 세션(p1k·u1)에 재현. **5차수에 묶어 전달** (2026-08-30: 하네스 handoff 폐기 시 이 원장으로 이관) |
| **우리 표를 `public` → 전용 스키마로 이관 검토** | En-Coach가 전용 스키마(`en_coach`)를 쓰는데 우리는 `public`에 있어 **비대칭**이다 — 우리 표가 "기본값 자리"를 차지해 남의 `search_path` 폴백이 우리 것으로 떨어진다. 우리 SQL이 전부 한정자 없이 쓰여 범위가 커서 지금은 미룬다. 규칙·근거는 `docs/ops/shared-database-naming-rules.md` §5 |
| 음성 픽스처 상주 배치 | 9개 배치 중 4차수 실사용은 5개(`u1`·`u2`·`p1a`·`p1m`·`p1k`). 5차수는 `p2` 쌍·N7(3턴)까지 돌아 9개가 다 필요하다 → **상주 배치는 사전 승인 범위**(테스트 자산 배치)라 별도 결정 불필요 |

---

## F. 전역 규약 정리 (범위: `~/.claude/**` — 이 리포 밖)

**상태: ✅ 완료 (2026-08-28). 남은 것 없음 — F-3 참조.**
캡틴 지시: "상충·중복을 전체 검토하고 정리. 핵심만, 중복 없이, 길지 않게" + "SVG도 너무 과한
gate면 제거(hook 포함), 단 검토는 꼭 해."

### F-1. 결과 (실측)

| 파일 | 전 → 후 | 무엇을 지웠나 |
|---|---|---|
| `rules/self-verification-gate.md` | **132 → 46** | 체크리스트 4개의 "증거 형식" 열(한 번도 안 씀) · "적용 범위" 매트릭스(N/A 목록과 중복) · 이력 주석. **위임 트리거를 "모든 분석·설계 결론" → "되돌리기 어려운 결론"으로 좁혔다** |
| `CLAUDE.md` | 98 → **95** | 중복 4건: 인계 절차 재서술(`session-handover.md` 소유) · agent 매핑 재서술(`AGENTS.md`) · superpowers 14개 열거(§0-2) · "self-approve 금지"(`<verification>`과 3중) |
| `AGENTS.md` | 47 → **45** | CLAUDE.md와 겹치던 SVG·병렬·Workflow 항목 |
| `scripts/self-verify-gate.sh` (hook) | 5줄 → **3줄** 주입 | "모든 결론에 critic"(과한 트리거) · 기준 파일 포인터. **실제로 돌려 3줄 출력을 확인했다** |
| 프로젝트 메모리 | 245 → **224**, 10 → 9개 | `handoff-per-work-unit`을 3층 분리 메모로 흡수·삭제. 끊긴 `[[링크]]` 3건 재지정 |

전역 규약 합계 **722 → 631줄**.

### F-2. SVG 판정 — 제거하지 않았다. 근거

**"작성자≠검증자" 원칙이 이 세션에서 실제 결함 3건을 잡았다**: ① 보조 신호 행을 Nova 판정이
닫던 것 ② 프롬프트가 `target_sound`를 요구하지 않아 Task 7 패턴 upsert가 **무증상 미실행**
③ 한 턴의 시범 문장이 전사문에서 사라진 것. 셋 다 게이트 없이는 커밋됐다. 그래서 **원칙은
남기고 미사용 부피만 걷어냈다.**

⚠️ **지우기 전 grep이 판정을 바꿨다** — `A1~A5`·`V1~V5`·`T0~T5` 항목 코드를
`code-development-principles.md`가 **5곳에서 참조**한다. 표를 통째로 지우려 했으나 끊기므로
**코드는 남기고 열만 지웠다.** "검토는 꼭 해"가 실제로 값을 한 지점이다.

### F-3. 종결 — 후보 2건 모두 "지우면 안 된다"로 판정 (grep 근거)

`code-development-principles.md` **215줄은 그대로 둔다.** 내가 세운 후보 둘 다 틀렸다:

| 후보 | 판정 | 근거 |
|---|---|---|
| LSP 우선 원칙 절(~30줄) | **유지** | `four-lenses-design-review.md`가 `LSP(findReferences)`·`goToDefinition`을 **7곳에서** 쓴다 — 지우면 그 표들이 전제하는 도구 지침이 사라진다. 그 절은 스스로 "범위: Python 전체 프로젝트 / 프로젝트 특수성은 각 프로젝트 `.claude/rules/`"로 계층을 나눠 두었다 |
| §2 `[skip ci]` 규칙 | **유지** | 참조하는 SoP 파일이 **실재한다**(`~/AgentDev/docs/ops/github-ci-cost-reduction-sop.md`). 다른 파일이 §2를 재서술하지 않으므로 중복이 아니고, GitHub Actions 비용은 전역 관심사다 |

메모리 `standing-approval-for-test-work.md` **상충 아님.** 그 승인은 **하네스 세션**의 것이고
"앱 코드는 수정 세션(`claude_air_3-14`)에 넘긴다"는 제약이 구속하는 대상도 하네스 세션이다.
이 세션이 바로 그 수정 세션이라 앱 코드 수정이 정상이었다. 오독 방지 한 줄만 추가했다.

**즉 전역 규약 정리는 완료다.** 더 지울 것을 찾지 말고, 새 규칙을 추가할 때 "어느 파일이
소유하는가"만 지키면 된다.

---

## H. En-Coach와 DB 공유 — ✅ 구성 완료 (2026-08-30)

규칙·접속 정본: **`docs/ops/shared-database-naming-rules.md`** (En-Coach에 전달한 문서, 단독 자립)
배경·구축 내역: `docs/ops/shared-database-guide.md`

| # | 항목 | 상태 |
|--:|---|---|
| H-1 | 같은 DB(`ohmyenglish`) + 스키마 분리. 역할·스키마 `en_coach`, 우리 표는 3개 `SELECT`만 | ✅ |
| H-2 | 네이밍 규칙 R1~R7 정하고 전달 (`ec_` 접두어 9개 전부 · `search_path`에서 `public` 제거 · 우리 표 읽기 전용) | ✅ |
| H-3 | **En-Coach가 실제로 붙었다** — 실측: `en_coach`에 `ec_*` 9개 + 자기 `schema_migrations`, 우리 `public`에 `ec_` 표 **0개** | ✅ |
| H-4 | 철회한 안: 별도 DB + `postgres_fdw`. 그때 걸린 3가지는 가이드 §4-alt에 보존(격리가 더 필요해지면 되돌릴 길) | — |

⚠️ **공유의 대가**: 이제 두 앱이 같은 DB다. 사람이 손으로 dev DB를 drop/재생성하면
`en_coach` 스키마와 그 데이터까지 사라진다. **우리 자동 테스트는 안전하다**(파괴 대상은
`ohmyenglish_test`·`ohmyenglish_smoke`뿐). 수동 재생성 전에 En-Coach 쪽에 알린다.

우리 쪽 남은 숙제(비대칭 해소 — 우리 표를 `public`에서 전용 스키마로)는 **E절**에 있다.

---

## I. 실물 마이크 1회(G-4)에서 나온 결함 — 2026-09-01 신설

세션 `bbfc3908-639c-4f1e-a565-fdbd74e0a420`(3분 28초, `completed`). 전부 이 세션의 DB를
직접 조회해 얻은 값이다.

### I-1. **발화 종료 감지가 이르면 문장이 쪼개지고, 그 조각이 오탐 패턴을 만든다** — ✅ 구현 완료 (2026-09-01)

**구현 완료 — 접점 4곳 + 코드 리뷰 지적 반영 + 회복 스윕.** 게이트: **365 passed**(348 → 365) ·
ruff·format(27파일)·`ty` clean · `tests/**` 베이스라인 **6 errors·4 files 그대로** ·
프론트 `tsc`·`eslint` exit 0.

T0 red를 구현 전에 실제로 관측했다. 정직하게 센 것:
- **본 수정 8건 중 8건 red.** 그중 2건은 단정 실패로 결함 자체를 증명했다(`assert 2 == 1` =
  조각 2개에 job 2건 / 저장만으로 job 3건). 나머지 6건은 미구현 red다.
- **회복 스윕 5건 중 3건 red.** 나머지 2건은 "아무것도 하지 않아야 한다"는 **부재 가드**라
  스텁에서도 통과했다(함정 **H-M**) — red 증거로 세지 않는다. 대신 구현 후 뮤테이션으로
  두 건 모두 실제로 red가 되는 것을 확인했다(`active` 필터 무력화 / `partition by` 제거).
- **T0가 아닌 것 2건**: flush 실패 내성(`test_gateway.py`)과 acquire 실패 내성은 green 이후
  **6단계 테스트 보강**으로 썼다. 후자는 결함을 되살려 red를 확인했다.

순증: 신설 18건 − 폐기 1건 = **+17** (348 → 365로 일치).

| # | 무엇을 했나 | 어디 |
|--:|---|---|
| 1 | `save_final_transcript`에서 즉시 `enqueue_analyze` 제거 | `services/utterances.py` |
| 2 | `flush_pending_analysis(conn, session_id)` 신설 — 묶음마다 **마지막 발화 1건**에만 job | 같은 파일 `_FLUSH_RUNS_SQL` |
| 3 | flush 두 지점 — agent final 저장 직후(`_save_final`) · 종료 경로(`_close_and_record`) | `audio_gateway/session.py` |
| 4 | `_LOAD_INPUT_SQL`이 묶음 전사문을 `string_agg`으로 이어붙여 분석 입력으로 준다 | `services/analysis.py` |

**설계에서 정정한 것 1건 — 멱등성은 기존 partial unique만으로 부족했다.** 앞선 설계는
"멱등성은 `uq_analysis_jobs_pending_utterance`(001:157)가 이미 준다"고 적었는데 **틀렸다**:
그 인덱스는 `pending`/`running`만 덮으므로 분석이 `done`이 된 묶음이 다음 flush에서 다시
등록된다. flush는 세션 하나에서 턴마다 + 종료 시 불리므로, 이 가드가 없으면 첫 묶음이
**턴 수만큼 재분석**되어 Claude 호출이 그만큼 늘어난다. 그래서 `not exists (… job_type = …)`
가드를 넣었다. 회귀 테스트: `test_flush_does_not_re_enqueue_a_run_whose_analysis_already_finished`.
⚠️ 이 가드는 flush 경로에만 있다 — `enqueue_analyze` 직접 호출(재분석 경로, E6 시나리오)은
그대로 허용된다.

**하네스 회귀는 "5 → 1"이 아니라 "턴을 하나씩 닫는다"로 처리했다.** 앞선 설계는 E1의 job 수가
5 → 1로 줄어드니 `wait_for_jobs` 단정을 고치라고 적었지만, 그러면 **E계층 시나리오 자체가
소멸한다** — E1은 "문장마다 다른 카테고리의 패턴이 생긴다"를 관측하는 것이고 5문장이 한 묶음이
되면 패턴 분산을 볼 수 없다. 실제 세션은 문장마다 agent가 응답하므로, `inject_errors.py`가
문장 하나 → agent 응답 하나 → flush를 반복하게 고쳤다. job 수는 **5건 그대로**이고
`wait_for_jobs`는 손대지 않았다. 부작용: 주입 발화의 `sequence_no`가 1·3·5…로 오른다.

**삭제한 테스트 1건과 그 근거** — `test_save_is_atomic_even_when_the_caller_opened_no_transaction`.
그것이 지킨 불변식("전사문 insert와 enqueue가 한 단위")은 enqueue가 저장에서 빠지면서
**사라졌다** — write가 하나뿐이라 단정할 원자성이 없다. 되살리지 말 것. 그 자리를 대신하는 것은
`tests/integration/test_gateway.py`의 flush 실패 내성 테스트다(flush가 터져도 세션은 `completed`로
닫히고 전사문 6행은 남는다). 원자성의 소유자는 `save_final_transcript`에서 **호출자의
트랜잭션**으로 옮겨졌고 `test_transcript_and_job_roll_back_together_when_the_turn_fails`가 지킨다.

**코드 리뷰에서 나온 결함 2건(HIGH)과 그 처리 — 2026-09-02**

| # | 무엇 | 처리 |
|--:|---|---|
| HIGH 1 | flush용 `pool.acquire()`를 예외 가드 **밖**에 뒀다 → acquire가 실패하면 `adapter.close()`와 `end_session()`이 **한 번도 실행되지 않아** 세션이 `active` 고아로 남고 Nova 스트림이 누수된다. 같은 메서드 docstring이 금지한 상태이고 **변경 전에는 도달 불가**였다 | ✅ 수정. 연결 획득을 `_flush_analysis` 안으로 넣었다. 회귀 테스트 `test_a_failing_flush_connection_still_closes_the_adapter_and_records_the_end` — 결함을 되살리면 실제로 red가 되는 것을 확인했다 |
| HIGH 2 | 종료 flush가 실패하면 그 묶음이 영구히 분석되지 않고, 결과 화면이 **terminal** 상태 `no_utterances`("분석 대상 없음")에 고정된다(`results.py` 규칙 2 → 프론트 `TERMINAL_STATUSES`). I-1 이전에는 "발화는 있는데 job 0건"이 도달 불가였다 | ✅ **캡틴 결정(2026-09-02): 워커 스윕 — 끝난 세션만.** 아래 참조 |

**회복 경로 (HIGH 2 해소)** — `flush_ended_sessions`(`services/utterances.py`) +
`sweep_lost_runs`(`workers/analysis_worker.py`). 워커가 **큐가 빌 때만** 부르고,
`status in ('completed','failed')` 세션만 훑는다.

⚠️ **`active` 세션을 넣지 마라.** 진행 중 세션의 마지막 묶음은 사용자가 말하는 중이라 아직
자란다 — 그것을 걸면 조각이 따로 분석되는 **I-1 결함이 그대로 되살아난다**. 회복 경로가 고친
것을 되돌리는 셈이다. 가드는 `test_sweep_never_touches_an_active_session`·
`test_worker_sweep_leaves_an_active_session_alone`이고, 필터를 무력화하면 둘 다 red가 된다(실측).

⚠️ **`lead()`의 `partition by u.session_id`를 지우지 마라.** 단일 세션 flush에서는 무의미하지만
스윕에서는 필수다 — 없으면 전역 `sequence_no` 순서로 섞여 다른 세션의 발화가 앞 세션의 묶음을
닫는다. `test_sweep_computes_run_boundaries_per_session`이 지킨다(뮤테이션으로 red 확인).
두 flush가 **같은 SQL 템플릿**(`_RUN_END_FLUSH_TEMPLATE`)을 쓰는 이유도 이것이다 — 묶음 정의가
두 벌로 갈라지면 회복 스윕이 턴 경계와 다른 경계를 계산한다.

비용: 끝난 세션 발화의 seq scan 1회. 시간 창으로 자르지 **않았다** — 워커가 그 창보다 오래
내려가 있으면 조용히 묶음을 잃기 때문이다. 단일 사용자 도구 기준으로 받아들였고, 이력이
커지면 그때 좁힌다.

**테스트로 덮지 못한 것 1건 (지우지 말 것)** — `_LOAD_INPUT_SQL`의
`order by u.sequence_no`. 뮤테이션(제거)이 전체 스위트를 통과한다. 뒤 조각을 먼저 insert해
힙 순서를 역전시켜 봤지만 **그래도 통과한다**: 계획은 Seq Scan인데(`explain` 확인) 앞선 테스트가
지운 행의 빈 공간을 FSM이 재사용하므로 물리 순서를 테스트에서 통제할 수 없다. 즉 위반을 공개
경로로 재현할 수 없는 종류의 가드다 — **커버리지가 없다는 것이 불필요하다는 뜻이 아니다.**
계획이 Bitmap Heap Scan이나 병렬 Seq Scan으로 바뀌면 어순이 깨지고, 그때 학습자는 뒤섞인
문장으로 교정을 받는다. 같은 이유로 `flush`의 `order by r.session_id, r.sequence_no`도 미검증이다.

**코드 리뷰 재검증 결과 — ✅ Approve (2026-09-02)**. CRITICAL·HIGH **0건**. 리뷰어가 독립적으로
게이트를 돌려 `365 passed`·ruff·format·ty clean·베이스라인 6 errors/4 files 전부 내 수치와
일치했고, HIGH 1 수정을 같은 재현 스크립트로 재검증했다(수정 전 `acquire=1 / RuntimeError /
close=False / 기록=[]` → 수정 후 `acquire=2 / 예외 None / close=True / 기록 2건`).
뮤테이션 4건(`partition by` 제거 · `active` 필터 무력화 · `else 1` · 스윕 no-op) **전부 죽었다**.

재검증에서 나온 신규 지적 3건 처리:

| # | 무엇 | 처리 |
|--:|---|---|
| MEDIUM 9 | `flush_ended_sessions` docstring이 **"그 전에 프로세스 사망"까지 덮는다고 주장**했는데 거짓이다 — 죽으면 세션이 `active`로 남고 스윕은 정의상 `active`를 건너뛴다 | ✅ docstring을 "러너가 `_close_and_record`까지 도달했으나 flush가 실패한 경우"로 좁혔다. 못 덮는 것을 ⚠️로 명시하고 **별건 `I-4`** 신설 |
| LOW 10 | `utterances.py`의 `order by`도 같은 미검증 상태인데 경고가 없었다 | ✅ 그 줄 옆에 경고 추가 |
| LOW 11 | "지우지 말 것" 경고가 지워질 코드(`analysis.py`) 옆이 아니라 테스트 파일에만 있었다 | ✅ `_LOAD_INPUT_SQL` 바로 위에 포인터 추가 |

**MEDIUM 5 후속 — 텍스트 tripwire를 넣었다** (리뷰어 제안 수용).
`test_merge_sql_keeps_its_explicit_ordering`(`tests/unit/test_analysis.py`)이 두 SQL의
집계식 전체를 문자열로 단정한다. 행동은 못 잡지만 진짜 위험인 "정리 중 조용히 지워지는 것"은
잡는다. 이 리포에는 소스 텍스트 단정 선례가 있다(`test_gateway.py:768`).
⚠️ **처음 쓴 tripwire는 실패할 수 없는 것이었다** — 경고 주석이 같은 SQL 문자열 안에 있어서
`"order by u.sequence_no"`만 찾으면 실제 `order by`를 지워도 주석이 남아 통과했다. 집계식
전체를 단정하도록 고치고 두 `order by`를 실제로 지워 red를 확인했다.

**리뷰가 확인하고 "결함 아님"으로 판정한 것** (다시 조사하지 말 것): occurrence가 묶음의
마지막 발화를 가리키는 것은 **화면에 새지 않는다** — `results.py`는 `eo.original_span`만 싣고
프론트도 그것만 렌더한다(`utteranceId`는 TS 코드에 없다). `pending_learning_utterances`의 의미
변화도 앱 호출처가 0곳이라 무영향. `enqueue_analyze` 직접 호출(재분석·E6)은 `not exists` 가드에
막히지 않는다. `analysis.py` → `utterances.py` → `sessions.py`·`jobs.py`에 순환 없음.

**스윕 안전성 실측 3건 (2026-09-02, 직접 실행)**

| 무엇 | 결과 |
|---|---|
| 무한 루프 — 스윕이 job을 걸었는데 claim이 계속 불가하면? | **없다.** `available_at`을 1시간 뒤로 밀어 claim 불가 상태를 만들고 워커를 0.5초 돌렸다(poll 0.02초): 스윕 호출 **21회** = poll 주기당 1회로, 스핀하지 않고 유휴 대기한다. job 총수는 **1 유지**(재등록 없음) — 모든 상태의 job을 보는 `not exists`가 막는다 |
| `ENDED_SESSION_STATUSES` 런타임 값 | `('completed', 'failed')` · `'active' in ...` = **False** |
| `_save_final` 경로의 flush가 호출자 트랜잭션 안인가 | **아니다.** 그 블록은 `pool.acquire()`만 하고 명시 트랜잭션이 없으며, `save_final_transcript`가 자기 트랜잭션을 닫은 뒤에 flush가 불린다 |

프로브는 dev DB에 세션 1건을 만들고 지웠다. **baseline 복원 확인**: 세션 3 · 발화 51 · 패턴 4 ·
occurrence 8 · job 21 · 발음시도 3 — 마이크 1회 좌표 그대로다.

⚠️ **커밋 `1c8446b`의 "게이트 재확인: 365 passed"는 틀렸다 (2026-09-02 정정).** 그 커밋 직전에
돌린 게이트는 실제로 `7 failed, 356 passed, 2 errors in 9.24s`였고, 출력을 `| tail -2`로 파이프해
exit code가 `tail`의 것이 되는 바람에 `&&` 체인이 실패를 무시하고 커밋까지 진행했다.
**원인은 회귀가 아니라 동시 실행이다** — 코드 리뷰를 subagent에 위임한 직후였고, 리뷰어도
베이스라인으로 전체 스위트를 돌린다. `tests/conftest.py`의 `test_database`가 매 실행 시작에
`DROP DATABASE`+`CREATE DATABASE`를 하므로(`scripts/db_utils.py:53-54`) 두 실행이 같은
`ohmyenglish_test`를 두고 충돌한다. 새 함정 **H-X**로 남겼다.
정정 후 실측: 같은 순서를 재현해도 나지 않고 **8회 연속 365 passed**다. 게이트 명령을 파이프로
감싸 exit code를 잃지 않도록 할 것 — 이것이 이 사고의 두 번째 원인이다.

**스윕과 종료의 타이밍 — 직접 따라간 결과 (2026-09-02)**

`_close_and_record`는 flush를 `end_session` **앞**에서 부르므로 그 순간 세션은 아직 `active`다.
그래서 그 창에 스윕이 겹쳐도 **스윕은 그 세션을 건너뛴다** — 안전한 방향이다. 영구히 놓치는
경로도 없다: 종료 기록 후 세션이 `completed`가 되면 다음 유휴 사이클이 본다. 이 안전성은
`_await_pending_saves()`가 **종료 기록보다 먼저** 모든 저장을 회수하는 데 의존한다 —
그래야 세션이 `completed`로 보이는 순간 그 발화가 전부 커밋돼 있다(L4 순서 제약).

🔁 **철회된 엣지 1건 — 되살리지 말 것 (2026-09-02).** 한때 이 자리에 "`_await_pending_saves()`가
`DRAIN_TIMEOUT`을 넘겨 저장이 **비행 중인데** `end_session`이 커밋되면 스윕이 아직 마지막이
아닌 발화에 job을 걸어 `frequency`가 부풀 수 있다"를 미해소로 적었다. **그 전제가 틀렸다.**
코드 리뷰가 반박했고 내가 직접 실측해 확인했다 — `_await_pending_saves`의 본문을 그대로 옮겨
`DRAIN_TIMEOUT=0.2`로 세 종류의 자식을 돌린 결과:

| 자식 | drain 반환까지 | 반환 시점 `done` | 커밋 |
|---|---|---|---|
| 느린 저장(취소 시 롤백) | 0.20s | **True** | 없음 |
| cleanup에서 await하는 저장(asyncpg ROLLBACK 모사) | **0.50s** | **True** | 없음 |
| 취소를 삼키고 커밋까지 하는 저장(최악 가정) | **0.50s** | **True** | drain 반환 **전에** 커밋 |

`asyncio.wait_for`는 타임아웃에서 `_GatheringFuture`를 취소하는데, `Task.cancel()`이
`_fut_waiter.cancel()`이 True면 그 자리에서 돌아가므로 외부 태스크는 **gather가 완료될
때까지 계속 매달린다**. gather는 자식이 전부 끝난 뒤에만 완료된다. 즉 **드레인은 상한을
넘겨서라도 자식을 회수한다** — 반환 시점에 비행 중인 저장은 없다.

**그래서 이것은 위험이 아니라 안전성의 근거다**: 세션이 `completed`로 보이는 순간 그 세션의
발화는 전부 커밋돼 있다(L4 순서 제약이 `DRAIN_TIMEOUT`을 넘겨도 유지된다). 끝난 세션에 발화가
추가되는 다른 경로도 없다 — `save_final_transcript` 호출처 전수 확인: 게이트웨이(종료 전) ·
`inject_errors.py`(`mark_session_ended`가 맨 마지막) · `smoke_analysis.py`(세션을 종료하지 않는다).

⚠️ **왜 철회를 기록으로 남기는가**: 내가 그때 함께 기각한 완화안("스윕이 `ended_at` 직후 몇 초는
건너뛴다")을 다음 세션이 되살릴 동기가 되기 때문이다. 그 완화안은 **없는 위험을 막으려고
실재하는 시간 창 버그를 들여온다.** 스윕에 시간 창을 넣지 마라.

📌 **부수 발견 (I-1과 무관한 기존 성질)**: 위 표가 보여주듯 `DRAIN_TIMEOUT`은 **드레인 시간의
상한이 아니다** — 자식의 cleanup만큼 넘긴다. 취소가 저장을 "끊는" 것도 아니다(최악 자식은
취소 후에도 커밋했다). 방향이 안전하므로(늦게 닫힐 뿐 잃지 않는다) 결함으로 보지 않지만
`_await_pending_saves` docstring이 그것을 "상한"이라 부르던 서술은 정정했다.

**남은 추측 1건 (마이크 2회에서 볼 것)**: Nova는 agent final을 `completionEnd`에 내는데
(`nova.py:249-250·340-358`) barge-in 등으로 사용자 ASR final이 그 **뒤에** 도착하면 한 문장이
여전히 두 묶음으로 갈릴 수 있다. 실측이 없어 단정하지 못한다 — 리뷰가 추측으로 표시한 것이다.

**대조 대기**: 오탐이 정말 사라졌는지는 **실물 마이크 2회**로 확인한다. 1회의 좌표
(세션 `bbfc3908-…`, 발화 51 · 패턴 4 · occurrence 8)는 보존돼 있다.

---

✅ **결정 (2026-09-01, 캡틴): (가) 턴 경계까지 모아서 분석한다.**
화면 표시는 그대로 두고 **분석 입력만** 합친다 — agent가 응답을 시작하면 그 직전까지의 사용자
final을 하나로 이어 job 1건을 건다.
하네스 **N8("실발화 병합 `u1`+`u2`")**이 이미 이 경로를 예정했으므로 검증 시나리오도 있다.
⚠️ 착수 전에 5차수를 열지 않는다 — 오탐이 섞인 데이터로 5차수를 판정하면 그 판정이 오염된다.

⚠️ **"고칠 자리는 `utterances.py:140` 한 곳"이라던 앞선 서술은 틀렸다** (2026-09-01 정정).
합치려면 **턴이 끝났다는 신호**가 필요하고 저장 시점에는 그것을 알 수 없다 — 그 발화가 마지막인지
아직 모른다. 실제 접점은 **4곳**이다. 코드 확인으로 얻은 좌표:

| # | 어디 | 무엇을 |
|--:|---|---|
| 1 | `services/utterances.py:140` (`save_final_transcript`) | 사용자 learning 발화에서 **즉시 enqueue 하지 않는다**. 저장은 그대로 — 화면·`sequence_no`는 건드리지 않는다 |
| 2 | `services/jobs.py` 또는 `utterances.py` (신설) | **flush 함수** — 세션의 **뒤에서 이어지는 사용자 learning 발화 묶음**(중간에 agent 발화가 없는 구간)을 찾아 그 **마지막 발화 1건에만** job을 건다. 멱등성은 기존 `uq_analysis_jobs_pending_utterance`(001:157)가 이미 준다 |
| 3 | `audio_gateway/session.py` **두 지점** | ① `_store_final`(`:280-283`)에서 **agent** final을 저장한 직후 flush ② `end_session` 경로(`:154`)에서도 flush. **②가 없으면 마지막 사용자 묶음이 영원히 분석되지 않는다** — 대화가 사용자 발화로 끝나는 것이 정상이다 |
| 4 | `services/analysis.py` `_LOAD_INPUT_SQL` | 지금은 `u.transcript` 한 건을 읽는다(`select u.transcript, s.user_id … where u.id = $1`). **그 발화로 끝나는 사용자 묶음의 전사문을 이어서** 돌려주게 바꾼다. 여기가 "분석 입력만 합친다"의 실체다 |

**묶음의 정의**: 같은 세션 · `speaker='user'` · `utterance_type='learning'` · `sequence_no`가 연속이며
사이에 다른 speaker가 없는 최대 구간. `ANALYZED_SPEAKER`·`ANALYZED_UTTERANCE_TYPE`
상수(`utterances.py:33-35`)를 그대로 쓴다 — enqueue 조건과 갈라지지 않게 두 곳이 같은 상수를 본다.

**T0(red) 계획** — 부재 가드가 되지 않게 **긍정 단정**으로 짠다(함정 H-M):
① 사용자 발화 3건을 연속 저장하면 job이 **3건이 아니라 0건**이다(flush 전) ②
agent final 저장 후 job이 **정확히 1건**이고 그 `utterance_id`가 **묶음의 마지막**이다 ③
`_load_input`이 세 전사문을 **이어붙인 문자열**을 돌려준다 ④ 사용자 발화로 끝난 세션을
`end_session`하면 job이 1건 생긴다 ⑤ agent 발화가 사이에 끼면 묶음이 **둘로 갈린다**.

**회귀로 지켜야 할 것**: 스텁 모드 E계층 시나리오는 발화 1건마다 job 1건을 기대한다 —
`inject_errors.py`가 `wait_for_jobs`로 job 수렴을 기다린다. 묶음이 1건이면 동작이 같지만
**연속 주입 시나리오(E1은 문장 5개)는 job 수가 5 → 1로 줄어든다.** 그 단정을 함께 고친다.

**원인 체인 (관측)**:
1. `endpointingSensitivity=MEDIUM`이 발화를 이르게 확정했다. **임계는 약 480ms**
   (`tests/harness/scenarios-N-real-voice.md:52`, N-1 실측) — 다음 말을 고르는 1초가 종료로 읽힌다.
   쪼개진 조각의 저장 시각 차는 1.05~2.54초였다(중앙 1.44초, **임계값이 아니라 상한**).
   내 발화 **18건 중 4건이 문장 중간에서 쪼개졌다** — `"i'm going to"`⇢`"have a meeting"` ·
   `"yes, i prepared."`⇢`"a report."`⇢`"for the meeting."` · `"i will plan the"`⇢`"active plan."`
   (단어가 사라진 것은 아니다 — 합치면 온전하다).
2. `services/utterances.py:140`이 **사용자 learning 발화마다 무조건 `enqueue_analyze`**를 부른다.
   길이·완결성 가드가 없어 **조각 하나가 완전한 문장처럼 분석된다**.
3. 문법 분석기가 조각에서 "주어 없음/목적어 없음"을 찾아낸다. **당연하다 — 주어는 앞 조각에 있다.**

**피해 (실측)**: 이 세션이 만든 occurrence **13건 중 7건이 조각에서 나왔다**.
패턴 6개 중 **2개는 100% 조각산이다** — `verb_form_missing_subject`(freq 4, 조각occ 4) ·
`verb_form_missing_object`(freq 2, 조각occ 2). `article_missing_before_noun`은 freq 5 중 1건이 오염됐다.
**즉 존재하지 않는 약점 2개가 학습자 프로필에 생겼다.**

**왜 중요한가**: 오류 패턴 기억이 이 제품의 핵심 가치다(PRD §7 Error Memory). 오탐 패턴은
§11 추천 루틴의 입력이 되고 복습 큐에 실린다 — **틀린 것을 반복 연습시킨다.** 4차수 P6이
"오탐이면 `frequency`를 오염시킨다"고 가설로 적어둔 것이 **관측으로 확정됐다.**

**완화 (2026-09-01 적용)**: `NOVA_ENDPOINTING_SENSITIVITY=LOW`를 `.env`·`.env.example`에 넣었다.
**단 이것은 완화이고 해소가 아니다** — 값이 HIGH/MEDIUM/LOW 3단뿐이라 조각을 0으로 만들지 못한다.

**후보 2개 (2026-09-01에 (가)로 확정됨 — 기록으로 남긴다)**:
- **(가) 턴 경계까지 모아서 분석한다** — agent가 응답을 시작하면 그 직전까지의 사용자 final을
  하나로 합쳐 job 1건을 건다. 화면 표시는 그대로 두고 **분석 입력만** 합친다.
  하네스 **N8("실발화 병합 `u1`+`u2`", 미실행)**이 이미 이 경로를 예정했다.
- **(나) 조각을 분석에서 제외한다** — 종결 부호가 없거나 너무 짧으면 job을 걸지 않는다.
  값싸지만 **"i don't know." 같은 정상 단문을 함께 잃는다**.
- (가)가 데이터를 잃지 않아 더 낫다고 본다. 고칠 자리는 `services/utterances.py:140` 한 곳이다.

**오염 데이터 정리 — ✅ 완료 (2026-09-01, 캡틴 지시 "오탐 삭제")**

한 트랜잭션으로 지우고 즉시 대조했다. **전사문·세션·job은 지우지 않았다** — 증거이고
I-1 수정 후 같은 좌표로 재대조해야 한다.

| 무엇 | 전 → 후 |
|---|---|
| `verb_form_missing_subject` · `verb_form_missing_object` | **삭제**(각 100% 조각산). occurrence는 FK `CASCADE`로 함께 |
| `article_missing_before_noun` | freq **5 → 4** (조각 occurrence 1건만 삭제) |
| `error_patterns` | 6 → **4** |
| `error_occurrences` | 15 → **8** |
| `utterances` · `learning_sessions` · `analysis_jobs` · `pronunciation_attempts` | **51 · 3 · 21 · 3 그대로**(보존) |

검증: 남은 패턴 4개의 **조각 occurrence가 전부 0**이고, 문법 패턴은 `frequency` = occurrence 수로
일치한다. 발음 시도 3건의 `pattern_id`도 온전하다(`pronunciation_attempts` FK는 `SET NULL`인데
발음 패턴은 지우지 않았으므로 발동하지 않았다).
⚠️ `pronunciation_an_as_a`는 freq 1 · occurrence 0인데 **정상**이다 — 발음 패턴은 **시도 수**를
센다(`docs/database-schema.md:111`). 이 불일치를 버그로 오인하지 마라.

### I-2. `target_sound` 값역이 계획과 다르다 — 관측 3건 (설계 재검토 필요)

실측된 키는 **`am_as_i_m` · `w_as_vw` · `an_as_a`**다. 계획서·시나리오가 가정한 `th_as_s` 같은
**음소 치환이 하나도 없다.** `am_as_i_m`은 `"i'm"`→`"I am"` 축약형이고 `an_as_a`는 관사다 —
**발음이 아니라 문법에 가깝다.** 게다가 `am_as_i_m` 시도는 `outcome=correct`로 판정됐다.

이로써 A-2가 "표시 사전·`_as_` 분해 규칙은 발명값"이라 유보했던 판단의 **입력이 생겼다**.
§10이 의도한 "발음 시범"과 Nova가 실제로 하는 일이 어긋나는지 재검토한다.
관측 3건은 표본이 작으므로 마이크 세션을 더 돌린 뒤 판정한다.

### I-3. `awscrt` teardown Traceback — 무해, 기록만

세션 종료 시 `awscrt/aio/http.py:389`에서 `InvalidStateError: CANCELLED`(취소된 future에
`set_result`) 1건 + `Treating Python exception as error 3(AWS_ERROR_UNKNOWN)`.
**우리 코드가 아니다.** 세션은 `completed`, 결과 API 200, 발음 저장 실패 로그 0건 —
시도 3건 전부 저장됐다. 로그 노이즈로만 다룬다.

### I-4. `active` 고아 세션 리퍼 — ✅ 완료 (2026-09-02 신설, 2026-09-03 구현)

**캡틴 결정 (2026-09-03): "1분 이상 답이 없으면 `failed`로 닫는다."** 후보 ②(시간 유예) 계열이고
①(기동 시 전부 닫기)은 채택되지 않았다. **무활동의 기준은 마지막 발화 시각**
(`utterances.created_at` 최댓값 — **화자를 가리지 않는다**, 발화가 없으면 `started_at`),
유예는 **60초**(`ORPHAN_IDLE_GRACE`).

**착수 전 확인에서 드러난 것 2개 — 설계를 바꿨다.**

1. **유예만으로는 위험하다.** 사용자가 60초 넘게 뜸을 들인 **진행 중** 세션이 닫히고, 그 직후
   스윕이 아직 자라는 중인 묶음을 걷어 **I-1 오탐이 되살아난다**(`flush_ended_sessions`는
   `failed`를 "끝난 세션"으로 본다). → **live 가드**를 함께 넣었다: `api/ws.py`가 살아있는
   WebSocket의 세션 id를 `app.state.live_sessions`에 등록·해제하고 리퍼는 그 집합의 세션을
   건드리지 않는다. 캡틴이 이 조합을 선택했다(단순한 "마지막 발화만" 안을 기각).
2. **리퍼가 닫은 세션의 결과 화면은 `connection_failed`("연결 실패")가 된다** — `results.py`
   규칙 1이 job 상태를 보지 않고 최우선하므로, 스윕이 걷은 묶음이 분석을 끝내도 **그 화면에
   교정은 실리지 않는다.** 사용자가 보는 변화는 "분석 대상 없음" → "연결 실패"뿐이다. 오류
   패턴·숙련도 같은 누적 데이터는 정상 갱신된다. 프로세스가 죽어 끝난 세션이라는 사실을 그대로
   표시하는 쪽을 택했다.

**구현 4곳**

| 파일 | 무엇 |
|---|---|
| `app/services/sessions.py` | `ORPHAN_IDLE_GRACE`(60초) + `reap_orphan_sessions(conn, *, live_session_ids, idle_after)`. `learning_sessions` 생명주기 SQL의 단일 소유자라서 여기 뒀다 |
| `app/workers/analysis_worker.py` | `reap_orphans()` — 큐가 빌 때 **리퍼 → 스윕** 순서로 부른다. 이 순서라서 방금 닫힌 세션의 묶음이 **같은 유휴 사이클에** 걷힌다 |
| `app/api/ws.py` | 세션 행 생성 **직후** 등록, `finally`에서 소켓 close **앞에** 해제 |
| `app/api/main.py` | `create_app()`이 `app.state.live_sessions`를 만든다(lifespan이 아니다 — 닫을 자원이 아니고, lifespan 없이 라우터만 쓰는 호출자에게도 있어야 한다). lifespan은 워커에 **집합 객체 자체**를 주입한다 |

**게이트 (2026-09-03, 이 절을 쓴 세션이 직접 실행)**: **377 passed**(366 → 377, +11) ·
ruff·`format --check`(27파일)·`ty` 전부 exit 0 · `tests/**` 베이스라인 **6 errors·4 files 유지** ·
프론트 `tsc`·`eslint` exit 0.

**red→green: 11건 중 11건이 red였다** — 부재 가드가 하나도 없다(H-M). 서비스 8건은
`ImportError: cannot import name 'ORPHAN_IDLE_GRACE'`, 워커 2건은
`TypeError: run_worker() got an unexpected keyword argument 'live_sessions'`, ws 1건은
`AttributeError: 'State' object has no attribute 'live_sessions'`로 각각 실패했다.

**뮤테이션 2건 전부 죽었다** (직접 실행 후 복원):

| 무력화한 것 | red가 된 테스트 |
|---|---|
| live 가드 → `and ($1::uuid[] is not null)` | `test_reaper_skips_a_session_a_live_connection_still_owns` **만** (1 failed, 7 passed) |
| `where s.status = 'active'` → `where s.status is not null` | `test_reaper_does_not_reclose_a_session_that_already_ended` **만** (1 failed, 7 passed) |

**시각을 `sleep`으로 만들지 않는다.** PostgreSQL `now()`는 트랜잭션 시작에 고정되므로 `db_conn`
안에서는 기다려도 유예를 넘길 수 없다 — 공용 헬퍼 `conftest.backdate_session`이 행을 과거로 민다.

**비용 실측 (dev DB `explain analyze`)**: `Execution Time` **0.389 ms**, 그리고
`max(utterances.created_at)` 서브플랜은 **never executed**였다 — `status='active'` 필터가 먼저
3행을 걸러서다. 즉 비용은 이력 크기가 아니라 **`active` 세션 수**에 걸린다(스윕의 0.400 ms와
같은 자리수). ⚠️ 이 측정이 함정 하나를 만들었다 — **`explain analyze`는 UPDATE를 실제로
실행한다**(`pitfalls.md` **H-Y**). 그때 `active` 세션이 0건이라 아무것도 바뀌지 않았을 뿐이다.

**실물 확인 (2026-09-03, 이 세션이 직접 실행)** — 전용 스크래치 DB `ohmyenglish_i4check`에서 돌렸다.
dev DB는 마이크 회차 대조용으로 보존 중이고 `ohmyenglish_test`는 pytest가 매 실행 DROP하는 공유
자원이라(**H-X**) 둘 다 쓰지 않았다. 끝난 뒤 dev DB 대조 — 세션 3 · 발화 51 · 패턴 4 · occurrence 8 ·
job 21 · 발음시도 3 · `active` 0으로 **handoff 기록값과 완전 일치**(무손상), 스크래치 DB는 삭제했다.

고아는 **실제 프로세스 사망으로** 만들었다: 문서 실행 명령으로 백엔드를 띄우고 WS 세션을 연속으로
여는 클라이언트를 돌린 뒤 `kill -9`. 스텁 세션은 밀리초에 끝나므로(픽스처를 지연 없이 재생한다)
이 방법만이 "종료 기록 전에 죽은" 상태를 만든다 — DB를 손으로 고치지 않았다.

| 회차 | 만들어진 고아 | 재기동 후 |
|---|---|---|
| 1 | 891건 완주 중 `active` **1건** — 발화 0 · `ended_at` null (**`started_at` 경로**) | 나이 **63초**에 `failed` + `ended_at` 기록 |
| 2 | 동시 3루프에서 `active` **3건** — 발화 5·3·2건. 그중 하나는 **사용자 발화 1건에 job 0건**, 즉 I-4 증상(결과 화면 "분석 대상 없음" 고정) 그 자체 | 3건 전부 `failed`, job **3 → 4**(스윕이 그 묶음을 걸었다), 이어서 전부 `done` |

즉 **리퍼 → 스윕 → 분석** 회복 체인이 실물에서 관통했다. 워커가 먼저 기존 job 3건을 비우고 큐가
빈 뒤에 리퍼가 도는 순서도 그대로 관측했다.

**실물 확인이 결함 1건을 찾아 고쳤다 — 리퍼 로그가 실물에서 보이지 않았다.** 문서가 지정한 실행
명령(`docs/ops/local-run.md`)은 root 로거에 핸들러를 두지 않아 `logging.lastResort`가 WARNING
이상만 흘린다: 같은 실행에서 INFO `analysis worker started`는 **0건**인데 WARNING `텍스트가 아닌
프레임을 무시했다`는 출력됐다(`pitfalls.md` **H-Z**). 리퍼가 걷었다는 **유일한 런타임 신호**가
INFO였으므로 `logger.warning`으로 올리고 tripwire를 붙였다
(`test_the_reaper_reports_above_info_so_the_documented_run_shows_it` — 레벨을 INFO로 되돌리는
뮤테이션으로 red 확인). 고친 코드로 다시 돌려 실물 로그에서 그 줄을 관측했다:
`마지막 발화 후 60초 넘게 조용했던 active 세션 3건을 failed로 닫았다 (I-4): [...]`.

게이트 갱신 — **378 passed**(377 → 378, tripwire 1건). 나머지 수치는 위와 같다.

**코드 리뷰 (2026-09-03) — 독립 리뷰어 2명. 판정 Not Approve / Block. 지적을 반영해 닫았다.**
`ReportFindings`가 두 리뷰어의 툴셋에 없어(각자 `ToolSearch`로 확인) 텍스트로 보고했다. 둘 다
`pytest` 미실행·DB 미조회(**H-X** 준수)이고 게이트 수치는 내가 준 값을 썼다 — 즉 **판정은 독립,
수치 증거는 내 것**이다. 두 리뷰어 모두 CRITICAL 0건이므로 하드 블록은 아니었고, Approve 기준
(HIGH 0)을 못 넘긴 것이다.

**둘이 독립적으로 같은 HIGH를 지목했다**: live 가드의 **유일한 배선**(`api/main.py`의
`live_sessions=app.state.live_sessions`)을 덮는 테스트가 0건이라 복사본으로 바꾸거나 kwarg를
빼도 스위트가 전부 green이다. 변경 전체에서 레버리지가 가장 큰 한 줄에 red 증거가 없었다.

| 지적 | 등급 | 조치 |
|---|---|---|
| live 가드 배선에 tripwire 없음 (`api/main.py`) | **HIGH (양쪽)** | ✅ 통합 테스트 `test_lifespan_hands_the_live_session_registry_itself_to_the_worker`. **뮤테이션 2방향 전부 red 확인** — 복사본(`set(app.state.live_sessions)`) · kwarg 삭제. 순서가 이 테스트의 전부다: lifespan을 연 **뒤** 등록하고, 등록한 **뒤** 과거로 민다(그래야 복사본이 그 id를 못 갖는다) |
| "단일 프로세스" 전제가 이 리포에서 **거짓** — `tests/harness/inject_errors.py`가 앱 밖에서 `active` 세션을 소유하고 `--wait` 기본 **180초**(유예의 3배) 동안 발화 없이 기다린다 | HIGH(A) / MEDIUM(B) | ✅ docstring 정정 — 전제를 단정하지 않고 **실재하는 예외를 명시**했다(`sessions.py` + 하네스 모듈 docstring ⚠️). 동작은 바꾸지 않았다: 스크립트 끝의 `mark_session_ended`가 덮어써 최종 상태가 수렴하고 하네스는 status를 단정하지 않는다 |
| 리퍼 예외가 **같은 사이클의 I-1 스윕을 막는다**(직렬로 묶였다) | MEDIUM(A) | ✅ 리퍼를 자기 `try/except`로 격리 + 테스트 `test_a_failing_reaper_still_lets_the_sweep_recover_a_lost_run`(격리를 제거하는 뮤테이션으로 red 확인) |
| `_END_SESSION_SQL`에 상태 가드가 없어 `end_session`이 리퍼를 **조용히 되돌린다** | MEDIUM(A) / LOW(B) | ✅ **캡틴 결정(2026-09-03): 가드를 넣는다.** `and status = 'active'` + `returning id`로 0행을 감지해 WARNING. red 관측 후 구현 |
| 나이 상한 없는 백필 버스트 · `ended_at`의 의미가 "리퍼가 알아챈 시각"으로 바뀐 것 | MEDIUM(A) | ✅ 문서화만. 상한을 넣으면 **진짜 오래된 고아가 영구히 안 걷힌다**. `ended_at`을 읽는 앱 코드는 0곳(grep) |
| `ws.py` 주석이 **일어날 수 없는** 위험을 순서의 근거로 든다 | LOW | ✅ 정정 — 갓 만든 세션은 `started_at` 기본값 `now()` 때문에 리핑 불가다. 순서의 진짜 근거는 바로 뒤 `_load_known_sounds_or_empty`의 **await 창**이다 |
| "화자 무관"이 긴 agent 턴을 지켜주는 것처럼 읽힌다 | LOW | ✅ 정정 — 시계는 **final이 저장되는 순간에만** 전진하고(partial은 방송만) 그 구간을 지키는 것은 live 가드다. 그래서 가드는 엣지 장치가 아니라 **정상 사용 핫패스**에 있다 |
| `idle_after`가 죽은 seam | LOW | ✅ 경계 테스트로 살렸다 — `test_reaper_honours_a_custom_grace`가 같은 세션을 10분·1분 유예로 재서 경계가 값에 따라 움직이는 것을 본다 |
| `test_sessions.py`의 `ended_at` 단정 **근거**가 틀렸다 | LOW | ✅ 단정 유지, 이유 정정 — 결과 경로는 `ended_at`을 읽지 않는다(`results.py`는 `status`만) |
| `live_sessions.add`가 `try` 밖 → 레지스트리 부재 시 세션 행만 남는다 | LOW | ✅ 레지스트리 조회를 **세션 행 생성보다 앞으로** 옮겼다 — 실패해도 남길 행이 없다 |
| 기존 I-1 스윕 테스트에 **벽시계 의존**이 생겼다(60초 넘으면 리퍼가 개입) | LOW | ✅ 그 테스트에 `live_sessions`를 넘겨 리퍼를 변수에서 제거했다 |

**✅ 캡틴 결정 (2026-09-03): `end_session`은 `active`인 세션만 닫는다.**
`_END_SESSION_SQL`에 `and status = 'active'`를 넣고 `returning id`로 0행을 감지해 **WARNING**을
찍는다(**H-Z** — 문서 실행 경로에서 INFO는 보이지 않으므로 이 신호는 WARNING이어야 한다).
가드가 없던 동안에는 리퍼가 `failed`로 닫은 세션을 소유자가 `completed`로 덮어써 **리퍼의 판정과
`ended_at`이 흔적 없이 사라졌다** — 그 상황 자체가 "live 가드가 진행 중 세션을 놓쳤다"는 뜻이고
그때 스윕은 이미 자라는 묶음을 걷었을 수 있으므로, 조용히 수렴시키는 것이 가장 나쁜 선택이었다.
정상 흐름(`active` → 종료)에서는 값이 그대로여서 이 가드가 보이지 않는다.

red 증거: 가드 없는 상태에서 `test_end_session_does_not_overwrite_a_reaped_session`이 실제로
`failed` → `completed` 덮어쓰기를 잡아 red였다(1 failed · 10 passed). 무회귀 짝으로
`test_end_session_closes_an_active_session`을 함께 뒀다 — 가드가 정상 종료까지 막으면 모든
세션이 영원히 `active`로 남으므로 그쪽도 못이 필요하다.

⚠️ **이 결정이 앞선 서술 1건을 낡게 만들었고 함께 정정했다.** 하네스(`inject_errors.py`) 세션이
리퍼에게 닫히면 이제 **`failed`로 끝난다** — 끝의 `mark_session_ended(…, "completed")`가 가드에
막혀 되돌리지 못하고 경고만 남긴다. 시나리오 자체는 성립한다(하네스가 보는 것은 패턴·occurrence
이고 status를 단정하지 않는다). 단 그 세션의 결과 API는 `connection_failed`가 된다 — Task 9에서
회귀로 오인하지 않도록 `sessions.py`와 하네스 모듈 docstring 양쪽에 못 박았다. 걸리적거리면
**대기 전에 세션을 닫도록** 하네스 순서를 바꾸는 것이 옳은 방향이다(실제 앱도 세션을 닫고 나서
워커가 분석한다).

**리뷰어가 지적한 "실물 확인이 구조적으로 볼 수 없었던 것" — 수용한다.**
`kill -9`는 프로세스와 함께 live 집합을 파괴하므로 가드가 **공집합으로 자동 충족**된다. 즉 실물로
관측한 것은 전부 "가드가 무의미한 경로"였고 **live 가드 자체의 실물 증거는 0건**이다. 그 공백을 위
HIGH 테스트가 메운다(리퍼와 **살아있는** 세션이 같은 프로세스에 공존하는 상황을 실제로 만든다).
함께 정정할 서술 3건 — 위 「실물 확인」 절을 이 세 줄과 **함께** 읽어라:

- **"job 3 → 4"는 "3건 전부 회복"이 아니다.** 고아 3개 중 2개는 턴 경계 flush가 이미 job을 걸어
  뒀고, 사망 경계에서 잃은 묶음은 **1개**였다. 스윕 회복 경로는 실물에서 **묶음 1개**만 검증됐다.
- **`job → done`은 사용자가 교정을 본다는 뜻이 아니다.** 그 세션들의 결과 화면은 전부 규칙 1로
  `connection_failed`이고 프론트 `TERMINAL_STATUSES`라 폴링이 멈춘다(캡틴이 수용한 사항).
- **`coalesce(max(created_at), started_at)`의 분기 선택은 실물이 구분하지 못한다** — 발화 있는
  고아는 두 시각이 붙어 있다. 회차 1(발화 0건)만 `started_at` 경로를 확정하고 나머지는 단위 테스트가 덮는다.

**리뷰어가 반증을 시도했고 깨지지 않은 것** (근거로 재사용 가능): in-process 등록 창에 `await`
없음 · 리퍼 id 재사용 경로 없음 · `discard`가 `CancelledError`에도 도는 `finally`에 있고
`_safe_close`보다 앞섬 · `list(live_session_ids)`가 `pool.acquire()` **뒤**에 평가되어 스냅샷
순서가 최선 · 리퍼 커밋 후 스윕이 **새 커넥션**을 얻어 같은 사이클에 본다 · `active`인데
`ended_at`이 non-null인 행은 스키마 CHECK + 한 문장 UPDATE로 **존재 불가**.

**리뷰어 보고의 한계(그들이 스스로 명시)**: 프론트 `page.tsx` 미개봉(grep 줄 히트만) · 게이트 수치
미검증 · DB 미조회 · "분석이 60초를 넘긴다"는 관측이 아니라 `--wait` 기본값에서의 **추론** ·
백필 버스트 미관측 · 뮤테이션 미재현(내가 돌린 값 사용).

게이트 갱신 — **383 passed**(378 → 381 → 383: 배선 tripwire · 리퍼 실패 격리 · 유예 파라미터 경계 · `end_session` 가드 2건).

---

## 관련 문서 지도

| 무엇을 알고 싶은가 | 어디 |
|---|---|
| 무엇이 남았나 / 무엇을 놓쳤나 | **이 파일** |
| 지금 어디까지 왔나 / 다음 한 걸음 | `handoff/HANDOFF-*.md` (짧게 유지) |
| 실측된 함정 (반복하지 말 것) | `docs/ops/pitfalls.md` |
| 왜 이렇게 설계했나 | `docs/design/**` — 결정과 근거의 정본 |
| 무엇을 만들어야 하나 | `docs/PRD.md` (v1.1) · `docs/requirements-summary.md` |
| 어떻게 돌리나 | `handoff/HANDOFF.md` §로컬 실행 방법 |
