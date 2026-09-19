# 회차 B9 — TS-36 AC#3 의 남은 한 자리 (즉시 드릴의 초점 대체)

## 1. 환경 — 이 회차에 직접 재서 적었음

| 항목 | 값 |
|---|---|
| 착수 HEAD | `2b537ec` (`design/first-vertical-slice` · `origin` 대비 ahead 3) |
| 측정이 대상으로 삼은 앱 소스 | `2b537ec` — 백엔드가 21:15:23 KST 에 그 소스로 기동해 있었고 회차 내내 재기동하지 않았음 |
| ⚠️ 회차 중 HEAD 가 움직였음 | 다른 세션이 21:18:28 KST 에 `9ead64f` 를 커밋했음 — `docs/ops/pitfalls.md` 한 파일 8줄 추가이고 **앱 소스·설정 0건**임. 내 측정은 21:19~21:22 에 났으므로 그 커밋 뒤지만, 그것이 바꾼 것이 문서뿐이라 어느 측정도 갈리지 않았음 |
| 백엔드 | `:8002` 리스너 pid 28778 · `uvicorn app.api.main:app --port 8002 --log-level warning` · `/health` 200 |
| 프런트 | `:3000` 리스너 pid 98298 |
| DB 스키마 | `current_schema()` = `ohmyenglish` (`H-BX` 대로 introspection 에 걸었음) |
| 유료 호출 | 회차 창(12:15Z 이후) `llm_calls` **0건** · 가장 최근은 08:37:06Z (회차 밖) |

**공유 인스턴스 판정**: **공유임.** 착수 시 `find app -newermt '-30 minutes'` 가 0건이었고
`git log` 최근 셋이 `2b537ec`·`84c028f`·`b96e2be` 였으나, **회차 끝에 다시 떠 보니 다른 세션의
`9ead64f` 가 끼어 있었음**(위 표). ⛔ 착수 시점의 확인만으로 「전용」이라 단정했다면 이 회차
전체가 회귀 비교에 쓸 수 없게 되었을 자리임 — 끝에 다시 뜬 것이 그것을 막았음. 포트 둘은 호출 세션이 소유한 것이라 죽이지 않았음. 전역·공유 상태는 바꾸지 않았음.

## 2. 범위 — 한 자리만 겨눴음

`TS-36` AC#3 의 **넷째 자리**: 「준비된 계획이 있으면 지시문의 초점이 그 패턴으로 바뀜」.
회차 B8 이 화면 세 자리(링크 문구 · `href` · 클라이언트 이동 + 세션 행의 `focus_pattern_key`)를
이미 관측했고 이 자리만 볼 표면이 없어 결함 `TASK-250` 으로 올렸으며, 그 결함이 커밋 `2b537ec`
로 고쳐져 `session_started` 에 `focus_pattern` 이 실리게 되었음. 이 회차는 그 프레임을 밖에서 읽음.

⛔ **다른 AC·다른 TS 를 다시 재지 않았음.**

## 3. 전제 확인 — 착수 지시의 전제를 그 자리에서 다시 쟀음

| 전제 | 재서 확인한 것 |
|---|---|
| 준비된 계획이 있음 | `session_plans` 최신 행 `26586108-…` (created 2026-09-11 22:41:27Z) · 초점 둘 = `pronunciation_an_as_a` · `article_missing_before_noun` |
| 고른 패턴이 계획 초점과 겹치지 않음 | 고른 것은 `verb_tense_past_simple_for_past_events` — 위 둘과 겹치지 않음 |
| 그 패턴이 실재함 | ⚠️ **대체가 성립할 조건은 `error_patterns` 이지 `daily_error_summary` 가 아님** — `load_focus_pattern` 의 SQL 이 `error_patterns` 를 읽음(`services/sessions.py:302-307`). 그 표에 그 키가 있음(`target_form` = `Yesterday + 주어 + 동사 과거형`) |
| 화면 카드가 뜰 조건 | `daily_error_summary` 오늘(KST) 행이 **없었음**(기준선). B8 의 `ts36_daily_seed.py` 로 1건 심고 회차 끝에 되돌렸음 |

## 4. 관측 — 팔 넷에서 «프레임에서 실제로 읽은 값»

