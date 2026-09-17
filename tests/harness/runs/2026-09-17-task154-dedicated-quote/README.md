# 회차 — 「소리를 따옴표로 따로 인용하라」를 실물로 재고 **되돌렸음** (`TASK-154` · 결정 124 반증)

2026-09-17 KST · 브랜치 `design/first-vertical-slice` · 기준 커밋 `3405cbc`
Nova 실물 세션 **7회**(ARM-A 4 + ARM-C 3) · 공유 dev DB·`:8002` 를 건드리지 않았음

> **왜 이 회차인가**: 사용자 결정 124(2026-09-17)가 `TASK-116.5` 의 구멍을 프롬프트 쪽에서 닫으라고
> 정했다. 일반 세션(`SYSTEM_PROMPT`)에는 그 자리에서 넣었고, 전용 모드
> (`PRONUNCIATION_MODE_PROMPT`)는 문면이 실측 산출물에 **바이트로 묶여** 있어
> (`test_the_pronunciation_prompt_is_byte_identical_to_the_measured_one`) 실물 회차가 필요했다.
> 그 게이트가 정한 순서가 **문면 수정 → 회차 → 판정 → 게이트 갱신**이고 이 회차가 그 두 번째다.
>
> ⛔ **결론이 뒤집혔다: 게이트를 갱신하지 않고 «문면을 되돌렸다».** 회차가 그 요구를 반증했다.

---

## 0. 상한과 판정 규칙 — 돌리기 전에 적었다

* **ARM-A 4회**(새 문면) — 기준선은 `TASK-128.3` ARM-A **4/4**(같은 픽스처·같은 후보)다.
* **ARM-C 3회**(앞 문면 · **같은 날**) — 이 팔은 회차 중간에 **더한 것이고 그 이유를 적는다**:
  ARM-A 의 결과가 기준선과 달랐을 때 「문면이 바꿨나 모델이 바뀌었나」를 가를 수단이 없었다.
  두 회차 사이가 **5일**이므로 그 차이를 문면에 돌리는 것이 근거가 없다. ⇒ 같은 날 앞 문면을
  돌리는 것이 그것을 가르는 유일한 측정이다.
  ⚠️ **상한을 늘린 것이므로 그 사실을 여기 적는다** — 처음 계획은 4회였고 실제로 7회를 썼다.
* **Nova 세션 상한 7회.** 실제 사용 7회(죽은 회차 0 — 일곱 다 `session_started`→`session_ended`).
* **판정선**: ① tool 이 오는가(회귀) ② 코치가 **어느 소리**를 집는가 ③ `sound_check` 가 무엇이 되는가.
  ⛔ **②를 판정선에 넣은 것이 이 회차의 값이다** — ①만 보면 「4/4 로 왔으니 통과」가 된다.

## 1. 스택 — 공유 자원을 건드리지 않았다

| 무엇 | 값 |
|---|---|
| 검증 DB | `ohmyenglish_t154` — 새로 만들어 마이그레이션 **24** 적용 · 표는 `ohmyenglish` 스키마 **17개** |
| 심은 후보 | `pronunciation_th_as_s`(`category=pronunciation_intonation`) **1행** — 제품 writer 경로(`p8_inject_pronunciation.py inject`) |
| 백엔드 | `:8014` · `VOICE_ADAPTER=nova` · `WORKER_ENABLED=false` · `DATABASE_URL=…_t154` (`ps -Eww` 로 확인) |
| 하네스 | `ws_session.py --mode pronunciation --wav pq06.wav,pq12.wav --no-register` |
| 공유 자원 | 공유 dev DB · `:8002`(pid 19296) 를 **건드리지 않았음** — §4 에서 다시 읽어 대조했음 |

**후보 목록이 실제로 1건임을 확인했다**: `load_known_sounds` 가 `['th_as_s']` 를 돌려줬다.
그것이 기준선 회차의 조건과 같다(후보 1건 판).

**길이 대역** — 전용 모드의 tool 도착은 길이에 민감하다(1,702자 4/4 대 5,078자 0/76 ·
`runs/2026-09-11-task86-length-boundary.md` §4). 그래서 먼저 쟀다:

| 판 | 후보 1건 길이 |
|---|--:|
| v3(ARM-A 4/4) | 1,660자 |
| v4(ARM-A 4/4 · 지금 게이트가 가리키는 판) | 1,825자 |
| v2(REG 4/4) | 1,927자 |
| **v5(이 회차의 새 문면)** | **1,959자** |

⇒ 1,959자는 **4/4 를 낸 세 판과 같은 대역**이다. 즉 이 회차는 길이가 아니라 문면을 잰다.
산출물은 `prompt_dedicated_v5.txt` 로 남긴다 — **되돌렸어도 지우지 않는다**(무엇을 쟀는지의 정본).

