---
id: TASK-184
title: '정리·검증: simplify 로 정리하고 게이트 여덟을 돌린다'
status: Done
assignee: []
created_date: '2026-09-18 01:40'
updated_date: '2026-09-18 02:11'
labels: []
dependencies:
  - TASK-183
ordinal: 245000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 지시 「주요 개발이 끝나면 simplify 로 정리하면서 진행해」 · 「개발 뒤 테스트 필수」 의 이행이다. 게이트 수치로 브라우저 관측을 대체하지 않는다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 /simplify 를 돌리고 지적된 것을 처리하거나 남기는 근거를 적는다
- [x] #2 게이트 여덟이 전부 exit 0 이다 (pytest·ruff·ruff format·ty·tsc·eslint·next build)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## /simplify 2026-09-18 — 네 각도 결과와 처분

| 각도 | 발견 | 처분 |
|---|---|---|
| Reuse | 0건 | — (`fixtures.py` 의 `_tone_wav` 는 스텁 전용 사인파 생성기라 재사용 대상이 아님을 확인함) |
| Altitude | 0건 | — (프런트가 녹음 URL 을 조립하는 것이 `ShadowingSetup` 이 세운 기존 관행과 같음) |
| Simplification | 토글 버튼 JSX 복붙 | **고쳤음** — 스타일을 `BUTTON_STYLE` 상수로 뽑음 |
| Efficiency | `wav_from_pcm` 복사 2회 | **유지했음** — 근거를 docstring 에 남김 |

⚠️ **리뷰가 센 것보다 한 곳 많았음** — 두 곳을 지적했으나 「따라 읽기」 버튼까지 **세 곳**이었음.
⛔ **컴포넌트로 뽑지는 않았음**: 세 버튼이 서로 다른 근거 주석을 갖고 각각 다른 조건에 감싸여 있어
뽑으면 근거가 호출부와 갈라짐. 한쪽만 고쳐 모양이 어긋나는 위험은 상수 하나로 닫힘.

⛔ **Efficiency 를 유지한 근거**: 줄이는 길이 44바이트 헤더 손 조립뿐이고 그것이 `wave` 를 고른 이유가
피한 위험임(청크 길이·바이트율·정렬이 한 자리 틀리면 브라우저가 조용히 재생을 거부함).
`setnframes` 로 헤더만 뽑는 중간 길은 **성립하지 않음** — `wave.close()` 가 `_patchheader()` 로
data 길이를 실제 쓴 양(0)으로 되돌림. 리뷰 자신이 「몇 밀리초 · 급하지 않음」이라 적었음.

## 게이트 여덟 (이 턴에 직접 돌린 출력)

`pytest` **1346 passed** · `ruff check` 0 · `ruff format` **291 files** · `ty` 0 · `tsc` 0 ·
`eslint` 0 · `next build` 0(`/` 가 `○` Static 유지). 전부 exit 0.

⚠️ **스타일 상수 치환 뒤 브라우저 재관측은 하지 않았음** — 값이 동일한 객체를 상수로 옮긴 것이고
`tsc`·`next build` 가 통과함. 다시 보려면 Nova 스택을 재기동해야 해서 이득이 비용을 넘지 않음.
⛔ 그 판단을 적어 두는 것이고 「확인했다」로 읽지 않음.
<!-- SECTION:NOTES:END -->
