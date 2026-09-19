# 배치 B2 회차 — TS-27 (A9 영상 학습) · TS-28 (A10 쉐도잉 클립 오디오)

## §1. 격리 수준 — 공유 인스턴스로 판정함

§2-6 규약에 따라 착수 전에 직접 확인했고, **공유**로 판정함.

| 확인 명령 | 결과 |
|---|---|
| `lsof -ti:8002` | `97888` — 호출 세션이 띄운 백엔드. 내가 띄운 것이 아님 |
| `lsof -ti:3000` | `98298` — 호출 세션이 띄운 프런트 |
| `find app/backend app/frontend -newermt '-30 minutes'` | 0건 — 회차 착수 시점에 다른 주체가 소스를 고치고 있지 않았음 |
| `orca tab list --json` | **탭 2개** — 다른 배치(`b1`)가 같은 브라우저의 `/results/...` 탭을 쓰고 있었음 |

적용한 규칙 셋:

1. **전역·공유 상태를 바꾸지 않았음.** 마이그레이션·`ALTER` 계열·DB 재시작·자격증명을 건드리지
   않았고, 백엔드·프런트 프로세스를 죽이거나 다시 띄우지 않았음.
2. **내가 만든 행만 되돌렸음.** 기존 행(`jNQXAC9IVRw` 영상 1건과 그 문장 1건, 시드 클립 1건)을
   지우지 않았음. 회차 끝 목록이 착수 시 목록과 같음(§6).
3. **전체 행 수를 판정에 쓰지 않았음.** `youtube_id` 를 키로 내 행만 골라 세었음 — 같은 시각에 도는
   `b1` 이 세션·결과 쪽 행을 늘릴 수 있기 때문임.

⚠️ **브라우저가 공유 자원이라 추가 규칙이 하나 더 필요했음.** `orca` 의 요소 참조(`e1`·`e2`…)는
**활성 탭 기준으로 재발급**되므로, `b1` 이 자기 탭에서 `snapshot` 을 뜨면 내 참조가
`browser_stale_ref` 로 죽었음(실측 2회). ⇒ 모든 `orca` 호출에 **`--page <내 browserPageId>` 를
명시**해 해결했음. 이 사실을 다음 회차가 알아야 하므로 적어 둠.

⚠️ **스크린샷을 얻지 못했음.** `orca screenshot` 이
`Screenshot timed out — the browser tab may not be visible or the window may not have focus` 로
실패했음 — 창 초점이 다른 배치와 경합하는 자리임. 판정은 §6 규약대로 `get`·`is`·접근성 스냅샷·API
응답·산출 파일로 했으므로 **판정 근거에는 영향이 없음**(스크린샷은 보조 증거임). 스냅샷 본문을
`evidence/TS-27-ac1-browser-snapshot.txt` · `evidence/TS-27-ac6-detail-snapshot.txt` 로 남겼음.

## §2. 환경 — 착수 시에 직접 재서 확인함

| 항목 | 값 |
|---|---|
| 착수 시 HEAD | `74fb5c0` (`design/first-vertical-slice`) |
| **회차 끝 HEAD** | **`81e150e`** — 회차 중 다른 배치가 커밋함 |
| 백엔드 | `:8002` · `/health` → `200` `{"status":"ok"}` · `WORKER_ENABLED=false` `VOICE_ADAPTER=stub` |
| 프런트 | `:3000` · `npm run dev` · `GET /videos` → `200` |
| DB | `postgresql://ohmy@localhost:5432/ohmyenglish` · `current_schema()` = **`ohmyenglish`** |
| Orca | `ready` · appVersion `1.4.205` |
| oEmbed 실호출 | `200` (2건 확인 — `9bZkp7q19f0` · `kJQP7kiw5Fk`) |

⛔ **HEAD 가 움직였으나 이 회차의 측정은 전부 같은 제품 코드에 대한 것임.**
`git diff --name-only 74fb5c0..81e150e -- app/ db/` 가 **0건**임 — `81e150e` 는 배치 `b1` 의 테스트
증거만 더했고 제품 코드·스키마를 건드리지 않았음. 그리고 백엔드는 `--reload` 없이 `74fb5c0` 에서
기동된 그대로였음. ⇒ 측정을 커밋별로 가를 필요가 없음.

