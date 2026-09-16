# 회차 — `TASK-61.15` AC#4: 버린 명령에 「거절」을 돌려주면 코치가 무엇을 말하는가

세션 `ohmyenglish-42` · 2026-09-16 KST · 구현 커밋 `0cf036c`(결정 118) ·
절차 정본 `tests/harness/browser_leg.md` · 드라이버 `tests/harness/p_app_path.py`

> 무엇을 재는가: 결정 118 의 고침이 **코치의 말을 앱의 상태에 맞췄는가.**
> 앞 회차가 이 자리에서 **4/4 로 「됐다」**를 관측했다
> (`runs/2026-09-16-task61-15-accepted-without-execution` §2-1) — 같은 조건으로 다시 밟는다.
>
> ⛔ **비교 대상이 명확하다** — 같은 픽스처(`vc27_end_nomarker_en` 등)와 같은 조건(표지 없는 명령)이고
> 바뀐 것은 어댑터가 결과를 **언제·무엇으로** 보내는가 하나다.

---

## 0. 스택과 상한

| 무엇 | 값 |
|---|---|
| DB | 검증 전용 `ohmyenglish_t6115c`(`schema_migrations` **23**) |
| 백엔드 | `:8012` · 래퍼 `/tmp/t6115c_app.py` — **양방향 계측**(들어온 제어 이벤트 + **나가는 실행 보고**) |
| 프론트 | 사본 `/tmp/fe-t6115c`(`:3001`) |
| 브라우저 | 전용 Chrome `:9333`(**152.0.7977.83**) |
| 상한 | Nova **3세션**(팔 3개) · Claude **0회** |

⚠️ **계측을 한 방향 더 넓혔음** — 이 회차의 물음이 「무엇이 나갔는가」이므로
`NovaVoiceAdapter.report_command_outcome` 을 감싸 `executed`·`reason`·`toolUseId` 를 남겼다.
앞 회차들은 들어오는 방향만 봤다.

---

## 1. 관측 — 팔 셋

| 팔 | 표지 | 실행 보고 | 코치가 마지막에 한 말 | 세션 |
|---|---|---|---|---|
| `r1-rejected-end-en` | 없음 | `executed=False reason='no_wake_word'` | *"Sorry, I still need the wake word. Please say "Hey" or "Oh My English" and then ask to end the session."* | 안 닫힘 |
| `r2-rejected-end-ko` | 없음 | 같은 보고 **2건** | *"I still need the wake word. Please say Hey or Oh My English and then ask to end the session."* | 안 닫힘 |
| `r3-accepted-end-en` | **있음** | `executed=True` **2건**(`requested`·`confirmed`) | (결과 화면으로 넘어가 발화 없음) | **닫힘**(`recv.session_ended` 1) |

제어 이벤트 **5건** · 실행 보고 **5건**(둘이 1:1 로 맞는다 — 보고를 빠뜨린 명령이 없다) ·
표지없음 warning **3건** · 세션 셋 전부 `completed`.

### 1-1. 앞 회차와의 대조 — 이것이 이 회차의 전부다

| | 앞 회차(결정 118 전) | 이 회차(결정 118 뒤) |
|---|---|---|
| 같은 조건에서 코치가 한 말 | *"Okay, the session has ended. Thank you for talking with me today!"* · **4/4** | *"I still need the wake word …"* · **2/2** |
| 앱의 상태 | 세션 살아 있음 | 세션 살아 있음(같음) |
| 둘이 맞는가 | ⛔ **아니오** | ✅ **예** |

⇒ **거짓 완료가 사라졌다.** 그리고 코치의 말이 **학습자가 다음에 할 일**을 담았다(표지를 붙여 다시
말하기) — 화면 알림(결정 113)이 같은 것을 말하고 있으므로 두 채널이 같은 사실을 말한다.

### 1-2. 정상 경로가 죽지 않았는가 — 예

`r3` 에서 `executed=True` 가 두 번 나가고 세션이 **실제로 닫혔다**(`recv.session_ended` 1).
⛔ 결정 109 가 고친 침묵(결과가 없어 코치가 그 턴을 이어 말하지 못하는 것)이 되돌아오지 않았다 —
그것이 이 회차가 대조 팔을 둔 이유다.

---

## 2. 판정 — AC#4 를 닫음. `TASK-61.15` 를 닫음

- **거절 보고 → 코치가 「안 됐다」**: **2/2**(영어·한국어).
- **정상 보고 → 세션이 닫힘**: **1/1**.
- **보고 누락**: **0건**(제어 이벤트 5 = 실행 보고 5 · 「실행 보고를 못 받은 제어 tool」 warning 0건).

⚠️ **표본이 작다**(팔 셋). 그리고 ⛔ **문면으로 거동을 보장하지 못한다는 결정 112 는 그대로다** —
이 회차가 보인 것은 「맞는 사실을 주면 모델이 맞게 말한 사례 2건」이고, 학습자에게 보이는 보장은
여전히 **화면 알림**이 갖는다.

---

## 3. teardown — 이 턴에 직접 돌린 출력

| 대상 | 결과 |
|---|---|
| `:8012` · `:3001` · `:9333` | 전부 HTTP **000** |
| 검증 전용 DB | `dropdb ohmyenglish_t6115c` 성공 |
| `/tmp` 사본 | `fe-t6115c` · `chrome-t6115c` · `t6115c_app.py` · 회차 로그 삭제 · 잔여 **0건** |
| 공유 dev DB | 손대지 않았음 — `schema_migrations` **23** · `learning_sessions` **17** |
| 리포에 남긴 것 | 이 디렉터리(관측 JSON 3 · `control-events.log` · `warnings.log` · `sessions.tsv` · `utterances.tsv` · 스크린샷 6) · 새 픽스처 0건 |
