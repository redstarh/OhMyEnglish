---
id: TASK-212
title: '정리: /simplify 네 각도 지적을 낭독 판정 축에 반영한다'
status: Done
assignee: []
created_date: '2026-09-18 07:42'
updated_date: '2026-09-18 07:52'
labels: []
dependencies: []
ordinal: 273000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-205~211 로 더한 코드(746줄)를 재사용·단순화·효율·고도 네 각도로 검토한 결과를 반영한다. 규약: 주요 개발 뒤 /simplify (사용자 지시). ⛔ 동작을 바꾸는 지적은 별 태스크로 가른다 — 이 태스크는 동작 보존 정리만 담는다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 거짓이거나 낡은 주석을 고친다 (프레임 크기 주장 · ws.py 의 실물 배선 하나뿐)
- [x] #2 동작을 바꾸지 않는 재사용·단순화 지적을 반영한다
- [x] #3 동작을 바꾸는 지적은 근거와 함께 별 태스크로 등록한다
- [x] #4 게이트 여덟을 다시 돌려 exit 0 을 확인한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 결과 (2026-09-18)

네 각도(재사용·단순화·효율·고도)를 병렬로 돌렸음. ⚠️ **고도 각도가 원장 게이트 메시지에 밀려
보고를 내지 못했음**(`H-AO` ④ 의 형태) — 새로 띄우지 않고 `SendMessage` 로 이어서 회수했음.

### AC#1 — 거짓·낡은 주석 둘을 고쳤음

1. ⛔ **`readback.py` 의 프레임 크기 주석이 거짓이었음.** 「소켓 계층이 브라우저에서 받는 크기와
   같은 자리수」라 적었으나 실제 소켓 프레임은 **1024바이트**(32ms · `lib/audio.ts`)이고 이쪽은
   3200 임. 직접 확인하고 고쳤음 — 그쪽은 실시간 지연용이고 이쪽은 끝난 파일을 흘린다는 차이를
   적었음. 값도 손으로 적지 않고 `RECORDING_SAMPLE_RATE_HZ`·`RECORDING_BYTES_PER_SAMPLE` 에서
   끌어왔음(침묵 길이도 같이 — 표본율이 바뀌면 「2초」가 조용히 다른 길이가 됨).
2. ⛔ **`ws.py:404` 의 「실물 배선은 여기 하나뿐이다」가 낡았음** — 낭독 판정이 둘째 지점이 됐음.

### AC#2 — 동작을 바꾸지 않는 지적을 반영했음

- **응답 키를 snake_case 로.** `grep -rnoE '"[a-z]+[A-Z][a-zA-Z]*":' app/backend/app/api/*.py` 의
  결과가 **내 두 줄뿐**이었음(직접 확인). 프런트 타입과 통합 테스트를 함께 고쳤음.
- **DB 연결을 Nova 스트림 내내 쥐지 않음.** `judge_readback` 이 `conn` 대신 `pool` 을 받아
  「읽기 → 반납 → 전사 → 다시 잡아 쓰기」로 나눴음. 그 구간이 최대 30초이고 그 안에서
  `pool_usage_sink` 가 연결을 또 잡아 판정 1건이 기본 풀(10)의 두 자리를 묶고 있었음.
- **배수 만료를 조용히 삼키지 않음.** `TimeoutError` 를 따로 잡아 `warning` 을 냄 — 만료되면
  `TASK-204` 가 고친 증상이 되돌아오는데 로그가 0줄이면 관측할 수 없었음.
- **`_words` 가 짝을 돌려줌** — 나란한 두 리스트가 길이로 어긋날 자리를 없앴음.
- **프런트의 갈라진 두 상태를 하나로.** `recordingUrl`·`recordingIds` 를 함께 들면 세션 ID 가
  비었을 때 한쪽에 `"null"` 이 박힌 주소가 들어감. 주소 조립을 `lib/api.ts` 의 `recordingUrl` 한
  자리로 모으고 상태는 `recordingIds` 만 남겼음. 판정 상태도 화면이 쓰는 `words` 만 들고 키 일치
  판정을 한 곳으로 모았음(세 곳에 있었음).
- ⛔ **배선 게이트를 둘째 지점까지 넓혔음** — `test_readback_api.py` 에 대역을 두고 `usage_sink` 에
  **기본값을 두지 않음**. 뮤테이션으로 확인: 라우터에서 그 인자를 떼면
  `TypeError: … missing 1 required keyword-only argument: 'usage_sink'` 로 죽음.

### AC#3 — 동작을 바꾸는 지적 다섯을 태스크로 갈랐음

| 태스크 | 무엇 | 실물 회차 |
|---|---|---|
| **`TASK-213`** | ⛔ **stub 서버에서 판정을 누르면 스텁 문장이 전사로 영구 저장됨** + 503 가드 부재 | 불필요 |
| `TASK-214` | 좁은 `Transcriber` 포트 — 결정 131 의 경계 약속을 실제로 만듦 | 불필요 |
| `TASK-215` | 사용량 기록을 `_pump_output` 의 `finally` 로 · 종료 예산 셋을 하나로 | 불필요 |
| `TASK-216` | teardown 이 앱의 고아 파일 스윕을 재사용(삭제 정책 한 자리) | 불필요 |
| `TASK-217` | 전사 전용 프롬프트 + `end_input()` — 입력 약 1,600 토큰 절감 | **필수** |

⛔ **`TASK-213` 이 가장 무겁다** — 개발용 `:8002` 가 평소 stub 으로 떠 있어 실제로 밟기 쉽고,
`judge_readback` 이 값이 있으면 다시 계산하지 않으므로 오염이 영구임.

### 반영하지 않은 것

하네스 드라이버의 복붙 셋(버튼 클릭 식 · 폴링 골격 · 중복 기록)은 값이 작고, 같은 형태가 이미
다섯 파일에 있어 공용 자리(`c2_render_hierarchy.Cdp`)로 올리는 것이 이 diff 범위를 넘음.
`'shadowing_recording'` 리터럴은 `recordings.py` 가 이미 인라인으로 쓰는 선례가 있어 두었음.

### 게이트 여덟

`pytest` **1387 passed**(1386 → +1) · `ruff` 0 · `ruff format` **302 files** · `ty` 0 · `tsc` 0 ·
`eslint` 0 · `next build` 0(`/` 가 `○` Static 유지).
<!-- SECTION:NOTES:END -->
