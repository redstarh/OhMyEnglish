# 회차 2026-11-01-b5 — 문법 코스 재검증 (`TASK-287`, HEAD `f574612` + 미커밋 작업 트리)

## 판정표

| # | 시나리오 | 판정 | 근거 요약 |
|---|---|---|---|
| D3-A | `/course/N` 0초에서 약 25초 재생 → 「← 학습 목록」 (b4 절차) | PASS — 고쳐짐(2/2) | Day 3: 직전 30.28 → 저장 25.4 · Day 4: 30.11 → 25.17. 0 으로 덮이지 않음. 차이 4.9초는 5초 주기 오차 (`VIDEO-day3-r1.json` · `VIDEO-day4-r2.json`) |
| D3-B | 저장 위치 S 가 있는 Day 를 목록에서 열어 12초 더 재생 → 「← 학습 목록」 | PASS (2/2) | Day 3: S 66.36 → 직전 82.75 → 저장 80.6 · Day 4: S 37.74 → 54.17 → 52.02 (`VIDEO3-day3-link.json` · `VIDEO3-day4-link.json`) |
| D3-C | 같은 경로에서 브라우저 뒤로 가기(`history.back()`) | PASS (1/1) | S 80.6 → 직전 96.96 → 저장 94.81 (`VIDEO3-day3-back.json`) |
| D3+ | 저장 위치 120 인 Day 를 열자마자 떠나기(0.3초 · 3초) | PASS (2/2) | 두 번 모두 120 유지 (`QUICKLEAVE-day6-*.json`) |
| D5 | Day 1~5 API 완료 → Day 6 마지막 문장 「Day 마치기」 → 6초 머묾 → 「← 학습 목록」 | PASS — 고쳐짐(2/2) | 두 번 모두 `cycle 2 · current_day 1`. 완료 뒤 `updated_at` 이 타이머·떠남·재진입으로 세 번 올라도 그대로임. 목록 강조와 「이어서 학습 ▶」 은 Day 1 (`FINISH-6-d5r1.json` · `FINISH-6-d5r2.json` · `RESUME_LIST-1-d5r1.txt` · `RESUME_LIST-1-d5r2.json`) |
| D5+ | 2회차에서 Day 3 을 문장 3 까지 진행 | PASS | `cycle 2 · current_day 3` · Day 3 「Unit 42 · 문장 3 · 0:00」 · 강조와 「이어서 학습 ▶」 이 Day 3 (`STEP_NEXT-3-plus.json` · `RESUME_LIST-3-plus.json`) |
| D5-V | 영상 끝 완료 경로(2590초에서 열어 끝까지 재생) | PASS | `completed_count 0→1` · 영상 0초 정지 · 30초 동안 다시 재생되지 않음 · 진도 0/101/0 유지 · `current_day 6 → 5` (`VIDEND-day6-r1.json`) |
| D4 | 수동 「Day 마치기」 | PASS | 시작 전·listen 중 disabled · done 뒤 활성 · 누르면 +1 · 첫 문장 · 안내 (`FINISH-6-d5r*.json` · `FINISH-4-c1.json`) |
| D6 | 다른 단원 첫 문장에 둔 Day | PASS | Day 5 Unit 90: 「Unit 90 · 문장 1 · 0:00」 · `current_day 5` · 열면 Unit 90 문장 1 (`RESUME_LIST-5-d6.json`) |
| W | 대기 막대 | PASS | 처음 1.000 · 중간 0.498 · 마지막 0.002 · 단조 감소 (`WAITBAR-2.json`) |
| C1 | 완료 뒤 되감기 — 수동 | PASS | Day 4: 목록 「완료 · 11/1」 · 100% · 다시 열면 Unit 63 문장 1 · 영상 0초 정지 (`FINISH-4-c1.json` · `C1-reopen-video.json`) |
| C2 | 완료 뒤 되감기 — 자동 | PASS | Day 3: +1 한 번 · Unit 42 문장 1 · 영상 0초 정지 (`FINISH-3-c2.json` · `C2-reopen-video.json`) |
| R1~R8 | b3 회귀 핵심 | PASS (8/8) | R1 Day 6개 · 칸 112 · 이동 53ms. R3 자동 `listen → repeat 1951 → judge 4904 → done 4907`. R4 done→listen 1505·1504ms. R7 87ms 뒤 시작. R8 두 변형 모두 `live` 0 |
| N2·N3 | 「다시」 수동 · 자동 「다시」/「이전」 | PASS | 흐름이 b4 와 같은 모양 (`RETRY_MANUAL.json` · `AUTO_RETRY.json`) |
| N11 | 콘솔 | PASS (관측 구간 한정) | 예외 0 · 앱 `console.error` 0. 오류 수준 로그는 stub 503 판정 19건과 YouTube `www-widgetapi` CORS 2건임 (`console-summary.txt`) |

