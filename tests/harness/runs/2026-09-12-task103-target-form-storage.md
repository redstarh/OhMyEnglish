# 회차 — `TASK-103`: 판정 호출의 옳은 문장이 저장되게 하고 **화면을 직접 열어** 확인함

세션 `ohmyenglish-19` · 2026-09-12 KST · 브랜치 `design/first-vertical-slice`
회차 디렉터리: `tests/harness/runs/2026-09-12-task103-target-form-storage/`

> **결함**: Nova 는 규칙 10 의 두 호출에 **다른 것**을 싣는다 — 시범 호출의 `target_form` 은 학습자
> 발화의 **무너진 전사**이고 판정 호출의 것이 **옳은 목표 문장**이다. 그런데
> `services/pronunciation.record_attempt` 의 판정 UPDATE 에 `target_form` 이 **없었다.** ⇒ 첫 값이
> 그 행의 최종값이 되고, 그 값이 결과 화면의 「시범 문장」 자리에 렌더된다(`page.tsx:344`) —
> **「이렇게 말하세요」 자리에 학습자의 오발음이 뜬다.**
>
> ⛔ **Nova 를 쓰지 않은 회차다.** 기전이 이미 확정돼 있어(`runs/2026-09-11-task97-tool-payload.md`
> §3 · 실물 6회 · 이 세션 REG 팔 4회) 재는 것은 **저장과 화면**이다.

---

## 0. ⛔ 상한과 해석 규칙 — 돌리기 전에 적음

| 무엇 | 값 |
|---|---|
| Nova 세션 | **0** — 실물 왕복이 필요 없다(기전 확정) |
| DB | 검증 전용 `ohmyenglish_t103` (`createdb -O ohmy` + `migrate.py`) |
| 백엔드 | `:8012` · `VOICE_ADAPTER=stub` · `WORKER_ENABLED=false` |
| 프론트 | `/tmp/t103-frontend`(`cp -Rc` 사본) · **`:3000`** |
| 절차 | TDD — 실패하는 테스트를 먼저 쓰고 초록을 확인한 뒤 화면을 연다 |

### ⚠️ 프론트를 `:3001` 이 아니라 `:3000` 에 띄운 이유

`api/main.py:48` 의 `FRONTEND_ORIGIN` 이 `http://localhost:3000` **하드코딩**이라 다른 포트는 CORS 로
막힌다(`H-BC`). 그 함정의 대응책은 `/tmp` 에 CORS 래퍼를 두는 것이었는데, 이 회차 시점에 `:3000`·
`:8002` 가 **둘 다 비어 있었으므로** 래퍼를 만들지 않고 **사본을 `:3000` 에** 띄웠다 —
리포 디렉터리를 건드리지 않고 `.next/` 도 남기지 않는다. ⛔ 동료 세션에 먼저 알리고 썼다.

⚠️ **사본의 `.env.local` 이 `:8002` 를 가리켰다** — 그대로 두면 안 떠 있는 공유 백엔드를 조회한다.
⛔ 「셸 env 가 이길 것」이라고 추측하지 않고 **사본의 그 파일을 고쳐** 모호함을 없앴다.

### ⛔ 해석 규칙 — 「화면이 옳게 보인다」로 닫지 않는다

| 무엇 | 어떻게 판정하나 |
|---|---|
| 저장 | `record_attempt` 를 **실제 생명주기로** 태워(pending → 판정) 그 행의 `target_form` 을 읽는다. ⛔ SQL 로 직접 넣으면 고친 UPDATE 경로를 지나지 않는다 |
| 화면 | 결과 화면을 **직접 열어** 「시범 문장」 자리를 읽는다. ⛔ API 응답만으로 닫지 않는다 |
| **판별력** | ⛔ **저장이 무너진 전사를 담은 세션을 «따로 만들어» 같은 화면에 띄운다.** 거기서 오발음이 드러나지 않으면 위 초록은 **판별력 없는 관측**이다 |
| 남은 구멍 | 두 호출이 **모두 pending** 인 봉투를 그대로 태워 무엇이 남는지 본다 |

---

## 1. 결과

