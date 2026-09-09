# P계층 미실행분 — 위임 회차 (`TASK-37` AC#4·AC#5 잔여)

> 판정 요약: **P계층 미실행 5건(P1 `p2a` · P4 `p2k` · P5 `p2` 쌍 · P6 `p2m` · P9)은 이 회차의
> 제약 아래 전부 「구조적 관측 불가」임.** 대신 스파이크 경로로 **실물 Nova 왕복 9회**를 돌려
> 그 다섯이 무엇에 막혀 있는지를 실측으로 좁혔고, **결함 후보 1건 · 판정 재구성 요구 1건 ·
> 자산 취약 1건**을 얻음.
> 원자료: `.harness/evidence/task37-p/S1~S9*.json` (git 추적 밖)

---

## 1. 환경 — 이 턴에 직접 재서 얻음

| 항목 | 값 |
|---|---|
| 착수 HEAD | `0e981fe` |
| 마감 HEAD | **`fc15b08`** — 회차 중 다른 세션이 `TASK-64` 를 커밋함 |
| HEAD 이동의 측정 귀속 | **영향 없음.** `git diff --name-only 0e981fe fc15b08` 에 `nova.py`·`models/pronunciation.py`·`services/pronunciation.py`·`spike_nova_protocol.py`·`fixtures/` 가 **0건**임 — 스파이크가 읽는 것이 하나도 바뀌지 않음 |
| 백엔드 | pid **52228** · `VOICE_ADAPTER=stub_unresponsive` · `WORKER_ENABLED=false` (`ps eww` 로 프로세스에서 읽음) · 기동 2026-09-09 17:34:58 · `/health` `{"status":"ok"}` |
| 프론트 | `:3000` 생존 (pid 22864 · 37650) |
| 공유 여부 | **공유로 판정함** — 백엔드를 다른 세션이 같이 씀. DB 는 StockAgent·En-Coach 와 공유 인스턴스임 |
| 픽스처 길이 | `p1a` 2.539s · `p1m` 2.492s · `p1k` 3.049s · `p2a` 2.957s · `p2m` 3.038s · `p2k` 3.792s. md5 여섯이 서로 다름 — 빈 파일 0건 |

**이 회차는 백엔드를 재기동하지 않았고 워커를 켜지 않았고 `pytest` 를 돌리지 않았음.**
앱 코드·프론트 코드·`.env` 를 읽기만 했음.

---

## 2. 무엇이 미실행이었는가 — 원자료로 확정함

시나리오 문서의 상태 열은 쓰지 않았음(§6-1 참조 — 낡음). 아래는 회차 기록과 **원자료**로 대조한 것임.

| 항목 | `p1` 쌍 | `p2` 쌍 | 미실행분 |
|---|---|---|---|
| P1 정확 발음 기준선 | 4차수 앱 경로 `PASS` | **미실행** | `p2a` 앱 경로 |
| P2 음소 치환 | 5차수 `PASS` | 5차수 `FAIL`(왜곡) | 없음 |
| P3 발음 교정 여부 | 4·5차수 `PASS` | 5차수 `PASS` | 없음 |
| P4 강한 억양 | 4차수 `PASS` · 5차수 미재현 | **미실행** | `p2k` 앱 경로 |
| P5 한글 전사문의 분석 처리 | 4차수 `PASS` | **미실행** | `p2` 쌍 |
| P6 오탐 | 4차수 `PASS` | **미실행** | `p2m` 종단 |
| P7·P8 | 5차수 `PASS` | — | 없음 |
| P9 tool 종단 | — | — | **미획득** |
| P10·P12 | 5차수 `PASS` | — | 없음 |
| P11 | 5차수 구조적 관측 불가(기준선 고정) | — | 없음 |

**근거**: `runs/2026-08-26-run-4.md` 16행(*"P1~P7 완료 — 단 `p1` 쌍만"*) · `runs/2026-09-09-run-5.md`
P계층 절 · 그리고 5차수 실물 2차 세션의 원자료 헤더
`runs/2026-09-09-run-5-live/transcripts-repr-9664afd1.txt:3` — **`# 흘린 WAV: p1m → p1k → p2m`**.
즉 그 세션이 흘린 것은 셋이고 **`p2a`·`p2k` 는 앱 경로를 지나간 적이 없음**(§6-2).

