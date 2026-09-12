# 회차 — `TASK-111`+`TASK-116`: 전용 지시문을 **자기완결로** 고치고 **키 규칙을 조건부로** 바꿈

세션 `ohmyenglish-19` · 2026-09-12 KST · 브랜치 `design/first-vertical-slice`
회차 디렉터리: `tests/harness/runs/2026-09-12-task111-116-selfcontained-key/`

> **왜 한 묶음인가**: 두 태스크가 같은 문면(`nova.PRONUNCIATION_MODE_PROMPT` ·
> `nova._SOUND_INSTRUCTION`)을 고치고, 그 문면은 `test_nova.py` 의 **바이트 대조 게이트**
> (`test_the_pronunciation_prompt_is_byte_identical_to_the_measured_one`)로 실측 **4/4** 판에 묶여
> 있음. 어느 쪽만 고쳐도 그 게이트가 깨지고 회차를 다시 돌려야 하므로 **따로 고치면 회차를 두 번 씀.**
> 이 판단의 정본은 두 태스크의 Implementation Notes 임(`backlog task view TASK-111 --plain`).

---

## 0. ⛔ 상한과 해석 규칙 — 돌리기 전에 적음

### 바꾸는 변수 — **셋**이고, 그것을 서로 가르지 못한다는 것을 먼저 적음

| 변수 | 태스크 | 무엇을 | 근거 |
|---|---|---|---|
| **V1** | `TASK-111` | 고정부 규칙 11 의 *"the one correction for that turn in rule 4"* → 규칙 번호 참조 없이 자기완결 | 전용 프롬프트에 **규칙 4 가 없음**(규칙 8~11 만 있음) |
| **V2** | `TASK-111` | 소리 줄의 *"the one correction of rule 4"* → 자기완결 | 같은 참조가 소리 줄에도 있어 **전용 프롬프트에서 두 번 허공을 가리킴**(`re.findall(r'rule \d+')` = `['rule 4','rule 9','rule 4']`) |
| **V3** | `TASK-116` | 소리 줄의 *"put `{sound}` in target_sound both times"* → **조건부** (코칭한 소리가 계획의 그 소리일 때만 그 키) | 코칭한 소리와 기록된 소리가 어긋남(`runs/2026-09-12-task114-mild-band-dedicated.md` §2.5 · `pq05` 1회) |

⛔ **한 회차에 변수 셋을 함께 바꾼다는 것을 명시함.** 결과가 갈리면 **어느 변수가 그것을 냈는지
이 회차는 가르지 못함.** 그래도 함께 바꾸는 이유는 위 「왜 한 묶음인가」이고, 그 대가를 여기 적어
둠으로써 뒷 세션이 이 회차의 수치를 **변수 하나의 효과로 오독하지 않게 함.**

### ⛔ 건드리지 않는 것 하나 — 그리고 그 이유

소리 줄의 *"instead of the Grammar first rule 9"* 는 **그대로 둠.** 전용 모드에서 규칙 9 는
존재하지만 **문면이 다름**(유보를 걷은 판이라 `Grammar first` 가 없음) — 즉 이 구절도 전용 모드에서는
어긋남. 그런데 그 문구는 `TASK-75`(사용자 승인 2026-09-10)가 정한 **대체 선언**이고
`test_nova.py::test_the_sound_line_replaces_grammar_first_and_spends_the_one_correction` 이
`"instead of the Grammar first rule" in sound_line` 으로 **고정하고 있음.** 고치는 것은 승인된 결정을
되돌리는 일이라 이 회차의 범위 밖임 → **별 태스크로 등록함.**

### ⛔ 변경하지 않기로 한 갈래 하나 — 제품 요구사항 판단이라 내가 정하지 않음

`TASK-116` AC#3 이 고칠 자리로 **두 갈래**를 적었음. 이 회차는 **②(키 규칙을 조건부로)만** 함.
①(전용 세션은 「위에 이름 붙인 그 소리만 코칭하라」로 좁힘)은 **코치가 무엇을 코칭하는지를 바꾸는 것**
이라 제품 요구사항 변경임 — 사용자 판단 사안이므로 넣지 않고 보고에 올림. ②는 기록이 발화와
어긋나는 **결함의 수정**이라 그 승인을 기다리지 않음. ⛔ **②가 ①을 막지 않음** — ①을 나중에 얹을 수 있음.

### 스택 — 공유 자원을 건드리지 않음

`TASK-114` 가 만든 길을 그대로 씀(`ws_session.py --mode pronunciation --wav --url`). 앱 경로인 이유는
결정 50 이 *"스파이크만으로 닫지 않는다"* 를 명시했고 전용 모드가 이미 제품에 있음(`?mode=pronunciation`).

