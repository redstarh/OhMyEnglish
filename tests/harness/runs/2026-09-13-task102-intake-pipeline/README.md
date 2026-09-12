# 회차 — 무대 정하기 진입을 앱 경로에서 종단으로 쟀다 (`TASK-102.1` AC#1·#2·#3)

세션 `ohmyenglish-f4` · 2026-09-13 · 기준 커밋 `b7ada24` 위에서 시작해 이어 돌렸다.

> **세 팔로 나뉜다 — 절이 늘어난 순서가 그대로 관측이 늘어난 순서다.**
> §1~§3 **스텁**: 배선·파이프라인·배치(사람 없이 돌린다) · §4 그 팔이 드러낸 결함 후보 ·
> §4-2 **실물 Nova 1회차**: 문면의 유도력 절반 · §4-3 **실물 Nova 2회차**: 나머지 절반.
>
> ⛔ **실물 팔은 사용자 승인 사안이고 각각 승인을 받았다**(결정 85 · 그 뒤 1회 추가 승인).
> ⛔ **스텁 팔은 「다섯을 하나씩 묻는가」를 재지 못한다** — 그것이 §4-2·§4-3 이 따로 있는 이유다.

## §0. 돌리기 전에 적은 조건

**통과 조건 넷** — 하나라도 틀리면 이 기능은 「질문은 했는데 무대가 안 생긴다」가 된다.

1. `?mode=scenario_intake` 로 붙으면 세션이 열린다.
2. 세션 행의 `mode` 가 그 값으로 **적힌다**(종료 경로가 그 값을 읽는다).
3. 종료 뒤 `analysis_jobs` 에 `generate_scenario` 가 걸린다.
4. 워커가 그 job 을 **`process_analysis` 가 아니라 `process_scenario`** 로 보내고, 정상 응답이면
   `learning_scenarios` 에 `source='generated'` 행 하나가 생긴다.

⛔ **공유 dev DB·`:8002` 를 쓰지 않았다**(`H-BC`). 검증 전용 DB `ohmyenglish_v102`(소유자 `ohmy`)와
포트 `:8022` 를 세우고 `VOICE_ADAPTER=stub` · `WORKER_ENABLED=false` 로 띄웠다(`H-AT`).
⚠️ **DB 소유자를 `ohmy` 로 두는 것이 조건이다** — `redstar` 로 만들면 `permission denied for schema
public` 로 마이그레이션이 죽는다(직접 밟았다). 준비 뒤 `schema_migrations` **17건** · 시드 **30행**
(`display_order` 1–30).

## §1. 앱 경로 구간 — 조건 1·2·3 이 참이다

실행체는 이 디렉터리의 `intake_stub_leg.py` 다(`--url`·`--dsn` 필수 · 기본값 없음).

| 세션 | 프레임 | 세션 행 `mode` | 걸린 job |
|---|---|---|---|
| `4fb80337` | `session_started → final·partial·audio … → session_ended` | **`scenario_intake`** | `generate_scenario` · `plan_next_session` 둘 다 `pending` |
| `117b5f72` | 같음 | **`scenario_intake`** | 같음 |

⚠️ **`plan_next_session` 이 «함께» 걸리는 것이 설계다** — 무대 정하기 세션에도 학습 발화가 있으므로
다음 계획의 근거가 된다(`sessions.end_session` 주석이 그 근거를 갖는다).

## §2. 워커 구간 — 거부와 성공을 **같은 회차에서** 쟀다

⛔ **`p5_worker_leg.py` 에 `generate_scenario` 분기를 더해야 돌았다.** 더하기 전에는 그 job 이
마지막 `else` 로 떨어져 `process_analysis` 로 갔다 — 그 함수는 종류가 다르면 실패로 보고하므로
**5회 재시도 뒤 영원히 `failed`** 가 된다. 그래서 그 파일의 분기를 **종류마다 지목**하도록 바꾸고
모르는 종류는 `exit 5` 로 거부하게 했다(새 종류가 조용히 그리로 가는 것을 막는다).

**Claude 는 실물이다**(`BedrockClaudeClient`). 두 팔의 입력만 다르다.

