# 회차 — `TASK-278`: 실물 Nova 로 `TASK-271`·`TASK-276` 변경을 검증했음

2026-09-26 KST · 드라이버 `tests/harness/p_app_path.py` · 상한 Nova **3세션**(처음 2세션으로 정했다가 비교 팔 1개를 더했음 — 아래 §2) · Claude 0회

## 0. 스택

| 무엇 | 값 |
|---|---|
| DB | 격리 `ohmyenglish_t278` — `~/Backups/OhMyEnglish/ohmyenglish-before-TASK-277-20260926-1843.dump` 복원. 관사 초점 계획(`article_missing_before_noun` · `article_wrong_definite_article`) + 발음 후보 `an_as_a`(빈도 3) = 11:58 실사용 세션의 실패 조건 |
| 백엔드 | `:8013` · `VOICE_ADAPTER=nova` · `WORKER_ENABLED=false` · CORS 래퍼 `/tmp/t275_app.py`(오리진 `:3001`) · SigV4 |
| 프런트 | 사본 `/tmp/fe-t272`(`:3001`) — `app/`·`lib/` 가 리포와 diff 0 |
| 학습자 발화 | macOS `say -v Samantha` 로 만든 **관사가 맞는** 문장 셋(리포 밖): `Hi. I had a small accident. I need a bandage.` · `I want an apple juice, please.` · `I would like a cup of coffee and a sandwich.` |

## 1. 원자료 (DB `utterances` · `pronunciation_attempts`)

| 회차 | 후보 `an_as_a` | 코치 턴 길이(자) | 발음 판정 | `interrupted` |
|---|---|---|---|---|
| r1 `467dd7d2` | 있음 | 198 · 106 · 117 | **0** | 2 |
| r2 `14be7adf` | 있음 | 33 · 46 · 60 | **1**(`an_as_a` · 맞는 문장을 `incorrect`) | 2 |
| r3 `88e5c082` | **없음** | 203 · 140 · 158 | **0** | 2 |

비교 기준: 수정 전 11:58 실사용 세션은 코치 턴 평균 252자 · 발음 판정 3건(전부 관사 `a`)이었음.

## 2. 판정

1. **관사 발음 고리**: 후보가 있으면 프롬프트 한 줄(`TASK-276`)만으로는 **2회 중 1회** 되살아났음. 후보가 없으면 0회. ⇒ `TASK-277` 의 기록 삭제가 필요했다는 근거임. 비교 팔 r3 은 이 구분을 위해 상한을 넘겨 더했음.
2. **턴 길이**: 수정 전 평균 252자보다 짧아졌으나 r1·r3 은 여전히 규칙 1(20단어)을 넘음. 넘는 턴은 관사 규칙 **설명**을 담았음(규칙 4 위반).
3. ⛔ **새 결함 — 코치가 틀린 교정을 가르쳤음**(r3 4번 턴): 학습자의 맞는 `an apple juice` 에 *"we also use a. Can you say: I want a apple juice"*. 세 회차 모두 코치가 **맞는 문장을 다시 따라 하게** 했음. 원인 후보는 관사 초점 계획과 드릴 지시(「다시 말하게 하라」)가 맞는 문장에도 교정 모양을 강요하는 것임 — `TASK-279` 가 소유함.
4. `interrupted` 가 세 회차 모두 2회임. 게이트 시점에 그 턴의 `final` 이 이미 와 있었으므로 코치 말을 중간에 자른 것은 아님. 드라이버가 프레임 **도착**의 정적(1.2초)으로 턴 끝을 재고 브라우저 **재생**은 더 늦게 끝나므로 생기는 드라이버 쪽 겹침으로 보이나, 원인은 **미확정**임.

## 3. teardown

회차 세션 셋은 격리 DB 에만 있음. dev DB(`ohmyenglish`)와 `:8002` 는 건드리지 않았음. 격리 스택은 `TASK-279` 검증에 이어 쓰고 그 태스크가 정리함.
