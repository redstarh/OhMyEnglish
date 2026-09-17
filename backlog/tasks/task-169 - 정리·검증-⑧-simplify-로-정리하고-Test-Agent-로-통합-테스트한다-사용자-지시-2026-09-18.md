---
id: TASK-169
title: '정리·검증 ⑧: /simplify 로 정리하고 Test Agent 로 통합 테스트한다 (사용자 지시 2026-09-18)'
status: Done
assignee: []
created_date: '2026-09-17 17:17'
updated_date: '2026-09-17 18:26'
labels: []
dependencies:
  - TASK-168
ordinal: 230000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 지시 — 주요 개발이 끝나면 simplify 로 정리하고 Test Agent 기반으로 꼼꼼히 테스트한다. 게이트 수치로 통합 테스트를 대체하지 않는다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 /simplify 를 돌려 지적된 것을 처리했다 (기각한 것은 근거를 적었다)
- [x] #2 게이트 일곱을 직접 돌려 exit 0 을 확인했다 (pytest · ruff · format · ty · tsc · eslint · 수집)
- [x] #3 백엔드를 재기동하고 app-test-agent 로 통합 테스트를 돌렸다 (--reload 가 없으므로 재기동이 선행된다)
- [x] #4 실제 YouTube 링크로 영상을 담고 구간과 문장을 담고 연습까지 한 바퀴를 돌린 증거가 있다
- [x] #5 결함이 나오면 재현 절차와 함께 원장에 등록했다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 실물 백엔드 한 바퀴 (2026-09-18 · 재기동한 서버에 직접 호출)

백엔드를 재기동했음(이전 pid 71188 → **83313** · `WORKER_ENABLED=false VOICE_ADAPTER=stub
--log-level info` · `:8002` · 로그 `/tmp/omy-backend.log`). 소스를 고쳤고 `--reload` 가 없으므로
재기동이 선행 조건임.

| 단계 | 요청 | 관측된 응답 |
|---|---|---|
| 0 | `GET /health` | `{"status":"ok"}` **200** |
| 0 | `GET /api/videos` | `{"videos":[]}` **200** — 새 라우터가 붙었음 |
| 1 | oEmbed (`jNQXAC9IVRw`) | `title=Me at the zoo` · `channel=jawed` — **API 키 없이** |
| 2 | `POST /api/videos` (`youtu.be` 형태) | **201** · `created: true` · `youtube_id: jNQXAC9IVRw` |
| 3 | `POST /api/videos` 같은 영상 (`watch?v=` 형태) | **200** · `created: false` · **같은 id** |
| 4 | `POST /api/videos/{id}/phrases` (`1.238`~`6.7`) | **201** · `clip_start_sec: 1.24` |
| 5 | `GET /api/videos/{id}` | 영상 + 문장 하나를 **한 번의 왕복**으로 |

### ⛔ 실물에서 확인된 설계 계약 셋

1. **URL 형태가 달라도 같은 영상임** — 2단계는 `youtu.be/...`, 3단계는 `watch?v=...` 인데 같은 행이
   됐음(`created: false` · 같은 id). 서버가 videoId 로 정규화한다는 것이 실물로 확인됐음.
2. **중복이 갱신임** — `201` 이 아니라 **`200`** 이 왔음. 화면 문구가 이 값에 걸림.
3. **서버가 반올림함** — `1.238` 을 보냈고 `1.24` 가 저장됐음(설계서 §1 질문 4).

### 기동 상태

- 백엔드 **83313** · `:8002`
- 프론트 **81310** · `:3000` (`next dev` · Turbopack · `.env.local` 이 `:8002` 를 가리킴)

⚠️ **화면 쪽은 아직 열어 보지 않았음** — 브라우저 흐름은 `app-test-agent` 가 잼. 여기서 「화면이
돈다」고 적지 않음.

## `/simplify` — 리뷰 넷을 병렬로 돌리고 반영했음 (AC#1)

재사용·단순화·효율·고도 네 각도로 30여 건을 받아 중복을 합쳐 반영했음. 상세는 커밋 `b4a7927` 의
메시지가 가짐.

⛔ **두 리뷰가 상충한 자리가 가장 값졌음** — 단순화는 `PLAYER_PLAYING` 을 「죽은 export」로, 효율은
「이 용도로 만들어 둔 값」으로 봤음. 타이머를 재생 상태에 묶으면 둘이 **함께** 해결됐음.

**기각한 것 셋과 근거**:

| 기각 | 근거 |
|---|---|
| 쓰기 응답으로 지역 상태를 갈아 끼우기 | 리뷰가 스스로 「서버를 정본으로 두는 단순함이 줄어든다」고 적었고 사용자가 심플을 요구했음 |
| `ADDITIONAL_LEARNING` 판별 유니언 | 항목 일곱에 유니언을 들이면 `entryForTarget`·렌더가 함께 바뀜 |
| 읽기 블록 헬퍼 통합 | 그 블록이 리포에 이미 일곱 벌이라 이 diff 안에서만 바꾸면 나머지와 갈라짐 |

