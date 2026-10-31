# 회차 2026-11-01-b4 — 문법 코스 재검증 (`TASK-287`, HEAD `f574612` + 미커밋 작업 트리)

## 판정표

| # | 시나리오 | 판정 | 근거 요약 |
|---|---|---|---|
| D3 | 앱 안 링크로 떠날 때 영상 위치 저장 | **FAIL — 여전히 실패(2/2)** | 1차 Day 3: 떠나기 직전 30.2초 → 떠날 때 저장 본문 `position_sec 0`(15:43:32.710) → 다시 연 영상 0초. 2차 Day 4: 저장 위치 11.32 에서 열어 14.8초까지 → 떠난 뒤 0 (`VIDEO-day3-r1.json` · `VIDEO2-day4-r2.json` · `console-all.jsonl` 의 POST 본문) |
| D4 | 수동 모드 「Day 마치기」 | PASS — 고쳐짐(2/2) | 마지막 문장에서 라벨 「Day 마치기」 · 시작 전과 listen 중 disabled · done 뒤 활성 · 누르면 `completed_count 0→1` · Unit 첫 문장 · 안내 「이 Day 를 끝까지 마쳤어요.」 (`FINISH-5-manual-r1.json` · `FINISH-6-manual-r2.json`) |
| D5 | 6편 완료 뒤 진행 중 Day = Day 1 | **FAIL — UI 경로에서 여전히 실패(2/2)** · API 만 쓴 경로는 PASS | UI 로 마친 Day 가 진행 중으로 뽑힘. r1: `cycle 2 · current_day 6`. UI 최소 재현: `cycle 4 · current_day 6`. API 로 1→6 완료: `cycle 3 · current_day 1` (`CYCLE-api-r1.txt` · `FINISH-6-manual-d5ui.json` · `CYCLE-api-r2.txt`) |
| D5+ | 회차 중 다른 Day 에 진도 → 그 Day 가 진행 중 | PASS | 4회차에 Day 1 을 Unit 2 문장 1 로 옮기자 `current_day 6 → 1` (`RESUME_LIST-1-d6r1.json`) |
| D6 | 다른 단원 첫 문장에 멈춘 Day 의 문구 | PASS — 고쳐짐(2/2) | 「Unit 2 · 문장 1 · 0:00」 · 열면 Unit 2 문장 1. API 로 둔 Day 2: 「Unit 30 · 문장 1 · 0:00」 · 열면 Unit 30 문장 1 (`RESUME_LIST-1-d6r1.json` · `RESUME_LIST-2-d6r2.json` · `RESUME_LIST-2-d6r2b.json`) |
| W | 대기 막대가 가득 찬 상태에서 줄어듦 | PASS (2회) | repeat 첫 표본 1.000 · 중간 0.496~0.500 · 마지막 0.003~0.007 · 단조 감소. 수동 1문장 · 자동 2문장 (`WAITBAR-*.json`) |
| C1 | 완료 뒤 되감기 — 「Day 마치기」 경로 | PASS (2회) | 목록 「완료 · 11/1」 · 막대 100% · 다시 열면 첫 문장 · 영상 0초 정지 · 완료 횟수 +1 (`FINISH-5-reopen-video-r1.json` · `FINISH-6-reopen-video-r2.json`) |
| C2 | 완료 뒤 되감기 — 자동 경로 | PASS | `completed_count 3→4` 한 번 · 다시 열면 Unit 42 문장 1 · 영상 0초 (`FINISH-3-auto-auto.json` · `FINISH-3-reopen-video-auto.json`) |
| C3 | 「Day 마치기」 실제 더블클릭 | PASS (2회) | CDP 마우스 더블클릭 → 완료 횟수 +1 만(5→6 · 6→7) (`FINISH-4-manual-realdbl*.json`) |
| L | 완료 전 늦은 저장 버림 | PASS | 완료 횟수 2 인 Day 에 `completed_count` 없이 보낸 저장 → 204 · 값 그대로. 2 를 넣어 보내면 반영 (`latesave-nocc.txt`) |
| R1~R8 | b3 회귀 | PASS (8/8) | R3 `listen 0 → repeat 3003 → judge 7007 → done 7011` · R4 done→listen 1506·1508ms · R7 로드 77ms 뒤 시작 · R8 두 변형 모두 `live` 트랙 0 |
| N2·N3 | 「다시」 수동 · 자동 「다시」/「이전」 | PASS | `RETRY_MANUAL.json` · `AUTO_RETRY.json` |
| N8 | 완료 날짜 KST | PASS | `last_completed_at 2026-10-31T15:45:11Z` → `last_completed_date 2026-11-01` · 목록 「완료 · 11/1」 |
| N11 | 콘솔 | PASS | 예외 0 · 앱 `console.error` 0. 오류 수준 로그 20건은 stub 503 판정 요청 · 경고 1건은 YouTube `www-widgetapi` (`console-summary.txt`) |

- 회귀(b3 대비): 고쳐짐 3건(D4 · D6 · 늦은 저장) · 여전히 실패 2건(D3 2회차째 · D5 2회차째) · 새로 실패 0건.

