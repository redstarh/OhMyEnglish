---
id: TASK-207
title: '구현 ③: 클립 전사문과 낭독 전사문을 낱말 단위로 견주는 순수 함수'
status: Done
assignee: []
created_date: '2026-09-18 05:54'
updated_date: '2026-09-18 06:16'
labels: []
dependencies: []
ordinal: 268000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
결정 131 · 설계서 §4-4. 모델을 부르지 않는다 — 낱말 일치로 답이 정해진다. 순수 함수라 테스트가 값싸다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 맞음·빠짐·다름 셋으로 낱말마다 판정한다
- [x] #2 대소문자·문장부호 차이를 오류로 세지 않는다
- [x] #3 같은 입력에 같은 답이 나는 것을 테스트로 고정한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 결과 (2026-09-18 · TDD)

`app/backend/app/services/readback.py` · `tests/unit/test_readback.py` (테스트 **10건**).

### 절차 — RED 를 실제로 봤음

1. 테스트 먼저 씀 → 모듈이 없어 **collection 오류**로 났음(실패가 아님).
2. 빈 결과를 돌려주는 껍데기를 두고 다시 돌려 **단정이 실패하는 것**을 봤음(7 failed, 1 passed).
3. ⛔ **그 1 passed 가 결정성 테스트였고 판별력이 0 이었음** — `[] == []` 로 통과했음.
   내용까지 고정하도록 고쳐 **8 failed** 로 만든 뒤 구현했음.
4. GREEN: 10 passed.

### AC 별

- **#1** `WordVerdict(word, verdict)` 로 낱말마다 `match`·`missing`·`different` 를 냄.
  기본값이 `missing` 이라 `delete` 갈래와 낭독이 아예 빈 경우가 그대로 그 값에 남음.
- **#2** 견줄 때만 쓰는 형태를 `[^0-9a-z]+` 로 지움 — 대소문자·문장부호·홑따옴표 차이가 오류가 아님.
  ⛔ 화면에는 **원본의 원래 모양**을 돌려줌(테스트가 그것을 고정함).
- **#3** 같은 입력에 같은 답이 나는 것을 테스트가 고정함. `autojunk=False` 를 명시했고 그 이유를
  코드가 가짐.

### 뮤테이션 세 개가 다 죽었음 — 테스트가 반증할 수 있음

| 뮤테이션 | 결과 |
|---|---|
| `autojunk=False` 를 기본값으로 되돌림 | **1 failed** |
| `replace` → `MATCH` 로 바꿈 | **2 failed** |
| 정규화를 없앰(문장부호를 지우지 않음) | **3 failed** |

### ⚠️ 판별력을 두 번 잘못 잡았고 둘 다 실측으로 갈렸음

1. 결정성 테스트가 빈 결과에서 통과했음(위 3번).
2. `autojunk` 가드를 **같은 문장**으로 재려 했고 그때 뮤테이션이 죽지 않았음. 직접 재보니
   **`autojunk` 는 열이 다를 때만 결과를 바꿈** ⇒ 다른 열로 고쳤음.
   ⚠️ 그 다음 판(같은 문장 30번 되풀이 · 270낱말)은 **정상 구현에서도 실패**했음 — `difflib` 이
   똑같이 긴 다른 정렬을 골라 99낱말을 빠짐으로 냄. 그것은 이 가드의 회귀가 아니라 **정렬 모호성**이고
   쉐도잉 클립은 한 문장이라 실제로 오지 않음 ⇒ 자연스러운 긴 글(225낱말)로 갈아 정확히 1건만
   잡히는 것을 봤음. 그 한계를 구현 docstring 에 남겼음.

### 게이트

`pytest` **1371 passed**(1361 → +10) · `ruff` 0 · `ruff format` **299 files** · `ty` 0 — 넷 다 exit 0.
<!-- SECTION:NOTES:END -->
