# 회차 — `TASK-66.7`: 합성 클립 오디오가 앱 경로에서 재생되는지 브라우저로 확인한다

세션 `ohmyenglish-f4` · 2026-09-14 KST · 브랜치 `design/first-vertical-slice`
회차 디렉터리: `tests/harness/runs/2026-09-14-task66-clip-audio/`

> **왜 브라우저가 필요한가**: 단위·통합은 서버가 바이트를 내주는 것까지만 잰다. 「패널이 뜨고
> 버튼이 눌리고 그 클릭이 오디오를 **설정된 속도로** 열고 **반복**한다」는 화면 쪽 사실이고,
> 프런트 테스트 인프라가 0이라(2026-09-14 실측) 이 회차가 그 축의 유일한 증거다.
> ⛔ **사람 청취는 이 회차가 닫지 못한다** — §5 가 그것을 미결로 남긴다.

---

## 0. 스택 — 공유 자원을 건드리지 않았다

| 무엇 | 값 |
|---|---|
| DB | 검증 전용 `ohmy_clipcheck`(`createdb` + `migrate.py` 전체 · 마이그레이션 **20건** = 파일 전부) |
| 백엔드 | `:8012` · `VOICE_ADAPTER` 기본값 `stub` · `WORKER_ENABLED=false` · **`SHADOWING_PLAYBACK_RATE=1.5`** · **`SHADOWING_REPEAT_COUNT=2`** |
| 프런트 | 리포의 `app/frontend` 를 `next dev --port 3000` · `NEXT_PUBLIC_API_BASE=http://127.0.0.1:8012` |
| CORS | 앱 코드를 고치지 않았다 — `FRONTEND_ORIGIN` 이 `:3000` 이므로 그 포트를 그대로 썼다 |
| 브라우저 | 전용 Chrome — `--remote-debugging-port=9333 --user-data-dir=/tmp/chrome-clipcheck --use-fake-device-for-media-stream --use-fake-ui-for-media-stream --autoplay-policy=no-user-gesture-required` |

⚠️ 회차 시작 시점에 `:3000`·`:8002` 가 **비어 있었다**(`lsof -sTCP:LISTEN` 로 확인) — 공유 스택이 떠
있었다면 다른 포트와 CORS 래퍼가 필요했다(`H-BC`).
⛔ 설정값을 기본(1.0배·1회)이 아닌 값으로 준 것이 의도다 — **기본값이면 「적용됐는가」를 가릴 수
없다**(항등원이라 적용 여부가 관측에 나타나지 않는다).

## 1. 확인한 것 넷 — 전부 직접 돌려 얻은 출력

**⑴ 패널이 뜨고 전사문이 화면에 있다** (`leg-with-audio.log`):

```
패널 제목: A morning routine before work
전사문: I usually wake up at seven. First, I check my phone for messages. …
```

**⑵ 오디오가 실제로 흐른다** — 브라우저가 백엔드에서 받은 WAV 를 디코드해 재생했다:

```
play 호출: [{"src": "http://127.0.0.1:8012/api/shadowing/clips/…201/audio", "rate": 1.5, …}]
오디오 상태: {"rate": 1.5, "paused": false, "currentTime": 2.215661, "duration": 17.36,
              "readyState": 4, "src": "http://127.0.0.1:8012/…/audio"}
```

⛔ **`duration` 17.36 이 시드의 `clip_end_sec` 과 같다** — 「시간 창이 곧 오디오 전체」라는 설계가
브라우저 층에서 교차 확인됐다. ⚠️ `src` 가 `:8012` 인 것이 `API_BASE` 를 쓴 증거다(상대 경로였다면
`:3000` 으로 갔고 404 였다 — §4 의 결함 하나가 그것이었다).

**⑶ 반복이 설정대로 멈춘다** — `ended` 를 일으켜 내 핸들러를 쟀다:

```
ended 뒤 play 호출 수: 2 (기대 2)
두 번째 ended 뒤 play 호출 수: 2
멈춘 뒤 버튼 문면: 클립 듣기
```

