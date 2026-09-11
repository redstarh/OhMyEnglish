# 회차 — `TASK-10.2` AC#3: 추가 학습 진입을 **브라우저**로 확인한다

세션 `ohmyenglish-7f` 후속 · 2026-09-12 KST · 브랜치 `design/first-vertical-slice`
회차 디렉터리: `tests/harness/runs/2026-09-12-task10-2-entry-browser-leg/`

> **왜 브라우저가 필요한가**: 단위·통합 테스트는 서버 배선만 잰다. 「버튼이 있고 눌리고 그 클릭이
> `?mode=pronunciation&source=additional` 로 붙는다」는 **화면 쪽 사실**이다. AC#3 이 그것을
> *"단위·통합만으로 닫지 않는다"* 로 요구했다.
>
> ⛔ **이 회차가 함정 둘을 실제로 우회했다** — `H-AE`(합성 클릭은 user activation 을 만들지 않는다)와
> **`H-BD`(CDP 에서 마이크가 열리지 않는다)**. 후자는 지금까지 이 리포의 브라우저 레그를 음성 경로에
> 대해 **통째로 막고 있었다.**

---

## 0. 스택 — 공유 자원을 건드리지 않는다

| 무엇 | 값 |
|---|---|
| DB | 검증 전용 `ohmyenglish_uicheck`(`createdb` + `migrate.py` + 발음 패턴 1행) |
| 백엔드 | `:8012` · **`VOICE_ADAPTER=stub`**(진입을 재는 회차라 Nova 를 쓰지 않는다) · `WORKER_ENABLED=false` |
| CORS | `/tmp/uicheck_app.py` 래퍼가 `:3001` 을 허용한다 — ⛔ 앱 코드를 고치지 않는다(`H-BC`) |
| 프론트 | `/tmp/fe-uicheck`(`cp -Rc` 로 **2.7초**) · `.env.local` 이 `:8012` 를 가리킨다 · `next dev --port 3001` |
| 브라우저 | **전용 Chrome 152.0.7977.83** — `--remote-debugging-port=9333 --user-data-dir=/tmp/chrome-uicheck --use-fake-ui-for-media-stream --use-fake-device-for-media-stream --autoplay-policy=no-user-gesture-required` |

⛔ 공유 스택(`:3000` 프론트 · `:8002` 백엔드)은 **그대로 뒀다** — 다른 세션이 쓰고 있고, 그쪽 DB 에
세션을 남기면 baseline 대조(`H-AY`)를 오염시킨다.

## 1. 결과 — 메뉴 여섯이 뜨고 두 경로가 갈렸다

**⑴ 메뉴**(설계서 §2 그대로):

```
버튼 목록: ['학습 시작', '자유 대화', '약점 패턴 집중', '질문 답변 5개', '발음 집중', '쉐도잉',
            '업무 역할극 (무대를 고르는 화면이 아직 없어요)']
비활성 버튼: ['업무 역할극 (무대를 고르는 화면이 아직 없어요)']
```

⛔ **항목이 여섯이고 업무 역할극만 비활성이다** — 설계서 §1 이 적은 PRD 내부 어긋남(§7 은 다섯,
R10-5 는 발음 집중을 독립 항목으로 요구)을 화면이 여섯으로 해소하고, 표면이 없는 하나를 **숨기지
않고 비활성으로** 보인다.

**⑵ user activation**: `navigator.userActivation.hasBeenActive` = **`True`**(무해한 `h1` 을 CDP 입력으로
한 번 클릭한 뒤 — `H-AE` 의 대응 그대로).

**⑶ 진입 안내 두 문면** — 소리가 있을 때와 없을 때가 갈렸다:

| 조건 | 화면에 뜬 줄 |
|---|---|
| 발음 패턴 1행 있음 | `발음 연습으로 시작했어요. 소리를 시범하고 다시 말하기를 부탁할 거예요.` |
| 그 행을 지운 뒤 | `오늘 다룰 소리가 아직 없어서 일반 대화로 시작했어요. 대화에서 소리가 모이면 이 연습이 열려요.` |

⛔ **둘째 경로에서 서버 경고가 1건 났다** — *"말하기 세션으로 진행한다"*. 즉 서버가 실제로 폴백했고
화면이 그것을 **말했다.** 그것이 AC#2 가 요구한 것이다.

**⑷ DB**: `learning_sessions` 4행이 전부 `learning_source='additional'` · `started_via='ui'` ·
`mode='speaking'`(설계대로 · `TASK-112`). ⇒ **메뉴 버튼의 진입 정보가 브라우저를 거쳐 DB 까지 닿았다.**

⚠️ **안내 줄을 폴링으로는 놓쳤다** — 스텁 어댑터가 세션을 곧 끝내고 화면이 결과로 넘어가므로 그 창이
짧다. **클릭 «전»에 `MutationObserver` 를 심어** 스냅샷을 전역에 모아 잡았다(결과 화면 이동이
클라이언트 라우팅이라 같은 문서가 유지된다). ⛔ **처음 판은 「안내가 없다」로 읽혔다** — 창이 짧은
것을 부재로 오독하는 형태다.

## 2. ⛔ `H-BD` 가 좁혀졌다 — 마이크는 «열 수 있다»

`H-BD` 는 *"CDP 로 몰 때 `getUserMedia` 가 응답하지 않아 세션이 시작되지 않는다"* 로 적혀 있고, 그
결과 **음성 경로의 브라우저 레그가 통째로 막혀 있었다**(`TASK-86` 의 앱 레그도 그 때문에 WS 직결로
우회했다). 이 회차가 그 서술의 범위를 좁힌다:

**막힌 것은 「CDP」가 아니라 「그 Chrome 에 오디오 장치가 없는 것」이다.**
`--use-fake-device-for-media-stream --use-fake-ui-for-media-stream` 으로 띄운 Chrome 에서는
`getUserMedia` 가 곧 resolve 하고 세션이 `active` 까지 갔다(세션 4건이 `completed` 로 닫혔다).

⇒ **앞으로 음성 경로의 브라우저 레그는 전용 Chrome 을 띄워서 한다.** 플러그인 Chrome 을 쓰지 않는
이유가 그것이다 — 그쪽은 그 플래그 없이 떠 있다.

## 3. 정리와 무변경 확인 — 직접 돌려 얻은 값

| 무엇 | 확인 |
|---|---|
| 전용 Chrome · 프론트 사본 · 래퍼 백엔드 | 전부 종료 — `:9333`·`:3001`·`:8012` 가 **`000`**(연결 불가) |
| 검증 전용 DB | `dropdb ohmyenglish_uicheck` **exit 0** |
| `/tmp` 사본 | `fe-uicheck`·`chrome-uicheck` 삭제 |
| 공유 dev DB | `learning_sessions` **17** · `error_patterns` **9** — 회차 앞 값과 같다 |
| 공유 스택 | `:3000`·`:8002` 를 **건드리지 않았다**(종료 대상에 넣지 않았다) |

⛔ **Nova·Claude 호출 0건** — 이 회차는 `VOICE_ADAPTER=stub` 이다. 진입을 재는 데 실물 음성이 필요하지
않고, 필요한 것(실물 왕복)은 `TASK-86` 이 이미 닫았다.
