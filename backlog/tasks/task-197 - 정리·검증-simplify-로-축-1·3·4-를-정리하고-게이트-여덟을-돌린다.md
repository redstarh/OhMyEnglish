---
id: TASK-197
title: '정리·검증: simplify 로 축 1·3·4 를 정리하고 게이트 여덟을 돌린다'
status: Done
assignee: []
created_date: '2026-09-18 04:28'
updated_date: '2026-09-18 04:50'
labels: []
dependencies: []
ordinal: 258000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 지시 「주요 개발이 끝나면 simplify 로 정리하면서 진행해」의 이행. 네 각도를 병렬로 돌렸고 reuse 는 0건이었다. 반영한 것: WordLookup 의 세 state 를 판별 유니온으로 · 응답 모델을 없애고 dict 관행에 맞춤(요청 모델은 models/vocab.py 로 옮김). ⚠️ 상태 기계를 바꿨으므로 브라우저 재검증이 필요하다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 네 각도의 발견을 처리하거나 남기는 근거를 적는다
- [x] #2 게이트 여덟이 전부 exit 0 이다
- [x] #3 상태 기계 변경 뒤 브라우저에서 낱말 조회를 다시 관측한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## /simplify 2026-09-18 (2회차) — 네 각도 결과와 처분

| 각도 | 발견 | 처분 |
|---|---|---|
| Reuse | **0건** | 네 항목을 직접 확인함 — 발화 수를 세는 공용 헬퍼가 리포에 없고, 프런트에 문장 분해 자산이 없고, `lookupWord` 는 기존 `postJson` 을 정확히 재사용하고, vocab 서비스는 `scenario_generator` 와 같은 프롬프트 빌더 규약을 따름 |
| Simplification | 2건 | **둘 다 고쳤음** (아래) |
| Efficiency | 4건 검토 · **문제 0건** | `count(*)` 는 1ms 미만이고 세션 행 수로 묶임 · `cleanWord` 는 마이크로초 · boto3 생성은 30~40ms 1회성 · 중복 호출 0건 |
| Altitude | 3건 판정 + **회귀 1건** | 회귀를 고쳤고 나머지는 근거와 함께 유지 (아래) |

### 고친 것 — Simplification 2건

1. **`WordLookup` 의 세 state → 판별 유니온.** `selected`·`meaning`·`looking` 을 매 호출에 올바른
   순서로 맞추던 규율을 타입이 지키게 했음. 닿을 수 없는 조합이 사라졌음.
2. **응답 모델을 없애고 `dict[str, object]` 로 바꿈.** `response_model=` 이 **리포 전체에서 유일한
   사용**이었고, ⛔ 내 docstring 이 「이 리포의 다른 라우터와 같은 규약」이라 **틀리게** 주장하고
   있었음. 요청 모델은 관행대로 `models/vocab.py` 로 옮겼음(`VideoCreateRequest` 와 같은 자리).

### ⛔ 회귀 하나를 잡았고 실측으로 확정했음 — Altitude 의 가장 큰 값

`TASK-194` 가 `BedrockClaudeClient` 생성을 `worker_enabled` 분기 밖으로 옮기면서, **`config.py` 가
스스로 안내하는 「자격증명 없이 띄우는 길」을 깼음.** 그 `RuntimeError` 문구가 *"자격증명 없이
백엔드만 띄우려면 WORKER_ENABLED=false로 기동하라"* 인데, 그 값으로도 기동이 막혔음.

재현: `app/backend/.env` 를 치우고 셸의 `AWS_*` 를 모두 지운 뒤 lifespan 을 열자
`RuntimeError: Bedrock 자격증명이 없다` ⇒ **자기 안내를 자기가 어기는 상태**였음.
⚠️ 첫 두 시도는 판별력이 없었음 — `env -u` 만으로는 `.env` 가 살아 있고, `.env` 만 치우면 셸의
bearer 키가 살아 있었음. **두 자리를 다 치운 뒤에야** 재현됐음.

고침: `worker_enabled` 이면 그대로 터뜨리고(기존 동작 · 그 SDK 는 자격증명 실패를 무응답으로
드러내므로 워커가 무한 대기에 걸림), 꺼져 있으면 삼키고 `app.state.claude = None` 으로 둠.
낱말 조회 경로는 `None` 이면 **503** 으로 답함 — ⛔ 200 + `meaning=null` 로 답하면 자격증명 문제가
「뜻을 모른다」로 위장돼 학습자가 영원히 다시 누름.
⚠️ **두 갈래에서 각자 클라이언트를 만드는 형태로 정리했음** — 한 번 만들고 `None` 검사를 워커 분기에
두면 「워커를 켰는데 클라이언트가 없다」는 닿을 수 없는 상태를 `ty` 가 계속 물어봄.
회귀 테스트 둘을 더했음(worker off → 기동됨 · worker on → 즉시 실패 유지).

### 유지한 것 — 근거와 함께

- **`shadowing_repeat_count` 과부하** — Altitude 가 「나중에 갈라야 할 지름길」로 판정했고 근거가
  구체적임(두 소비처가 다른 메커니즘 · 가를 때 여섯 자리를 고쳐야 함). 그래도 유지함: 지금 가르면
  설정 노브가 늘고 「누가 그 기본값을 정했나」가 다시 생김(결정 129 ④ 가 피한 것). ⇒ 결정 129 의
  「갈릴 이유가 생기면 그때 나눔」을 유지하고 **그 판정을 이 노트가 갖음.**
- **`turn_index` 를 그 이벤트에 실은 것** — 맞는 자리로 판정됐음. 기존 `final` 의 `sequence_no` 와
  같은 모양이고 `session_started` 는 세션당 한 번이라 진행 중 갱신을 못 담음.
- **`purpose` CHECK 구조** — 원칙 유지를 지지받았음. 다만 「값 추가마다 전체 목록 재작성」이 이번이
  세 번째이고 021 이 한 번 값을 빠뜨린 기록이 있어, **참조 표 + FK** 대안이 제시됐음. ⇒ 지금 범위
  밖이라 하지 않았고 **이 노트에 남김.**

### ⚠️ 위임 리뷰에서 실패 하나 — 기록해 둠

Efficiency·Altitude 두 에이전트가 첫 응답에 findings 를 내지 않았음. 원인: **원장 게이트(Stop hook)
메시지가 그들 컨텍스트에 들어가 원래 과제를 밀어냈음** — 둘 다 원장 상태만 조사해 보고했음.
⇒ 새 Agent 를 띄우지 않고 `SendMessage` 로 이어서 요청해 둘 다 회수했음(`H-AO` ④ 의 대응).

### 게이트 (이 턴 실측)

`pytest` **1361 passed** · `ruff check` 0 · `ruff format` **296 files** · `ty` 0 · `tsc` 0 ·
`eslint` 0 · `next build` 0(`/` 가 `○` Static 유지).

### 브라우저 재관측 (상태 기계 변경 뒤)

`elephants` → 「코가 길고 몸집이 매우 큰 포유동물」 · `right,` → 「'좋아, 자'처럼 말문을 열 때 쓰는
말」 · 밑줄이 누른 낱말에 걸림 · 구두점 정리 동작함.
<!-- SECTION:NOTES:END -->
