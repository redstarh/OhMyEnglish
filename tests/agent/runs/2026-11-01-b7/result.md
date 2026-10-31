# 회차 2026-11-01-b7 — 문법 코스 D1·D2 재확인 (`TASK-288` · `TASK-289`)

HEAD `65df3d6` + 미커밋 작업 트리. 회차 시작과 끝 모두 같음.

## 먼저 알릴 것

1. 이 회차를 돌리는 중에 다른 주체가 백엔드 파일 둘을 더 고쳤음. `nova.py` 는 02:47:16 KST, `transcribe.py` 는 02:47:32 KST 임. 회차 시작은 02:45 경임.
   백엔드 pid 21343 은 02:44:58 에 기동했고 `--reload` 가 없음. 그래서 아래 D1 측정은 모두 **02:44:12 판**(기동 때 적재된 판)에 대한 것임.
   그 뒤에 더해진 변경은 이 회차가 검증하지 않았음. 그 변경은 연결 실패를 503 으로 돌리는 것과 입력 쪽 예외를 `failure` 로 남기는 것임.
   프런트 소스(`CoursePlayer.tsx` · `youtube.ts`, 02:44:40)는 회차 중 바뀌지 않았음.
2. 공유 판정: :3000(pid 98345) · :8002(pid 21343, `VOICE_ADAPTER=nova`, DB `ohmyenglish_course_paid`)는 남의 것이라 재기동·종료하지 않았음.
3. 전용 런처 없이 서브에이전트로 돌았음. 쓰기는 이 폴더와 `/private/tmp/_b7-chrome-*`(삭제함)뿐임. 원장 갱신과 결함 등록은 하지 않았음. 회차 폴더 밖 쓰기 금지 지시 때문임.
4. 지시의 전제와 다른 점이 하나 있음. Day 3 의 저장 위치는 120 이 아니라 150.84 였음(`db-start.json`). 그 값으로 확인했음.

## 판정표

| # | 확인 | 판정 | 근거 |
|---|---|---|---|
| 1a | D1 수동 — 503 · 안내 · 횟수 · DB | 통과 (1/1) | 응답 `503 {"detail":"따라 하기 판정을 쓸 수 없다"}`. 화면 「지금은 따라 하기 판정을 쓸 수 없어요. 문장은 계속 이어져요.」. 「따라 함 2회」 그대로이고 새로 고침 뒤도 같음. API `attempts` 는 2 → 2, 격리 DB attempts 는 2 → 2 (`ATTEMPT-d1-manual.json` · `attempts.jsonl` · `db-after-d1manual.json`) |
| 1b | D1 자동 모드 | 통과 (1/1) | 503 뒤 judge → done 은 1.26초, done → 다음 문장 listen 은 1.5초 걸렸음. 흐름은 문장 5 의 repeat 까지 이어졌음. 안내 문구는 다음 문장에도 남아 있음(아래 관찰). 횟수는 모든 문장에서 그대로임 (`AUTO-d1-auto.json`) |
| 2a | D2 Day 3(150.84) 자동 재생 해제판 | 통과 | 15초 동안 cued(`state 5`)·정지. 썸네일과 ▶ 이 보임(`VIDEO-np-day3-open.png`). ▶ 1.5초 뒤 151.15 이므로 약 150 에서 시작함 (`VIDEO-np-day3.json`) |
| 2b | D2 기본 정책 Day 4(37.5) · Day 3(156.74) | 통과 (2/2) | 둘 다 15초 동안 cued·정지. ▶ 1.5초 뒤 37.83 · 157.13 (`VIDEO-def-day4.json` · `VIDEO-def-day3.json`) |
| 2c | D2 저장 위치 0 — 해제판 Day 6(행 없음) · 기본 Day 2(되감기 뒤 0) | 통과 (2/2) | cued·0초 정지. ▶ 1.5초 뒤 1.09 · 1.11. 임베드 URL 에 `start` 없음 (`VIDEO-np-day6.json` · `VIDEO-def-day2-zero.json` · `FINISH-def-day2.json`) |
| 3 | 재생 전 12초 머문 뒤 앱 안 링크로 떠남 | 통과 (2/2) | Day 4 37.5 → 37.5 · Day 2 6.49 → 6.49. 머무는 동안의 5초 저장과 떠날 때 저장이 모두 원값(내림 없음) (`STAY-np-day4.json` · `STAY-def-day2.json` · `console-np1.jsonl` 의 요청 본문) |
| 4 | 플레이어 준비 전 「시작」 | 통과 (2/2) | 임베드 문서 요청을 6초 붙잡은 채 54ms 에 「시작」. listen → repeat → judge → done 이 붙잡힌 동안 끝났음(5.97초). 그 뒤 준비된 플레이어는 cued·정지이고 저장 162.71 이 유지됨 (`READY-def-day3.json`). 1.2초 붙잡기(연습 중 준비)도 repeat 중 cued·정지임. 녹음 창 종료 전에 떠나 POST 0 (`READY-def-day4-mid.json`). 임베드 URL `start=162` · `start=43` 으로 D2 배선을 직접 확인함 |
| 5a | 「Day 마치기」 | 통과 | 시작 전·listen 중 disabled, done 뒤 활성. 누르면 completed 0 → 1, `last_completed_date 2026-11-01`, 안내 「이 Day 를 끝까지 마쳤어요.」. 6초 뒤와 떠난 뒤도 유지. 목록 「완료 · 11/1」 (`FINISH-def-day2.json`) |
| 5b | 완료 뒤 되감기 | 통과 | 마친 뒤 Unit 22 문장 1 · position 0. 다시 열면 같은 문장이고 영상은 0초 cued (`FINISH-def-day2.json`) |
| 5c | 재생 중 앱 안 링크로 떠날 때 위치 저장 | 통과 | 43.42 에서 ▶ 후 12초 재생. 떠나기 직전 플레이어 54.60, 떠날 때 POST 54.4, DB 54.4 (`STAY-def-day4-linkleave.json` · `console-def1.jsonl`) |
| 5d | 자동 모드 대기 막대 | 통과 | repeat 진입 때 폭 비율 1.00, 1초 뒤 0.666 (창 2996ms). 애니메이션 `omy-course-wait-fill`, 길이가 창과 같음 (`AUTO-d1-auto.json`) |
| 6 | 콘솔 앱 예외 | 통과 (관측 구간 한정) | 두 Chrome 모두 `exception` 0. 오류 수준 로그는 503 리소스 로그 4건뿐임(의도한 응답). 기본 정책 쪽 `postMessage` 보안 경고 29건은 모두 임베드를 붙잡은 READY 구간에서 YouTube 의 `www-widgetapi` 스크립트가 냄 (`console-*.jsonl`) |
| AC | dev DB 쓰기 없음 | 통과 | `devdb-start.json` = `devdb-end.json` (attempts 0 · progress 0 · llm_calls 109 · 쓰기 통계 0) |