---

## 3. 못 돌린 것과 이유 — 「구조적 관측 불가」

⛔ **아래 다섯은 `FAIL` 이 아님.** 프로그램이 기대와 다르게 동작한 것이 아니라 **전제를 세울 수
없어 관측하지 못한 것**임.

| 항목 | 세울 수 없는 전제 | 근거(코드·프로세스로 확인) |
|---|---|---|
| **P1** (`p2a`) | 앱 경로에는 `VOICE_ADAPTER=nova` 와 브라우저 레그가 필요함 | 지금 프로세스가 `stub_unresponsive` 임(`ps eww`). 재기동은 이 회차 금지 — 다른 세션이 같은 프로세스를 씀 |
| **P4** (`p2k`) | 위와 같음 | 위와 같음 |
| **P5** (`p2` 쌍) | 분석 job 이 `done` 까지 가야 함 | 워커 금지(`H-AT`). `WORKER_ENABLED=false` 를 바꾸지 않았음 |
| **P6** (`p2m` 종단) | 위와 같음 | 위와 같음 |
| **P9** | ① Nova 어댑터 ② `report_pronunciation_coaching` 가 `outcome='incorrect'` 로 도착 | `PronunciationEvent` 를 내는 자리가 **`nova.py:544` 하나**임(grep 2종으로 확인) · `stub.py` 에 `pronunciation` 참조 **0건** → 지금 어댑터로는 사슬이 시작되지 않음 |

**브라우저 레그가 필요한 항목은 이 회차에 브라우저 제어 도구가 없어 시도하지 않았음.**
스크린샷을 만들지 않았고 화면 렌더를 단정하지 않았음.

### 3.1 P11 만은 브라우저 없이 재확인했음 — 기준선 유지

P11 은 「화면이 **없다**」를 고정한 항목이라 부재 확인에 브라우저가 필요하지 않음. `fc15b08` 에서
코드로 다시 셈:

| 무엇 | 값 |
|---|---|
| 프론트 라우트(`page.tsx`) | **2개** — `app/page.tsx` · `app/results/[sessionId]/page.tsx` |
| API 클라이언트 export 함수 | **2개** — `fetchNextPlan` · `fetchSessionResults` |
| `app/`·`lib/` 의 `review`·`복습` 참조 | **0건** |

5차수의 기준선이 그대로임 — 발음 복습 과제가 도달할 화면이 여전히 0개임. 소유자는 `TASK-3`·`TASK-10` 임.

---

## 4. 돌린 것 — 스파이크 경로 실물 Nova 왕복 9회

**왜 이 경로인가**: 앱 경로가 막힌 상태에서 위 다섯이 **무엇에** 막혀 있는지를 좁힐 수 있는 유일한
살아 있는 수단임. DB 세션을 만들지 않아 보존 세션을 위험에 두지 않음.

명령 꼴: `cd app/backend && .venv/bin/python ../../tests/harness/spike_nova_protocol.py --wav <픽스처> [--tools] [--app-prompt]`

| # | 픽스처 | 프롬프트 | ASR 전사문 | `toolUse` | payload |
|--:|---|---|---|--:|---|
| S1 | `p2a` | 스파이크(tool 없음) | `i finished the report and shared the results with my team.` | — | — |
| S2 | `p2m` | 스파이크 + tool | `i finished the la porte en chaille de lesseps with my team.` | **1** | `target_form:"I finished the port of Shell of Lesseps with my team." · outcome:"pending"` |
| S3 | `p2m` | **앱** + tool | `i finished the la porte en chaille de lesseps with my team.` | **0** | — |
| S4 | `p1k` | **앱** + tool | `아이싱크 아이파운드 쓰리 베리 유스풀 비디오즈` | **0** | — |
| S5 | `p1k` | 스파이크 + tool | `아이싱크 아이파운드 쓰리 베리 유스풀 비디오즈` | **1** | `target_form:"I think I found three very useful videos." · outcome:"pending"` |
| S6 | `p2k` | **앱** + tool | `아이피니시트더리포트엔쉐어드더리절치위드마이팀` | **0** | — |
| S7 | `p2k` | 스파이크 + tool | `아이피니시트더리포트엔쉐어드더리절치위드마이팀` | **1** | `target_form:"I will initiate the report and share the results with my team." · outcome:"pending"` |
| S8 | `p1k` | **앱** + tool (재측정) | `아이싱크 아이파운드 쓰리 베리 유스풀 비디오즈` | **0** | — |
| S9 | **`p2a`**(정확 발음) | 스파이크 + tool | `i finished the report and shared the results with my team.` | **1** | `target_form:"I finished the report and shared the results with my team." · outcome:"pending"` |

