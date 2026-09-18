---
id: TASK-209
title: '구현 ⑤: 쉐도잉 화면에 낭독 판정을 보인다'
status: Done
assignee: []
created_date: '2026-09-18 05:54'
updated_date: '2026-09-18 06:47'
labels: []
dependencies:
  - TASK-208
ordinal: 270000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
결정 131 · 설계서 §7. 「내 낭독 듣기」를 없애지 않고 그 옆에 붙인다. ⛔ 결과 화면에 숫자를 렌더하지 않는 기존 계약을 지킨다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 「낭독 판정 보기」 를 누르면 낱말마다 맞음·빠짐·다름이 보인다
- [x] #2 「내 낭독 듣기」 가 그대로 남는다
- [x] #3 전사가 비었을 때의 안내가 영어 오류 문면이 아니다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 결과 (2026-09-18)

`lib/api.ts`(`judgeReadback` · 타입 둘) · `app/ShadowingPanel.tsx` · `app/page.tsx`.

### AC 별

- **#1** 「낭독 판정 보기」를 누르면 낱말마다 표시가 남. ⛔ **색 하나로만 가르지 않음** —
  `globals.css` 에 `--danger` 뿐이고 성공 색이 없어서, 다름은 **밑줄** · 빠짐은 **취소선**으로 함께
  가르고 범례가 그 뜻을 말함. 전부 맞았으면 범례 대신 「원본대로 읽었어요」를 보임(없는 표시를
  설명하는 문장을 만들지 않음).
- **#2** 「내 낭독 듣기」를 그대로 둠 — 설계서 §7 이 「귀로 견주는 길」을 없애지 않기로 정했음.
  판정 버튼은 그 옆에 붙었고 같은 조건(`recordingIds` 존재)에 감싸임.
- **#3** 전사를 못 얻으면 「읽은 소리를 알아듣지 못했어요. 다시 읽고 눌러 주세요.」를 보임 —
  영어 오류 문면이 아님. ⛔ 요청 실패와 전사 실패를 **같게** 말함(`api/vocab.py` 와 같은 판단 —
  학습자에게 남는 행동이 같음).

### 설계에서 스스로 잡은 것 둘

1. ⛔ **판정 상태에 발화 id 를 함께 들었음.** 다시 읽으면 발화가 새로 생기는데 판정만 남으면
   **앞 낭독의 판정이 새 낭독의 것처럼** 보임. 키를 함께 들어 렌더에서 갈리게 했음 — effect 로
   지우지 않으므로 `set-state-in-effect` 규칙과도 부딪히지 않음.
2. ⛔ **세션이 초기화되는 두 자리에서 `recordingIds` 도 함께 비움** — `setRecordingUrl(null)` 이
   있는 자리 둘을 grep 으로 찾아 둘 다 고쳤음. 하나만 고치면 판정 버튼이 남아 404 를 받음.

⛔ **주소를 다시 쪼개지 않음** — `recordingUrl` 에서 조각을 뽑는 대신 조립하는 자리(부모)가
`{sessionId, utteranceId}` 를 그대로 넘김. 주소 형태가 바뀔 때 조용히 어긋나지 않게 하는 것임.
⛔ **판정을 자동으로 받지 않음** — 첫 호출이 Nova 를 한 번 타므로(결정 131) 누를 때만 비용이 남.

### 게이트

`tsc` 0 · `eslint` 0 · `next build` 0 — 셋 다 exit 0. `/` 가 여전히 `○ (Static)` 임.
⚠️ 프런트에 테스트 러너가 없으므로 **화면 판정은 `TASK-210` 의 브라우저 회차가 유일한 증거임.**
<!-- SECTION:NOTES:END -->