회귀(b6 대비): 고쳐짐 2건(D1 · D2) · 새로 실패 0건. b6 의 차단(실제 전사·자동 모드 실제 전사)은 Bedrock 권한이 그대로라 여전히 차단됨.

## 시도 POST — 4회 (상한 5)

- `u001-s4` 수동 1 · `u001-s4` 자동 1 · `u042-s1`(확인 4) 1 · `u041-s5`(Day 마치기 전 연습) 1. 4건 모두 503 임.
- 계수 근거: `attempts.jsonl` 의 POST 4건 = `backend-paid2.log` 의 attempts POST 4건(모두 503). 격리 DB attempts 는 2 → 2 이고 최근 `llm_calls` 행은 0 임.
- 사전 실행 `ATTEMPT-d1-probe` 와 `READY-def-day4-mid` 는 녹음 창이 끝나기 전에 떠나 POST 0 임.

## 새 결함

없음.

## 남은 것 (결함으로 새로 올리지 않음)

- b6 D1 의 진단 부족은 그대로임. 백엔드 로그의 끝줄이 `aws_sdk_bedrock_runtime.models.AccessDeniedException` 뿐이고 거부 메시지가 없음. 응답 `detail` 도 원인을 담지 않음. 회차 중 바뀐 판은 예외 클래스 이름만 `TranscriberUnavailable` 에 실음.
- 자동 모드에서 문장 4 의 「판정을 쓸 수 없어요」 안내가 문장 5 의 listen·repeat 동안에도 남음. 문구가 「문장은 계속 이어져요」라 뜻은 맞지만, 다음 문장의 결과로 읽힐 여지가 있음.
- b6 관찰인 5초 저장마다의 `net::ERR_ABORTED`(Fetch)가 이번에도 났음(해제판 31 · 기본 38). 저장은 도착했음.
- 한계: 헤드리스 Chrome 에서만 봤음. 창 있는 브라우저는 확인하지 않았음.

## 만든 데이터 (격리 DB · 지우지 않음)

- `course_attempts` 추가 0행(2행 그대로).
- `course_day_progress` 5행 → 6행. Day 6 은 열고 재생해 생김(6.67). 끝 값은 `db-end.json` 임.
- Day 2 는 앱 API 로 마지막 문장에 놓은 뒤(`api-writes.log`, 1건) 「Day 마치기」로 completed 1 이 됨.
- Chrome·수집기는 `TaskStop` 으로 종료함. :9334 는 비어 있음.

## 덧붙임 (작업 세션 · 2026-11-01)

- 이 회차의 `audio/` 는 `../2026-11-01-b6/audio/` 와 바이트 단위로 같은 사본이었음(`cmp` 로 확인). 중복을 커밋하지 않으려고 이 폴더의 사본을 지웠음 — 입력 음성은 b6 쪽을 봄.
