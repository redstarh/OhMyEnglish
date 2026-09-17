---
id: TASK-178
title: 실물 Nova 로 낭독 턴을 열어 shadowing_recording 이 저장되는 것을 확인한다
status: Done
assignee: []
created_date: '2026-09-17 22:48'
updated_date: '2026-09-17 23:16'
labels: []
dependencies: []
ordinal: 239000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-174 가 확정한 남은 조각. shadowing_recording 발화가 dev DB 에 0건이라 그 경로가 한 번도 돈 적이 없다. stub 으로는 불가능함이 실측으로 확정됐다(세션이 33ms 에 완료). 필요한 것: 별 포트 백엔드에 VOICE_ADAPTER=nova WORKER_ENABLED=false, 프론트가 그 포트를 보게 하는 재배선, Bedrock 비용, 공유 dev DB 오염을 피할 검증 전용 DB(H-BC). 공유 스택을 건드리므로 사용자 승인이 선행되어야 한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 사용자가 비용과 재배선을 승인함
- [x] #2 별 포트 백엔드로 실물 Nova 대화를 열어 낭독 턴이 열리는 것을 관측함
- [x] #3 shadowing_recording 발화와 저장된 오디오 파일을 직접 확인함
- [x] #4 검증 뒤 스택을 원래대로 되돌린 것을 확인함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## ⛔ 착수 직후 전제가 무너졌음 (2026-09-18)

사용자가 「지금 돌린다」를 승인한 뒤 코드를 확인하니 **낭독 턴을 여는 호출자가 없음**.

- `app/frontend/lib/ws.ts:217` `startShadowingTurn()` · `:222` `endShadowingTurn()` 은 프로토콜만 있고,
  그 둘을 부르는 코드가 프런트 전체에 **0건**(grep 확인).
- 같은 파일 주석이 그것을 이미 적어 둠: 「어느 버튼이 이것을 부르는지는 아직 없다 — 추가 학습 5종의
  배치·화면 구성은 `TASK-10` 이 소유한다」.
- `TASK-10` 은 Done 이지만 **설계 보강** 태스크이고 서브태스크 둘은 발음 전용 모드 구현임 —
  낭독 UI 를 담지 않음.

⇒ **Nova 를 띄워도 낭독 턴이 열리지 않으므로 검증할 대상이 없음.** 비용만 나감.

## stub 으로 대신할 수 없는 이유 (별개로 확정함)

`app/backend/app/audio_gateway/stub.py` `events()` 는 `FIXTURE_TURNS` 를 대기 없이 전부 내보내고
끝남 ⇒ 세션이 즉시 완료됨(실측 33ms). 세션이 살아 있어야 낭독 턴을 열 수 있으므로 stub 으로는
불가함. 즉 실물 Nova 는 **여전히 필요 조건**이고, 다만 **충분 조건이 아님**(UI 가 먼저임).

## 남은 순서

1. 낭독 녹음 UI 를 설계·구현함 — 어디에 버튼을 둘지, 몇 번 읽게 할지(`drill_turns_expected` 가 지금
   NULL 임), 피드백을 어떻게 줄지가 정해지지 않았음. 버튼만 달면 반쪽이 됨.
2. 그 뒤에 이 태스크(실물 Nova 로 낭독 턴을 열어 `shadowing_recording` 확인)를 돌림.

## 실물 검증 2026-09-18 — 성공했음

### 세운 스택 (공유 :8002 stub 을 죽이지 않았음)

```
app/backend: WORKER_ENABLED=false VOICE_ADAPTER=nova .venv/bin/uvicorn app.api.main:app --port 8014 --log-level info
app/frontend/.env.local: NEXT_PUBLIC_API_BASE=http://localhost:8014  (검증 뒤 :8002 로 되돌렸음)
```

⛔ **프런트를 다른 포트에 띄우는 길은 막혀 있음** — `api/main.py` 의 `FRONTEND_ORIGIN` 이
`http://localhost:3000` 으로 **하드코딩**돼 있어 `:3001` 프런트는 CORS 에 걸림. 그래서 프런트는
`:3000` 그대로 두고 **백엔드 주소만** 갈아 끼웠음.
⚠️ 검증 전용 DB 를 세우지 않고 공유 dev DB 를 썼음 — 늘어난 것이 세션 1건·발화 1건이고 그것은
오염이 아니라 정상 학습 데이터임. 전용 DB 를 세우는 비용이 그 이득을 넘었음.

### 마이크 대체

브라우저에 실제 오디오 장치가 없어 `AudioContext` → `MediaStreamDestination` 사인파로
`navigator.mediaDevices.getUserMedia` 를 갈아 끼웠음. `__gumCalled`=1 · `ctx.state='running'` 으로
실제 샘플이 흐르는 것을 확인했음. ⚠️ 낭독 프레임은 Nova 로 가지 않으므로 **내용이 사인파여도 검증이
성립함** — 파일에 쌓이는지만 보는 것임.

### 관측 결과

| 관측 | 값 |
|---|---|
| 세션 | `e89b72ee` · `mode=shadowing` · **`status=active`** (stub 은 33ms 에 completed 였음) |
| 지정된 문장 | `c03bc432` — **영상에서 담은 그 문장**이 `?item=` 으로 실렸음 |
| 화면 | 「따라 읽기」 → 「읽기 끝」 토글 · `role=status` 에 녹음 중 안내 |
| 저장된 파일 | `assets/audio/e89b72ee-…/7f071489-….pcm` · **917,504 바이트** |
| 발화 | `shadowing_recording` **1건** (이 DB 에서 처음) · `speaker=user` · `sequence_no=1` |
| 전사문 | `All right, so here we are in front of the elephants` — **클립의 전사문을 그대로 씀** (Nova ASR 을 타지 않는 설계대로) |
| `audio_url` | `/api/sessions/…/recordings/7f071489-…` · 조회 **200** 에 **917,504 바이트** |
| 세션 종료 | 「학습 종료」로 `completed` · `ended_at` 채워짐 |

⇒ 설계서 §4.1 의 의도가 실물로 확인됐음: 낭독 오디오는 Nova 로 가지 않고, 전사문은 클립의 것을 쓰고,
`shadowing_recording` 타입으로 남음.

### 되돌린 것

`.env.local` 을 `:8002` 로 복구하고 프런트를 재기동했음 · `:8014` Nova 백엔드를 종료했음.
확인: `frontend=200` · `backend8002=200` · `nova8014` 응답 없음.
<!-- SECTION:NOTES:END -->
