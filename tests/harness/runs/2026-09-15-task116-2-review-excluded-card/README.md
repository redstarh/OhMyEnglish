# 회차 — `TASK-116.2`(결정 95 화면 표시) + `TASK-128.4` AC#1(진입 안내 문구)

세션 `ohmyenglish-65` · 2026-09-15 KST · 실물 모델 사용 **0**(Nova 0 · Claude 0) —
`VOICE_ADAPTER=stub` 으로 충분한 관측이다

> ⛔ **재는 것이 화면이다.** 기록 경로는 `runs/2026-09-15-task116-3-verdict-condition` 이 이미 쟀고
> 여기서 다시 세지 않는다. 그래서 `sound_check` 를 **SQL 로 직접 넣었다**(하네스 개입이며 제품
> 경로가 만든 값이 아니다 — `setup.py.txt` 가 그것을 명시한다).

---

## 0. 스택 — 공유 자원을 건드리지 않는다

| 무엇 | 값 |
|---|---|
| DB | 검증 전용 `ohmyenglish_t1162`(마이그레이션 024) |
| 백엔드 | `:8012` · 래퍼 `/tmp/t1162_app.py`(사본 프론트 origin 을 CORS 에 더함) · `VOICE_ADAPTER=stub` · `WORKER_ENABLED=false` |
| 프론트 | 사본 `/tmp/fe-t1162` · `.env.local` 이 `:8012` 를 가리킴 · `next dev --port 3001` |
| 브라우저 | 전용 Chrome `:9333`(진입 관측 때는 가짜 오디오 장치 플래그를 더해 띄웠다 — 함정 `H-BD`) |
| 공유 자원 | `:3000`·`:8002`·공유 dev DB·다른 세션의 Chrome(`:9222`)을 **건드리지 않았다** |

**dev DB**: 회차 전후가 같다 — `learning_sessions=17` · `pronunciation_attempts=7` ·
`error_patterns=9` · `session_plans=6` · `utterances=128` · `review_tasks=15`.

## 1. `TASK-116.2` — 검증에 걸린 시도의 카드

**착수 전 코드 확인(AC#1)**: 결과 API 가 `sound_check` 를 **아예 내보내지 않았다** —
`_PRONUNCIATION_SQL` 이 그 컬럼을 뽑지 않고 `_pronunciation_payload` 에도 키가 없었다.
⇒ 화면이 그 사실을 알 수단이 없었다.

**고친 것**(TDD · 실패를 먼저 봤다: `KeyError: 'review_excluded'`):

| 자리 | 무엇 |
|---|---|
| `services/results.py` | 조회에 `sound_check` 를 더하고 `PronunciationAttempt` 에 **`review_excluded: bool`** 을 둔다 — ⛔ 판정값 자체를 담지 않는다(그것도 기계 키다). 값은 `pronunciation.SOUND_CHECK_MISMATCHED` 상수와 비교해 만든다 |
| `api/results.py` | 페이로드에 `review_excluded` 를 싣는다 |
| `lib/api.ts` | 타입에 `review_excluded: boolean` 을 더한다 |
| `results/[sessionId]/page.tsx` | 판정 줄 **아래**에 문구를 붙인다 — 위에 붙이면 판정보다 먼저 읽혀 「이 시도는 무효」로 보인다 |

**문구는 사용자가 2026-09-15 에 승인했다**: `기록만 했어요 · 복습에는 쓰지 않아요`.
⛔ 기각된 안: 「코치가 말한 소리와 달라서…」(내부 사정을 화면에 증명한다) · 「복습에는 쓰지 않아요」만
(기록이 남았다는 안심이 없어 시도가 무시된 것으로 읽힌다).

**API 실측**: `review_excluded: true` 가 어긋난 행에 실렸다.

**화면 실측**(`shot.py.txt` 가 읽은 카드 줄 · `shot-results.png`):

```
카드 ①  시범 문장 / early / 내 발화 / early / ✓ 좋아요 / 기록만 했어요 · 복습에는 쓰지 않아요
카드 ②  시범 문장 / I think it's three. / 내 발화 / I sink it's sree. / 다시 연습해요
```

⚠️ **반대 방향을 같은 화면에서 봤다** — 정상 카드(②)에는 그 줄이 **없다**. ⛔ 이것이 없으면
「모든 카드에 문구가 붙는」 실패를 못 잡는다. 단위 테스트도 같은 두 방향을 못 박는다
(`test_a_mismatched_attempt_is_flagged_as_excluded_from_review`).
**스크린샷을 내가 직접 열어 봤다** — 문구가 muted 색으로 판정 줄 아래에 붙었다.

## 2. `TASK-128.4` AC#1 — 진입 안내 문구

**코드는 이미 참을 말하고 있었다**(결정 83 으로 승인된 문구 둘 · `page.tsx:81-83`). 남은 것은
**화면에서 실제로 그렇게 뜨는지**였고 그것이 이 AC 다.

⚠️ **폴링으로는 못 잡았다** — stub 어댑터에서 세션이 곧 끝나 결과 화면으로 넘어간다. 100ms 폴링 ·
1.2초 · 15초 대기가 **모두 결과 화면만** 봤다. ⇒ 클릭 **전**에 `MutationObserver` 를 걸어 한 번이라도
그려진 문장을 모으는 방식으로 바꿨다(`enter.py.txt`).

**관측된 문구**(`fixture DB 에 발음 패턴 0건 = 후보 0건`):

```
발음 연습으로 시작했어요. 오늘 다룰 소리는 대화에서 듣고 고를 거예요.
```

⇒ **전용 세션임을 참으로 말하고**(「발음 연습으로 시작했어요」) **후보가 없다는 것을 폴백이라 말하지
않는다**(「대화에서 듣고 고를 거예요」). `learning_sessions.mode` 도 `pronunciation` 으로 기록됐다.
⇒ AC#1 충족.

⚠️ 함께 관측된 문장 이력: `마이크 권한을 요청하는 중입니다...` → 진입 문구 → stub 의 정해진 대화 →
`결과를 불러오는 중입니다...`. 즉 진입 문구는 **세션이 살아 있는 짧은 창**에만 있다.

## 3. 게이트 (직접 돌린 출력)

`pytest` **1198 passed**(13.04s) · `ruff check .` · `ruff format --check .` **48 files** ·
`ty check` — 넷 다 exit 0. 프론트는 `npx tsc --noEmit` **exit 0** · `npx eslint .` 출력 0줄.

## 4. 정리 — 직접 돌려 얻은 값

| 무엇 | 확인 |
|---|---|
| `:8012` · `:3001` · `:9333` | 전부 HTTP **`000`** |
| 검증 전용 DB | `dropdb ohmyenglish_t1162` exit 0 |
| `/tmp` 사본 | `fe-t1162` · `chrome-t1162` · `t1162_app.py` 삭제 |
| 공유 dev DB | 회차 전후가 **같다**(위 §0 의 여섯 값) |
| 다른 세션의 Chrome | `:9222` **200**(살아 있다) |