| 무엇 | 값 |
|---|---|
| DB | 검증 전용 `ohmyenglish_t111` (`createdb -O ohmy` + `migrate.py`) · 발음 패턴 **1행만** |
| 백엔드 | `:8012` · `VOICE_ADAPTER=nova` · `WORKER_ENABLED=false` |
| 소리 심기 | `error_patterns.category='pronunciation_intonation'`(⛔ `pronunciation` 이 아님 — `H-BH`) |

⚠️ **소리는 팔마다 다시 심음** — 행이 여럿이면 `load_known_sounds` 가 `order by target_form` 으로
알파벳 첫 항목을 뽑음. 그래서 행을 **하나만** 두고 갈아 심음.

### ⚠️ 픽스처의 오류와 「오늘의 소리」가 맞는지 **먼저** 확인함 (착수 전 필수 ③)

정본은 `tests/harness/scenarios-PQ-qwen-phoneme.md` 임.

| 오디오 | 문장 | 의도한 오류 | 심는 소리 | 맞는가 |
|---|---|---|---|---|
| `pq06`→`pq12` | `I sink sree sings are ready for the demo.` | /θ/→/s/ ×3 | `th_as_s` | **맞음** |
| `pq05`→`pq05a` | `It is eaji to understand the new process.` | /z/→/dʒ/ (`easy`) | `z_as_j` | **맞음** |

네 파일이 `tests/harness/fixtures/voice/` 에 실재함을 확인함(`pq05.wav`·`pq05a.wav`·`pq06.wav`·`pq12.wav`).

### 팔과 상한

| 팔 | 오디오 짝 | 심는 소리 | 회차 | 재는 것 |
|---|---|---|--:|---|
| **REG**(회귀) | `pq06`→`pq12` | `th_as_s` | **4** | 고친 문면이 **4/4 를 유지하는가** |
| **KEY**(어긋남) | `pq05`→`pq05a` | `z_as_j` | **3** | **코칭한 소리와 `target_sound` 가 맞는가** |

**Nova 세션 상한 7회.** ⛔ 중간에 늘리지 않음. (오늘 누적: 앞 세션 133 + 7 = **140**)

⚠️ **대조군이 «역사적»이라는 한계를 먼저 적음.** REG 의 기준선 4/4 는 이 회차가 아니라
`runs/2026-09-12-task114-mild-band-dedicated.md` §1(MILD 팔)에서 나온 값임 — 같은 앱 경로 · 같은
오디오 짝 · 같은 심은 소리 · 같은 날이지만 **동시 대조가 아님.** 동시 대조군을 두면 상한이 11 로
늘어남. ⛔ 그래서 「환경이 그 사이 바뀌었다면 갈리지 않는다」를 판정문에 함께 적어야 함.

### ⛔ 해석 규칙 — 판정선을 **먼저** 정함

| 결과 | 읽는 법 |
|---|---|
| REG **4/4** 코칭 | 고친 문면이 **열등하지 않음.** ⛔ 다만 표본 4 로 **동등을 증명하지 않음** — `P(0 in 4 \| 0.1)=0.66` 이라 10% 열화는 배제되지 않음 |
| REG **3/4 이하** | ⛔ **되돌림.** 판정선을 먼저 정했으므로 표본 4 로 갈리지 않는다는 사실이 이 결정을 뒤집지 않음. 「읽기 좋아졌다」로 유지하지 않음 |
| KEY 에서 코칭한 소리와 `target_sound` 가 **맞음** | 조건부 키 규칙이 작동함. ⛔ 표본 3 이라 **비율이 아니라 방향**임 |
| KEY 에서 다시 **어긋남** | 지시문으로 막지 못함 → 다음 물음은 「기록 경로(코드)로 옮기는가」이고 그것은 `TASK-97` 축과 합침 |
| KEY 에서 코치가 **계획의 그 소리를 코칭** | ⛔ 어긋남 조건이 재현되지 않은 것이라 **조건부 규칙을 시험하지 못함.** 「고쳤다」로 읽지 않음 |
| 세션이 `session_failed` | 환경 고장이므로 판정하지 않음 |

⚠️ **코칭 발생과 tool 도착을 갈라 셈.** 되말하기는 코칭이 아님(결정 51).
⚠️ **발화로 지목한 소리를 원문으로 인용해 적음** — `target_sound` 값만 보면 어긋남이 보이지 않음
(그것이 `TASK-116` 이 태어난 자리임).
⛔ **표본 1~8 의 0 을 「안 된다」로 읽지 않음**(착수 전 필수 ③-2).

