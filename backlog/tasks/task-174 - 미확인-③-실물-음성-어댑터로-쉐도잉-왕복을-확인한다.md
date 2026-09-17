---
id: TASK-174
title: '미확인 ③: 실물 음성 어댑터로 쉐도잉 왕복을 확인한다'
status: Done
assignee: []
created_date: '2026-09-17 22:06'
updated_date: '2026-09-17 22:48'
labels: []
dependencies: []
ordinal: 235000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
지금 백엔드가 VOICE_ADAPTER=stub 이라 실물 음성 경로가 이 세션에서 검증되지 않았다. 영상에서 담은 문장으로 쉐도잉을 열어 실물 왕복이 되는지 본다. 이전 절차는 handoff/backup/2026-09-18/HANDOFF-0328.md 85행이 가리키는 형태다 — 다른 포트에 VOICE_ADAPTER=nova 로 띄운다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 낭독 프레임이 어댑터로 가지 않고 파일로 가는 것을 코드에서 직접 확인함
- [x] #2 실물 Nova 로 쉐도잉 세션 진입이 이미 검증된 회차를 원장에서 직접 확인함
- [x] #3 stub 어댑터로는 낭독 턴 검증이 불가능한 이유를 실측으로 확정함
- [x] #4 실물로 돌리는 데 필요한 조건과 막힌 자리를 노트에 적고 실행을 별 태스크로 올림
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 실측 2026-09-18 — 「실물 음성 왕복」이 이 갈래에서 무엇을 뜻하는지 확정함

### 1. 낭독 프레임은 어댑터로 가지 않음 (코드 직접 확인)

`app/backend/app/audio_gateway/session.py` `_forward_audio` — 낭독 턴이 열려 있으면
`_write_recording_frame(turn, frame)` 으로 **파일에 쓰고 return** 하며 `self._adapter.send_audio` 에
도달하지 않음. 주석이 근거를 적어 둠: Nova 로 보내면 그 전사가 `learning` 발화로 저장되어 학습자가
짓지 않은 문장이 오류 패턴을 오염시킴.

### 2. 실물 Nova 쉐도잉 세션 진입은 이미 검증됨

`TASK-61.8` 노트 — 2026-09-16 · `:8012` · `VOICE_ADAPTER=nova` · `WORKER_ENABLED=false` ·
검증 전용 DB. 음성 명령으로 세션을 갈아 열어 `mode=shadowing` 반영과 쉐도잉 클립까지 실린 것을
확인함(ARM-EN PASS). ⇒ **세션 진입은 미검증이 아님.**

### 3. ⛔ stub 으로는 낭독 턴을 열 수 없음 — 이 회차가 확정한 것

가짜 마이크 스트림(`AudioContext` → `MediaStreamDestination`)으로 `getUserMedia` 를 갈아 끼워
실제 앱 경로를 태웠음(`__gumCalled`=1 로 확인). 결과:

| 관측 | 값 |
|---|---|
| 만들어진 세션 | `f8f1f64b` · `mode=shadowing` · `learning_source=additional` · 클립 실림 |
| 세션 수명 | `started_at` 22:46:56.535 → `ended_at` .568 — **33ms** |
| `utterances` | 164 → 170 (6건 늘었고 **전부 `learning`**) |
| `shadowing_recording` 발화 | **0건** (이 DB 에서 한 번도 없음) |

⇒ **stub 어댑터는 쉐도잉 세션을 즉시 완료시켜 낭독 턴이 열릴 틈이 없음.** 낭독 프레임 자체는 Nova 를
타지 않지만 **낭독 턴이 열리기까지의 대화가 Nova 를 탐** — 그래서 stub 으로 대신할 수 없음.
⚠️ 이 회차에서 내 판단이 한 번 뒤집혔음: 「낭독은 어댑터를 안 타니 stub 으로 충분하다」로 시작했고
위 33ms 관측이 그것을 반증했음. **지난 세션의 「stub 이라 미검증」이 옳았음.**

### 4. 실물로 돌리는 데 필요한 것

별 포트 백엔드(`VOICE_ADAPTER=nova WORKER_ENABLED=false`) · 프론트가 그 포트를 보게 하는 재배선 ·
Bedrock 비용 · 공유 dev DB 오염을 피하려면 검증 전용 DB(`H-BC`). ⛔ 공유 스택을 건드리므로 사용자
승인이 선행되어야 함 ⇒ 실행을 별 태스크로 올림.
<!-- SECTION:NOTES:END -->