**S2/S3 · S4/S5 · S6/S7 이 통제 대조 세 쌍임** — 같은 픽스처·같은 tool 스키마·같은 모델에서
**시스템 프롬프트만** 갈랐음. 각 쌍의 ASR 전사문이 문자까지 같아 오디오·ASR 이 변수에서 빠짐.

**관측 수단의 판별력을 먼저 증명했음**(「0건」을 결함으로 올리기 전의 요건). 같은 스크립트·같은
`--tools` 플래그가 S2·S5·S7·S9 에서 `toolUse` 를 **잡았음.** 즉 S3·S4·S6·S8 의 0건은 드라이버가
그 신호를 못 잡는 것이 아님.

### 4.1 S1 — `p2` 쌍의 실측 ASR 기준선이 생김

`p2a` 전사문이 기대 문장과 **문자 단위로 일치**함. 5차수가 `p2m` 을 판정할 때 대조한 것은
**하드코딩된 기대 문장**이었고 실측 `p2a` 전사문이 아니었음 — 이 회차가 그 대조 기준을 실측으로
바꿨고 **5차수의 `P2`(`p2m`) `FAIL` 판정은 유지됨**(기대 문장과 실측 `p2a` 가 같으므로).

⚠️ 이것은 P1 의 앱 경로 단정이 아님. P1 은 전사문 외에 **분석 findings 0건**과 **화면**을 함께
요구하므로 여전히 미실행임.

---

## 5. 발견 — 결함 후보와 재구성 요구

### F1 · 결함 후보 (심각도 높음) — 앱 프롬프트에서 발음 코칭은 **발화되는데** tool 보고가 0건임

**현상**: 앱 프롬프트(`nova.SYSTEM_PROMPT`)로 **한글로 전사될 만큼 심한** 발음을 넣으면 agent 가
규칙 9 의 거동(문장을 올바른 발음으로 되읽고 다시 말하게 요구)을 **실제로 수행함.** 그런데 규칙 10
이 지시한 `report_pronunciation_coaching` 호출은 **0건**임.

agent 발화(앱 프롬프트 팔에서 직접 관측):

| # | agent 가 말한 것 |
|--:|---|
| S4 | `I think I heard "I think I found three very useful videos."` / `Is that right?  Can you say that again for me, please?` / `If that's what you meant, let's try saying it together: "I found three very useful videos."` |
| S8 | S4 와 사실상 같음(공백 1칸만 다름) — **간헐 아님** |
| S6 | `I hear you want to talk about a report. Let's start with a simple sentence.` / `Can you say, "I shared the report with my team"?` |

앱 프롬프트 규칙 10 원문(`nova.SYSTEM_PROMPT` 28~31행): *"Call report_pronunciation_coaching
twice: once with outcome "pending" right after you have modeled the sentence … Always include
target_sound"*. **문장을 모델링하고 재발화를 요구한 시점에 호출이 있어야 하는데 없음.**

⛔ **5차수의 설명이 이 표본을 덮지 못함.** 5차수는 *"규칙 9(`never for a mild accent`)가 B-2 결정의
구현이라 앱은 고장이 아니다"* 로 닫았으나 그 판정의 표본은 `p1m`(mild)임. `p1k`·`p2k` 는 mild 가
아니며 — ASR 이 한글로 무너지고 agent 자신이 「알아듣기 어렵다」로 취급함 — 규칙 9 의 억제 조항이
발동할 자리가 아님.

**파급**: 설계서 `2026-09-08-pronunciation-review-cycle-design.md` §9 약점 1 의 「복습 시계가 Nova 의
선택에 걸려 있다」가 이 경로에서 **입력 0건**으로 나타남. P9 의 사슬이 첫 칸에서 끊김.

