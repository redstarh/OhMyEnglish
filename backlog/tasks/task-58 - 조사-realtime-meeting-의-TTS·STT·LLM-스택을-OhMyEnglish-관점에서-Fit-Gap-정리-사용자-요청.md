---
id: TASK-58
title: '조사: realtime-meeting 의 TTS·STT·LLM 스택을 OhMyEnglish 관점에서 Fit/Gap 정리 (사용자 요청)'
status: Done
assignee: []
created_date: '2026-09-09 09:04'
updated_date: '2026-09-09 12:58'
labels: []
dependencies: []
ordinal: 61000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자가 /Users/redstar/Downloads/realtime-meeting 을 요약하고 TTS·STT·Qwen 3 한국어/영어 발음 관점에서 OhMyEnglish 에 적용할 부분을 Fit/Gap 으로 보고하라고 지시했다(2026-09-09). 분석 트랙 — 코드 변경 없음. ⛔ 결론을 내기 전에 그 리포의 결정 정본(docs/decisions)과 기술 선택 근거(docs/design/tech-stack.md)를 직접 읽는다. 남의 README 요약을 근거로 쓰지 않는다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 realtime-meeting 의 목적·아키텍처·기술 스택을 요약한다 — 직접 읽은 파일을 근거로 든다
- [x] #2 TTS·STT·Qwen 3·발음 처리의 실재 여부를 확인한다. 없으면 없다고 적고 추측으로 채우지 않는다
- [x] #3 OhMyEnglish 에 적용 가능한 것(Fit)과 맞지 않는 것(Gap)을 갈라 근거와 함께 적는다 — 두 앱의 목적 차이를 먼저 못박는다
- [x] #4 산출물을 docs/design/ 에 남기고 사용자에게 보고한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-09 완료. 산출물은 docs/design/2026-09-09-realtime-meeting-fit-gap.md 다.

핵심 넷:
① TTS 는 그 프로젝트의 제품 기능이 아니라 테스트 음원 생성 도구다. Qwen3-TTS(Apache-2.0 · 로컬 MLX · 화자 9종 · 0.6B/2.3GB/RTF 0.92x)를 임시 venv 로 격리해 썼고 say -v Yuna 보다 전사 정확도가 낫다는 실측(3문장 중 1문장 어긋남 대 3/3 일치)이 있다.
② 발음 평가는 없다(「발음」 0건 · pronunciation 2건은 Transcribe 의 item type 이다). 우리 고유 영역이다.
③ BlackHole 은 불필요하다 — 코드로 확정했다. 하네스가 getUserMedia 를 합성 스트림으로 대체해 마이크·스피커·시스템 오디오를 거치지 않는다(scenarios-N-real-voice.md:154~163).
④ ⛔ prompt cache 를 「가장 큰 Fit」으로 적었다가 조사 중에 반증해 뒤집었다. 고정 프리픽스가 2,469자(≈617~1,646 토큰)로 최소 4096 에 못 미치고 그쪽이 실패를 관측한 2,426 토큰보다도 짧다. 붙이려면 품질과 무관하게 프롬프트를 팽창시켜야 하고 그러면 캐시 읽기 지연을 함께 산다. 대신 실질적 빈자리를 찾았다 — 우리는 토큰을 어디에도 기록하지 않아 비용 개선의 기준선이 없다(H4).

가장 값어치 있는 Fit 은 F2(Qwen3-TTS 로 발음 픽스처 재생성)다. 우리 픽스처가 say -v Yuna 로 만들어졌고(scenarios-P-pronunciation.md:83~85) 5차수에서 P4(p1k)가 「영어로 정확히 전사」돼 오류가 재현되지 않았으며 TASK-13 이 「합성 픽스처로 늘릴 수 없음」을 통제 대조로 확정했다. 그 열등한 도구가 정확히 우리가 쓰는 것이다. ⚠️ 다만 Qwen 이 「의도한 발음 오류」를 낼 수 있다는 증거는 없어 H1 로 남겼다.

2026-09-09 후속 — 사용자 요청으로 사람용 HTML 판본을 만들었다: docs/ops/2026-09-09-realtime-meeting-fit-gap.html. 약어와 파일 이름을 풀어 쓰고 판정을 색으로 갈랐다(있음/없음/기능 아님/열림/닫힘).

검증: 브라우저로 띄워 렌더를 확인했다(표·색상·강조 박스 정상). ⚠️ 4번 절(비용 절감 판단을 뒤집은 부분)은 스크린샷 캡처가 스크롤 위치를 완전히 따르지 않아 화면으로 직접 보지 못했다 — 대신 HTML 구조를 기계로 검증했다(태그 짝 오류 0 · 닫히지 않은 태그 0 · CSS 에 없는 클래스 0 · 4번 절 1,305자에 강조박스 2개와 표 1개가 실재). 한국어 검사도 돌려 통과했다(의존명사·반말 0건 · 뜻이 갈리는 짝 6건을 문맥으로 읽어 전부 맞음).

md 정본은 그대로 두고 HTML 이 그것을 가리킨다 — 두 곳에 사실을 쓰지 않았다.
<!-- SECTION:NOTES:END -->