## 2. 결과 — 세 팔을 한 표로

바꾼 문면(v5)은 규칙 9 에 두 문장을 더한 것이다:
*"name the sound that was off **and put it in quotes on its own - the "th" sound, the "er"
sound -** then say the whole sentence back … **Quoting only the whole sentence does not name
the sound.**"*

| 팔 | 문면 | 날짜 | 세션 | tool 프레임 | 코치가 집은 소리 | `sound_check` |
|---|---|---|--:|--:|---|---|
| **ARM-B0**(기준선) | v4 | 2026-09-12 | 4 | **2** ×4 | `"th"` **4/4** | `matched` 4/4 |
| **ARM-A**(새 문면) | **v5** | 2026-09-17 | 4 | **1** ×4 | **`"are"`·`"er"` 4/4** | **`mismatched` 4/4** |
| **ARM-C**(짝 대조) | v4 | 2026-09-17 | 3 | **2** ×3 | `"th"` **3/3** | `matched` 3/3 |

**입력이 비교 가능함을 먼저 확인했다** — 세 팔 다 `pq06.wav,pq12.wav` 이고 첫 전사문이 전부
`i think sri, sings are ready for the demo.` 로 같았다. 오디오의 오류는 /θ/→/s/ 다
(`sink sree sings` → ASR 이 `think`·`sri, sings` 로 복원).

**ARM-A 의 코치 발화**(네 세션이 글자 그대로 같았다):
> I noticed a small pronunciation issue with the word "are." You said it in a way that sounds
> a bit like "er" instead of the clear "are" sound.

**ARM-C 의 코치 발화**(3회 중 2회가 같았다):
> Sorry, I didn't catch that clearly. There seems to be a small pronunciation issue with the
> "th" sound.

## 3. 판정 — ⛔ **반증됐다. 문면을 되돌렸다**

깨진 것이 **둘**이고, 둘 다 ①(tool 이 오는가)만 보면 보이지 않는다:

1. ⛔ **코치의 조준이 옮겨졌다.** 오디오의 오류는 /θ/→/s/ 인데 v5 는 **`"are"`** 를 집었다(4/4).
   `are` 는 그 문장에 있는 낱말이고 오류가 아니다. ⇒ **학습자가 틀리지 않은 소리를 연습하게 된다.**
2. ⛔ **tool 호출이 2 → 1 로 줄었다.** 규칙 10 은 두 번 부르라고 요구한다(모델링 직후 `pending` ·
   재발화를 들은 뒤 판정). v5 에서 두 번째 호출이 사라졌다 ⇒ **재발화가 판정되지 않는다.**

⚠️ **`sound_check` 가 `mismatched` 4/4 로 «켜진» 것을 성과로 읽지 않는다.** 그것은 검사가 좋아진 것이
아니라 **코치가 틀린 소리를 코칭했기 때문에** 어긋난 것이다. 즉 검사는 제 일을 했고 그 신호가
가리키는 결함이 이 문면이다.

⛔ **모델 변화가 아니다 — 같은 날 대조가 그것을 배제한다.** ARM-C 는 앞 문면으로 같은 날 3/3 으로
`"th"` 를 집고 tool 이 2회 왔다. 두 회차 사이의 5일을 원인으로 돌릴 수 없다.

⚠️ **기전(가설이고 단정하지 않는다)**: 「인용할 수 있는 형태로 말하라」가 코치를 **인용하기 쉬운
낱말**로 끌어당긴다. 그 요구는 검사의 눈을 뜨게 하려는 것이었는데 실제로는 **코치의 조준을 옮겼다.**

**비용 대비**: 겨냥한 이득은 「문장 인용만 있어 판정 불가인 세션 **2/59**」였고, 치른 대가는
「없는 오류를 연습시킴 + 재발화 판정 상실」이다. ⇒ **이득이 대가를 정당화하지 않는다.**

## 4. 되돌린 것과 남긴 것

**되돌렸다 — 두 프롬프트 모두**:
* `PRONUNCIATION_MODE_PROMPT` 규칙 9 → v4 문면. 바이트 게이트가 **초록**으로 돌아왔다(직접 확인).
* `SYSTEM_PROMPT` 규칙 9 → 앞 문면. ⚠️ **일반 세션은 이 회차가 직접 재지 않았다** — 같은 문면이고
  기전이 같으므로 **안전한 쪽으로 되돌렸다.** 그 판단의 근거를 여기 적는다: 겨냥한 이득이 2/59 이고
  관측된 해가 「틀린 소리를 연습시킴」이라 **비대칭이 크다.** 재려면 일반 세션 회차가 따로 필요하다.

