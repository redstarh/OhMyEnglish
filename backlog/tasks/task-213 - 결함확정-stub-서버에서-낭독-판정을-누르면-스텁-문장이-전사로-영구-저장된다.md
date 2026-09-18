---
id: TASK-213
title: '결함(확정): stub 서버에서 낭독 판정을 누르면 스텁 문장이 전사로 영구 저장된다'
status: Done
assignee: []
created_date: '2026-09-18 07:50'
updated_date: '2026-09-18 09:11'
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
- [x] #1 stub 어댑터로는 전사를 저장하지 않게 한다
- [x] #2 전사기를 쓸 수 없는 것과 전사를 얻지 못한 것을 갈라 앞쪽은 503 으로 낸다
- [x] #3 이미 저장된 오염 행이 있는지 dev DB 에서 세고 있으면 지운다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 2026-09-18 처분 — 가드를 전사 앞에 두고 화면이 두 갈래를 가름

구현 셋:
1. `audio_gateway/factory.transcriber_available(settings)` 신설 — 어댑터 값을 아는 자리를 팩토리 하나로 둠(G3).
2. `api/results.judge_recording_readback` 이 전사 **앞에서** 503 으로 끊음(`낭독 판정을 쓸 수 없다`). 뒤에 두면 막기 전에 오염 행이 생김.
3. 화면(`ShadowingPanel`)이 `ok: false` 를 빈 낱말로 접지 않고 「지금은 낭독 판정을 쓸 수 없어요.」 를 보임.

⛔ 되돌린 판단: `TASK-212` 의 「요청 실패와 전사 못 얻음을 같게 말한다」를 뒤집음. 그 근거가 *"둘 다 다시 눌러 볼 일이다"* 였고 그 전제가 틀림 — 503·500 은 몇 번 눌러도 달라지지 않음. 상태는 필드 대신 갈래 한 값(`kind`)으로 들어 닿을 수 없는 조합을 없앰(관행은 `WordLookup` 의 `Lookup`).

실측(전부 이 세션에서 직접 돌림):
- 스텁 서버 `POST …/readback` → **503** `{"detail":"낭독 판정을 쓸 수 없다"}`(재기동 뒤 두 번 확인).
- AC#3 dev DB 오염 행 **0건**(사전·사후 동일) · `analysis_jobs` pending **0건** · 최근 3시간 세션 **0건**(회차 여섯을 `teardown_session.py` 로 걷음).
- 게이트 여덟 다 exit 0 — `pytest` **1389 passed**(새 테스트 2건: 픽스처 둘을 parametrize) · `ruff` 0 · `ruff format` 302 files · `ty` 0 · `tsc` 0 · `eslint` 0 · `next build` 0.

⚠️ 화면 관측 방법이 함정이라 `H-CG` 로 남김 — 스텁 둘로는 그 화면에 닿지 못함(`stub` 은 픽스처 소진으로 세션 즉시 종료 · `stub_unresponsive` 는 10초 연결 상한에 걸리고 녹음이 저장되지 않음). 실물 `nova` 세션 한 회차에서 포인터를 지워 404 를 만들고(같은 `ok:false` 갈래) 문구를 직접 관측했음 — 스크린샷 `/tmp/rb-unavailable.png`.
<!-- SECTION:NOTES:END -->
