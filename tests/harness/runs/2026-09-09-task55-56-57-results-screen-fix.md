# 회차 기록 — 결과 화면 결함 셋(TASK-55·56·57) 수정 후 관측

수단은 기존 브라우저 다리와 같음 — CDP :9222 · `next dev`(v16.3.2) :3000 · 백엔드 :8002.
새 수단 0개임. 이 문서는 **수정 후에 직접 돌려 얻은 출력만** 담음.

## 1. C3 결과 화면 5상태 + 없는 세션 — `c3_results_screen.py`

```
세션 5건 · API 상태: analyzing=analyzing · final=final · partial_failure=partial_failure
              · connection_failed=connection_failed · no_utterances=no_utterances
  analyzing          첫 직계 <p> = '분석 중'          · 원문/교정문 = 0/0 · 카드 0
  final              첫 직계 <p> = '확정'             · 원문/교정문 = 1/1 · 카드 1
  partial_failure    첫 직계 <p> = '부분 실패'         · 원문/교정문 = 0/0 · 카드 0
  connection_failed  첫 직계 <p> = '연결 실패'         · 원문/교정문 = 0/0 · 카드 0
  no_utterances      첫 직계 <p> = '분석 대상 없음'     · 원문/교정문 = 0/0 · 카드 0
  missing-uuid       첫 직계 <p> = '그 학습 결과를 찾을 수 없습니다.' · 라벨 잔존 []

--- 판정 (단정 58건 검사) ---
  미확인   A4-2 기대값 교차 대조: 교정 2건 이상인 세션이 없어 평가할 수 없다 → 판별력 미확인
  PASS  58건 전건 통과 · 미확인 1건은 통과로 세지 않았다
```

판독 원본을 `runs/2026-09-09-c3-dom-read-post-task55.json` 으로 보존함 — `test_c3_gates.py` 의
픽스처가 이것을 가리킴. 이전 회차 `runs/2026-09-06-t4-c3-dom-read.json` 은 **그 시점의 기록이라
지우지 않았음.**

**TASK-55 · TASK-57 의 증거가 이 판독에 있음**:

| 태스크 | 무엇을 봤는가 | 판독값 |
|---|---|---|
| TASK-55 | 없는 uuid 화면의 학습자 문구 | `그 학습 결과를 찾을 수 없습니다.` — 상태 코드·`API` 가 없음 |
| TASK-55 | 인앱 출구가 모든 상태에 있음 | 직계 `<p>` 에 `← 학습 시작 화면으로` 가 6화면 전부에 있음 |
| TASK-57 | 부분 실패 안내 문체 | `분석하지 못한 발화가 있습니다 — 재시도되지 않습니다` |

## 2. 폴링 정지 — TASK-56

⛔ **개수만 재면 「멈췄다」와 「폴링이 애초에 죽었다」가 같은 값으로 보임.** 그래서 같은 계측으로
비종료 상태(`analyzing`) 화면을 함께 재고 그쪽이 계속 도는 것을 음성 대조로 요구했음.
계측은 `Page.addScriptToEvaluateOnNewDocument` 로 `fetch` 를 감싸 세는 것이라 백엔드 로그에
의존하지 않음.

```
  missing(404)   결과 API 호출 2건 · 관측창 10.0s · 첫~끝 0.0s  · 첫 주기 뒤 0건
  analyzing      결과 API 호출 6건 · 관측창 10.0s · 첫~끝 8.02s · 첫 주기 뒤 3건
  PASS  4xx 는 첫 주기 뒤 0건이고 analyzing 은 3건 이어졌다 — 두 경로가 갈렸다
```

호출 시각(첫 호출 기준 초): `missing` = `[0.0, 0.01]` · `analyzing` = `[0.0, 0.0, 2.01, 4.01, 6.02, 8.02]`.

⚠️ **t≈0 의 2건은 재시도가 아님 — 개발 모드의 이펙트 이중 실행임.** App Router 는 Strict Mode 가
기본 `true` 이고 개발 모드 한정 기능임(근거를 번들 문서에서 직접 확인함:
`node_modules/next/dist/docs/01-app/03-api-reference/05-config/01-next-config-js/reactStrictMode.md`
— *"Since Next.js 13.5.1, Strict Mode is `true` by default with `app` router"* · *"development mode
only feature"*). **두 화면에 똑같이 나타나므로 판정 기준에서 뺐음** — 처음에 「1건이어야 한다」로
재서 FAIL 을 봤고, 그 FAIL 이 앱 결함이 아니라 내 기준의 결함이었음.

## 3. 판별력을 게이트로 옮긴 것

`check_missing` 에 「학습자 문구에 기계 낱말이 없다」를 넣었음. ⛔ **그것이 등호의 종속절이 아님을
증명해야 함** — 이 리포는 독립 판별력 0인 단정을 지운 전례가 있음(`test_sentinel_control_is_gone`).
단정은 **직계 `<p>` 전체**를 보고 등호는 **첫 `<p>` 하나**만 보므로 둘이 갈림.
`test_machine_word_check_has_independent_discrimination` 이 그 갈림을 잼 — 첫 줄을 기대 문구
그대로 두고 둘째 줄로만 상태 코드를 흘려 **어긋남이 정확히 1건**인 것을 요구함.

`bodyText` 로 재지 않은 이유: 거기에 `next dev` 가 주입하는 스크립트가 섞여 판정이 도구 버전에
매임(실측한 원문이 `self.__next_r=...` 로 이어짐).

## 4. 게이트 — 이 회차에 직접 돌린 값

`app/backend` cwd 에서 돌렸음. 수치는 §5 인계 지표에 옮겼음(`handoff/HANDOFF.md`).