- 회귀(b4 대비): 고쳐짐 2건(D3 · D5) · 새로 실패 0건 · 여전히 실패 0건.
- R3 은 이번에 저장된 모드가 자동이어서 자동 모드로 돌았음. 수동 단계는 N2 가 덮음.

## 먼저 알릴 것

1. 이 회차는 전용 런처 없이 서브에이전트로 돌았음. 쓰기는 이 폴더와 `/private/tmp/_b5-chrome` 뿐이었음.
2. 백엔드 pid 49765 는 00:55:30 KST 에 기동했음. 서비스 변경 시각은 00:54:57 이므로 변경을 싣고 있었음. 프론트(:3000, next dev)가 제공한 번들에 `lastTimeRef` · `finishDay` 가 있음을 확인했음 (`codecheck.json`). HEAD 는 시작과 끝 모두 `f574612` 이고, 회차 중 소스 mtime 변화는 없었음.
3. 수집기 1판이 15:57:58Z 부터 16:15:32Z 까지 연결이 끊긴 채 아무것도 받지 못했음. 그래서 D3-A/B/C 와 D5 1·2차의 콘솔은 관측하지 못했음. 재기동한 2판은 끊기면 다시 붙도록 했음. 이후 D3 떠남 경로(`VIDEO3-day2-link-console.json`) · 완료 경로 C1·C2·영상 끝 · 회귀 전부를 관측했음.
4. 1차 D3 시도는 드라이버가 교체 전 iframe 에 붙어 멈췄음(앱 결함 아님). 매 읽기마다 지금의 iframe 에 다시 붙도록 고쳐서 돌렸음.
5. Chrome 은 `--headless=new --use-fake-device-for-media-stream --use-fake-ui-for-media-stream --autoplay-policy=no-user-gesture-required` 로 띄웠음.
6. 테스트 원장과 작업 원장은 갱신하지 않았음. 회차 폴더 밖 쓰기와 커밋이 금지됐기 때문임.

## 관찰 (결함으로 올리지 않음)

- 저장 위치가 0보다 큰 Day 를 열면 영상이 스스로 재생을 시작했음. `CoursePlayer` 의 `onReady` 가 `seekTo` 를 부르기 때문으로 보임. YouTube API 는 cued 상태의 `seekTo` 를 재생 시작으로 다룸. 다만 이 Chrome 은 자동 재생 제한을 끈 상태였음. 그래서 기본 정책의 브라우저에서도 같은지는 확인하지 못했음. 설계상 의도인지 확인이 필요함.
- 「← 학습 목록」 으로 떠날 때 나가는 POST 는 마지막 5초 타이머 값을 다시 보냄(예: 49.02 → 49.02). 허용 오차(최대 약 5초) 안임.

## 만든 데이터와 정리

- API 쓰기 기록: `evidence/api-writes.log`. 회차 중 `cleanup.py` 로 두 번 중간 초기화했음 (`evidence/db-midreset.txt`)
- `course_attempts` 는 회차 내내 0건(판정은 모두 stub 503)
- 최종 정리(16:20:56Z): 회차 시작(15:56:40Z) 이후 `course_day_progress` 5행을 삭제했음. 회차 이전 행은 0건이었음
  - 삭제 뒤: `attempts 0` · `progress_rows 0` · API `cycle 1 · current_day 1 · progress 전부 null` (`evidence/db-cleanup.txt`)
- `users.timezone` 은 읽기만 함(`Asia/Seoul`). :3000(pid 98345) · :8002(pid 49765) 는 재기동·종료하지 않았음
- Chrome 과 수집기는 `TaskStop` 으로 종료함 · `:9333` 비어 있음 · `/private/tmp/_b5-chrome` 삭제
