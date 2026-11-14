# 회차 b16 — 화면 탭 (`TASK-316.1`)

먼저 `BRIEF-common.md` 를 읽음. 브라우저 포트는 **9401**, 쓰기 폴더는 `runs/2026-11-14-b16/screens/`.

## 할 일 — 현재 화면의 스토리보드를 새로 만들고 배치를 판정함

기존 보드 `docs/ux/2026-11-01-user-scenarios/index.html`(e2e86c0 기준 · 10장면 70단계)는 낡았음. 그 뒤 바뀐 것: 메뉴가 Home 하나 · Continue your path 의 Day 줄이 홈 카드에서 연습을 엶 · View all 이 목록을 펼침 · Grammar course 가 홈 카드를 엶 · Your progress 에 History/Weekly report 버튼 · 이동 링크가 모두 버튼 모양 · 문장 연습의 Listen/Slow 제거. 설계서 `docs/design/2026-11-01-v0-home-redesign-design.md` §3 이 정본임. 먼저 옛 보드와 설계서를 읽고 장면 목록을 지금 화면에 맞게 다시 정함.

1. 장면마다 1400×1000 과 390×844 두 폭으로 단계별 스크린샷을 찍음. 최소 장면:
   홈 대기 · 홈 문장 연습(Start speaking) · Day 2 를 고른 연습 · View all 펼침 · 코치 세션(Free talk 1개) · 세션 실패 화면(마이크 거부) · 기록 `/history` · 주간 `/history/weekly` · 결과 `/results/<id>`(격리 DB 의 완료 세션) · 코스 목록 `/course` · Day 화면 `/course/1` · 영상 목록 `/videos` · 영상 화면.
2. 화면마다 판정함: 가로 넘침 없음(`scrollWidth <= clientWidth`) · 잘린 글자 없음 · 홈 카드 높이(대기와 연습이 같음, 1400 약 433 px · 390 약 490 px) · Your progress 카드가 넓은 화면에서 홈 카드와 같은 높이 · 섹션 라벨 글꼴 통일(12px · 700 · 대문자) · UI 상수에서 온 한국어 없음(백엔드 콘텐츠의 한국어는 출처를 적고 결함으로 보지 않음).
3. 스토리보드 HTML 을 `screens/storyboard/index.html` 로 만듦 — 장면별 단계 카드(번호 · 한 줄 설명 · 1400/390 썸네일 · 클릭하면 원본). 이미지는 `screens/storyboard/shots/` 에 jpg 로 둠. 외부 파일 없이 열리게 함.

결과는 `screens/result.md`, 끝나면 `screens/DONE`.
