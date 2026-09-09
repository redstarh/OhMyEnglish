---
id: TASK-59
title: 발음 픽스처를 Qwen3-TTS 로 다시 만든다 — say 로는 발음 오류가 재현되지 않는다
status: Done
assignee: []
created_date: '2026-09-09 13:04'
updated_date: '2026-09-09 13:50'
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
- [x] #1 Qwen3-TTS(Apache-2.0)를 임시 venv 로 격리해 설치한다 — ⛔ 프로젝트 의존성에 넣지 않는다(가중치 2.3GB 를 게이트·배포에 얹지 않는다)
- [x] #2 한국어 원어민 화자로 영어 문장을 읽혀 p1k·p2k 를 다시 만들고 16kHz mono WAV 로 변환한다
- [x] #3 ⛔ 새 음원의 길이를 먼저 재고 그 값을 단정에 넣는다 — 미설치 음성은 0.016초 빈 파일을 만들고 그것을 앱 결함으로 오인한 사례가 그 리포에 있다
- [x] #4 H1 을 판정한다 — 같은 문장·같은 주입 경로로 P4 를 다시 재서 전사가 영어로 정확히 복원되는지 본다. 재현되지 않으면 「도구 품질이 원인이 아니다」로 닫고 그 사실을 적는다
- [x] #5 판정 결과를 회차 기록에 남기고 scenarios-P-pronunciation.md 의 음원 생성 절차를 갱신한다 — say 를 쓰던 서술을 고친다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-09 완료 — H1 반증. 판정 정본은 tests/harness/runs/2026-09-09-task59-qwen-tts.md 다.

결론: 도구 품질이 우리 픽스처의 병목이 아니다. 이 목적(강한 한국어 억양 재현)에는 say -v Yuna 가 Qwen3-TTS 보다 낫다 — 정반대 방향이 나왔다.

Nova 왕복 6회 실측(spike_nova_protocol.py 직결 · 앱 경로 아님 · DB 세션 0):
- p1q(Qwen Sohee·lang en, 4.88s) → 'i think i found three very useful videos' (영어 정확)
- p1qk(Qwen Sohee·lang ko, 3.92s) → 'i think i found three very useful videos.' (영어 정확)
- p1k(기존 say -v Yuna, 3.05s) → '아이싱크 아이파운드 쓰리 베리 유스풀 비디오즈' + agent 가 unclear 로 되묻음
- p2q(4.96s) → 'i finished the report and shared the results with my team.' (영어 정확)
- p2qk(5.36s) → 같음 (영어 정확)
- p2k(기존 say, 3.79s) → '아이피니시트더리포트엔쉐어드더리절치위드마이팀' + agent 가 unclear

F2 가 놓친 것은 부호 반전이다. 참고 리포의 수치는 틀리지 않았고 그쪽은 전사가 원문과 일치하는 것을 좋다고 세는데 P계층은 전사가 무너지는 것을 관측한다. 같은 표를 정반대로 읽어야 한다.

AC#2 의 이행 방식을 바꿨다 — p1k·p2k 를 덮지 않고 p1q·p1qk·p2q·p2qk 로 신설했다. 근거: 덮으면 위 3·6행의 통제 대조를 다시 만들 수 없고 TTS 는 표본마다 출력이 갈려 명령만으로는 같은 음원을 되찾지 못한다. AC 의 목적(한국어 화자 음원을 확보해 H1 을 판정)은 그대로 달성했다.

함께 확정한 것 — 5차수 P4 미재현은 픽스처 탓이 아니다. 같은 p1k.wav 가 스파이크 경로에서는 지금도 한글로 전사된다. 갈라지는 것은 앱 경로이고 원인은 미확정이다 → TASK-65 로 등록했다.

TASK-63 에 넘긴 증거 — Qwen Sohee 의 영어는 Nova ASR 이 4/4 원문과 일치했다(기계 전사 기준의 명료도). 학습자가 따라 할 원어민 발화로서의 적합성은 판정하지 않았다.

원자료 6건: .harness/evidence/task59/*.json (git 추적 밖)
<!-- SECTION:NOTES:END -->