**단정도 뒤집었다** — 「요구가 있는지」를 재던 테스트를 **「요구가 들어오지 못하게」** 막는 테스트로
바꿨다(`test_neither_prompt_asks_the_coach_to_quote_the_sound_on_its_own`). 두 프롬프트를 함께 본다.

**남겼다**:
* `prompt_dedicated_v5.txt` — 무엇을 쟀는지의 정본. 지우면 이 판정의 근거가 사라진다.
* `.harness/evidence/T154A1…A4·T154C1…C3-frames.json` — 일곱 세션의 프레임 원본.
* `inject-a.json` — 후보 1행을 심은 기록.
* 검사 쪽 단정 둘(`test_a_quoted_sound_beside_a_sentence_quote_*`)은 **그대로 유효하다** — 순수 함수의
  거동을 재고 프롬프트에 걸려 있지 않다. 코치가 «스스로» 그 모양으로 말할 때(v4 에서 실제로 그랬다)
  판정이 살아야 한다는 것이 그 단정의 내용이다.

⛔ **겨냥한 구멍은 열린 채로 남는다.** `test_a_whole_sentence_quote_is_still_not_judged` 가 그 사실을
이름으로 갖는다. 검사 쪽 대안은 이득이 **구조적으로 0** 이고(`mismatched` 는 `word_supports_key` 가
거짓일 때만 나오며 그 값은 인용 범위를 넓히면 참이 되기만 한다 — 단조), 프롬프트 쪽은 이 회차가
반증했다. 남은 후보는 **오디오를 듣는 판정**이고 설계서 §6 이 범위 밖으로 두었다.

## 5. 스택 정리 — 출력으로 확인했다 (주장하지 않았다)

| 무엇 | 확인 |
|---|---|
| 백엔드 `:8014` | pid `87701` 을 직접 `kill` · `curl` 상태코드 **`000`**(연결 불가). ⛔ `lsof -ti` 를 쓰지 않았음(`H-BK`) |
| 검증 DB | `drop database ohmyenglish_t154` 성공 · 남은 `ohmyenglish*` 는 `ohmyenglish`·`_smoke`·`_test` **셋뿐** |
| 공유 dev DB | 여덟 표가 통합 회차 뒤 값과 **같음** — `learning_sessions` 17 · `utterances` 128 · `error_patterns` 9 · `review_tasks` 15 · `analysis_jobs` 57 · `pronunciation_attempts` 7 · `harness_runs` 28 · `harness_sessions` 100 |
| 공유 `:8002` | pid **19296** 그대로 · `/health` **200** — 건드리지 않았음 |

⚠️ **`harness_runs` 28 · `harness_sessions` 100 은 이 회차가 만든 것이 아니다** — 앞선 통합 회차
(`TASK-155`)가 각각 +1 했고 그 값이 그대로다. 이 회차는 `--no-register` 로 돌아 그 두 표를 쓰지 않는다.

## 6. 게이트 — 되돌린 뒤 실측

수집 **1286** · `pytest` **1286 passed** · `ruff check` **0** · `ruff format --check` **272 files** ·
`ty check` **0** · `tsc` **0** · `eslint` **0**.
⚠️ `ruff format` 의 파일 수가 271 → 272 로 늘어난 것은 회차 문서 하나가 늘어난 것이다(그 명령이
`runs/**/README.md` 경로까지 훑는다) — 코드가 늘어난 것이 아니다.

⛔ **바이트 게이트가 초록이다** — 즉 지금 트리의 전용 모드 문면이 `prompt_dedicated_v4.txt` 와
**바이트로 같다.** 그것이 「되돌렸다」의 기계 증거다.

## 7. 다음 사람에게 — 이 회차에서 배운 것 둘

1. ⛔ **프롬프트 변경을 「tool 이 오는가」로만 검수하면 이 결함이 통과한다.** ARM-A 는 tool 이 4/4 로
   왔다. 깨진 것은 **코치가 무엇을 코칭하는가**와 **몇 번 보고하는가**였다. ⇒ 프롬프트 회차의 판정선에
   **「무엇을」과 「몇 번」을 함께** 넣는다.
2. ⛔ **앞 회차와 날짜가 다르면 그 차이를 문면에 돌릴 수 없다.** 같은 날 앞 문면을 돌리는 팔이
   **가장 값싼 통제**다(이 회차는 3세션을 더 썼고 그것이 판정을 뒤집었다). 그 팔이 없었으면
   「모델이 바뀐 것 같다」로 잘못 닫았을 것이다.