| 팔 | 입력 전사문 | 결과 |
|---|---|---|
| 거부 | 스텁 픽스처 대화(무대 정하기 문답이 아니다) | `status=pending` · `attempts=1` · `last_error` = `ScenarioValidationError: category 가 값역 밖이거나 비었다: None (허용: ['business','daily_life','health','shopping','travel'])` · **생성 0행** |
| 성공 | 질문 다섯의 문답 10줄을 심었다(회의 보고 상황) | `status=done` · `attempts=1` · **생성 1행** |

⛔ **거부 팔이 판별력이다** — 성공만 재면 「무엇을 넣어도 행을 만드는 파서」와 구별되지 않는다.
⚠️ 허용 목록에 **`shadowing` 이 없는 것**이 함께 관측됐다 — 값역을 CHECK 에서 파싱하지 않고
「시드에 실재하는 계열」로 읽기 때문이고(그 파일 주석이 근거를 갖는다) 그 설계가 실제로 동작했다.

**생성된 행**:

| 열 | 값 |
|---|---|
| `category` | `business` (모델이 골랐다 — 회의·사무실 무대에 맞다) |
| `level` | `A2` — ⛔ **모델이 준 값이 아니라 `users.current_level` 이다**(호출자가 붙인다) |
| `source` | `generated` |
| `display_order` | `0` (019 의 기본값 — 시드 자리가 없는 행) |
| `title` | `주간 팀 회의에서 매니저와 동료들에게 프로젝트 진행 상황 보고하기` |
| `prompt_template` | `You are the learner's manager in a fairly formal weekly team meeting …` (영어) |

## §3. 배치에 실제로 집히는가 (AC#3) — 무력화로 **가른** 뒤에야 참이다

`_pick_scenario_for_user` 를 그 DB 에 직접 돌렸더니 `pick=new` · `source=generated` 였다.
⛔ **그 관측 하나로는 근거를 가릴 수 없었다** — 생성 행의 `display_order` 가 `0` 이고 시드가
`1..30` 이므로 **「생성이 먼저」와 「자리가 앞」이 같은 답을 낸다.** 그래서 그 행의 `display_order`
를 **99** 로 밀어 다시 돌렸다:

| 조건 | 고른 것 |
|---|---|
| `display_order = 0` | `source=generated` |
| `display_order = 99` (시드 전부보다 뒤) | **`source=generated`** — 여전히 먼저다 |

⇒ 이기는 것은 `_staleness` 의 **맨 앞자리(`is_generated`)** 이고 019 의 기본값 0 이 아니다.
결정 80 이 DB 행으로 확인됐다. 밀었던 값은 되돌렸다(`0`).

## §4. 이 회차가 남기는 결함 후보 하나 — 제목의 언어가 갈린다

**생성된 `title` 은 한국어이고 시드 30행은 전부 영어다.** 원인은 프롬프트가 언어를 지정하지 않는
것이다 — `build_scenario_prompt` 의 그 줄은 *"「title」: 화면에 보일 한 줄 라벨. 한 문장, 물음표
없이."* 이고 **언어에 대해 침묵한다.**
⛔ **게이트가 이것에 침묵한다** — 어느 단정도 제목의 언어를 재지 않는다.
⚠️ **어느 쪽이 옳은지는 제품 판단이다**: 제목은 한국인 학습자가 보는 화면 라벨이므로 한국어가 나을
수 있고, 그렇다면 **시드 30행이 틀린 쪽**이 된다. 섞이는 것만은 확실히 틀렸다 — 학습 현황 목록
(`scenario_progress`)이 두 언어를 한 목록에 낸다. 소유는 `TASK-133` 이다.

## §4-2. 실물 Nova 1회 — 「한 턴에 여러 질문을 묶는가」만 닫혔다 (`TASK-102.1` AC#2 · 결정 85)

사용자 승인(결정 85)을 받고 **실물 Nova 세션 1회**를 돌렸다. 격리는 §0 과 같고 어댑터만
`VOICE_ADAPTER=nova` 다(DB `ohmyenglish_v102b`). 실행체는 기존 `tests/harness/ws_session.py` 이고
`--mode scenario_intake --url … --wav pq11.wav,pq02a.wav` 로 불렀다.
원자료: `SI1-frames.json`(550줄 · `.harness/evidence/` 에서 옮겼다).

