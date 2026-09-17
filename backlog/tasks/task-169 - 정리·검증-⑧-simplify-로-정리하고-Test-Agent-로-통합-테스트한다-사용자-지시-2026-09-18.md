---
id: TASK-169
title: '정리·검증 ⑧: /simplify 로 정리하고 Test Agent 로 통합 테스트한다 (사용자 지시 2026-09-18)'
status: Awaiting Decision
assignee: []
created_date: '2026-09-17 17:17'
updated_date: '2026-09-17 18:18'
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
- [ ] #1 /simplify 를 돌려 지적된 것을 처리했다 (기각한 것은 근거를 적었다)
- [ ] #2 게이트 일곱을 직접 돌려 exit 0 을 확인했다 (pytest · ruff · format · ty · tsc · eslint · 수집)
- [ ] #3 백엔드를 재기동하고 app-test-agent 로 통합 테스트를 돌렸다 (--reload 가 없으므로 재기동이 선행된다)
- [ ] #4 실제 YouTube 링크로 영상을 담고 구간과 문장을 담고 연습까지 한 바퀴를 돌린 증거가 있다
- [ ] #5 결함이 나오면 재현 절차와 함께 원장에 등록했다
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
<!-- SECTION:NOTES:END -->
