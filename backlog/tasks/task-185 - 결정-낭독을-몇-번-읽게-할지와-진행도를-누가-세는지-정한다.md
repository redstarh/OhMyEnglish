---
id: TASK-185
title: '결정: 낭독을 몇 번 읽게 할지와 진행도를 누가 세는지 정한다'
status: Done
assignee: []
created_date: '2026-09-18 02:28'
updated_date: '2026-09-18 02:31'
labels: []
dependencies: []
ordinal: 246000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
지금은 한 번 읽고 끝이라 연습량이 학습자 재량이다. 반복 횟수의 정본을 어디 둘지(Settings vs 고정값)와 회차를 서버가 셀지 화면이 셀지 정한다. 화면이 세면 새로 고침에 잃고, 서버가 세면 shadowing_recording 발화 수로 복원된다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 반복 횟수의 정본 위치를 정하고 근거를 적는다
- [x] #2 회차를 세는 주체를 정하고 근거를 적는다
- [x] #3 결정 129 를 지시 대장에 등재한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 결정 129 (2026-09-18)

⛔ **먼저 낡은 서술을 정정했음** — `config.py` 의 `shadowing_repeat_count` 주석이 *"코치 지시문이
「각 문장을 N회 따라 말하게 한다」로 이 값을 싣는다"* 고 적었으나 **그런 지시문이 없음.** 이 값이 닿는
곳은 `api/ws.py:189` → `ShadowingTurns.as_event_payload()` → 화면뿐이고 프롬프트 조립에 닿는 경로가
**0건**임(grep 확인). 계획 단계의 의도가 주석에 남고 구현이 다르게 간 자리임.

| # | 정한 것 | 근거 |
|--:|---|---|
| ① | 반복 횟수의 정본은 **이미 있는 `shadowing_repeat_count`** | 새 설정을 만들지 않음(Simplicity First) |
| ② | **한 값이 두 뜻을 겸함** — 들려주는 횟수 = 읽는 횟수 | 값역이 같고(1~10) 「듣고 따라 읽기」가 짝임. 갈릴 이유가 생기면 그때 나눔 |
| ③ | 회차는 **서버**가 셈 | 정본이 `shadowing_recording` 발화 수라 재접속·새로 고침에도 복원됨 |
| ④ | 기본값 **1 을 유지**함 | 값역의 항등원이라는 결정 6 의 근거가 살아 있음 |

**④의 따름 결과**: 화면은 목표가 **2 이상일 때만** 진행도를 보임 — 1 이면 「1/1」이 뜻이 없고 기본
동작도 바뀌지 않음. ⇒ `TASK-188` 검증은 env 로 값을 올려 돌림.

⚠️ `drill_turns_expected` 를 쓰지 않음 — 그 컬럼은 **계획의 질문 수**로 계산되는 관측용 값이고
(`record_drill_turns_expected`) 쉐도잉에는 질문이 없어 NULL 인 것이 설계상 자연스러움. handoff 가
그것을 후보로 적었던 것은 열린 질문이었고 여기서 닫음.

게이트: `ruff check` 0 · `ruff format` **57 files**(app/backend 범위). ⚠️ 한글 주석이 `E501` 에
세 줄 걸려 줄였음(`H-BW` 가 예고한 자리).
<!-- SECTION:NOTES:END -->