**관측한 전사문 전부** (세션 `3b9d70e5`):

| # | 화자 | 말 | 물음표 |
|--:|---|---|--:|
| 1 | user | `i think we need to fix this bug today.` (픽스처 `pq11`) | – |
| 2 | **agent** | `I see you want to talk about work. Let us start with your English needs.` | **0** |
| 3 | user | `i need to send the final report today.` (픽스처 `pq02a`) | – |
| 4 | **agent** | `Good. Where do you need English soon?  Tell me the place.` | **1** |

**닫힌 것 하나**: ⛔ **코치가 한 턴에 여러 질문을 묶지 않았다 — 2 턴 중 0 턴.** 그리고 4번 턴이
질문 1(무대)을 **프롬프트 문면 그대로** 냈다. 그것이 이 축의 가장 큰 위험이었다(한 번에 다 물으면
학습자가 한 문장으로 답해 다섯 축이 섞인다).

⛔ **닫히지 않은 것 둘 — 「1회로 쟀다」를 「다 쟀다」로 쓰지 않는다.**

1. **다섯을 «끝까지» 순서대로 묻는가** — 코치 턴이 **둘**뿐이었다. 픽스처 WAV 가 둘이라 거기서
   세션이 끝났다. 질문 2~5 의 순서와 단독성은 **관측되지 않았다.**
2. **답을 못 받은 축을 지어내는가** — 그 상황이 생기지 않았다(학습자가 「모르겠다」를 말한 적이 없다).

⚠️ **관측 조건의 한계를 함께 적는다.** ⑴ 픽스처가 발음 회차용 문장이라 **질문의 답이 아니었다** —
그래서 2번 턴이 질문 없이 방향을 잡는 데 쓰였고, 그것은 지시문의 결함이 아니라 입력의 성질이다.
⑵ **코치가 먼저 말하지 않았다** — 하네스가 곧바로 오디오를 흘리므로 「학습자 오디오 없는 첫 턴」
팔은 이 회차에서 지나가지 않았다. 그 팔을 재려면 오디오를 늦게 보내는 실행체가 필요하다.
⛔ **1회 관측을 비율로 읽지 않는다**(결정 39 가 박은 못).

⚠️ **첫 시도가 세션을 하나 더 만들고 죽었다** — `ws_session.py` 가 `harness_sessions` 표를 요구하는데
검증 DB 에 그 표가 없었다(하네스 전용 표이고 마이그레이션에 없다). 오디오를 보내기 전에 죽었으므로
**관측은 0이고 Nova 스트림도 열리지 않았다.** 그 뒤 `harness_runs`·`harness_sessions` 를 그 DB 에
만들고 다시 돌렸다. ⇒ **실물 스트림이 실제로 돈 것은 1회다.**

## §4-3. 실물 Nova 2회차 — 나머지 절반이 닫혔다 (`TASK-102.1` AC#2 완료)

사용자가 **1회를 더 승인**했다(§4-2 의 미산 둘 때문이다). 격리는 같고 DB 는 `ohmyenglish_v102c` 다.

⛔ **1회차의 미산 원인이 입력이었으므로 «답» 픽스처를 만들었다** — `tests/harness/gen_si_fixtures.sh`
(`si00`~`si05` · 목소리·포맷을 `gen_pq_fixtures.sh` 와 같게 뒀다).
⚠️ **`si00` 은 답이 아니라 여는 인사(`Hello.`)다.** 1회차에서 **Nova 가 오디오 전에 말하지 않는 것**을
관측했고, 그러면 학습자가 먼저 한마디 하는 것이 **제품의 실제 경로**다 — 그래서 「코치가 먼저 말하는가」
를 요구로 세우지 않고 그 자리를 픽스처로 채웠다. ⛔ 관측을 요구로 바꾸지 않는다.
⚠️ **`si04 = I don't know.` 가 「지어내는가」를 재는 유일한 입력이다** — 그 입력이 없으면 그 축은
시험 자체가 성립하지 않는다.
⚠️ `ws_session.py` 는 **`--no-register`** 로 불렀다(검증 DB 에 하네스 표가 없다) — §4-2 에서 그 표를
손으로 만든 것은 **불필요했다**(발음 축이 그 플래그를 알려 주고 내가 `:189` 에서 직접 확인했다).