⚠️ **23초를 기다리지 않았다** — 클립이 17.36초이고 두 번이면 그 이상이다. 브라우저가 재생 끝에 하는
일(`ended` 발화)을 CDP 로 일으켜 **핸들러의 셈**을 쟀다. 셋째 `ended` 에서 늘지 않는 것이 상한이
`repeat_count` 임을 말한다.

**⑷ 오디오가 없으면 버튼이 사라진다** (`leg-no-audio.log` · `audio_filename` 을 null 로 바꾼 뒤):

```
버튼 목록: ["학습 종료"]
안내 문구: 이 클립은 소리가 아직 없어요
play 호출 수: 0 (기대 0)
```

**스크린샷 셋을 직접 열어 봤다**: `panel.png` · `playing.png`(버튼이 「멈추기」) ·
`no-audio.png`(버튼이 없고 안내만 있다).

## 2. ⛔ 회차의 개입 하나 — 숨기지 않고 적는다

스텁 어댑터가 세션을 곧 닫아 **패널이 뜬 창이 1초를 못 넘겼다**(첫 시도에서 화면이 이미 결과로
넘어가 「재생 버튼이 없다」로 끝났다 — `H-BD` 아래 적힌 앞 회차의 경고와 같은 형태다).

그래서 브라우저에서 **`session_ended` 프레임과 소켓 `close` 둘만 붙잡았다**(`clip_leg.py` 의
`INSTALL_HOOKS`). 재는 대상은 그 둘과 무관하다 — 패널 렌더는 `session_started` 가 만들고, 오디오는
백엔드로 가는 **별개의 HTTP GET** 이며, 속도·반복은 클라이언트 안의 일이다.
⚠️ 실물 세션(Nova)에서는 대화 동안 창이 열려 있으므로 이 개입이 필요하지 않다.

## 3. 정리와 무변경 확인 — 직접 돌려 얻은 값

| 무엇 | 확인 |
|---|---|
| 전용 Chrome · 프런트 · 백엔드 | 전부 종료 — `:3000`·`:8012`·`:9333` 이 **`000`**(연결 불가) |
| 검증 전용 DB | `dropdb ohmy_clipcheck` **exit 0** |
| `/tmp` 흔적 | `chrome-clipcheck`·`qwen_out` 삭제 |
| **공유 dev DB** | `schema_migrations` **17** · `shadowing_items` **1행** · `clip_end_sec` **`16.64`** |

⛔ **dev DB 의 시간 창이 `16.64` 로 남아 있는 것이 「내가 022 를 적용하지 않았다」는 증거다** —
리포 상수는 `17.36` 이고 그 동기화는 `TASK-66.9`(승인 사안)의 몫이다.
⛔ **Nova·Claude 호출 0건** — 어댑터가 스텁이다.

## 4. 이 회차가 잡은 결함 하나 — 회차 전에 고쳤다

`ShadowingPanel` 이 오디오 주소를 **상대 경로**(`/api/shadowing/...`)로 만들고 있었다. 프런트는
`:3000`, 백엔드는 다른 포트이므로 그 요청은 Next 개발 서버로 가서 404 가 된다.
⇒ `lib/config.ts` 의 `API_BASE` 를 쓰도록 고쳤다(`lib/api.ts` 가 세운 규약).
⚠️ **단위·통합 게이트로는 잡히지 않는 부류다** — 프런트 테스트가 0이고, 백엔드 단정은 자기 포트로
직접 부르므로 주소 조립이 재지지 않는다. 이 회차의 값어치가 그 자리에 있다.

## 5. 이 회차가 닫지 못한 것

- ⛔ **사람 청취.** 합성음이 학습에 쓸 만한 소리인지는 사람이 들어야 판정된다 — 2026-09-09 선행
  검토 §8 이 남긴 미결이 그대로 남아 있다. 이 회차가 말할 수 있는 것은 **「브라우저가 그 파일을
  디코드해 재생했다」**까지다(`readyState` 4 · `currentTime` 이 흘렀다).
- **`playbackRate` 가 `0.5~2.0` 전 구간에서 음질을 유지하는지** 재지 않았다 — 1.5 하나만 걸었다.
- **실물 Nova 세션에서의 창 길이**를 재지 않았다 — 스텁으로 확인했고, 실물에서는 대화 동안 열려
  있을 것이라는 추정이다.