⛔ **원인 미확정.** 후보가 여럿임 — 규칙 10 의 강제력(`Call` 대 스파이크의 `you MUST call`) ·
규칙 11 의 one-per-turn 제약과의 상호작용 · 규칙 2 의 「한 번에 하나만 묻고 멈춤」과의 경합 ·
모델의 tool 우선순위. 이 회차는 어느 것도 배제하지 못했음.

**최소 재현 3단계**:

```bash
cd app/backend
.venv/bin/python ../../tests/harness/spike_nova_protocol.py --wav p1k.wav --tools --app-prompt
#   → [tool use 판정] tool 관련 이벤트: 없음
.venv/bin/python ../../tests/harness/spike_nova_protocol.py --wav p1k.wav --tools
#   → [tool use 판정] tool 관련 이벤트: {'toolUse': 1}
```

증거: `.harness/evidence/task37-p/S4-p1k-tools-appprompt.json` ·
`S8-p1k-tools-appprompt-repeat.json` · `S6-p2k-tools-appprompt.json` (0건 팔) ·
`S5-p1k-tools-spikeprompt.json` · `S7-p2k-tools-spikeprompt.json` (대조 팔)

**제안**(직접 고치지 않음): 규칙 10 을 스파이크 프롬프트처럼 `you MUST call` 로 올리는 것이 가장
작은 개입임. 단 그것은 프롬프트 변경이므로 **기능 신설에 준하고**, 규칙 4·11 의 one-per-turn 계약과
B-2 결정(문법 교정 우선)을 함께 봐야 함 — 이 에이전트가 결정할 범위 밖임.

### F2 · 관측 — `target_sound` 가 없어 P9 는 스파이크 경로로 **대리 관측할 수 없음**

`toolUse` 가 온 4회(S2·S5·S7·S9) **전부** `target_sound` 가 payload 에 없음. 앱 계약에 먹여 확인함 —
`parse_tool_payload(...)` → `PronunciationReport(..., target_sound=None)` 셋 다 `None`(거부는 아님).

그것이 왜 사슬을 끊는가(코드로 확인):

- `services/pronunciation.py` 의 `_UPSERT_PRONUNCIATION_PATTERN_SQL` 이
  `and a.outcome = 'incorrect'` **와** `and length(btrim(coalesce(a.target_sound, ''))) > 0` 을 함께 요구함.
- 세션 종료의 `resolve_dangling` 이 남은 `pending` 을 `incorrect` 로 수렴시켜 앞 조건은 충족되지만
  **뒤 조건이 충족되지 않음** → 패턴이 생기지 않음 → `next_review_at` 도 `review_tasks` 도 생기지 않음.

⚠️ **이것은 앱 결함이 아님.** 스파이크 프롬프트(`TOOL_SYSTEM_PROMPT`)에 `target_sound` 지시가
**없음** — 앱 프롬프트 규칙 10 에만 `Always include target_sound` 가 있음. 그리고 기존
`pronunciation_attempts` 4행은 **전부 `target_sound` 를 가짐**(`am_as_i_m`·`w_as_vw`·`an_as_a`×2,
`signal_source=nova_tool`, 실물 마이크 유래) → 「Nova 가 그 필드를 못 준다」가 아님.

**결론**: P9 는 **앱 프롬프트 + 실물 마이크**로만 관측 가능함. 스파이크 경로로 우회할 수 없음이
이 회차로 확정됨.

### F3 · 판정 재구성 요구 — 「스파이크 1건 대 앱 0건」이 잰 것은 감지 능력이 아님

**S9 가 반증임**: `p2a`(정확 발음 · ASR 전사문이 원문과 완전 일치 · 교정할 것이 없음)에도
스파이크 프롬프트가 `toolUse` **1건**을 냈고 agent 가 `Great job. Say it again for me: …` 로
재발화를 요구했음.

따라서 5차수의 통제 대조가 잰 것은 **「프롬프트가 tool 호출을 강제하는가」**이고
**「모델이 발음 오류를 감지하는가」**가 아님. run-5 의 결론 「0건의 원인은 프롬프트다」 자체는
유지되지만, 거기서 **「능력은 있고 지시만 없다」로 넘어가는 추론은 이 관측이 지지하지 않음.**

같은 재구성이 걸리는 자리 둘: `runs/2026-09-09-run-5.md` 의 「이 차수의 결정적 결과」절 ·
설계서 `2026-09-08-pronunciation-review-cycle-design.md` §9 약점 1 의 2026-09-09 갱신 블록.