### 게이트 — 이 회차가 깨뜨릴 것을 미리 적음

| 게이트 | 예상 | 처리 |
|---|---|---|
| `test_the_pronunciation_prompt_is_byte_identical_to_the_measured_one` | **깨짐** | 이 회차의 새 프롬프트 파일을 이 디렉터리에 남기고 그 경로로 갱신 |
| `test_the_sound_line_replaces_grammar_first_and_spends_the_one_correction` | 통과 예상 | 단정이 `"spend the one correction"` 까지라 V2 가 그 앞뒤만 바꿈 |
| `test_the_sound_line_keeps_rule_10_alive` | 통과 예상 | 단정이 `"Rule 10 still applies unchanged"` · `"twice"` |
| `test_the_two_prompts_carry_the_same_tool_contract_word_for_word` | 통과 예상 | 규칙 8·10 을 건드리지 않음 |

⛔ **바이트 게이트를 「회차를 돌리기 전에」 갱신하지 않음** — 먼저 갱신하면 그 게이트가 지키려는 것
(문면이 그 수치에 묶여 있다는 사실)이 사라짐. 순서는 **문면 수정 → 회차 → 판정 → 게이트 갱신**임.

---

### 산출물 — 이 디렉터리에 넷

| 파일 | 무엇 |
|---|---|
| `run_reg.sh` | REG 팔 실행체(4회) |
| `run_key.sh` | KEY 팔 실행체(3회) |
| `prompt_dedicated_v2.txt` | **바이트 게이트가 가리키는 정본**(1,927자 · `test_nova.py` 가 대조) |
| `extract.py.txt` | 프레임에서 코칭 발화·tool 이벤트만 뽑는 추출기 |

⚠️ **추출기를 `.py.txt` 로 보관하는 것이 이 리포 관례임**(앞 회차 여덟이 그렇게 했음 —
`build_dedicated_prompt.py.txt` 꼴). `.py` 로 두면 게이트 밖 `ruff` 가 그 파일을 집어 lint 부채가
늘어남(직접 확인: `EXE001` 1건 + 포맷 1건. 게이트 밖 `tests` 트리의 기존 baseline 은 **148건**이므로
내가 더한 것이 그 안에 묻힘 — 그래서 관례를 따랐음).
⚠️ **추출기는 값을 만들지 않고 프레임 키를 그대로 옮김** — 앞 세션이 이 자리에서 정규식으로
`target_sound` 열을 틀리게 적은 정정이 있었음.

## 1. 결과 — **REG 는 유지됐고, KEY 는 「시험하지 못했음」**

상한(§0) **7세션을 정확히 썼음**(REG 4 + KEY 3). **죽은 회차 0** — 일곱 다 `session_started` →
`session_ended` 로 끝났고 `session_failed` 0건임.

⚠️ **문면이 길어졌음**: 전용 프롬프트 **1,702자 → 1,927자**(+225 · +13%). 직접 잼
(`len(build_pronunciation_prompt('th_as_s'))`). 규모가 지렛대가 아니라는 것은
`runs/2026-09-11-task86-length-boundary.md` 가 이미 정했지만, **이 회차의 수치는 1,927자 판의
수치**라는 것을 적어 둠. 저장한 문면: `prompt_dedicated_v2.txt`.
번호 참조는 `re.findall(r'rule \d+')` = `['rule 9']` 하나만 남음(§0 이 일부러 남긴 것).

### REG 팔 — `pq06`→`pq12` · 심은 소리 `th_as_s` · 4회

| 세션 | 코칭(소리를 이름으로 지목) | `pronunciation` 이벤트 | 발화 원문(발췌) |
|---|:--:|--:|---|
| REG1 | **○** | 2 | *the "th" sound in "think."* → 재발화 뒤 *Great job! Your "th" sound in "think" was clear* |
| REG2 | **○** | 2 | *a small pronunciation issue with the word "things."* |
| REG3 | **○** | 1 | *the word "things."* → *could you focus on the "th" sound in "things"?* |
| REG4 | **○** | 1 | 위와 같음 |

**코칭 4/4.** 기준선(`runs/2026-09-12-task114-mild-band-dedicated.md` §1 MILD 팔)이 **4/4** 였고
같은 값임 ⇒ **§0 의 판정선을 통과했고 되돌리지 않음.**

