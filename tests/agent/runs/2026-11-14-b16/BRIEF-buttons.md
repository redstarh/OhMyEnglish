# 회차 b16 — 버튼 탭 (`TASK-316.2`)

먼저 `BRIEF-common.md` 를 읽음. 브라우저 포트는 **9402**, 쓰기 폴더는 `runs/2026-11-14-b16/buttons/`.

## 할 일 — 모든 화면의 버튼·링크를 실제로 눌러 동작과 모양을 판정함

정본: 설계서 `docs/design/2026-11-01-v0-home-redesign-design.md` §3(특히 TASK-308~318 절)과 소스(`app/frontend/app/**` · `app/frontend/components/**` 읽기만).

1. 화면마다(홈 · `/history` · `/history/weekly` · `/results/<id>` · `/course` · `/course/1` · `/videos` · 영상 화면 · 세션 실패 화면) 보이는 버튼·링크를 모두 모아 목록을 만듦(testid · 문구 · 태그 · href).
2. 하나씩 눌러 기대 동작을 판정함. 예:
   - 홈: Start speaking → 홈 카드에 문장 연습 · Close → 대기 · Day 줄 → 주소 `/` 그대로 그 Day 연습 · 고른 줄 강조 · View all ↔ Show less(6↔2) · Grammar course → 현재 Day 연습 · Free talk 등 → 코치 세션 · 세션 중 다른 이동이 잠김 · End lesson → 결과로 · History/Weekly report → 그 화면.
   - 문장 연습: Auto/Manual · Start → 단계(① Listen → ② Say it → ③ Check) · Try again · Back/Next · 마지막 문장의 Finish Day. Listen/Slow 버튼이 없어야 함.
   - 각 화면의 ← Home · ← History · History → · Weekly report → · ← Back · ← Videos 등.
   - 390 폭에서 아래쪽 입구(Day 줄 · More practice)를 누르면 화면 밖 홈 카드로 스크롤되고, Start speaking 은 창을 움직이지 않음.
3. 모양 판정: 이동·실행 버튼은 홈 기준 `omy-button`(높이 36px · 글자 13.6px · 앞으로 가는 이동만 파란 바탕). 어긋나는 버튼을 목록으로 남김.

결과는 `buttons/result.md`(버튼 목록 표 + 동작 판정 표 + 결함), 끝나면 `buttons/DONE`.