계약 정본은 `app/backend/app/api/ws.py` 머리말 「즉시 드릴 진입」 절임 — **대체가 실제로
일어났을 때만** `focus_pattern` 이 실림. 그래서 「키가 실렸다」 하나로는 판정하지 않았음:
모든 세션에 싣는 구현도 그것을 통과하고, 그것은 「일어나지 않은 대체를 보고한다」는 반대 방향
결함임. ⇒ **부재를 뜻으로 읽는 팔 둘을 대조로 두었음.**

⚠️ **키 부재와 값 `null` 을 갈라 적었음** — 계약이 「있을 때만 싣는다」이므로 `null` 로 실리는
것은 계약 위반임. 드라이버가 `'focus_pattern' in frame` 검사와 값 검사를 따로 기록함.

| 팔 | 진입 | `session_started` 의 키 목록 | `focus_pattern` | 세션 행 `focus_pattern_key` |
|---|---|---|---|---|
| **A** (드라이버) | `?source=additional&pattern=verb_tense_past_simple_for_past_events` | `focus_pattern` · `session_id` · `type` | **`verb_tense_past_simple_for_past_events`** | 같은 키 |
| **A′** (실제 화면) | 결과 화면의 「이 패턴으로 연습하기」를 눌러 진입 | `focus_pattern` · `session_id` · `type` | **`verb_tense_past_simple_for_past_events`** | 같은 키 |
| **B** (대조) | `?source=additional` — 패턴 없음 | `session_id` · `type` | **키 자체가 없음** | `NULL` |
| **C** (대조) | `?source=additional&pattern=존재하지않는키_b9` | `session_id` · `type` | **키 자체가 없음** | **`존재하지않는키_b9` 가 남음** |

**팔 C 가 이 회차에서 가장 값있음** — 「기록은 남기지만 대체는 보고하지 않는다」가 실제로
성립함. 세션은 그대로 열렸고(`status=completed` · 발화 6건 · `session_ended`) 요청한 키는 세션
행에 남았는데 프레임에는 실리지 않았음.

**재현(§7-3)**: 팔 C 를 다른 없는 키(`없는키_두번째_b9`)로 한 번 더 돌려 같은 결과를 봤음 —
프레임에 키 없음 · 세션 행에 그 키 남음 · 세션 열림. 간헐 아님.
팔 A 는 진입 수단이 다른 둘(드라이버 · 실제 화면 클릭)에서 같은 값을 냈음.

**관측력 증명(§7-7)**: 팔 B·C 의 「키 없음」을 결함 아닌 **기대값**으로 읽을 수 있는 근거는
**같은 드라이버·같은 코드 경로가 팔 A 에서 그 키를 실제로 잡았다는 것**임. 내 관측 수단이 그
신호를 잡을 수 없어서 「0건」인 경우가 배제됨.

## 5. 팔 A′ — 화면 경로를 한 번의 관측으로 이었음

B8 은 「화면이 `pattern` 을 넘긴다」를 세션 행으로, 이 회차의 드라이버는 「서버가 초점을
대체한다」를 프레임으로 각각 보였음. 그 둘을 **합성**하지 않고 한 번의 관측으로 잇기 위해
브라우저에서 `WebSocket` 을 감싸 프레임을 기록했음.

- 결과 화면 `/results/5c0c614b-…` 을 열고 `WebSocket` 기록기와 마이크 대체본을 심었음(`H-CC`)
- 접근성 스냅샷의 `link "이 패턴으로 연습하기" [ref=e3]` 을 요소 참조로 눌렀음 —
  `href` 는 `/?source=additional&pattern=verb_tense_past_simple_for_past_events`
- 클릭 뒤 심어 둔 것이 살아 있었음(`injected_alive=true` · `gum=1`) ⇒ **같은 문서 안의 클라이언트
  이동**이고 전체 로드가 아님(B8 의 같은 관측과 일치)
- 프런트가 연 소켓 주소를 직접 읽었음:
  `ws://localhost:8002/ws/session?source=additional&pattern=verb_tense_past_simple_for_past_events`
  — **화면이 그 키를 소켓 질의로 넘기는 것**이 여기서 보임
- 그 소켓의 첫 프레임:
  `{"type":"session_started","session_id":"5cf40a76-…","focus_pattern":"verb_tense_past_simple_for_past_events"}`
- 세션 수가 **정확히 1건** 늘었음(30 → 31). B8 이 잡아 둔 드라이버 산물(`tab create --url` 이
  같은 주소를 두 번 로드함)을 피하려고 진입은 **클릭**으로만 했음