⛔ 이 문서들을 이 회차가 고치지 않았음 — 정정 주체가 그쪽임.

### F4 · 관측(낮음) — 스파이크 팔의 `target_form` 이 목표 문장과 다른 사례 2건

| 픽스처 | 실제 목표 문장 | Nova 가 보고한 `target_form` |
|---|---|---|
| `p2m`(S2) | `I finished the report and shared the results with my team.` | `I finished the port of Shell of Lesseps with my team.` |
| `p2k`(S7) | 〃 | `I will initiate the report and share the results with my team.` |
| `p1k`(S5) | `I think I found three very useful videos.` | 일치 |
| `p2a`(S9) | `I finished the report and shared the results with my team.` | 일치 |

`target_form` 은 패턴 키의 재료가 아니므로(키는 `'pronunciation_' || btrim(target_sound)`) 파급은
저장된 기록의 가독성에 한정됨. **결함으로 올리지 않고 관측으로 고정함.**

### F5 · 자산 취약(중간) — 스파이크 원자료가 고정 파일명에 덮여 소실됨

`spike_nova_protocol.py` 는 결과를 세 고정 파일명에만 씀 — `N1-nova-protocol.json` ·
`P-tooluse-nova-protocol.json` · `P-tooluse-appprompt-nova-protocol.json`. 5차수 통제 대조 두 팔의
원본이 `.harness/evidence/` 에 **단 한 벌**이었고 그 폴더는 git 추적 밖임 → 회차를 한 번 더 돌리면
소실됨.

이 회차는 착수 직후 `.harness/evidence/run5-preserved/` 로 세 벌을 복사해 살렸음(그 뒤 9회가
실제로 덮었음). **제안**: 스크립트가 `--out` 을 받거나 파일명에 타임스탬프를 넣게 함.

### F6 · 문서(낮음) — 두 곳이 원자료와 어긋남

1. `scenarios-P-pronunciation.md` §4 표의 상태 열이 P1~P8 전부 「미실행」임. 문서 자신이
   *"아래 표의 상태는 4차수 개시 시점 값이다"* 로 밝혔으나 §4.1 의 P9~P12 상태 열도 「미실행」인 채
   5차수가 P10·P12 를 `PASS`, P11 을 구조적 관측 불가로 닫았음. **상태 열이 정본이 아니게 됐음.**
2. `runs/2026-09-09-run-5.md` AC#4 가 「`p2` 쌍 실물 완료」로 적었으나 그 회차 실물 세션이 흘린 것은
   `p1m`·`p1k`·`p2m` 셋임(`runs/2026-09-09-run-5-live/transcripts-repr-9664afd1.txt:3`).
   **`p2a`·`p2k` 는 앱 경로 미실행임.**

---

## 6. 정리 결과 대조

| 확인 | 결과 |
|---|---|
| 띄운 프로세스 | **0개.** 스파이크는 단발 실행이고 배경 처리기를 쓰지 않았음 |
| 백엔드·프론트 | 손대지 않음. pid 52228 이 회차 전후 동일 |
| DB 세션 생성 | **0건.** 8개 표 전부 delta **+0** — `learning_sessions` 13 · `utterances` 120 · `error_patterns` 9 · `error_occurrences` 24 · `pronunciation_attempts` 4 · `review_tasks` 15 · `session_plans` 2 · `analysis_jobs` 49 |
| teardown | **필요 없음**(생성 0건). 시각창 스윕도 불필요 |
| 보존 세션 6개 | 전건 생존 — `210233be` `completed` · `6225ddaf` `completed` · `b2f0d169` `completed` · `76d9ef31` `failed` · `d127dece` `completed` · `e0c5e580` `completed` |
| 임시 파일 | 없음. 원자료는 `.harness/evidence/task37-p/`(9건) · `run5-preserved/`(3건) |
| 커밋 | 하지 않았음(위임 지시) |

⚠️ **HEAD 가 회차 중 `0e981fe` → `fc15b08` 로 움직였음.** 스파이크가 읽는 파일이 그 커밋에 **0건**
포함되므로 9회 측정 전부 같은 코드에 대한 것임 — 측정을 커밋별로 가를 필요가 없음.