### ⑴ TDD — 빨강을 먼저 얻었다

| 단계 | 출력 |
|---|---|
| 실패하는 테스트를 먼저 씀 | `1 failed, 3 passed, 28 deselected` — `test_verdict_target_form_replaces_the_broken_transcript` |
| ⛔ **순진한 고침**(`target_form = $6` 무조건 대입)을 «일부러» 넣어 봄 | `1 failed` — `asyncpg.exceptions.CheckViolationError: pronunciation_attempts_target_form_check` |
| 공백만 걸러 내는 `case` 로 고침 | `32 passed` → 남은 구멍 테스트를 더해 `33 passed` |

⛔ **두 번째 줄이 이 회차의 값어치 있는 산출이다.** 무조건 대입은 값을 **비우는 것이 아니라**
003 의 `check (length(btrim(target_form)) > 0)` 위반으로 **판정 트랜잭션을 통째로 죽인다.** 판정이
공백만 실어 오는 턴에 그렇다. ⇒ 빈 값 가드는 「깔끔함」이 아니라 **필수**다. 그 사실을
`pronunciation.py` 주석에 남겼다.
⚠️ 그리고 이 단계가 **빈 값 가드 테스트에 판별력이 있음을 증명한다** — 그 테스트는 고침 전에는
통과했으므로(갱신 자체가 없었으니) 그것만으로는 무력한 단정이었다.

### ⑵ 저장 — 실제 생명주기로 확인

`seed.py.txt`(pending=무너진 전사 → 판정=옳은 문장):

```
session_id = 23a26ef4-61f5-47ae-b673-ce7ed687fd9d
  저장된 target_form = 'I think three things are ready for the demo.' · outcome = correct
```

API(`GET /api/sessions/{id}/results`)도 같은 값을 낸다 —
`"target_form":"I think three things are ready for the demo."` ·
`"spoken_form":"i think sri, sings are ready for the demo."`.

### ⑶ 화면 — 직접 열었다 (`screen_fixed.png`)

```
발음
  시범 문장   I think three things are ready for the demo.   ← 옳은 문장
  내 발화     i think sri, sings are ready for the demo.     ← 학습자의 오발음이 제자리
  ✓ 좋아요
```

⇒ **AC#2 가 요구한 것이 충족됐다.** 오발음은 「내 발화」 자리에만 있다.

### ⑷ ⛔ 이 관측이 «반증할 수 있는지» 확인했다 (`screen_residual.png`)

`seed_residual.py.txt` 로 **두 호출이 모두 pending** 인 봉투를 그대로 태웠다(판정이 오지 않는다 ·
`resolve_dangling` 이 수렴). 저장 결과:

```
target_form = 'I think Sri sings are ready for the demo.'      · outcome = incorrect
target_form = 'I think three things are ready for the demo.'   · outcome = incorrect
```

같은 화면이 그것을 **드러냈다**:

```
발음
  시범 문장   I think Sri sings are ready for the demo.      ← ⛔ 오발음이 「이렇게 말하세요」 자리에
  내 발화     대답 없이 끝났어요
  다시 연습해요
  시범 문장   I think three things are ready for the demo.
  내 발화     대답 없이 끝났어요
  다시 연습해요
```

⇒ **⑶ 의 초록은 판별력 있는 관측이었다.** 화면은 저장된 값을 그대로 보여 준다.

## 2. 판정

| 물음 | 답 |
|---|---|
| 판정 호출의 옳은 문장이 저장되는가 | **된다** — 실제 생명주기 · API · 화면 셋이 같은 값 |
| 화면의 「시범 문장」 자리에 오발음이 뜨지 않는가 | **뜨지 않는다**(정상 봉투에서) — 직접 열어 봤다 |
| 이 화면 검사가 결함을 드러낼 수 있는가 | **드러낸다** — ⑷ 가 같은 화면에서 오발음을 보였다 |
| 결함이 **전부** 닫혔는가 | ⛔ **아니다** — 아래 |

### ⛔ 남은 구멍 둘 — 「여기까지만 고쳤다」

