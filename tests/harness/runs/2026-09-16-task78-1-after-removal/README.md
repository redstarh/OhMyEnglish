# 회차 — `TASK-78.1` AC#3: 보조 신호 경로를 지운 뒤에도 발음 신호가 0 이 되지 않는가

세션 `ohmyenglish-43` · 2026-09-16 KST · 제거 커밋 `33c15f5`(결정 120) ·
드라이버 `tests/harness/ws_session.py --wav`

> 무엇을 재는가: **지운 뒤 실물 세션에서 발음 신호가 실제로 남는가.** AC#3 의 문면 그대로다.
> ⛔ **브라우저를 쓰지 않았다** — `/ws/session` 이 base64 오디오 프레임을 받으므로 마이크·Chrome
> 없이 같은 앱 경로를 지난다(`ws_session.py` 의 `--wav` 가 그 목적으로 만들어졌다).
> ⚠️ **모델 팔은 실물이다** — `VOICE_ADAPTER=nova` 로 Nova **1세션**을 썼다. Claude 0회.

---

## 0. 스택 — 공유 자원을 건드리지 않음

| 무엇 | 값 |
|---|---|
| DB | 검증 전용 `ohmyenglish_t781b`(소유자 `ohmy` · `schema_migrations` **23**) · 회차 뒤 drop |
| 백엔드 | `:8013` · `VOICE_ADAPTER=nova` · `WORKER_ENABLED=false` · 앱 코드 그대로(래퍼 없음) |
| 오디오 | `pq13.wav`("My blother will allive ealy tomollow molning." · /r/→/l/) → `pq13a.wav`(정답판) |
| 진입 | `?mode=pronunciation` — 오늘의 소리 후보로 `error_patterns` 1행(`r_as_l`)을 심었다 |
| 공유 자원 | `:8002` · 공유 dev DB · `:3000` 을 건드리지 않았다 |

기준선(심은 뒤 · 회차 전 직접 조회): `pronunciation_attempts=0` · `utterances=0` ·
`learning_sessions=0` · `analysis_jobs=0`.

⚠️ **심은 것을 숨기지 않는다** — 발음 전용 진입은 오늘의 소리를 못 고르면 말하기로 떨어지므로
(`api/ws.py` 의 규약) 후보 1행이 없으면 이 회차의 물음에 도달하지 못한다. 심은 것은 **후보**이고
관측 대상인 **시도 행**은 심지 않았다.

## 1. 관측 — 코치가 발음을 코칭하고 앱이 그것을 기록했다

코치의 마지막 발화(원문 `T781B-frames.json`):

> *"I heard you say "My brother will arrive early tomorrow morning." I noticed a small
> pronunciation issue with the "r" sound in "brother." … Can you repeat the word "brother" for me?"*

DB(`db-after.txt`):

| `signal_source` | `outcome` | `target_sound` | `sound_check` | 패턴 연결 |
|---|---|---|---|---|
| **`nova_tool`** | `incorrect` | **`r_as_l`** | **`matched`** | **연결됨** |

집계: `pronunciation_attempts` **1** · `signal_source <> 'nova_tool'` **0건** ·
`utterances` **3**(전부 `learning`) · `analysis_jobs` **4** · 패턴 `frequency` **1** ·
`next_review_at` **설정됨** · 세션 `mode=pronunciation` · `status=completed` ·
백엔드 `warning` **0건**.

## 2. 판정 — AC#3 충족

1. **발음 신호가 0 이 아니다.** 우회로를 지운 코드에서 실물 세션 1회가 `nova_tool` 행 1건을
   남겼고, 패턴 연결과 복습 시계 전진까지 갔다 — 우회로가 하던 몫이 없어도 파이프라인이 돈다.
   ⚠️ 애초에 우회로는 51세션에서 입력이 0 이었으므로 이 결과가 예상과 같다. 그 예상을
   **관측으로 갚은 것**이 이 회차다.
2. **`sound_check=matched`** — 오염 방어(결정 82·98)가 정상 기록을 배제하지 않았다. 코치가 코칭한
   소리(`"r"`)와 실린 키(`r_as_l`)가 맞다.
3. **게이트웨이의 갈래 재구성이 아무것도 깨지 않았다.** 제거와 함께 `if speaker == "user"` 를
   `if speaker != "user"` 로 바꿨는데, 학습 발화 **3건이 모두 저장**되고 분석 job **4건**이 걸렸다.
   ⛔ 그 두 수치가 이 변경의 유일한 위험(학습 발화가 agent 갈래로 떨어져 flush 가 어긋나는 것)을
   직접 반증한다.

## 3. 이 회차가 말하지 않는 것

- **tool 도착률을 다시 재지 않았다** — 표본 1세션이다. 도착률은 제거 «전»에 측정된 값
  (코칭 세션 11/11)이고 제거가 Nova 어댑터를 건드리지 않았으므로 이 회차의 물음이 아니다.
- **Nova tool 이 안 올 때의 대비가 사라진 사실**은 그대로다(결정 120 이 그 대가를 명시했다).

## 4. 재현 절차

```bash
cd ~/MyProject/OhMyEnglish
/opt/homebrew/opt/postgresql@17/bin/psql "postgresql://ohmy:ohmy@localhost:5432/postgres" \
  -c "create database ohmyenglish_t781b owner ohmy"
DATABASE_URL="postgresql://ohmy:ohmy@localhost:5432/ohmyenglish_t781b" \
  app/backend/.venv/bin/python scripts/migrate.py
/opt/homebrew/opt/postgresql@17/bin/psql "postgresql://ohmy:ohmy@localhost:5432/ohmyenglish_t781b" \
  -c "insert into error_patterns (user_id, category, pattern_key, target_form, frequency)
      values ('00000000-0000-0000-0000-000000000001','pronunciation_intonation',
              'pronunciation_r_as_l','r_as_l',1)"
cd app/backend && DATABASE_URL="postgresql://ohmy:ohmy@localhost:5432/ohmyenglish_t781b" \
  VOICE_ADAPTER=nova WORKER_ENABLED=false ./.venv/bin/uvicorn app.api.main:app --port 8013 &
./.venv/bin/python ../../tests/harness/ws_session.py --scenario T781B --mode pronunciation \
  --wav pq13.wav,pq13a.wav --url ws://localhost:8013/ws/session --timeout 120
# 끝나면 백엔드를 죽이고 DB 를 drop 한다
```

⚠️ **`--url` 을 빼면 공유 dev 백엔드(`:8002`)로 간다** — 그러면 공유 dev DB 가 오염된다(`H-BC`).
