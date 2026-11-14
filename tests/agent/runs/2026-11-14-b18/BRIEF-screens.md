# 회차 b18 — 화면 탭 (`TASK-330`)

먼저 `BRIEF-common.md` 를 읽음. 브라우저 포트는 **9461**, 쓰기 폴더는 `runs/2026-11-14-b18/screens/`.

## 할 일 — 고친 뒤의 현재 화면으로 스토리보드를 새로 만들고 흐름·논리를 다시 점검함

앞 회차 보드 `docs/ux/2026-11-14-user-scenarios/index.html`(b16 · 고치기 전)과 보고서
`docs/ux/2026-11-14-ux-flow-review/index.html` 를 먼저 읽음. 그 뒤 바뀐 것(정본은 설계서
`docs/design/2026-11-01-v0-home-redesign-design.md` §3 과 `docs/design/2026-11-14-live-readback-transcript-design.md`):
빠른 카드 · Grammar course 제거 · `/course` · `/course/<day>` 는 홈으로 리다이렉트 · 모든 이동·실행 버튼이 `omy-button` ·
문장 연습의 Listen/Slow 제거 · 「← Previous」 · 말하는 동안 실시간 표시(Web Speech) · 말한 내용이 문장과 같은 글자 ·
KO 켜면 문장 아래 한국어 번역 · Your progress 의 「Last week · 기간」 · 주간 리포트 제목의 기간 · 기록 날짜 줄이 그날 결과로 감 ·
결과 화면 「You finished on <날짜>」 · 발화 없는 세션은 「We didn't hear you this time」.

1. 장면마다 1400×1000 과 390×844 두 폭으로 단계별 스크린샷을 찍음. 최소 장면:
   홈 대기 · 홈 문장 연습(KO 끔 · KO 켬) · Day 2 를 고른 연습 · View all 펼침 · 코치 세션(Free talk 1개) ·
   기록 `/history`(날짜 줄 → 결과) · 주간 `/history/weekly` · 결과(완료 세션 · 발화 없는 세션) · `/course` 리다이렉트 · 영상 목록 · 영상 화면.
   ⚠️ 실시간 표시는 가짜 `SpeechRecognition` 을 `addInitScript` 로 심어 보임 — 참고 `runs/2026-11-14-b17/live.mjs` 의 `installFakes`.
   시험 Chrome 의 진짜 인식기는 가짜 오디오를 전사하지 않음(설계서 §2-2).
2. 화면마다 판정함: 가로 넘침 없음(`body.scrollWidth` · 글자 상자 검사 — b16 실측대로 문서 `scrollWidth` 는 못 씀) ·
   잘린 글자 없음 · 홈 카드 높이(대기 = 연습 · KO 끔 약 514 px · KO 켬 약 558 px) · 섹션 라벨 글꼴 통일 ·
   UI 상수에서 온 한국어 없음(번역 줄 · 단원 이름 · 분석 콘텐츠의 한국어는 출처를 적고 결함으로 보지 않음).
3. 「흐름·논리 점검」 절 — 장면마다 사람 사용자 입장에서 ① 다음 할 일이 화면만으로 보이는가 ② 버튼·문구가 하는 일이 이름과 맞는가
   ③ 막다른 곳 · 되돌아갈 길 없음 · 같은 일을 하는 두 입구가 있는가. b16 보고서의 항목이 고쳐졌는지도 하나씩 대조함.
   문제마다 근거 스크린샷 경로와 보완안 한 줄.
4. 스토리보드 HTML 을 `screens/storyboard/index.html` 로 만듦(b16 과 같은 형식 · 이미지는 `screens/storyboard/shots/*.jpg`).

결과는 `screens/result.md`, 끝나면 `screens/DONE`.
