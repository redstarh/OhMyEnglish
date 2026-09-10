---
id: TASK-89
title: '하네스: Qwen3-TTS 로 한국인 학습자 오류 음소 픽스처 세트를 만든다 — 지금 픽스처에 「중간 지대」가 없다'
status: Done
assignee: []
created_date: '2026-09-10 13:51'
updated_date: '2026-09-10 13:57'
labels: []
dependencies: []
ordinal: 92000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 지시 2026-09-10: 「실제 발음 Test 는 어제 만든 Qwen 3 를 사용해서 상세한 케이스 만들어서 진행」.

⛔ 어제(TASK-59)가 반증한 것과 다른 축임을 먼저 못박음. 반증된 것은 「억양판(*k)의 생성 도구를 Qwen 으로 바꾼다」임 — Qwen Sohee 는 lang_code 를 ko 로 줘도 Nova 가 영어로 정확히 복원해 억양이 전사에 남지 않았음. 이번 용도는 「음소 치환판(*m)을 한국어 원어민 화자로 다시 만든다」이고 Qwen 의 높은 명료도가 여기서는 강점임 — 의도한 오류 음소가 그대로 발음됨.

근거: scenarios-P-pronunciation.md §2 「이 실측의 한계」가 p1m 을 「원어민 음성이 다른 단어를 정확히 발음한 것 — 한국인이 /θ/를 /s/로 낼 때의 중간값·불안정성은 재현하지 않는다」로 적었음. Sohee 는 한국어 원어민 여성 화자라 그 한계를 좁힘.

병목과의 연결: TASK-86·87 이 발음 코칭률 6.1%(33회 2건)로 막혀 있음. 지금 픽스처는 두 극단만 있음 — p1m 은 ASR 이 원문으로 복원(신호 소실) · p1k 는 한글 전사로 agent 가 unclear 회피(코칭 아님). 「알아들을 만한데 그 소리가 틀린」 중간 지대가 비어 있고 그것이 코칭이 나는 조건일 수 있음.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 한국인 학습자 전형 오류 음소를 축으로 케이스를 정의하고 케이스별 판정선을 시나리오 문서에 적는다 — 오류 음소 종류·오류 밀도·문장 도메인 세 축을 가른다
- [x] #2 Qwen3-TTS 로 픽스처를 만들고 길이를 먼저 재서 빈 파일이 아님을 확인한다 (16kHz·16bit·mono 규격)
- [x] #3 ⛔ 기존 p1a·p1m·p1k·p2a·p2m·p2k 를 덮지 않는다 — 덮으면 통제 대조를 다시 만들 수 없다 (TTS 는 표본마다 출력이 갈린다)
- [x] #4 어제 반증된 용도(억양판 대체)와 이번 용도(음소 치환판 보강)의 구별을 문서에 적는다 — 같은 도구의 두 용도가 섞여 판정이 뒤집힌 것으로 읽히지 않게 한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-10 완료. 시나리오 정본은 tests/harness/scenarios-PQ-qwen-phoneme.md 임 (케이스 12개 · 판정선 4축 · 가설 3개와 반증 조건 · 뺀 케이스와 이유).

픽스처 12개를 tests/harness/fixtures/voice/pq01~pq12.wav 로 생성했음. 전수 16000Hz·1ch·Int16 이고 길이 3.28~5.28초 — 빈 파일 0건(직접 afinfo 로 확인).

⛔ 기존 픽스처 열 개(p1a·p1k·p1m·p2a·p2k·p2m·p1q·p1qk·p2q·p2qk)의 mtime 이 8월 26일·9월 9일 그대로임 — 덮이지 않았음을 ls 로 확인했음.

축 구별을 scenarios-P-pronunciation.md §3.1 에 4번 항목으로 못박았음 — 그 절이 「Qwen 을 쓰지 않는다」로 읽히던 것을 「억양판 축에서만 반증됐고 음소 치환판 축은 PQ 가 소유함」으로 갈랐음. 이 리포의 지배 실패 모드(본문을 고치고 그것을 설명하는 문장을 안 고침) 방어임.

생성 실행체는 /tmp/gen_pq_fixtures.sh 임 — 존재 검사로 덮어쓰기를 구조적으로 막음.
<!-- SECTION:NOTES:END -->
