---
id: TASK-59
title: 발음 픽스처를 Qwen3-TTS 로 다시 만든다 — say 로는 발음 오류가 재현되지 않는다
status: To Do
assignee: []
created_date: '2026-09-09 13:04'
labels: []
dependencies: []
ordinal: 62000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
우리 발음 테스트 음원은 macOS say(-v Samantha 정확판 · -v Yuna 한국식 억양판)로 만들었다(tests/harness/scenarios-P-pronunciation.md:83~85). 그런데 5차수에서 P4(p1k)가 한글이 아니라 영어로 정확히 전사돼 발음 오류가 재현되지 않았고 P2(p2m)는 왜곡됐으며 TASK-13 이 「합성 픽스처로 표본을 늘릴 수 없음」을 통제 대조로 확정했다. pronunciation_attempts 는 4행에 멈춰 있고 전부 signal_source=nova_tool 이며 korean_transcript 신호는 0행이다. ⛔ realtime-meeting 이 바로 그 say -v Yuna 가 열등하다고 실측했다 — 같은 문장 3개에서 say 는 1문장 어긋남 · Qwen3-TTS 는 3/3 일치. 즉 우리 픽스처가 막힌 원인의 일부가 도구 품질일 수 있다. 근거 정본은 docs/design/2026-09-09-realtime-meeting-fit-gap.md 의 F2 와 H1 이다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Qwen3-TTS(Apache-2.0)를 임시 venv 로 격리해 설치한다 — ⛔ 프로젝트 의존성에 넣지 않는다(가중치 2.3GB 를 게이트·배포에 얹지 않는다)
- [ ] #2 한국어 원어민 화자로 영어 문장을 읽혀 p1k·p2k 를 다시 만들고 16kHz mono WAV 로 변환한다
- [ ] #3 ⛔ 새 음원의 길이를 먼저 재고 그 값을 단정에 넣는다 — 미설치 음성은 0.016초 빈 파일을 만들고 그것을 앱 결함으로 오인한 사례가 그 리포에 있다
- [ ] #4 H1 을 판정한다 — 같은 문장·같은 주입 경로로 P4 를 다시 재서 전사가 영어로 정확히 복원되는지 본다. 재현되지 않으면 「도구 품질이 원인이 아니다」로 닫고 그 사실을 적는다
- [ ] #5 판정 결과를 회차 기록에 남기고 scenarios-P-pronunciation.md 의 음원 생성 절차를 갱신한다 — say 를 쓰던 서술을 고친다
<!-- AC:END -->