**코치 턴 전부** (세션 `81bd6df2` · 원자료 `SI2-frames.json` 1268줄):

| 코치 턴 | 말 | 축 |
|--:|---|---|
| #4 | `That is good to know.` / `Where do you need English soon?` | 1 무대 |
| #6 | `Thanks.` / `Who will you talk to there?  A colleague?` | 2 상대 |
| #8 | `I understand.` / `What do you want to get done in that talk?` | 3 목표 |
| #10 | `That is fine.` / `What part feels hardest for you there?` | 4 초점 |
| #12 | `Okay, I hear you.` / `Is it a formal talk or a relaxed one?` | 5 어조 |

⛔ **다섯을 «설계서 §3 의 순서 그대로» 턴마다 하나씩 물었다 — 5/5.** 묶은 턴 0건이다.
⚠️ **물음표 개수를 질문 개수로 읽지 않는다.** #6 은 물음표가 **2개**인데 축은 **하나**다 — 두 번째
물음표는 블록 문면이 예시로 담은 `A colleague?` 다(`A stranger?` 는 빠졌다). 즉 이 축의 단정은
「물음표 1개」가 아니라 **「축 하나」**여야 한다.
⚠️ **학습자 발화와 질문이 한 칸 어긋났다** — 하네스가 정해진 순서로 오디오를 흘리므로 코치가 묻기
**전에** 그 답이 들어왔다. ⛔ 그것이 이 축의 판정을 흔들지는 않는다: 코치는 **무엇이 오든** Q1→Q5 를
순서대로 하나씩 밟았다. ⚠️ 다만 「답을 듣고 다음으로 넘어간다」는 **재지 못했다** — 그것을 재려면
응답형 실행체가 필요하고 이 회차의 요구가 아니다.

**「지어내는가」 — 지어내지 않았다.** 전사문 어디에도 **초점(무엇이 가장 어려운가)** 의 답이 없다
(`si04` 가 `I don't know.` 였고 나머지는 다른 축의 답이었다). 그 전사문으로 만든 무대:

| 열 | 값 |
|---|---|
| `title` | `Reporting your project status in the weekly team meeting` |
| `prompt_template` | `You are the learner's manager, joined by two colleagues, in a formal weekly team meeting where the learner gives a project status update. Listen to the report and respond as a manager would, asking for clarification on progress and next steps.` |

⇒ 담긴 축은 **무대·상대·목표·어조 넷**이고 **초점은 없다.** 어려움을 지어낸 구절이 0건이다.
⛔ **이것이 판별력을 갖는 이유**: 지어냈다면 「질문이 불분명할 때 얼어붙는다」 같은 구절이 나타난다.
⚠️ 코치가 #10 에서 `That is fine.` 을 낸 것은 지시문 문면 그대로다(*"say that is fine and move to the
next question"*). ⛔ 다만 **「다음으로 넘어갔다」는 그것만으로 증거가 아니다** — 코치는 어차피 순서를
밟으므로 그 관측은 두 기전을 가리지 못한다. 지어냄의 증거는 **무대에 초점이 없다는 것** 하나다.

📌 **결정 84(제목은 영어)가 실물에서 확인됐다** — 프롬프트를 고친 뒤 만든 첫 무대의 제목이 영어다.
§4 의 한국어 제목과 같은 경로·같은 모델이고 **바뀐 것은 프롬프트 한 줄**이다.

## §5. 정리

⚠️ **`p5-guard*.json` 스냅샷 둘은 되돌릴 대상이 없다** — 검증 DB 를 지웠기 때문이다. `guard` 를
그래도 돌린 이유는 **`claim` 이 같은 단정을 요구**하기 때문이고(그 실행체의 설계), 보존 세션 보호는
공유 dev DB 에서만 뜻을 갖는다. 파일은 회차 기록으로 남긴다.

**teardown**: 회차마다 `:8022` 백엔드를 죽이고 검증 DB(`ohmyenglish_v102`·`_v102b`·`_v102c`) 를 drop 했다. ⛔ **공유 dev DB 와 `:8002` 는
이 회차에서 한 번도 건드리지 않았다** — dev DB 의 `learning_scenarios` 는 여전히 시드 30행이다.
