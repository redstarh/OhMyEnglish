---
id: TASK-128.4
title: '구현 C4: 폴백이 사라지면 화면의 진입 안내가 거짓이 된다 — 「키의 부재 = 폴백」 신호를 바꾼다'
status: In Progress
assignee: []
created_date: '2026-09-12 13:47'
updated_date: '2026-09-12 14:32'
labels: []
dependencies:
  - TASK-128.2
parent_task_id: TASK-128
ordinal: 141000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
결정 72 가 «소리를 못 골라도 전용 모드로 간다» 로 바꾸므로, page.tsx 가 pronunciation_focus 의 «부재» 를 「말하기로 떨어졌다」 로 읽는 것이 거짓이 된다. 지금 dev DB 는 발음 기록 0건이라(nova.py:464) 후보가 빈 것이 «기본» 상태이고, 그때 화면이 «일반 대화로 시작했어요» 를 띄운다 — 실제로는 전용 세션이다. 자리: app/frontend/app/page.tsx:70-75(문구 둘)·147-153(분기) · app/frontend/lib/ws.ts:56-63(그 키의 계약 주석). ⚠️ 이 문구에는 테스트가 없음(grep 0건).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 화면 문구가 «전용 세션인데 후보가 없다» 를 참으로 말한다 — 폴백이라 말하지 않는다
- [x] #2 ws.ts 의 pronunciation_focus 계약 주석에서 「부재 = 폴백」 서술을 걷는다
- [x] #3 학습자에게 보이는 한국어 문구는 사용자 승인 대상이라 올려서 받는다 — 내가 정하지 않는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-12 KST 문구를 바꿨음 — 사용자 결정 83(`docs/ops/captain-instruction-register.md`)을 받아
이행했음. `PRONUNCIATION_FELL_BACK` → `PRONUNCIATION_NO_CANDIDATE` 로 이름과 문면을 함께 바꿨고
(「발음 연습으로 시작했어요. 오늘 다룰 소리는 대화에서 듣고 고를 거예요.」) `page.tsx` 의 분기와
`lib/ws.ts` 의 계약 주석을 함께 고쳤음. 기계 검사: `tsc --noEmit` exit 0 · `eslint` exit 0 ·
옛 이름 참조 grep **0건**.

⛔ **AC#1 을 열어 둠 — 렌더된 화면을 «직접 읽지» 못했음.** 기계로 확인된 것은 사슬의 두 끝임:
서버가 후보 없이도 `mode='pronunciation'` 으로 연다는 것(`tests/integration/test_ws.py`
`…records_the_pronunciation_mode_even_without_a_sound`)과 후보가 0건이면 키 자체를 넣지 않는다는 것
(`…omits_the_focus_key_when_there_is_no_candidate`), 그리고 클라이언트가 그 부재에서 새 문구를
고른다는 것(`page.tsx` 분기 · 위 grep). ⚠️ **가운데 한 칸 — React 가 그 문장을 실제로 그리는가 — 만
남았고 그것은 화면을 열어야 보임.**

⚠️ **왜 이번 턴에 안 했는지**: 브라우저 레그 자산이 전부 정리돼 있음(직접 확인 — `/tmp/uicheck_app.py`
· `/tmp/fe-uicheck` · `/tmp/chrome-uicheck` 셋 다 `No such file or directory`). 재구성은 검증 DB +
CORS 래퍼 + 프론트 사본 + 전용 Chrome 이고 `2026-09-12-task10-2-entry-browser-leg.md` §0 이 그 절차를
갖음. ⛔ 그 회차가 **두 분기 모두 화면에 뜨는 것을 이미 확인했으므로** 남은 것은 「둘째 분기의 문면이
바뀐 것」 하나임 — 그래도 문면 자체를 눈으로 읽은 것은 아니므로 AC 를 체크하지 않음.
⚠️ 그 회차의 함정 하나를 미리 옮겨 둠: **안내 줄의 창이 짧아 폴링으로는 놓침** — 클릭 «전»에
`MutationObserver` 를 심어야 잡힘. 처음 판이 「안내가 없다」로 오독됐음.
<!-- SECTION:NOTES:END -->
