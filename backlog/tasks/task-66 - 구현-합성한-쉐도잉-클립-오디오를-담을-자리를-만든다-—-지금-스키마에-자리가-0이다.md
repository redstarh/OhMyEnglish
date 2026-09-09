---
id: TASK-66
title: '구현: 합성한 쉐도잉 클립 오디오를 담을 자리를 만든다 — 지금 스키마에 자리가 0이다'
status: To Do
assignee: []
created_date: '2026-09-09 14:16'
labels: []
dependencies:
  - TASK-63
ordinal: 69000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
결정 47 이 「쓴다 · 미리 만들어 저장」으로 확정했다. 그런데 011_shadowing_items.sql 을 직접 읽어 확인한 사실 둘: ① shadowing_items 의 컬럼은 id·source_title·source_url·transcript·clip_start_sec·clip_end_sec·level·created_at 뿐이고 오디오를 담을 자리가 없다. source_url 주석이 「외부 영상은 링크만 보관한다」라 그 자리는 출처 링크이고 로컬 오디오 경로를 넣는 것은 의미 오버로드다 ② utterances.audio_url 은 CHECK utterances_audio_only_for_shadowing 이 speaker='user' 인 학습자 낭독만 받는다 — 합성음은 원리적으로 못 들어간다. 근거와 생성 절차는 docs/design/2026-09-09-shadowing-synthetic-clip-review.md 가 소유한다(§4·§7). ⛔ 결정 47 이 R10-7 예외를 「합성한 쉐도잉 클립 오디오」 하나로 좁혀 열었다 — 그 범위를 넓히지 않는다. ⚠️ 설계서 §9 의 data-first 규율을 지킨다: 소비자(재생 경로)와 같은 커밋에서 나간다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 오디오를 어디에 두고 무엇으로 가리키는지 정한다 — 컬럼 추가인지 별도 표인지, 파일이 리포 안인지 밖인지. 발명하지 않고 기존 학습자 낭독 저장 방식과 대조해 근거를 든다
- [ ] #2 R10-7 예외 범위를 스키마에 새긴다 — 011 의 CHECK 주석이 「다른 오디오가 조용히 쌓이는 길을 막는다」고 한 의도를 유지한다. 합성 클립 외의 오디오가 새 자리로 들어오지 못하게 한다
- [ ] #3 시드 1건의 clip_end_sec 을 실측값으로 고친다 — 지금 30.00 을 선언했으나 그 전사문의 합성음은 16.64초다(2026-09-09 실측). 합성음에서는 시간 창이 곧 오디오 전체다
- [ ] #4 재생 경로(소비자)와 같은 커밋으로 낸다 — 소비자 0곳이면 진행하지 않는다(설계서 §9)
- [ ] #5 클립 생성 절차 문서의 마지막 줄을 채운다 — 파일을 어디에 두는가가 정해지면 review 문서 §7.4 가 닫힌다
<!-- AC:END -->