1. **두 호출이 모두 `pending`** 인 봉투에서는 판정 UPDATE 가 **아예 돌지 않아** 고친 경로를 타지
   못한다. 관측된 봉투 하나가 그 모양이었다(**12/12** · `runs/2026-09-11-task97-tool-payload.md`).
   ⇒ 무너진 전사가 살아남아 화면에 뜬다(⑷ 가 눈으로 보여 준다).
2. **한 코칭 사건에 카드가 두 장 뜬다** — ⑷ 의 화면에 「시범 문장」 블록이 둘이다. 학습자에게는
   같은 일을 두 번 한 것처럼 보인다.

⛔ **둘 다 「표시」 문제가 아니라 「행이 둘 열린다」는 저장 문제다** — AC#4 가 경고한 자리이므로
표시를 고쳐 덮지 않는다. 새 태스크로 등록한다.
⚠️ 그리고 그 거동을 **테스트로 못박았다**(`⑥-3
test_two_pendings_leave_the_broken_target_form_on_the_older_row`) — 뒤 태스크가 이 구멍을 닫으면
**그 단정을 의도적으로 뒤집어야** 한다. 주석이 그 근거를 갖는다.

## 3. 스택 정리

| 확인 | 출력 |
|---|---|
| 공유 dev DB 기준값(회차 **전**) | `learning_sessions=17` · `pronunciation_attempts=7` · `error_patterns=9` · `session_plans=6` · `learner_notes=7` |
| 공유 dev DB 대조(회차 **뒤**) | `learning_sessions=17` · `pronunciation_attempts=7` · `error_patterns=9` · `session_plans=6` · `learner_notes=7` ⇒ **다섯 표 전부 같음. 내가 남긴 변경 0건** |
| 검증 전용 DB | `dropdb ohmyenglish_t103` **exit 0** · `psql -l` 에 남은 것은 `ohmyenglish`·`_smoke`·`_test` 뿐(내가 만든 것 아님) |
| 백엔드 · 프론트 | `:8012` **`curl` 000** · `:3000` **`curl` 000** · `/tmp/t103-frontend` **삭제 확인**(`No such file or directory`) |

### 3-1. ⚠️ 정리에서 밟은 함정 하나 — 남긴다

첫 정리 시도가 **zsh 단어 분할** 때문에 실패했다. `lsof -ti tcp:8012` 가 PID 를 **둘** 냈는데
`kill $pids` 로 넘기면 무인용 변수가 **한 낱말**이 되어 `kill: illegal pid: 88084\n96229` 로 죽는다
(착수 전 필수 ⑦ 이 이름 붙인 함정과 같은 뿌리다). ⇒ 백엔드가 살아남아 `dropdb` 가
*"database is being accessed by other users (4 other sessions)"* 로 거부됐다.
**대응**: `lsof -ti tcp:$p | xargs -r kill`.

⛔ **여기서 「종료했다」를 출력 없이 적었다면 DB 가 남은 채 마감했을 것이다** — `curl` 로 다시 읽어
`404`·`200` 을 보고서야 살아 있는 것을 알았다. 종료를 **주장하지 않고 재는** 이유가 이것이다.

⚠️ **그리고 그 `kill` 이 «클라이언트»까지 잡았다.** PID `96229` 는 `:8012` 와 `:3000` **양쪽**에
잡혀 있었다 — `lsof -ti` 는 그 포트에 **연결을 가진** 프로세스도 내므로 브라우저 헬퍼가 함께
들어온다. 실제로 그것을 죽였고 **Chrome 본체는 살아 있다**(`pgrep` 으로 PID 664 확인).
⛔ 다음에는 서버 프로세스만 고르는 편이 맞다(`lsof -ti tcp:$p -sTCP:LISTEN`).

### 산출물

| 파일 | 무엇 |
|---|---|
| `seed.py.txt` | 정상 봉투 씨앗(pending → 판정) — 실제 생명주기를 탄다 |
| `seed_residual.py.txt` | 남은 구멍 씨앗(둘 다 pending) — **반증 대조** |
| `screen_fixed.png` · `screen_fixed.md.txt` | 고친 뒤 화면 |
| `screen_residual.png` · `screen_residual.md.txt` | 남은 구멍 화면 |
