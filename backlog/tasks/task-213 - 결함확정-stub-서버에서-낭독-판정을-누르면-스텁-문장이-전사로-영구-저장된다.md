---
id: TASK-213
title: '결함(확정): stub 서버에서 낭독 판정을 누르면 스텁 문장이 전사로 영구 저장된다'
status: To Do
assignee: []
created_date: '2026-09-18 07:50'
labels: []
dependencies: []
ordinal: 274000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
/simplify 고도 각도가 찾았음(2026-09-18). VOICE_ADAPTER=stub 으로 띄운 서버에서 「낭독 판정 보기」를 누르면 스텁 픽스처의 학습자 final(stub.py)이 전사로 받아들여져 utterances.readback_transcript 에 저장되고, judge_readback 은 값이 있으면 다시 계산하지 않으므로 그 오염이 영구다. ⛔ 개발용 :8002 가 평소 stub 으로 떠 있어 실제로 밟기 쉽다. 함께 볼 것: api/vocab.py 는 같은 「빈 결과를 200 으로」 규약을 쓰면서 503 가드로 그것을 안전하게 만들었는데 낭독 판정은 그 가드를 빼고 왔다 — 자격증명·설정 실패가 화면에서 「알아듣지 못했어요」로 보여 학습자가 영원히 다시 누른다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 stub 어댑터로는 전사를 저장하지 않게 한다
- [ ] #2 전사기를 쓸 수 없는 것과 전사를 얻지 못한 것을 갈라 앞쪽은 503 으로 낸다
- [ ] #3 이미 저장된 오염 행이 있는지 dev DB 에서 세고 있으면 지운다
<!-- AC:END -->
