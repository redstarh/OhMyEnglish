---
id: TASK-196
title: '검증: 브라우저에서 낱말 뜻 조회를 실측한다'
status: Done
assignee: []
created_date: '2026-09-18 04:01'
updated_date: '2026-09-18 04:20'
labels: []
dependencies:
  - TASK-195
ordinal: 257000
---

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 낱말을 눌러 뜻이 화면에 나오는 것을 관측한다
- [x] #2 다의어가 문맥에 맞는 뜻으로 나오는지 확인한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 브라우저 실측 2026-09-18 — 문맥이 뜻을 가르는 것을 확정했음

스택: 백엔드 `:8002`(`WORKER_ENABLED=false VOICE_ADAPTER=stub` · 재기동 **PID 2696** · `/health` 200) ·
프런트 `localhost:3000`. ⚠️ **이 갈래는 Nova 가 필요 없어 stub 백엔드로 검증했음** — 낱말 조회는
Bedrock Claude 를 부르고 음성 어댑터와 무관함.

### 판별력 — 문맥을 보내지 않으면 갈리지 않을 것을 골랐음

⛔ **같은 낱말이 문맥에 따라 다른 뜻으로 나오는지**를 잼. 문장을 안 보내면 두 결과가 같아야 하므로
이 대조가 「문맥이 실제로 쓰인다」의 유일한 증거임.

| 낱말 | 문장 | 뜻 |
|---|---|---|
| `book` | `I need to book a table for two.` | **(자리를) 예약하다** |
| `book` | `I read a book before bed.` | **글이 인쇄되어 묶여 있는 읽을거리, 책** |

### 화면 관측 (영상 `e5463a72` · 담은 문장 `All right, so here we are in front of the elephants`)

| 관측 | 값 |
|---|---|
| 문장이 낱말 버튼으로 쪼개짐 | `All` `right,` `so` `here` `we` `are` `in` `front` `of` `the` `elephants` |
| 누르기 전 안내 | 「낱말을 누르면 이 문장에서 쓰인 뜻을 알려 줘요」 |
| `front` 를 누름 | **front — 앞쪽, 어떤 대상의 정면 방향** ⇒ 「전선」이 아님 |
| `right,` 를 누름 | **right — 말을 시작할 때 "좋아, 자"라며 뜻을 나타내는 말** ⇒ 「오른쪽」이 아니고 **구두점이 정리됐음**(`cleanWord` 가 동작함) |
| 누른 낱말 표시 | 그 버튼에 밑줄이 걸림 |
| 빈 낱말 | `POST` 가 **422** (모델에 닿기 전에 막힘) |

⚠️ `right` 의 뜻 문장이 조금 어색함("…라며 뜻을 나타내는 말") — **프롬프트 품질이고 기능 결함이
아님.** 고치려면 프롬프트 회차가 필요하므로 지금 고치지 않고 적어 둠.

### 게이트 (이 턴 실측)

`tsc` 0 · `eslint` 0 · `next build` 0(`/` 가 `○` Static 유지). 백엔드는 `TASK-194` 에서 돌렸음.
<!-- SECTION:NOTES:END -->