⛔ **같지 않은 것 하나를 숨기지 않음**: `pronunciation` 이벤트가 기준선은 **세션마다 2건**(합 8)인데
이 회차는 **2·2·1·1**(합 6)임. 기전으로 **보이는** 것은 둘째 오디오(`pq12` · 정답판)의 전사문임 —
네 세션 전부 `i think sri, sings are ready for the demo.` 로 **오류판과 같은 문면**이 나왔고, 그래서
REG3·REG4 의 코치가 판정 대신 **다시 요청**했음(둘째 tool 호출이 안 남). 기준선에서는 그 자리가
`i think three things are ready for the demo.` 였음. ⛔ **그것을 문면 변경의 결과로 단정하지 않음** —
`TASK-114` §2 가 이미 「전사문이 팔에 따라 달랐다」를 관측하고 **단정을 보류했음.** 표본 4 로는
ASR 변동과 문면 효과를 가르지 못함.

**기록**(검증 전용 `ohmyenglish_t111`):

| 무엇 | 값 |
|---|---|
| `pronunciation_attempts` | **4행** · 세션 **4개**(세션당 1행) · `target_sound` 전부 **`th_as_s`** · `signal_source` 전부 **`nova_tool`** |
| `outcome` | `correct` 1 · `incorrect` 3 |
| `pattern_id` 연결 | **3/4**(`incorrect` 인 셋) |
| `error_patterns` | `th_as_s` · `frequency` **3** · `next_review_at` **`2026-09-13 08:59:22+09`** ⇒ **복습 시계가 섰음** |

### KEY 팔 — `pq05`→`pq05a` · 심은 소리 `z_as_j` · 3회

| 세션 | 코치가 지목한 소리(발화 원문) | 기록된 `target_sound` |
|---|---|---|
| KEY1 | *the "s" sound in "process." It should sound like a "z" sound, similar to the "s" in "easy."* | **`z_as_j`** |
| KEY2 | *a small pronunciation detail in the word "process."* | **`z_as_j`** |
| KEY3 | *the "s" sound in "process." … more like a "z" when it appears between vowels … "pro-SEESS."* | **`z_as_j`** |

**기록**: `pronunciation_attempts` **3행** · 세션 3개 · `target_sound` **`z_as_j` ×3** ·
`signal_source` 전부 `nova_tool` · `outcome` `incorrect` 2 · `correct` 1 · 연결 2/3 ·
`error_patterns.z_as_j` `frequency` **2** · `next_review_at` **`2026-09-13 09:05:11+09`**.

⚠️ **첫 오디오의 전사문이 세 번 다 `it is easy to understand the new process.` 였음** — ASR 이 의도한
오철자(`eaji`)를 **`easy` 로 복원했음.** `pq*` 정본 §5 의 주의와 같은 모양임.

## 2. 판정

| 물음 | 답 |
|---|---|
| 자기완결로 고친 문면이 코칭을 유지하는가(`TASK-111`) | **유지함** — REG **4/4**, 기준선과 같음 |
| 표본 4 가 동등을 증명하는가 | ⛔ **아님** — `P(0 in 4 \| 0.1)=0.66`. 말할 수 있는 것은 **「판정선을 넘었다」** 까지임 |
| 조건부 키 규칙이 어긋남을 막는가(`TASK-116`) | ⛔ **이 회차는 그것을 시험하지 못했음** — 아래 |
| 복습 시계가 도는가 | **돎** — 두 팔 다 `next_review_at` 이 섰고 `signal_source` 가 `nova_tool` 임(결정 59 의 필터 통과) |

### ⛔ KEY 팔을 §0 의 어느 행으로도 읽지 않았음 — 그 이유를 적음

§0 이 미리 적은 행은 「맞음」·「다시 어긋남」·「계획의 그 소리를 코칭(시험 못 함)」 셋이었음.
관측된 것은 **그 셋 어디에도 정확히 들어가지 않는 넷째 모양**임:

- 코치는 **다른 낱말**(`process`)을 골랐음 ⇒ 「계획의 그 소리를 코칭」이 아님.
- 그런데 코치가 그 소리를 설명한 말이 *"should sound like a `z`"* · *"similar to the `s` in `easy`"*
  임 ⇒ **코치 자신이 그것을 /z/ 로 부르고 심은 낱말(`easy`)까지 지목했음.** 그러면 기록된 `z_as_j` 는
  **코치가 코칭했다고 «스스로 여기는» 소리와 어긋나지 않음.**

⇒ **조건부 규칙의 조건절(「코칭한 소리가 다르면」)이 발동했는지 자체를 이 관측으로 가를 수 없음.**
⛔ **미리 적은 행에 억지로 끼워 넣지 않음** — 그렇게 하면 §0 을 먼저 적은 이유(사후 재해석 금지)가
사라짐. 그래서 **「막았다」도 「막지 못했다」도 적지 않음.**

