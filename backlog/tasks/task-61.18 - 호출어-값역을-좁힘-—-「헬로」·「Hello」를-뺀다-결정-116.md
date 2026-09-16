---
id: TASK-61.18
title: 호출어 값역을 좁힘 — 「헬로」·「Hello」를 뺀다 (결정 116)
status: Done
assignee: []
created_date: '2026-09-16 04:30'
updated_date: '2026-09-16 04:35'
labels: []
dependencies: []
parent_task_id: TASK-61
ordinal: 193000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
결정 116: 「Hello」로 시작하는 학습 발화가 명령으로 분류돼 오류 분석에서 빠지는 것을 실물로 확인했고(runs/2026-09-16-task61-16-divergence-surface §3-② · 1/1) 사용자가 「버린다 — 헤이/Hey 만 둠」을 골랐다. ⇒ _WAKE_FORMS 에서 hello·헬로 를 빼고 hey·헤이·해이 와 앱 이름 표지를 남긴다. ⚠️ 대가가 «작아지지만 사라지지는 않는다» — 「Hey, how are you?」 같은 발화는 여전히 표지를 얻는다. 그 사실을 단정으로 남긴다. ⛔ 실물 회차를 다시 돌리지 않는다: 값역을 «좁히는» 변경이라 새로 성립하는 경로가 없고, 「Hello, end the session」은 이제 앱이 버리며 그 자리는 TASK-61.16 이 만든 알림이 이미 덮는다(실측함).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 hello·헬로 가 표지가 아닌 것을 단정으로 지킨다
- [x] #2 hey·헤이·해이 와 앱 이름 표지가 그대로 성립하는 것을 단정으로 지킨다
- [x] #3 남는 대가(「Hey」로 시작하는 학습 발화)를 단정으로 명시한다
- [x] #4 지시문 규칙 12 의 표지 열거를 함께 고친다 — 앱과 갈리면 명령이 조용히 사라진다
- [x] #5 게이트 여섯이 초록인 것을 직접 돌려 확인한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-16 — 값역을 좁히고 닫았음. _WAKE_FORMS 는 ohmyenglish · 오마이잉글리시 · 오마이잉글리쉬 · hey · 헤이 · 해이 여섯임. 지시문 규칙 12 도 함께 좁혔음. ⚠️ 기존 단정 하나가 줄바꿈으로 끊긴 「Oh My English」를 잡아냈음(문면을 다시 감을 때 표지 문구가 두 줄로 갈렸음) — 그 단정이 있어서 조용한 값역 갈림을 막았음. 게이트 여섯 초록(pytest 1250 passed). ⛔ 실물 회차를 다시 돌리지 않았음: 값역을 좁히는 변경이라 새로 성립하는 경로가 없고 「Hello, end the session」의 자리는 TASK-61.16 의 알림이 이미 덮는 것을 실측했음.
<!-- SECTION:NOTES:END -->
