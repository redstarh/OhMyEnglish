---
id: TASK-94
title: '실행: P계층 마지막 이월분 P8 — pronunciation_intonation 주입 내성'
status: Done
assignee: []
created_date: '2026-09-10 17:27'
updated_date: '2026-09-10 22:15'
labels: []
dependencies: []
ordinal: 97000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
4차수부터 미실행으로 남은 유일한 P 항목이다. scenarios-P §4 의 P8 단정: inject_errors.py 로 pronunciation_intonation 카테고리를 «직접» 주입해 저장·조회·렌더가 깨지지 않는지 본다. 저장 경로 자체는 카테고리를 차별하지 않아야 한다. ⛔ 실물 Nova 호출이 필요하지 않다 — 주입이므로 비용이 낮고 값어치가 높다. 지금 이 카테고리는 error_patterns CHECK 에 허용돼 있고(직접 확인) pronunciation_an_as_a 행이 실재하지만, 그 행은 pronunciation_attempts 에서 frequency 를 세므로 error_occurrences 가 0행이다(H-AX) — 주입 경로가 그 비대칭을 어떻게 다루는지가 이 시나리오의 핵심이다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 inject_errors.py 로 pronunciation_intonation 패턴을 주입하고 error_patterns·error_occurrences 에 무엇이 생기는지 기록한다 — frequency 를 어느 writer 가 세는지 함께 확인한다
- [x] #2 결과 API 와 결과 화면이 그 카테고리를 깨지지 않고 렌더하는지 확인한다 — 스크린샷을 직접 열어 본다
- [x] #3 복습 과제가 생기는지 본다. 생기면 shadowing 매핑 의도(scenarios-E L3)와 실제가 갈리는지 적는다
- [x] #4 회차 전에 browser_leg.md §8-0 절차대로 스냅샷을 뜨고 teardown 후 어긋난 행 0 을 확인한다 — 주입도 DB 쓰기다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
⚠️ 착수 전 알아 둘 것 (2026-09-11) — 이 태스크 파일이 외부에서 한 번 변경됐다가 되돌려졌음.

다른 세션(ohmyenglish-7f)이 자기 새 태스크 ID 를 짐작해 -s "In Progress" 를 돌렸는데 실제 자기 것은 TASK-95 였고 이 태스크 상태가 To Do → In Progress 로 바뀌었음. 그 세션이 스스로 알리고 git diff 로 되돌렸음.

팀리드가 커밋 5e0772f 판과 git diff 로 직접 대조했음 — status To Do · AC 4건 전부 미체크 · 설명·AC 문면 차이 0 임. 즉 원래대로임.

⚠️ 유일한 잔여는 updated_date 줄이 «추가»된 것임(원래는 태스크 생성 후 수정이 없어 그 키가 아예 없었음). 그 세션은 「원래 값 17:32 로 복구 불가」로 적었으나 정확히는 «그 줄을 지우면 커밋 판과 글자 그대로 같아짐» 이므로 복구 가능함. ⛔ 지우지 않았음 — 도구가 다음 편집에 다시 넣을 값이고 판정에 쓰이지 않음(상태·AC·의존이 정본임). 즉 「복구 가능하나 무의미해서 두었다」임.

⛔ 이 사고에서 얻은 절차: 남의 세션이 내 태스크를 건드렸는지 감지하는 수단은 git diff <내 마지막 커밋> -- <태스크 파일> 임. 그 diff 가 비면 안전하고, 그 대조가 「알려 줬으니 믿는다」보다 강함. 같은 리포에 여러 세션이 태스크를 만들면 번호가 사이에 끼어들므로 backlog task create 의 반환 ID 를 읽지 않고 짐작하지 않음.

2026-09-11 판정 — **AC 4건 전부 충족. 정본은 `tests/harness/runs/2026-09-11-task94-p8.md` 이고 여기서 수치를 다시 세지 않는다.** 실물 Nova·Claude 호출 **0회** · 워커 미기동.