### ⛔ 그리고 픽스처를 의심함 — `pq05` 는 이 축을 재는 데 쓸 수 없음

`pq05` 문장은 `It is eaji to understand the new process.` 이고 **의도한 소리(/z/ in `easy`)와 코치가
고른 자리(`process` 의 어말 `s`)가 같은 /s/~/z/ 축**임. 게다가 ASR 이 `eaji` 를 `easy` 로 복원해
전사문에 오류가 남지 않음. ⇒ **「코칭한 소리가 계획의 소리와 «다른 소리»인 경우」를 이 픽스처는
만들지 못함.** `TASK-115` 가 `pq04` 를 같은 이유(문장이 다른 변수를 들여옴)로 대체한 것과 같은 부류임.

다음 회차가 필요한 것은 **의도한 소리와 눈에 띄는 대안이 «다른 소리»인 픽스처**임 — 별 태스크로 등록함.

⛔ **상한을 지금 늘리지 않음** — 7/7 을 썼고 §0 이 *"중간에 늘리지 않는다"* 를 적었음.

### 남긴 변경과 그 근거

| 변수 | 남김/되돌림 | 근거 |
|---|---|---|
| **V1**(규칙 11 자기완결) | **남김** | REG 4/4 로 판정선 통과. 번호 참조가 사라져 전용 프롬프트가 자기완결에 가까워짐 |
| **V2**(소리 줄의 `of rule 4`) | **남김** | 같음. 단정 `"spend the one correction"` 이 그대로 통과함 |
| **V3**(조건부 키 규칙) | **남김 — 다만 「시험되지 않음」으로 적음** | 되돌릴 근거가 없음(REG 가 나빠지지 않았음). ⛔ **효과가 확인된 것으로 인용하지 않음** — 다음 회차가 갈라야 함 |

⚠️ **대조군이 역사적이라는 §0 의 한계가 그대로 남음** — REG 기준선 4/4 는 같은 날 같은 스택의
`TASK-114` MILD 팔이고 **동시 대조가 아님.** 환경이 그 사이 바뀌었다면 이 대조는 갈리지 않음.

## 3. 스택 정리 — 공유 자원 무변경 대조

| 무엇 | 값 |
|---|---|
| 검증 전용 DB | `ohmyenglish_t111`(REG) · `ohmyenglish_t111k`(KEY) — 둘 다 `dropdb` |
| 백엔드 | `:8012`(REG) · `:8013`(KEY) — 둘 다 종료 |
| 공유 dev DB 기준값(회차 **전**) | `learning_sessions=17` · `pronunciation_attempts=7` · `error_patterns=9` · `session_plans=6` · `learner_notes=7` |
| 공유 dev DB 대조(회차 **뒤**) | `learning_sessions=17` · `pronunciation_attempts=7` · `error_patterns=9` · `session_plans=6` · `learner_notes=7` ⇒ **다섯 표 전부 같음. 내가 남긴 변경 0건** |

### 3-1. 정리를 «주장하지 않고» 출력으로 확인함

| 확인 | 출력 |
|---|---|
| `:8012`·`:8013` 종료 | 두 포트 `curl` **`000`**(하네스도 배경 작업 종료를 `exit 143`=SIGTERM 으로 보고함) |
| DB 삭제 | `dropdb ohmyenglish_t111` **exit 0** · `dropdb ohmyenglish_t111k` **exit 0** · `psql -l` 에 남은 `ohmyenglish_t111*` **0개** |
| 공유 DB 무변경 | 위 표 — 회차 **전** 값을 먼저 받아 두고 **뒤**에 다시 읽어 대조함 |

⚠️ **DB 를 둘 쓴 이유**: 심은 소리를 갈아 끼우려면 `error_patterns` 행이 **하나**여야 하는데
(`load_known_sounds` 가 `order by target_form` 으로 첫 항목을 뽑음 — `th_as_s` < `z_as_j`), REG 팔의
행에는 이미 `pronunciation_attempts` 가 연결돼 있어 지울 수 없었음. ⇒ KEY 팔을 **별 DB · 별 포트**로
돌려 **REG 증거를 보존**했음.

⚠️ **`ws_session.py --no-register` 를 썼음** — 그 표(`harness_sessions`)가 검증 전용 DB 에 없음.
⛔ 붙이지 않으면 `psql_cli` 가 `DATABASE_URL` 을 따라가 **공유 dev DB 에** 하네스 세션을 남김.