⚠️ **호출자가 준 전제 중 어긋난 것 1건.** 「`git` 이 exit 69 로 죽으면 Xcode 라이선스 미동의
(`H-CH`)」를 전제로 받았으나, 이 회차에서는 `git` 이 정상 동작했음 — `git ls-files --error-unmatch`
가 `0`, `git check-ignore` 가 `1` 을 냈음(§4 의 TS-28 AC#1). `69` 는 한 번도 나오지 않았음. 그래도
**종료 코드를 `1` 과만 견주지 않고 `0`·`1`·`69` 셋으로 갈라** 판정했으므로 그 함정에 걸리지 않음을
증거로 남겼음.

## §3. 착수 시 테스트 원장 상태 — 회귀 비교의 기준선

```
In Progress:  TS-27 · TS-28   (이 배치의 범위)
Done:         TS-8 ~ TS-18    (이 영역의 이전 회차)
```

TS-27 의 AC 여섯이 겨누는 이전 시나리오: TS-8(AC#1) · TS-9(AC#2) · TS-10(AC#3) · TS-12·TS-13(AC#4) ·
TS-14(AC#5) · TS-17(AC#6). 전부 착수 시 `Done` 이었음.

## §4. 판정표

### TS-27 · A9 영상 학습 — **통과** (AC 6/6)

| AC | 판정 | 무엇을 어떻게 재서 갈랐나 | 근거 |
|---|---|---|---|
| #1 담기가 oEmbed 로 제목·채널을 받아 201 created=true | 통과 | **실제 브라우저 경로**로 `localhost:3000/videos` 에서 링크를 붙여 「확인」→「담기」를 눌렀음. 미리보기에 oEmbed 가 준 `PSY - GANGNAM STYLE(강남스타일) M/V` · `officialpsy` 가 나왔고, 담은 뒤 `status` 에 **「담았어요.」**(= `created===true` 분기의 문구)가 나왔음. 상태 코드는 같은 엔드포인트에 새 영상을 POST 해 **`http=201` `created:true`** 로 직접 읽었음 | AC 문면 |
| #2 URL 형태 넷이 같은 영상 한 행으로 모임 | 통과 | `watch?v=…&t=42s` → `201 created=true` · `youtu.be/` · `shorts/` · `embed/` → 셋 다 `200 created=false`. **네 응답의 `id` 가 동일**하고 목록에서 그 `youtube_id` 행 수가 **1** | AC 문면 |
| #3 비 YouTube 호스트·11자 아닌 id·유사 도메인이 422 | 통과 | 7건 전부 `422`: `vimeo.com` · `v=short` · `v=kJQP7kiw5FkTOOLONG` · `youtube.com.attacker.test` · `notyoutube.com` · 맨 식별자 · `myoutube.com`. **대조군**(정상 링크)은 같은 드라이버로 `200` | AC 문면 |
| #4 문장 값역이 422 · 영상 출처 문장에 오디오가 안 붙음 | 통과 | TS-12 의 AC **일곱 전부 `422`**(90초 초과·끝<시작·끝=시작·음수·빈 문장·1001자·접으면 같아지는 `5.0~5.001`). 대조군 정상 값은 `201`. 오디오 쪽은 두 겹으로 갈랐음 — ⑴ 앱 경로 `GET /api/shadowing/clips/{그 문장}/audio` → **`404`** ⑵ 스키마 제약 `shadowing_items_audio_only_for_synthetic` 이 **살아 있음**을 introspection 으로 확인하고, 내 행에 `audio_filename` UPDATE 를 **되돌리는 트랜잭션 안에서** 시도해 실제로 거부되는 것을 봤음(`rollback` 뒤 값이 `NULL` 그대로) | AC 문면 + 마이그레이션 022 |
| #5 영상을 지워도 문장이 남고 `youtube_video_id` 만 null | 통과 | `DELETE /api/videos/{id}` → `204`. 문장 행이 **남아 있고**(`rows_found=1`) `youtube_video_id` 가 `NULL` 로 바뀌었으며 `source_url` 은 `https://www.youtube.com/watch?v=kJQP7kiw5Fk` 그대로. 영상 행은 `0` | AC 문면 |
| #6 화면 `/videos` 와 `/videos/[videoId]` 가 200 으로 렌더 | 통과 | 둘 다 `200`. **HTTP 코드만으로 접지 않았음** — `/videos` 는 접근성 스냅샷에 목록 항목·「지우기」버튼·React 상태가 반영된 `[disabled]` 가 나와 하이드레이션까지 확인했고, `/videos/[videoId]` 는 YouTube 플레이어 iframe(`Luis Fonsi - Despacito…`)·「담은 문장」·낱말 버튼 8개·`0:01~0:06` 구간 표시가 나왔음 | AC 문면 |

### TS-28 · A10 쉐도잉 클립 오디오 — **통과** (AC 3/3)

| AC | 판정 | 무엇을 어떻게 재서 갈랐나 |
|---|---|---|
| #1 시드 클립 오디오가 200 이고 본문 길이가 0 이 아님 | 통과 | `GET /api/shadowing/clips/00000000-…-201/audio` → **`http=200` `bytes=559616` `content-type: audio/wav`**. 본문을 파일로 받아 `file(1)` 로 **`RIFF … WAVE audio, Microsoft PCM, 16 bit, mono 16000 Hz`** 를 확인했음(헤더만 믿지 않았음). 자산이 리포에 있는지도 확인함 — `assets/clips/00000000-…-201.wav` 가 `git ls-files --error-unmatch` **exit 0**(추적됨), `git check-ignore` **exit 1**(무시되지 않음). **`69` 가 아니므로 `H-CH` 에 걸리지 않았음** |
| #2 영상에서 담은 문장은 오디오가 없어 404 | 통과 | 이 회차가 담은 문장 `408d6cc5…` → **`404`** `{"detail":"clip audio not found"}`. 같은 드라이버가 시드 클립에는 `200`·559616바이트를 냈으므로 **관측력이 증명됨** |
| #3 없는 item_id 가 404 | 통과 | 없는 UUID → **`404`**. 곁가지로 꼴이 틀린 id → `422`, 경로 탈출 시도(`..%2F..%2Fetc%2Fpasswd`) → `404` 로 라우팅에서 막힘. 대조군(시드 클립) `200` |

## §5. 회귀 판정 — §9 의 4종으로 가름

기준선은 §3 의 테스트 원장 상태임.

| 분류 | 건수 | 내용 |
|---|---|---|
| **새로 실패** | **0건** | 이전 `Done` 이던 TS-8·9·10·12·13·14·17 이 겨누는 판정이 전부 지금도 성립함 |
| **고쳐짐** | 0건 | 착수 시 이 영역에 실패로 남은 것이 없었음 |
| **여전히 실패** | 0건 | 같음 |
| **새 시나리오** | 0건 | TS-27·TS-28 이 이미 원장에 있었음 |

### AC 밖에서 함께 확인한 이전 시나리오 — 설명서의 「TS-8~TS-18 회귀」 때문에 더 돌렸음

TS-27 의 AC 여섯은 TS-11·TS-15·TS-16·TS-18 을 문면에 담지 않음. 설명서는 「TS-8~TS-18 의 회귀 확인」
이라 적었으므로 **AC 밖이라도 돌릴 수 있는 것은 돌렸음.**

| 이전 시나리오 | 결과 | 측정 |
|---|---|---|
| TS-11 (반올림·level·`source_url` 정규화·`youtube_video_id`) | **여전히 통과** | `shorts/` 형태로 담았는데 저장된 `source_url` 이 **`watch?v=` 형태로 정규화**됐음. `level=A2` · `source_title` 이 영상 제목 · `youtube_video_id` 가 그 영상 · `audio_filename=NULL`. 반올림 `12.345→12.35` · `19.994→19.99` (HALF_UP) |
| TS-15 (다른 영상 경로로 문장을 지우면 404 이고 문장이 남음) | **여전히 통과** | 다른 영상 id 로 `DELETE …/phrases/{item}` → **`404`** `{"detail":"phrase not found"}`. 그 뒤 올바른 영상의 상세에 그 문장이 **그대로 1건** 있었음. **대조군**: 올바른 짝으로 같은 요청을 보내면 `204` 로 지워짐(정리 단계에서 확인) — 404 가 드라이버 고장이 아님을 증명함 |
| TS-18 (CORS 프리플라이트가 POST·DELETE 를 허용) | **여전히 통과** | `OPTIONS /api/videos` + `Origin: http://localhost:3000` 로 `POST`·`DELETE`·`GET` 셋 모두 `200` 이고 `access-control-allow-methods: GET, POST, DELETE` · `allow-origin` 이 요청 Origin 을 반영 |
| TS-16 (담은 문장 id 로 쉐도잉 세션이 열림) | **돌리지 않았음** | AC 문면 밖이고, **세션 행을 만드는 것이 같은 시각에 도는 배치 `b1` 의 자료**임(착수 지시 6번이 금지). 이 회차가 판정하지 않았음을 밝힘 — 통과로 세지 않음 |

### 추가로 두드린 경계 — AC 가 함축하나 이전 회차가 재지 않은 자리

| 경계 | 결과 |
|---|---|
| 호스트가 대문자(`WWW.YOUTUBE.COM`) | 받아들임(`200 created=false`, 같은 행). `urlparse().hostname` 이 소문자로 정규화하므로 의도대로임 |
| 모르는 필드를 섞음 (`extra="forbid"`) | 영상 몸통에 `youtube_id` 주입 → **`422`** · 문장 몸통에 `level`·`audio_filename` 주입 → **`422`**. 값역 우회 경로가 막혀 있음 |
| **같은 새 영상을 동시에 8건 담기(업서트 경쟁)** | **행이 1개**. `created=true` 가 정확히 **1건**, `created=false` 가 7건, 응답의 `video id` 가 **전부 동일**. 중복 행도 `500` 도 없었음 |

## §6. 파괴적 조작과 되돌린 결과

허용 범위 안에서만 했음 — 앱 경로를 통한 영상·문장 담기와 삭제 · oEmbed 실호출 · `/tmp` 쓰기.
마이그레이션·`ALTER` 계열·DB 재시작·자격증명 회전은 하지 않았고, **이 회차가 만들지 않은 기존 행을
지우지 않았음.**

| 이 회차가 만든 것 | 되돌렸나 |
|---|---|
| 영상 4건 (`9bZkp7q19f0` · `kJQP7kiw5Fk` 2회 · `dQw4w9WgXcQ`) | 되돌림 — `DELETE /api/videos/{id}` 로 4건 전부 `204` |
| 문장 2건 (`408d6cc5…` · `c451c05d…`) | **1건만 되돌림.** `c451c05d…` 는 `204` 로 지웠음 |

착수 시 목록과 회차 끝 목록이 **같음**: `jNQXAC9IVRw` / `Me at the zoo` / `jawed` / 담은 문장 1개.
`youtube_videos` 행 수 **1**.

⛔ **되돌리지 못한 것 1건 — 문장 `408d6cc5-da54-4f82-b3a7-69b32404ecd4` 가 남아 있음.**
AC#5 가 「영상을 지워도 문장이 남는가」를 재는 것이므로 그 측정 자체가 출처를 잃은 문장을 만들고,
**그 문장을 지울 앱 경로가 없음.** 이것은 내 실수가 아니라 제품의 표면이 그러함 — 아래 §7 에 관측으로
적었음. DB 에 직접 `delete` 를 넣는 것은 허용 범위 밖이므로 하지 않았고, 남은 사실을 여기 적음.

## §7. 등록한 결함 — **0건**. 다만 결함이 아닌 관측 1건을 남김

이 회차는 **TS-27·TS-28 의 AC 아홉이 전부 성립**했으므로 작업 원장에 결함을 등록하지 않았음.

### 관측 — 출처를 잃은 문장은 앱 경로로 지울 수 없음

**결함으로 올리지 않은 이유**: 설계서 §10-4 가 「출처를 잃은 문장의 화면 처리」를 **정하지 않은 것으로
명시**했음(*"지금은 기존 화면이 그대로 보여주고 특별한 표시를 하지 않음"*). 판정 우선순위 ②가 침묵이
아니라 **명시적 유보**를 말하므로, 이것은 어긋남이 아니라 알려진 미결임.

**측정**: `DELETE` 엔드포인트가 리포에 **둘뿐이고 둘 다 `video_id` 를 경로에 요구**함
(`videos.py:155` · `videos.py:190`). 화면도 `/videos` 와 `/videos/[videoId]` 둘뿐이라 영상에 매이지
않은 문장을 보여 주는 화면이 없음. 실제로 확인했음 — 지운 영상 id 로 `404`, 살아 있는 다른 영상 id
로도 `404`, 행은 그대로 남음(`orphan_rows=1`). **대조군**: 올바른 짝은 같은 경로로 `204` 가 되므로
드라이버 고장이 아님.

**제안**(§1 에 따라 고치지 않고 적기만 함): 영상에 매이지 않은 문장을 지울 경로를 하나 두는 것 —
예컨대 `DELETE /api/shadowing/items/{item_id}`. 대안은 「쉐도잉 목록 화면에서 지우기」를 만드는 것이고,
어느 쪽도 설계서 §10-4 를 여는 결정이 먼저 필요함. ⇒ **이 회차가 결정하지 않음.**

## §8. 증거 파일

전부 `tests/agent/runs/2026-09-19-b2/evidence/` 아래에 있음.

| 파일 | 무엇 |
|---|---|
| `TS-27-ac1-browser-snapshot.txt` | 브라우저로 담은 직후의 접근성 스냅샷 — 「담았어요.」 |
| `TS-27-ac1-oembed-raw.json` · `TS-27-ac1-ac2-console.txt` | oEmbed 원문과 형태 넷의 상태 코드·본문 |
| `TS-27-ac3-console.txt` + `TS-27-ac3-*.json` | 거부 7건과 대조군 |
| `TS-27-ac4-console.txt` + `TS-27-ac4-*.json` | 값역 일곱과 대조군 |
| `TS-27-ac4-schema-checks.txt` | `shadowing_items` CHECK 제약 9개와 내 행 |
| `TS-27-ac4-check-blocks-update.txt` | 되돌리는 트랜잭션 안의 UPDATE 가 제약에 막히는 원문 |
| `TS-27-ac5-delete-video.txt` | 영상 삭제 전후의 문장 행 |
| `TS-27-ac6-detail-snapshot.txt` | 영상 상세 화면의 접근성 스냅샷 |
| `TS-27-ts11-*` · `TS-27-ts15-*` | TS-11·TS-15 회귀 |
| `TS-27-cors-preflight.txt` | TS-18 회귀 |
| `TS-27-boundaries-console.txt` + `TS-27-bd-*.json` | 대문자 호스트·extra 필드·동시 8건 경쟁 |
| `TS-27-orphan-unreachable.txt` | §7 의 관측 |
| `TS-28-ac1-console.txt` · `TS-28-ac1-seeded-clip-headers.txt` · `TS-28-ac1-seeded-clip-head1k.bin` | 시드 클립 오디오. ⚠️ 본문 559616바이트 전체는 리포에 넣지 않고 앞 1024바이트만 남겼음 |
| `TS-28-ac2-video-phrase-audio.txt` · `TS-28-ac3-console.txt` | 404 갈림 둘 |
| `00-baseline-videos.json` · `99-cleanup.txt` | 착수 시 목록과 정리 결과 |

## §9. 이 회차가 판정하지 않은 것 — 밝혀 둠

1. **TS-16** — 이유는 §5 에 적었음(세션 행이 `b1` 의 자료임).
2. **플레이어의 `onError`·`onReady` 거동** — 함정 `H-CB` 가 겨누는 자리이나 TS-27 의 AC 여섯에
   없음. AC#6 은 「렌더됨」까지이고, 정상 영상으로 iframe 이 실려 제목·채널 링크가 나오는 것까지
   확인했음. **없는 videoId 로 프로브를 띄우지 않았음** — 대조군 없이 「이벤트가 안 온다」를 확정하지
   말라는 지시와, 그 판정이 AC 밖이라는 것 둘 때문임.
3. **스크린샷** — §1 에 이유를 적었음. 판정 근거에는 쓰지 않는 것이 §6 규약이라 판정에 영향 없음.