⛔ **기록기는 프레임을 감싸기만 하고 삼키거나 바꾸지 않음** — 앱이 보는 동작이 달라지면 이
관측이 앱 경로의 관측이 아니게 됨. 세션은 `session_ended` 까지 정상으로 끝나고 화면이 그 세션의
결과 화면으로 이동했음(`/results/5cf40a76-…`).

⚠️ **화면은 `focus_pattern` 값을 읽지 않음** — 소비자는 회차와 로그임(`TASK-250` 노트가 같게
적어 둠). 이 회차의 판정은 프레임 계약에 대한 것이고 화면 표시에 대한 것이 아님.

## 6. 관측하지 않은 갈래 하나 — 그 사실을 적어 둠

계약에는 갈래가 하나 더 있음: 「계획이 없으면 대체할 자리가 없어 키만 세션 행에 남음」(AS4 규약).
**이 회차는 그것을 재지 않았음** — 재려면 최신 `session_plans` 행을 없애야 하고, 그것은 회차가
만들지 않은 기존 행의 삭제라 허용 범위 밖임. 그 갈래는 AC#3(「즉시 드릴을 만드는 경로가 성립함」)
의 구성 요소가 아니라 계획 부재 시의 퇴화 동작이므로 판정에 쓰지 않았음.

## 7. 판정

**`TS-36` AC#3 을 체크하고 시나리오를 `Done` 으로 올림.**

근거 넷이 모두 성립함: ⑴ 화면이 패턴을 보여 주고 누를 자리를 줌(B8) ⑵ 누른 것이 세션을 열고
그 키가 세션 행에 남음(B8 · 이 회차 재확인) ⑶ **지시문의 초점이 그 패턴으로 실제로 대체됨**
(팔 A·A′) ⑷ **대체가 일어나지 않은 경우에는 보고하지 않음**(팔 B·C).

⛔ 「방금 고쳐진 것」이라고 관대하게 보지 않았음 — 고친 쪽이 통과한다고 한 것을 근거로 쓰지 않고
팔 넷을 직접 돌려 프레임에서 값을 읽었음. 고친 쪽이 판별력 근거로 든 인프로세스 통합 검사는
이 판정에 쓰지 않았음(`TS-4` 노트와 같은 규약).

**새로 실패 0건 · 차단 0건 · 새로 등록한 결함 0건.**

기존 결함과 뿌리가 겹치는지 먼저 봤음: `TASK-250` 은 이 회차가 관측으로 닫은 자리이고 이미
`Done` 임. `TASK-251`(말로 하는 요청 경로 A 가 코드에 없음)은 이 회차의 관측 대상이 아니며
B8 이 이미 등록해 열려 있음 — AC#3 판정에 쓰지 않은 것도 B8 과 같음.

## 8. 정리

| 항목 | 확인 |
|---|---|
| 회차가 만든 세션 | 5건 — `a331a4e5`(A) · `1bd11c50`(B) · `1e755344`(C) · `5cf40a76`(A′) · `731770c9`(C 재현) |
| teardown | 5건 모두 `session_deleted: 1` · 잔존 0건 · 매달린 `analysis_jobs` 잔존 0건 |
| 세션 수 | 기준선 27 → 회차 중 32 → **정리 뒤 27** |
| 시드 되돌림 | `daily_error_summary` 오늘 행 **없음** = 기준선과 같음 |
| Orca 탭 | 닫았음(`closed: true`) |
| 임시 파일 | `/tmp/b9_*` 지웠음 |
| 워커 | 켜지 않았음 · 유료 호출 0건 |

## 9. 증거

- `evidence/TS-36-armA-session-started.json` — 팔 A 프레임 전체
- `evidence/TS-36-armA-browser-session-started.json` — 팔 A′ (소켓 주소 · 프레임 · 주입 생존)
- `evidence/TS-36-armB-session-started.json` — 팔 B (키 부재)
- `evidence/TS-36-armC-session-started.json` · `TS-36-armC-repeat-session-started.json` — 팔 C 와 재현
- `evidence/TS-36-session-rows-three-arms.txt` — 세션 행 셋
- `evidence/00-no-paid-calls.txt` · `evidence/99-cleanup-verified.txt` · `evidence/TS-36-daily-seed-restored.txt`
- 드라이버: `ts36_focus_frame_driver.py` (이 회차가 씀) · `../2026-09-19-b8/ts36_daily_seed.py` (재사용)
