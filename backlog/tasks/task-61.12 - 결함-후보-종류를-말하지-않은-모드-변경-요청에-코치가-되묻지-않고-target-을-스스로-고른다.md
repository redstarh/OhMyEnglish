---
id: TASK-61.12
title: '결함 후보: 종류를 말하지 않은 모드 변경 요청에 코치가 되묻지 않고 target 을 스스로 고른다'
status: Done
assignee: []
created_date: '2026-09-15 18:27'
updated_date: '2026-09-15 18:47'
labels: []
dependencies: []
parent_task_id: TASK-61
ordinal: 187000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
회차 `runs/2026-09-16-task61-10-mode-change` §3 미충족 ② 에서 1회 관측했다. 학습자가 「Oh My English, change the practice mode.」 처럼 종류를 말하지 않았을 때 코치는 어느 연습인지 되묻지 않고 「오늘 세션을 끝내고 새 연습 세션을 시작할까요?」로 예·아니오 확인만 물었다. 백엔드 warning 이 0건이므로 페이로드는 버려지지 않았고 모델이 값역 안의 target 을 스스로 골랐다는 뜻이다. ⇒ 학습자가 「예」라고만 답하면 자기가 고르지 않은 모드로 세션이 열릴 수 있다. ⛔ 결정 111 을 뒤집지 않는다 — 종류를 «말한» 경로는 두 언어에서 2/2 로 성립했다. 구멍은 말하지 않은 경로 하나다. ⚠️ 표본 1건이므로 기전으로 단정하지 않는다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 되묻지 않는 거동의 크기를 실물 회차로 센다 — 같은 픽스처를 반복해 되묻는 비율을 얻는다
- [x] #2 고치는 자리를 정한다: 지시문 문면인가 앱인가 — 앱이 막는 안은 「target 을 못 들은 requested 를 버리지 않고 학습자에게 되묻는 경로」이고 지금 리포에 그 경로가 없다
- [x] #3 고치면 실물 회차로 관측한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 2026-09-16 — 측정하고 문면을 고쳤음 (세션 `ohmyenglish-42`)

회차 `tests/harness/runs/2026-09-16-task61-12-unspecified-mode` 가 정본임. Nova 10세션 · Claude 0회.

- **AC#1(크기)**: 되묻기 **0/4(기준선) → 3/5(고친 뒤)**. ⛔ 결정적이지 않음 — 같은 문면에서 거동이 갈림.
- **AC#2(고치는 자리)**: **문면임.** 앱에는 만들 자리가 없음 — 모델이 `target` 을 **항상 유효하게 채우므로**(계측 3/3) 앱은 「학습자가 종류를 말했는가」를 알 수 없고, 알려면 `heard` 문장을 해석해야 함(표지처럼 접두어 한 줄로 끝나지 않으므로 `models/voice_command.py` 의 규약 밖임).
- **AC#3(관측)**: 위 회차 §2. 고친 문면은 `Never guess which kind they want … do not call the tool at all until they answer` 임.

**계측을 새로 붙였음** — 래퍼에서 `NovaEventTranslator.translate` 를 감싸 제어 이벤트의 command·stage·target 을 남겼음(`control-events.log`). ⛔ **이것이 없으면 판정이 불가능했음** — `recv.voice_command` 는 프레임 수라서 어느 명령·어느 target 인지 구별하지 못함. 그 유도의 부족을 `TASK-61.10` 회차 README 에 정정으로 남겼음.

⚠️ **「tool 을 부르지 마라」는 지켜지지 않았음**(추측 `requested` 3/3). 그 추측이 학습자를 해치지 않은 이유는 **앱이 `confirmed` 에서만 세션을 열기 때문**임 — 안전은 문면이 아니라 앱이 지킴.
⚠️ **남은 구멍 하나를 `TASK-61.13` 으로 등재했음** — 코치가 연습을 시작한다고 말했는데 stage 가 `requested` 에 머물러 앱이 세션을 갈지 않은 모양(1/1).
<!-- SECTION:NOTES:END -->
