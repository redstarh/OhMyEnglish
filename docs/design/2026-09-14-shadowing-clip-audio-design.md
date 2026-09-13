# 합성 쉐도잉 클립 오디오의 자리와 소비자 — 설계

> **소유 태스크**: `TASK-66` (AC#1·#2·#4·#5). AC#3 은 이미 닫혔음 — 결정 88.
> **선행 결정**: 47(쓴다 · 미리 만들어 저장 · R10-7 예외를 이 하나로 좁혀 엶) · 6(재생 `0.5~2.0배` ·
> 반복 `1~10회` · 설정값으로 관리) · 25(분량을 늘리지 않음) · 88(시드의 시간 창은 실측 `16.64`).
> **이 설계에 걸린 사용자 결정 셋의 정본은 `docs/ops/captain-instruction-register.md` 의 결정 90 임** —
> 아래 §2 는 그것을 설계 문맥에서 다시 읽는 자리이고 근거의 정본이 아님.
> **선행 검토**: `2026-09-09-shadowing-synthetic-clip-review.md` — §4(자리가 없음) · §5(선택지 셋) ·
> §7(생성 절차) · §7.4(미정으로 남긴 것)를 그 문서가 소유함. 이 설계가 그 §7.4 를 닫음.

작성 2026-09-14 · 브랜치 `design/first-vertical-slice`

---

## §1. 무엇이 걸려 있었나 — 직접 읽어 확인한 사실 넷

1. **`shadowing_items` 에 오디오를 담을 자리가 0임.** 컬럼은
   `id`·`source_title`·`source_url`·`transcript`·`clip_start_sec`·`clip_end_sec`·`level`·`created_at`
   뿐임. `source_url` 주석이 *"외부 영상은 링크만 보관한다"* 이므로 그 자리는 출처 링크이고 로컬
   오디오 경로를 넣는 것은 의미 오버로드임.
2. **학습자 낭독 자리는 CHECK 가 막음.** `utterances_audio_only_for_shadowing` 이
   `audio_url is null or (utterance_type = 'shadowing_recording' and speaker = 'user')` 이고, 그 위
   주석이 *"다른 오디오가 조용히 쌓이는 길을 여기서 막는다"* 로 의도를 적었음. `speaker='user'` 라
   합성음은 원리적으로 못 들어감.
3. ⛔ **프런트에 쉐도잉 화면이 통째로 없음** — 앞선 조사가 「엔드포인트가 0곳」이라 적었는데 그보다
   넓음. `session_started` 의 `shadowing` 키를 읽는 코드가 0곳이고
   `startShadowingTurn`·`endShadowingTurn` 은 정의만 있고 호출부가 0곳임. 즉 백엔드 프로토콜과 타입만
   있고 소비자가 비어 있음. **이 사실이 AC#4 의 크기를 바꿨고 그래서 범위를 사용자에게 물었음**(§2).
4. **오디오를 내려주는 전례는 하나임** — `api/results.py:get_recording` 이
   `Response(content=bytes, media_type="audio/L16; rate=16000; channels=1")` 로 내려줌.
   `StaticFiles` 마운트는 0곳이고 `recording_url` 주석이 *"파일 경로가 아니라 API 경로다"* 로 그
   방향을 이미 정해 뒀음.

## §2. 사용자 결정 셋 — 이 설계의 갈림길

| 물음 | 정한 것 | 기각한 것 |
|---|---|---|
| 배포 모델 (AC#1 의 「리포 안인가 밖인가」) | **리포에 추적함** | 리포 밖 루트에 배치 · DB `bytea` |
| AC#4 의 범위 | **최소 쉐도잉 화면까지**(전사문 + 오디오 재생) | 낭독 녹음까지 함께 · 스키마와 엔드포인트만 내고 화면은 다음 |
| 접근 | **A — 컬럼 하나 + WAV + 새 엔드포인트** | B(별도 표 + raw PCM + `VoiceIo` 재사용) · C(`StaticFiles` 정적 서빙) |
| 설계 세부 (승인 시점) | **이 설계 그대로** — `has_audio` 를 payload 에 싣고 파일명 CHECK 를 엄격히 둠 | `has_audio` 없이 404 로 판별 · 파일명 CHECK 를 모양 정규식으로 느슨하게 |

⛔ **셋째 물음의 기각 항목 하나는 규율 위반이었음** — 「스키마와 엔드포인트만 내고 화면은 다음」은
`data-first` 규율(*"소비자가 0곳이면 진행하지 않는다"* · 이 리포가 네 번 낸 실패)을 유예하는 것임.
사용자가 그것을 고르지 않았으므로 **이 설계는 소비자와 같은 커밋으로 나감.**

## §3. 스키마 — `022_shadowing_clip_audio.sql`

`shadowing_items` 에 `audio_filename text` 하나를 더하고 CHECK 둘을 건다.

| 제약 | 문장 | 무엇을 막는가 |
|---|---|---|
| `shadowing_items_audio_filename_matches_id` | `audio_filename is null or audio_filename = id::text \|\| '.wav'` | 파일명 규약을 스키마가 강제함. **경로 구분자가 원리적으로 못 들어가므로 경로 이탈이 불가함** |
| `shadowing_items_audio_only_for_synthetic` | `audio_filename is null or source_url is null` | **R10-7 예외를 「합성한 쉐도잉 클립」 하나로 좁힘**(결정 47 이 연 범위). 출처 링크가 있는 클립에는 오디오가 못 붙음 — PRD §5(*"저작물 전체를 저장하지 않는다"*)와 같은 방향임 |

**AC#2 가 이 둘로 닫힘.** 011 의 CHECK 주석이 *"docstring 은 그 함수를 읽을 이유가 없는 사람을
구속하지 못한다 — 스키마는 한다"* 로 방식을 이미 정했고, 이 파일은 그 방식을 따름.

⚠️ **교환을 밝혀 둠**: 파일명이 `id` 로 결정되므로 **포맷을 바꾸려면 마이그레이션이 필요함.**
그것을 의도로 둠 — 이 리포는 값역을 계약으로 쓰고 011 이 같은 방식으로 오디오 경계를 새겼음.
느슨한 정규식(모양만 검사)은 사용자가 기각했음(§2 의 넷째 줄).

⚠️ **번호는 022 임** — `ls db/migrations/` 실측 최대가 `021` 임(`H-AL` 대로 적용 직전에 다시 조회함).
⛔ **020·021 이 dev DB 에 미적용이고 022 의 적용도 승인 사안임**(§9).

## §4. 파일 자리와 설정

- 자리는 **`assets/clips/<item id>.wav`** 이고 **git 이 추적함.** `.gitignore` 가 무시하는 것은
  `assets/audio/` 뿐이라 형제 디렉터리는 그대로 추적됨. 리포는 이미 오디오 바이너리를 추적함 —
  `tests/harness/fixtures/voice` 에 wav 40개 4.9MB(2026-09-13 실측).
- 설정 키를 **새로** 둠: `shadowing_clip_audio_root`(기본 `../../assets/clips`).
  ⛔ **`shadowing_audio_root` 를 재사용하지 않는 것이 이 절의 핵심임** — `sweep_orphan_recording_files`
  가 그 루트를 `iterdir()` 로 순회하며 UUID 이름 규칙에 맞는 것을 지우므로, 같은 루트에 두면
  **제품 자산이 스윕 대상이 됨.** 두 오디오의 수명주기가 다르므로 루트도 다름.
- 포맷은 **WAV 16kHz mono 16-bit** 임 — 선행 검토 §7.2 가 `afconvert -f WAVE -d LEI16@16000 -c 1` 로
  「앱 재생 규격」을 이미 지정했음. 1건이 약 0.5MB 임(16.64초 × 32KB/s).
- **AC#5 가 이 절로 닫힘** — 선행 검토 §7.4 의 마지막 줄이 「`assets/clips/<클립 id>.wav` 에 두고
  DB 는 파일명을 가리킨다」로 채워짐. 생성 절차 자체는 그 문서 §7.1 이 계속 소유함.

## §5. 엔드포인트

- 새 라우터 `api/shadowing.py` — `APIRouter(prefix="/api/shadowing", tags=["shadowing"])` ·
  `GET /clips/{item_id}/audio`. 기존 라우터 둘은 `/api/sessions`(results)와 `/api`(daily)이고 클립
  오디오는 세션에 매인 자원이 아니므로 그 아래에 넣지 않음.
- 응답은 `get_recording` 전례를 그대로 따라 `Response(content=bytes, media_type="audio/wav")` 임.
  ⛔ `StaticFiles` 를 쓰지 않는 근거는 §1-4 임(파일시스템을 웹에 노출하지 않는 방향이 이미 정해짐).
- 서비스는 새 모듈 **`services/clip_audio.py`** 에 둠 — 낭독과 수명주기가 다르고 `recordings.py` 가
  이미 큼. 함수 둘: `clip_audio_path(root, item_id)` · `load_clip_audio(conn, root, item_id)`.
- **404 는 세 갈래임**: 클립 없음 · `audio_filename` 이 null · 파일이 없음. 500 으로 던지지 않음
  (`get_recording` 이 같은 셋을 같은 방식으로 처리함).
- ⛔ **경로는 DB 문자열이 아니라 `item_id` 로부터 조립함.** CHECK 가 둘의 일치를 강제하지만 방어를
  겹으로 둠 — 한 겹이 뚫려도 다른 겹이 막아야 함.

## §6. 프런트 최소 화면

- `app/page.tsx` 의 `session_started` 처리가 `event.shadowing` 을 읽어 상태에 담음(지금 0곳임).
- 새 컴포넌트 `components/ShadowingPanel.tsx` 가 `source_title` · `transcript` · 재생 버튼을 렌더함.
- 재생은 `new Audio()` 이고 `playbackRate = playback_rate` 를 걸고 `ended` 에서 `repeat_count` 까지
  반복함. **결정 6 의 값역이 추가 발명 없이 충족됨.** ⛔ `VoiceIo`(AudioContext 큐)를 쓰지 않는
  근거는 그것이 실시간 스트리밍용이라 속도·반복 제어를 갖지 않는 것임.
- 서버 payload 에 **`has_audio: bool`** 을 더해 프런트가 404 를 기다리지 않고 버튼 표시를 정함 —
  `load_session_clip` 의 select 에 `audio_filename` 을 넣고 `as_event_payload()` 가 불린으로 실음.
  ⚠️ 파일명을 프런트에 내려보내지 않음(경로는 서버의 것임).
- ⛔ **낭독 녹음·비교는 범위 밖임**(§2). `startShadowingTurn` 을 호출하지 않고 **화면에 그 진입 안내도
  넣지 않음** — 없는 기능을 있다고 알리지 않기 위함임(같은 부류의 결함이 `TASK-128.4` 로 이미 등록돼
  있음: *"폴백이 사라지면 화면의 진입 안내가 거짓이 된다"*).

## §7. 테스트 축

| 축 | 무엇을 재는가 | 어디 |
|---|---|---|
| 스키마 | CHECK 둘이 **거부**하는가 — 규약 밖 파일명 · `source_url` 이 있는 행에 오디오 붙이기 | `tests/unit/test_schema.py` 의 022 절 |
| 시드 | 시드가 파일명을 갖고 **그 파일이 리포에 실제로 있는가** | `tests/unit/test_shadowing_seed.py` |
| 서비스 | `load_clip_audio` 의 네 갈래(정상 · 클립 없음 · null · 파일 없음) | `tests/unit/test_clip_audio.py`(신규) |
| API | 200 의 바이트·Content-Type · 404 셋 | `tests/unit/test_results.py` 이웃에 신규 절 |
| 종단 | 앱 경로(브라우저 레그)에서 **실제로 소리가 나는가** | 회차 1회 |

⛔ **시드 단정이 이 설계에서 가장 값어치 있는 자리임** — 「제품 자산이 배포되는가」를 재는 유일한
단정이고, 파일을 `.gitignore` 된 자리에 두는 실수를 그것만이 잡음.

⚠️ **프런트 테스트 인프라가 0임**(테스트 스크립트도 파일도 없음 · 2026-09-14 실측). 그래서 프런트
레그는 브라우저 회차로 확인함 — 결정 50 이 *"스파이크만으로 닫지 않는다"* 를 이미 명시했음.

## §8. 되돌리기

`alter table shadowing_items drop column audio_filename;` 하나임. **값역 축소가 아니므로 011 과 달리
안전함** — 잃는 것은 파일명 문자열이고 **파일은 리포에 남음**(git 이 추적하므로 되돌림에도 살아 있음).
⚠️ 되돌리면 프런트의 `has_audio` 가 항상 거짓이 되어 재생 버튼이 사라짐 — 화면이 깨지지 않고 전사문만
남는 것이 §6 의 설계임.

## §9. 선행과 위험

1. ⛔ **TTS 회차 1회가 필요함** — 2026-09-09 생성물이 `/tmp/qwen_out` 에서 사라졌음(2026-09-14 실측).
   생성 절차는 선행 검토 §7.1 이 소유하고 모델 캐시는 `~/.cache/huggingface` 에 남아 있을 수 있음.
   ⚠️ **길이를 다시 재서 `clip_end_sec` 과 대조함** — 재생성물이 16.64초와 다르면 그것이 새 실측이고
   결정 88 의 기록을 그 값으로 갱신함(값을 고르지 않고 잰 것을 씀).
2. ⛔ **022 의 dev DB 적용은 승인 사안임.** 지금 dev DB 는 `019` 까지 적용돼 있고 020·021 이
   미적용임(2026-09-13 직접 조회). 011 의 적용 5단계 규약을 따름.
3. **파일 1개 약 0.5MB 를 커밋함.** 전례가 있으나 클립을 늘리면 선형으로 커짐 — 결정 25 가 분량을
   늘리지 않으므로 지금은 1건임.

## §10. 이 설계가 확인하지 못한 것

- **합성음을 사람이 들어보지 않았음.** 선행 검토 §8 의 미판정이 그대로 남아 있음 — 학습 적합성은
  브라우저 회차에서 사람이 들어야 판정됨.
- **`playbackRate` 가 `0.5~2.0` 전 구간에서 음질을 유지하는지 재지 않았음.** 브라우저가 음높이를
  보존하는 것은 일반적이나 이 리포에서 측정하지 않았음.
- **문장 단위 제공(PRD §7)을 이 설계가 다루지 않음** — 전사문을 쪼개는 규칙은 `TASK-10` 의 것이고
  `ws.ts` 주석이 *"쪼개는 규칙은 `TASK-10` 이 정한다"* 로 이미 그 경계를 적어 뒀음.
