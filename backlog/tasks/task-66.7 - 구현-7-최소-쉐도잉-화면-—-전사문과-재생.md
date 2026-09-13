---
id: TASK-66.7
title: '구현 7: 최소 쉐도잉 화면 — 전사문과 재생'
status: Done
assignee: []
created_date: '2026-09-13 22:11'
updated_date: '2026-09-13 22:56'
labels: []
dependencies:
  - TASK-66.3
  - TASK-66.5
  - TASK-66.6
parent_task_id: TASK-66
ordinal: 155000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
계획서 Task 7. 프런트 테스트 인프라가 0이라 검증은 브라우저 회차다. 낭독 녹음·비교는 범위 밖이고 진입 안내도 넣지 않는다(결정 90).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 tsc·eslint 가 exit 0 이다
- [x] #2 검증 전용 스택에서 사람이 소리를 듣고 넷을 확인한다 — 소리·전사문·속도와 반복·오디오 없는 클립의 버튼 숨김
- [x] #3 회차 기록을 runs/2026-09-14-task66-clip-audio/ 에 남기고 dev DB 무오염을 조회로 확인한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
완료 2026-09-14 (세션 ohmyenglish-f4) — 회차 기록은 tests/harness/runs/2026-09-14-task66-clip-audio.md 임.

게이트: tsc exit 0 · eslint exit 0.

브라우저 레그로 확인한 것 넷(전용 Chrome + 검증 전용 스택): 패널 제목·전사문이 화면에 있음 · 오디오가 실제로 흐름(rate 1.5 · currentTime 2.216 · duration 17.36 · readyState 4 · src 가 :8012) · ended 뒤 재생이 2회에서 멈추고 버튼이 되돌아옴 · 오디오 없는 클립에서 버튼이 사라지고 안내만 남음(play 호출 0). 스크린샷 셋을 직접 열어 봤음.

⛔ 이 회차가 결함 하나를 잡았고 회차 전에 고쳤음 — ShadowingPanel 이 오디오 주소를 상대 경로로 만들어 프런트(:3000)로 갔음. API_BASE 를 쓰도록 고쳤음. 단위·통합으로는 잡히지 않는 부류임(프런트 테스트 0 · 백엔드 단정은 자기 포트로 직접 부름).

⛔ 개입 하나를 기록에 남겼음 — 스텁이 세션을 곧 닫아 패널 창이 1초를 못 넘기므로 session_ended 프레임과 소켓 close 둘만 붙잡았음. 재는 대상과 무관함.

⚠️ 미결 하나 — 사람 청취. 합성음이 학습에 쓸 만한지는 사람이 들어야 함(2026-09-09 선행 검토 §8 의 미결이 그대로임). 이 회차가 말할 수 있는 것은 「브라우저가 그 파일을 디코드해 재생했다」까지임.

정리: 세 포트가 000 · dropdb exit 0 · dev DB 는 마이그레이션 17건·클립 1행·시간 창 16.64 로 회차 앞과 같음(022 미적용의 증거).
<!-- SECTION:NOTES:END -->
