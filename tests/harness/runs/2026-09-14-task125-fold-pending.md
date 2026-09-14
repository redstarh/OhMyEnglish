# 회차 — `TASK-125` AC#4: 카드가 한 장이고 「시범 문장」에 오발음이 없다

세션 `ohmyenglish-f4` · 2026-09-14 KST · 브랜치 `design/first-vertical-slice`
회차 디렉터리: `tests/harness/runs/2026-09-14-task125-fold-pending/`

> **씨앗을 새로 만들지 않았다** — AC#4 가 요구한 대로
> `runs/2026-09-12-task103-target-form-storage/seed_residual.py.txt` 를 **그대로** 돌렸다.
> 그 스크립트가 결함의 눈 증거를 만든 것이므로 **같은 입력에서 결과가 갈리는 것**이 이 회차의 축이다.

---

## 0. 스택

검증 전용 DB `ohmy_125check`(`migrate.py` 전체 · 21건) · 백엔드 `:8016`(`WORKER_ENABLED=false`) ·
프런트 `:3000`(`NEXT_PUBLIC_API_BASE=http://127.0.0.1:8016`) · 브라우저는 플러그인 Chrome
(마이크가 필요 없는 화면이라 전용 Chrome 이 필요하지 않다).

## 1. 같은 씨앗, 갈린 결과

**전(2026-09-12 · `…task103…` §1-⑷)**:

```
target_form = 'I think Sri sings are ready for the demo.'      · outcome = incorrect
target_form = 'I think three things are ready for the demo.'   · outcome = incorrect
```

**후(2026-09-14 · 이 회차)**:

```
session_id = c18e4c83-0e87-4481-81f0-9045bc30de24
  target_form = 'I think three things are ready for the demo.' · outcome = incorrect
```

⇒ **행이 둘에서 하나로 접혔고 남은 값이 옳은 문장이다.**

## 2. 화면 — 직접 열어 봤다 (`screen-folded.png` · `screen-folded.md`)

```
학습 결과
분석 대상 없음

발음
  시범 문장   I think three things are ready for the demo.
  내 발화     대답 없이 끝났어요
  다시 연습해요
```

⛔ **카드가 한 장이고 「시범 문장」에 오발음이 없다** — 전에는 카드가 두 장이고 첫 장의 시범 문장이
학습자의 오발음(`I think Sri sings…`)이었다. API 응답(`api-results.json`)도 `pronunciation` 배열이
**1건**이다.

## 3. 정리와 무변경 확인

| 무엇 | 확인 |
|---|---|
| 프런트·백엔드 | `:3000`·`:8016` 이 **`000`** |
| 검증 전용 DB | `dropdb ohmy_125check` **exit 0** |
| 공유 dev DB | `learning_sessions` **17** · `pronunciation_attempts` **7** · 최대 마이그레이션 **`022`** |

## 4. 고침이 건드린 이웃 넷 — 전부 「내 변경이 옳아서」였다

| 테스트 | 무엇이 바뀌었나 |
|---|---|
| `test_two_pendings_leave_the_broken_target_form_on_the_older_row` | ⛔ **의도적으로 뒤집었다** — 이름과 단정과 주석을 함께 고쳤다(AC#3). 그 주석이 이 자리를 미리 지목해 뒀다 |
| `test_two_pendings_resolve_newest_first` | setup 만 `_legacy_pending` 으로 바꿨다 — 재는 축(판정이 최신 pending 을 닫는다)은 그대로다 |
| `test_resolve_dangling_converges_pending_to_incorrect` | 같은 이유로 setup 만 바꿨다 |
| `test_resolve_dangling_merges_two_pendings_of_one_sound` | 같은 이유로 setup 만 바꿨다 |
| `test_pending_converges_to_incorrect_when_the_session_ends`(게이트웨이) | 행 수 단정을 둘에서 하나로 고치고 **나중 `target_form`** 단정을 더했다 — 그 대본이 바로 이 결함의 봉투다 |

⚠️ **`_legacy_pending` 헬퍼를 왜 두었나**: `record_attempt` 로는 이제 두 pending 을 만들 수 없지만
**DB 에는 실재할 수 있다**(고침 전에 쓰인 행). `resolve_dangling` 과 판정 UPDATE 는 그 상태를 계속
처리해야 하므로 그 축을 잃지 않으려고 setup 만 우회했다.

## 5. 이 회차가 닫지 못한 것

- **실물 Nova 봉투로는 재확인하지 않았다** — AC#1 이 *"Nova 를 쓰지 않고 닫는다"* 로 그렇게 정했고
  (재현 조건이 분기로 설명된다) 이 회차도 그 규약을 지켰다.
- ⚠️ **접힘의 대가는 관측하지 않았다** — 한 세션에 판정 없는 코칭이 **두 번** 일어나면 복습 시계가
  하나로 센다. 그 상황이 실물에서 얼마나 자주 나는지는 재지 않았고, 그 대가를 택한 근거는 반대쪽이
  **사용자에게 보이는 오류**를 냈다는 것이다(`services/pronunciation.py` 의 그 분기 주석).
