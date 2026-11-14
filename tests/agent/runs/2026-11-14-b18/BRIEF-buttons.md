# 회차 b18 — 버튼 탭 (`TASK-330`)

먼저 `BRIEF-common.md` 를 읽음. 브라우저 포트는 **9462**, 쓰기 폴더는 `runs/2026-11-14-b18/buttons/`.

## 할 일 — 고친 뒤 모든 화면의 버튼·링크를 다시 눌러 동작과 모양을 판정함

정본: 설계서 `docs/design/2026-11-01-v0-home-redesign-design.md` §3 (TASK-308~329 절) · 실시간 표시 설계서
`docs/design/2026-11-14-live-readback-transcript-design.md` · 소스(`app/frontend/**` 읽기만). 앞 회차 결과
`runs/2026-11-14-b16/buttons/result.md` 의 결함 D1~D4 가 고쳐졌는지도 대조함.

1. 화면마다(홈 · 문장 연습 · `/history` · `/history/weekly` · `/results/<id>` · `/course` · `/course/1` · `/videos` · 영상 화면 · 세션 화면) 보이는 버튼·링크 목록(testid · 문구 · 태그 · href).
2. 하나씩 눌러 기대 동작을 판정함. 특히:
   - 홈: Start speaking(창 스크롤 그대로 · 1400×700 에서도) · Close · Day 줄 · View all ↔ Show less · More practice(Grammar course 없음) · History →/Weekly report →(파란 바탕) · 390 아래쪽 입구는 카드로 스크롤.
   - 문장 연습: KO 켬/끔(문장 아래 번역 · 새로 고친 뒤에도 기억) · Auto/Manual · Start → ① Listen → ② Say it(실시간 줄) → ③ Check → 판정 · Try again · ← Previous / Next → · Finish Day. 가짜 `SpeechRecognition`(참고 `runs/2026-11-14-b17/live.mjs`)로 돌리고 판정 요청 `**/attempts/text` 와 진도 저장은 `page.route` 로 막아도 됨(격리 DB 라 막지 않아도 됨 — 어느 쪽인지 적음).
   - 말 없음: Try 가 늘지 않고 「I couldn't hear you」.
   - 기록 날짜 줄 → 결과(세션 하나 · 여럿) · 주간 ← Home · ← History · 결과 ← Home · History → · Start again →(발화 없는 세션) · 영상 화면 Mark a hard part · End the hard part here · Cancel.
   - `/course` · `/course/1` 은 홈으로 리다이렉트.
   - 세션: End lesson(testid `session-end`) → 결과 · 세션 중 다른 이동이 잠김.
3. 모양 판정: 이동·실행 버튼은 `omy-button`(36 px 안팎 · 13.6 px · 앞으로 가는 이동만 파란 바탕). KO · Auto · Manual 은 같은 모양의 전환 묶음.

결과는 `buttons/result.md`(버튼 목록 · 동작 판정 · b16 결함 대조 · 새 결함), 끝나면 `buttons/DONE`.
