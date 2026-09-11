---
id: TASK-106
title: '하네스: 목표 소리가 실제로 든 픽스처로 소리 줄 축을 다시 잰다 — 지금 픽스처(p2m)에는 «an» 이 없다'
status: In Progress
assignee: []
created_date: '2026-09-11 00:35'
updated_date: '2026-09-11 00:38'
labels: []
dependencies: []
ordinal: 109000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-105 회차가 21회를 돌리고 «질문에 답하지 못한다» 는 판정을 냈음. 정본은 tests/harness/runs/2026-09-11-task105-sound-line.md §3 임.

⛔ 기전: 계획이 지목하는 소리는 an_as_a 인데 p2m.wav 의 오류는 f→p · r→l · θ→s 이고 두 문장에 «an» 이 아예 없음(scenarios-P-pronunciation.md:75~76). 즉 코칭할 목표 소리가 오디오에 없어서 tool 0/21 은 프롬프트가 아니라 픽스처가 예측한 값임.

⚠️ 두 번째 교란: 저장된 계획의 초점이 [pronunciation_an_as_a, article_missing_before_noun] 둘이고 둘이 같은 낱말에서 만남. 그래서 관측된 문법 지시가 «소리 키를 관사 지시로 읽은 것» 인지 «둘째 초점을 따른 것» 인지 갈리지 않음.

⚠️ DB 의 발음 패턴은 pronunciation_an_as_a 하나뿐임(직접 조회 · frequency=2 · next_review_at 2026-09-04). 그래서 계획은 항상 그 소리를 고름 — 픽스처를 그 소리에 맞추는 쪽이 유일한 길임.

배제된 것 둘은 다시 재지 않아도 됨: 소리 줄이 프롬프트에 도달함(5,223자에 1건) · 대조군 tool 5/5 로 환경은 정상임.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 계획이 지목하는 소리(an_as_a)가 실제로 든 wav 를 만들고 그 오류가 전사에 어떻게 나타나는지 먼저 적는다 — 전사에 흔적이 0이면 그 사실 자체가 관측값이다
- [ ] #2 초점 교란을 없앤다 — 문법 초점이 같은 낱말을 요구하지 않는 구성으로 두거나 그 팔을 «하네스 팔» 로 이름 붙여 제품 팔과 섞지 않는다
- [ ] #3 그 픽스처로 팔 A 를 돌려 코칭 발생 · tool 도착 · target_sound 실림을 세고 대조군으로 판별력을 «먼저» 확인한다
- [ ] #4 ⛔ 결과가 0 이어도 「소리 줄이 무효」로 단정하지 않는다 — 그 회차가 무엇을 배제했고 무엇을 배제하지 못했는지 갈라 적는다
<!-- AC:END -->