## Test Agent 통합 테스트 (AC#3·#4)

`app-test-agent` 가 시나리오 열하나를 실물 HTTP·WebSocket·DB 로 돌렸음. 증거는
`tests/agent/runs/2026-09-18-0303/evidence/` 이고 그 회차를 스스로 `be5187c` 로 커밋했음.

**성립한 계약 열** — 담기(형태 여섯이 한 행) · 거부 링크 **열여덟 건 전부 422**(`youtube.com.attacker.test`
포함) · 문장 담기와 `level`·`source_url` 정규화 · 값역 여섯 · **오디오가 붙지 않는 것**(스키마 CHECK) ·
⛔ **영상을 지워도 문장 11건이 남고 그 문장으로 연습이 다시 열림** · 하위 자원 경계 · 연습 배선
(`?item=` 이 그 문장을 붙이고 없는 id 는 자동 선택으로 떨어짐) · 프론트 200 · CORS.

**⛔ 실패 하나 — 그것이 이 회차의 값임**: `TASK-170`(HIGH). 고쳐서 닫았음(그 태스크 노트가 근거를 가짐).
`TASK-171`(LOW · 설계서 필드명)도 고쳐 닫았음.

⚠️ **에이전트가 「다른 주체가 같은 DB·화면을 썼다」고 보고했고 그것은 나였음** — 내가 병렬로 브라우저를
조작하고 `/simplify` 를 반영했음. 그 관측은 정확하고, 에이전트가 **백엔드가 reload 없이 한 프로세스였음을
근거로 자기 측정의 유효 범위를 스스로 좁힌 것**이 옳은 판단이었음.

## 화면은 내가 직접 열어 봤음 (AC#4 · `TASK-168` AC#5 가 넘긴 것)

에이전트에 브라우저 도구가 없어 **화면 판정을 내가 CDP 로 했음.** 관측한 것:

| 확인 | 관측값 |
|---|---|
| 목록 화면 | 제목·안내·입력칸·카드(썸네일·제목·채널·「담은 문장 N개」)·지우기 |
| 썸네일 조립 | `i.ytimg.com` 에서 **실제로 로드됨** — 저장하지 않고 조립하는 판단이 화면에서 성립함 |
| 학습 화면 | iframe `src=youtube.com/embed/jNQXAC9IVRw?enablejsapi=1` — **플레이어가 실제로 붙음** |
| 정책 III.I.6 | 재생 버튼·「Watch on YouTube」가 **가려지지 않음** |
| 구간 담기 상태 전이 | `구간 시작` → `구간 끝`·`구간 다시 잡기` → 입력칸 + `담기`(빈 문장이면 **disabled**) |
| 구간 반복 문구 | `구간 0:00~0:19 을 반복해 들려주고 있어요.` |
| 담긴 뒤 | 문장이 목록에 쌓이고 `clip_start_sec` 순으로 정렬되며 입력 상태가 초기화됨 |
| 시각 표시 | `1.24`·`6.7` 이 `0:01~0:06` 으로 — `asClock` 이 작동함 |
| ⛔ 오류 문구 | `role=status` 에 **`"구간 끝이 시작보다 뒤여야 해요."`** — 설계서 §7 이 약속한 그 문구임 |
| 콘솔 | error·warn **0건** |

⚠️ **확인하지 못한 것을 밝힘**: 임베드가 막힌 영상의 `101`·`150` 안내(그런 영상 id 를 갖고 있지 않음) ·
실제 음성 연습 왕복(`VOICE_ADAPTER=stub` 임) · 30일 stale 갱신의 화면 거동(시각을 밀어야 함 — 서버
쪽에서는 에이전트가 확인했음).

## dev DB 정리와 불변 지표 재측정 (직접 조회)

⛔ **`source_url is not null` 로 좁혀 지웠음** — 시드 합성 클립을 보호함. `DELETE 3` + `DELETE 1`.

| 표 | 이전(handoff) | 지금 |
|---|--:|--:|
| `learning_sessions` | 17 | **23** |
| `utterances` | 128 | **164** |
| `error_patterns` | 9 | 9 |
| `review_tasks` | 15 | 15 |
| `analysis_jobs` | 57 | **93** |
| `pronunciation_attempts` | 7 | 7 |
| `schema_migrations` | 24 | **25** |
| `shadowing_items` | — | **1** (시드 합성 클립만) |
| `youtube_videos` | — | **0** |
| `harness_runs` | 28 | 28 |
| `harness_sessions` | 100 | 100 |

세션·발화·job 이 늘어난 것은 통합 테스트가 실물 소켓을 여섯 번 연 결과임.

## 게이트 (AC#2 · 이 턴에 직접 돌린 출력)

수집 **1343** · `pytest` **1343 passed** · `ruff` 0 · `ruff format` **291 files** · `ty` 0 ·
`tsc` 0 · `eslint` 0 · **`next build` 0**(`/` 가 여전히 Static).
<!-- SECTION:NOTES:END -->