**⛔ 이 태스크의 문면에 결함이 있었다** — P8 이 지목한 `inject_errors.py` 로는 이 시나리오가 성립하지 않는다. 그 스크립트는 문장을 **실제 분석 워커**에 흘리고 그 워커 프롬프트가 이 카테고리를 금지한다(`UNJUDGEABLE_CATEGORY`). 그 카테고리를 만드는 앱의 유일한 경로는 `services/pronunciation.record_attempt` 다. 신설 실행체 `tests/harness/p8_inject_pronunciation.py`(`inject`·`collide`·`teardown`)가 그 제품 함수를 직접 부른다. `scenarios-P-pronunciation.md` §4-0 에 그 사실을 고정했다.

**AC#1** — 저장 경로는 카테고리를 차별하지 않는다. `pending` 은 패턴을 만들지 않고 `incorrect` 가 `pronunciation_th_as_s` 를 만들며 `error_occurrences` 가 **0행**인데 `frequency` 가 1이다(`H-AX` 비대칭 실측).

**⛔ AC#1 이 더한 것 — 두 writer 가 서로를 덮는다.** 개수를 가른 조건(시도 2 대 occurrence 1)에서 문법 재계산이 `frequency` 2→**1**, `last_seen_at` 을 **과거로** 옮겼다. **독립 2회 재현.** ⚠️ 도달성은 재지 않았다 — 프롬프트에 발음 키를 싣는 경로는 `category <> UNJUDGEABLE_CATEGORY` 로 막혀 있고 남은 것은 모델이 규칙 2 를 어기는 것인데 **앱 검증이 없다.** ⇒ **`TASK-99` 로 등록했다**(앱 코드라 구현 세션 몫).

**AC#2** — 결과 API·결과 화면이 깨지지 않는다. 화면을 **직접 열어** 판독했다(`P8-results-r2.png`). `발음` 절과 시도 2건·배지가 렌더되고 `target_sound` 는 화면에 **없다**. ⚠️ 1회차 캡처의 「시범 문장 = `th_as_s`」는 **내 하네스가 `target_form` 에 기계 키를 넣은 결과였고 앱 결함이 아니다** — 실행체를 고쳐 2회차를 다시 떴고 1회차 캡처는 오독의 증거로 남겼다.

**AC#3** — 복습 과제가 생기고 `task_type` 이 **`rephrase`** 다(`shadowing` 아님). `review.REVIEW_TASK_TYPE` 이 모듈 상수이고 카테고리 분기가 0이다. ⛔ **결함으로 세지 않는다** — 주석이 슬라이스 1의 경계로 문서화했고 소유자는 슬라이스 2다. `scenarios-E-agent-learning.md` L3 의 의도와 갈리는 자리를 회차 기록이 고정했다.

**AC#4** — drift **0 / 0** · 행 수 9·15·7 이 회차 전과 같음 · 내 패턴·세션 잔존 **0** · 보존 세션 6개 결과 API 어긋남 **0**. ⛔ **§8-0 의 「컬럼을 늘린 첫 회차」 전이가 이 회차에 걸려 실행했다** — `harness_pattern_baseline` 이 옛 컬럼 넷이었고 `harness_review_task_baseline` 은 **없었다**(신설 15행). `browser_leg.md` §8-0 에 그 실행을 기록했다. ⚠️ 원인은 `TASK-91` P7 이 §8-0 을 **파일 스냅샷으로만** 만족시키고 DB baseline 표를 갱신하지 않은 것이다 — 두 산출물을 함께 내야 한다는 규약을 그 문서에 추가했다.

**부수 확인**: handoff 착수 전 필수 ③-2(「백엔드가 낡은 코드라 `awaiting_analysis` 키가 없다」)가 **해소됐다** — 응답에 그 키가 있다.
<!-- SECTION:NOTES:END -->
