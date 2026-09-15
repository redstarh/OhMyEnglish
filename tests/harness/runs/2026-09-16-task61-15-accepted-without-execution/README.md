# 회차 — `TASK-61.15`: 앱이 버린 명령에 코치가 「실행됐다」고 말하는 크기

세션 `ohmyenglish-42` · 2026-09-16 KST · 기준선 커밋 `b93d49f`(코드 변경 0건) ·
절차 정본 `tests/harness/browser_leg.md` · 드라이버 `tests/harness/p_app_path.py`

> 무엇을 재는가: `TASK-61.14` 회차 §3-② 가 **1회** 관측한 것의 크기임(AC#1) — 표지가 없어 앱이
> 명령을 버린 턴에서 코치가 「종료됐다」고 말하는 비율. 그리고 **지시문·내부 추론을 소리로 읽는 것이
> 그 조건에서 나는 것인지**를 가름(AC#2).
>
> ⛔ **조건을 ASR 우연에 기대지 않고 만들었음.** 앞 회차는 영어 표지가 `all my english` 로
> 전사되기를 기다린 것이라 재현이 확률에 걸렸음. 이 회차는 **표지가 애초에 없는 명령 픽스처**를
> 새로 만들어 그 턴을 결정적으로 만듦 — 앱의 게이트(`session.py` 결정 104 D5)는 표지의 유무만
> 보므로 두 경로가 같은 자리로 들어감.

---

## 0. 스택과 상한

| 무엇 | 값 |
|---|---|
| DB | 검증 전용 `ohmyenglish_t6115`(`schema_migrations` **22**) · 계획·리포트를 심지 않음 |
| 백엔드 | `:8012` · 래퍼 `/tmp/t6115_app.py`(CORS `:3001` + 제어 이벤트 계측) · `VOICE_ADAPTER=nova` · `WORKER_ENABLED=false` |
| 프론트 | 사본 `/tmp/fe-t6115`(`:3001`) · `node_modules` 하드링크 복사(`H-BU`) |
| 브라우저 | 전용 Chrome `:9333`(**152.0.7977.83**) · fake media stream |
| 상한 | Nova **6세션**(팔 6개) · Claude **0회** |

### 픽스처 둘을 새로 만들었음 — 표지가 없는 명령

```bash
say -v Samantha -o /tmp/z6115a.aiff "End the session now, please."   # vc27_end_nomarker_en (1.75초)
say -v Yuna     -o /tmp/z6115b.aiff "학습 종료해 주세요."             # vc28_end_nomarker_ko (1.39초)
afconvert -f WAVE -d LEI16@16000 -c 1 /tmp/z6115<x>.aiff tests/harness/fixtures/voice/<id>.wav
```

기존 것을 씀 — `vc13_learning_en` · `vc15_learning_ko` · `vc20_yes_en` · `vc18_yes_ko` ·
`vc01_cmd_en` · `vc02_yes_en`(대조 팔).

---

## 1. 팔 6개

| 팔 | 픽스처 | 표지 | 제어 이벤트 | 표지없음 warning | `voice_command` 프레임 | `session_ended`(클릭 전) |
|---|---|---|---|---|---|---|
| `a1-nomarker-en` | `vc13`,`vc27` | 없음 | `end/requested` → `end/confirmed`(heard=`'yes'`) | **2** | **0** | **0** |
| `a2-nomarker-en` | `vc13`,`vc27` | 없음 | `end/requested` | **1** | **0** | **0** |
| `a3-nomarker-yes-en` | `vc13`,`vc27`,`vc20` | 없음 | `end/requested` → `end/confirmed` | **2** | **0** | **0** |
| `a4-nomarker-yes-en` | `vc13`,`vc27`,`vc20` | 없음 | `end/requested` → `end/confirmed` | **2** | **0** | **0** |
| `a5-nomarker-yes-ko` | `vc15`,`vc28`,`vc18` | 없음 | `end/requested` → `end/confirmed` | **2** | **0** | **0** |
| `c1-marker-en`(대조) | `vc13`,`vc01`,`vc02` | **있음** | `end/confirmed` | **0** | **1** | **1** |

제어 이벤트 **10건** · 표지없음 warning **9건**(`marker-drop-warnings.log`).
⚠️ `a1` 은 학습자가 「예」를 말하지 않았는데 모델이 `heard='yes'` 로 `confirmed` 를 불렀음.

---

## 2. 관측

### 2-1. AC#1 — 버려진 명령에 코치가 「종료됐다」고 말한 비율: **4 / 4**

`confirmed` 까지 간 팔 넷 전부에서 코치가 종료를 **완료로** 말했고 앱은 세션을 닫지 않았음:

```
a1  Do you want to end today's session? Okay, the session has ended. Thank you for chatting today!
a3  Okay, the session is ending now. Thank you for talking with me today. See you next time!
a4  Okay, the session is ending now. Thank you for talking with me today! Have a good evening!
a5  Okay, the session has been ended as requested. If you need any more help in the future, …
```

`a2` 는 분모에서 가름 — 학습자가 답하지 않아 모델이 `requested` 에서 멈췄고, 코치는
*"Do you want to end today's session?"* 만 말했음. **거짓 주장이 없었음.**
⇒ **거짓 주장은 `confirmed` 를 부른 팔에서만 나고, 그 팔에서는 4/4 로 남.**

### 2-2. 대조 팔 — 표지가 있으면 정상 실행됨 (거짓 주장이 아님)

`c1-marker-en` 은 warning **0** · 프레임 **1** · 종료 클릭 **전** `session_ended` **1** 로
세션이 실제로 닫혔음. ⇒ 갈림의 조건은 **표지의 유무**이고 명령 자체나 언어가 아님.
⚠️ 부수 관측 하나: `c1` 에서 모델이 `requested` 를 건너뛰고 `confirmed` 하나만 불렀고 앱이 그것으로
닫았음. 이 회차는 그 자리를 판정하지 않음(`session.py` 가 `confirmed` 에서 닫는 것은 계약임).

### 2-3. AC#2 — 지시문·내부 추론 읽기는 이 조건이 결정하지 않음: **0 / 5**

앞 회차 `end-en` 에서 코치가 지시문 문장(*"The app closes the session only on 'confirmed' …"*)과
자기 추론을 여러 문단 읽었고 그 팔의 `audio` 는 **1189** 였음. 이 회차의 다섯 팔에서는
**한 번도 나오지 않았고** `audio` 는 **64~165** 였음.
⇒ **버려짐이 그 낭독의 충분조건이 아님.** 앞 회차의 1건은 남기되 **조건을 특정하지 못했음**을
그대로 적음. ⚠️ 표본 5로 「나지 않는다」를 단정하지도 않음.

### 2-4. 기록에도 갈림이 남음 — 그 발화가 학습 발화로 저장됨

발화 유형 집계: `voice_command` **1**(대조 팔의 것) · `learning` **31**.
즉 표지 없는 명령 다섯은 전부 **`learning` 으로 저장**됐고, 코치는 그것을 명령으로 다뤘음.
⛔ `learning` 은 분석 대상의 유일한 조건이라(`services/utterances.py` 를 인용한
`_classify_user_final` 주석) **「End the session now, please.」가 교정 대상 학습 발화가 됨.**
⚠️ 이것은 결정 104·105 가 알고 받은 대가와 같은 방향이고 새 결함으로 등재하지 않음 — 다만
갈림이 **말·상태·기록 세 층에서 같이** 난다는 것이 이 회차의 관측임.

---

## 3. 판정 — AC#1·#2 를 닫음. AC#3·#4 는 열어 둠

- **AC#1(크기)**: `confirmed` 를 부른 팔에서 **4/4**. 앞 회차 1건을 더하면 **5/5**.
  ⛔ 「가끔」이 아니라 **그 조건에서는 늘 그렇다**로 읽힘 — 다만 표본 5임.
- **AC#2(가름)**: 지시문 낭독은 **0/5** 로 이 조건이 결정하지 않음. 거짓 주장과 낭독은 **다른
  현상**이고 이 회차가 그 둘을 갈랐음.
- **AC#3(고치는 자리)**: ⛔ 닫지 않음 — 설계 판단이고 통합 테스트 세션의 몫이 아님. 재료만 적음:
  `accepted` 를 돌려주는 자리(`nova.py` `_flush_tool_results`)와 실행을 판정하는 자리
  (`session.py` 표지 게이트)가 다른 층이고, 어댑터 주석이 **번역기가 버린 경로에 대해서만** 같은
  위험을 이미 막아 뒀음.
- **AC#4(고친 뒤 관측)**: 미착수 — 고침이 없음.

⚠️ **`TASK-61.13` 과 같은 부류의 두 번째 원인임**(결정 112 의 근거). 두 원인이 만드는 화면은 같음 —
학습자는 「됐다」고 듣고 앱은 아무것도 하지 않음.

---

## 4. teardown — 이 턴에 직접 돌린 출력

| 대상 | 결과 |
|---|---|
| `:8012` · `:3001` · `:9333` | 전부 HTTP **000** |
| 검증 전용 DB | `dropdb ohmyenglish_t6115` 성공 · 남은 DB 는 `ohmyenglish` · `ohmyenglish_smoke` · `ohmyenglish_test` |
| `/tmp` 사본 | `fe-t6115` · `chrome-t6115` · `t6115_app.py` · 회차 로그 삭제 · 잔여 **0건** |
| 공유 dev DB | 손대지 않았음 — `learning_sessions` **17** · `schema_migrations` **22** 로 기준선과 같음 |
| 리포에 남긴 것 | 픽스처 둘(`vc27` · `vc28`) · 이 디렉터리(관측 JSON 6 · `control-events.log` · `marker-drop-warnings.log` · `sessions.tsv` · `utterances.tsv` · 스크린샷 12) |