## 먼저 알릴 것

1. 전용 런처 없이 서브에이전트로 돌았음. 쓰기는 이 폴더와 `/private/tmp` 뿐이었음.
2. 백엔드 pid 7762 는 00:40:32 KST 기동이며, 서비스 변경(00:26:48)을 싣고 있었음. 회차 중 소스 mtime 변화 없음. HEAD 는 시작과 끝 모두 `f574612` 임.
3. 테스트 원장·작업 원장은 갱신하지 않았음. 회차 폴더 밖 쓰기와 커밋이 금지됐기 때문임.

## 결함

### D3 (여전히 실패) — 「← 학습 목록」으로 떠나면 영상 위치가 0 으로 저장됨 · HIGH

- 재현: `/course/3` 열기 → 영상 25초 재생 → 「← 학습 목록」 → `GET /api/course/days/3` 의 `position_sec` 확인
- 실제: 떠날 때 나간 POST 본문이 `"position_sec":0` 임. 직전 5초 타이머 저장(30.23)을 덮어씀
- 근거(관측 + 코드 읽기): 2차에서 시작 위치가 11.32 인데 0 이 나갔음. 자식 정리가 남긴 `startRef`(≥11.32)가 쓰였다면 0 이 나올 수 없음. 따라서 부모의 언마운트 저장 시점에 `playerRef.current`(imperative handle)가 이미 `null` 이고 `?? 0` 이 쓰였다고 판단함
  - React 는 삭제 시 ref 와 `useImperativeHandle` 을 레이아웃 단계에서 떼고, `useEffect` 정리는 그 뒤에 돌림. 자식 쪽 수정만으로는 닿지 않음
- 제안: 부모가 5초 타이머·`onPlaying` 때마다 마지막 위치를 자기 ref 에 담고, 언마운트 저장은 그 값을 씀. 또는 핸들이 없을 때 0 대신 «저장 생략»으로 다룸

### D5 (여전히 실패, 경계가 좁혀짐) — 화면에서 Day 를 마치면 완료 뒤 저장이 그 Day 를 「이번 회차에 손댄 Day」로 만듦 · MEDIUM

- 재현(최소): Day 1~5 를 API 로 완료 → Day 6 을 마지막 문장에 두고 수동 「시작」 → done → 「Day 마치기」 → 5초 머물거나 「← 학습 목록」 → `/course` 확인
- 기대: 새 회차의 진행 중 Day 는 Day 1
- 실제: `current_day 6` · Day 6 에 「이어서 학습 ▶」 · 강조
- 근거: 완료 시각 15:46:48.864 = `updated_at`. 4.6초 뒤 5초 타이머 저장이 `updated_at` 을 15:46:53.445 로, 떠날 때 저장이 15:46:56.440 으로 올림. 두 저장은 새 `completed_count` 를 실어 늦은 저장 가드를 통과함. `_touched_since_completion` 은 `updated_at > last_completed_at` 만 보므로 참이 됨
- API 만으로 완료하면 이 저장이 없어 통과함(r2). 그래서 단위 테스트가 이 경로를 놓쳤을 가능성이 큼
- 제안: 「손댐」 판정을 `updated_at` 대신 위치 변화(완료 뒤 `unit`·`sentence_index`·`position_sec` 가 처음이 아님)로 보거나, 값이 바뀌지 않은 저장은 `updated_at` 을 올리지 않게 함

## 관찰 (결함으로 올리지 않음)

- 같은 이벤트 틱 안에서 `button.click()` 을 두 번 부르면 완료 POST 가 2건 나가 완료 횟수가 2 오름(3→5). 실제 더블클릭은 +1 이므로 사용자 경로가 아님. `_COMPLETE_DAY_SQL` 은 `completed_count` 를 보지 않아 서버 쪽 중복 방어는 없음
- `completed_count` 를 빼고 보낸 저장은 오류 없이 204 로 버려짐. 다른 클라이언트·스크립트가 조용히 무시될 수 있음
- 화면을 열고 떠나기만 해도 그 Day 가 진행 중이 됨(b3 와 같음). D5 와 같은 기전임
- `net::ERR_ABORTED`(Fetch) 125건 · Document 1건 — b3 도 114건이었음. 분류하지 않았음

## 만든 데이터와 정리

- API 쓰기 기록: `evidence/api-writes.log`. 405/000 4줄은 zsh 단어 분할 실수로 깨진 요청이며 서버 쓰기 없음
- `course_attempts` 는 회차 내내 0건(판정 20건 모두 stub 503)
- 정리(15:52:46 UTC): 회차 시작(15:42:27 UTC) 이후 `course_day_progress` 6행 삭제. 회차 이전 행 0건
  - 삭제 뒤: `attempts 0` · `progress_rows 0` · API `cycle 1 · current_day 1 · progress 전부 null` (`evidence/db-cleanup.txt`)
- `users.timezone` 은 읽기만 함(`Asia/Seoul`). :3000 · :8002 는 재기동·종료하지 않음
- Chrome · 수집기 `TaskStop` 종료 · `:9333` 비어 있음 · `/private/tmp/_b4-*` 삭제
