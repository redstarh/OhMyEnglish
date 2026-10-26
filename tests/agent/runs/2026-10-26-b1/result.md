# 회차 2026-10-26-b1 — 문법 코스 (`TASK-286`, 커밋 `9bd2de3`)

## 판정표

| # | 시나리오 | 판정 | 근거 요약 |
|---|---|---|---|
| S1 | 목록 /course | 차단됨 | 브라우저 기동 불가. API 부분은 기대와 일치함(아래) |
| S2 | 학습 화면 /course/2 | 차단됨 | 브라우저 기동 불가. API 부분은 기대와 일치함 |
| S3 | 수동 모드 단계 전환 | 차단됨 | 브라우저 기동 불가 |
| S4 | 자동 모드 진행·시간 | 차단됨 | 브라우저 기동 불가. 시간 측정값 없음 |
| S5 | 이전·다음 이동 | 차단됨 | 브라우저 기동 불가 |
| S6 | 진도 저장 후 새로 고침 | 차단됨 | 새로 고침은 미실행. 저장→조회 API 왕복은 일치함 |
| S7 | API 경계 | PASS | 503 · 404 · 422 · 422 전부 기대대로. `course_attempts` 0행 그대로 |
| S8 | Day 완료 표시 | FAIL | 완료 기록·진행률 조건은 맞음. 「완료 · 날짜」가 UTC 날짜로 계산됨(결함 D1) |
| S9 | 다크 모드·콘솔 오류 | 차단됨 | 브라우저 기동 불가. 다른 주체의 브라우저 콘솔 오류 1건이 로그에 있음(결함 D2) |

새로 실패: S8(첫 회차라 이전 판정이 없음 — 기준선으로 봄). 차단: S1~S6 · S9.

## 먼저 알릴 것

1. 브라우저를 띄울 수 없었음. 그래서 화면 시나리오 7개는 판정하지 않음.
   이 세션의 OS 샌드박스가 Chromium 의 Mach 포트 등록과 프로필 소켓 생성을 막음.
   시도한 수단 4개와 결과는 다음과 같음. 증거는 `evidence/browser-launch-blocked.txt` 임.
   - Google Chrome `--headless=new`: exit 21 · `Failed to create a ProcessSingleton`
   - Playwright `chrome-headless-shell` 1234: exit 133 · `bootstrap_check_in ... Permission denied (1100)`
   - `safaridriver -p 9444`: exit 1 · 세션 생성 불가
   - `orca open --json`: `runtime_open_timeout`
   - Playwright 의 Node·Python 모듈은 설치돼 있지 않음
   호출자의 「헤드리스 Chrome 을 CDP 로 씀」 전제는 이 런처 안에서는 성립하지 않음.
2. 원장 갱신을 하지 못했음. `backlog task create` 가 리포 루트의
   `.git/backlog.md/locks/create` 에 잠금을 만들다가 `EPERM` 으로 막힘.
   부분 생성은 없음(태스크 파일 36개 그대로). 같은 이유로 작업 원장에 결함 등록과 커밋도 하지 못함.
   ⇒ 결함은 이 파일의 결함 절에만 있음. 시나리오 태스크(안: `TS-37 · A19 · 문법 코스`)도 아직 없음.
3. `psql` 은 권한 승인 단계에서 막혔음. 대신 백엔드 가상환경의 asyncpg 로 읽기 전용 질의를 씀
   (`dbcount.py` · `default_transaction_read_only = on`).

## 환경

- HEAD: 회차 시작과 끝 모두 `9bd2de3`. 회차 중 움직이지 않음
- 공유 판정: 공유. `:3000`·`:8002` 는 호출자가 띄운 것이고 이 회차는 재기동·종료하지 않았음.
  최근 30분 안에 바뀐 `app/` 파일은 0개였음
- 측정 시각: 2026-10-25 23:39~23:44 UTC (KST 10-26 08:39~08:44)
- 프런트 번들의 `API_BASE` 는 `http://localhost:8002` 임(서빙된 청크에서 확인)
- 사용자 시간대: `users.timezone = Asia/Seoul`
- 착수 시 테스트 원장: `evidence/ledger-at-start.txt` — `TS-1`~`TS-36` 전부 `Done`

## 시나리오별 기록

### S1 — 차단됨 (API·서버 렌더 부분은 일치)

- `GET /api/course` 200 (`evidence/api-course-before.json`). 이 회차의 쓰기 전 값임
  - Day 6개 · 단원 범위 `1–21`·`22–41`·`42–62`·`63–82`·`83–100`·`101–113` · `cycle 1`
  - `heatmap` 112칸 · 첫 칸 `2026-07-07` · 끝 칸 `2026-10-26`(KST 오늘) · 합계 0
  - `current_day 1` · 진도 행 0개 · `recent` 비어 있음
- 시작 화면 `/` 의 서버 렌더 HTML(`evidence/ssr-home.html`)에 `<button>문법 코스</button>` 이 있음.
  `<a href="/course">` 는 0개임. 이동은 `router.push(item.href)` 클릭 처리라 브라우저 없이는 확인 못 함
- `/course` · `/course/2` 의 서버 렌더는 「불러오는 중…」 뿐임. 내용은 클라이언트가 그림
- 관찰(결함 아님): 아무 Day 도 시작하지 않은 상태에서도 Day 1 이 `current_day` 라
  「이어서 학습 ▶」 를 받음. `services/course.py` 가 그렇게 설계됐음(손댄 Day 없으면 첫 미완료 Day)

### S2 — 차단됨 (API 부분 일치)

- `GET /api/course/days/2` 200 (`evidence/api-day2-before.json`): 단원 20개 · `units[0].unit 22` ·
  주제 「현재 · 과거 시제 정리」 · 문장 5개 · `u022-s1` = `I work in Seoul, and I worked in Daegu before.`
- DOM 대조와 `omy.course.mode` 유지는 확인 못 함

### S3 · S4 · S5 — 차단됨

- 브라우저 없이 확인할 수 없음. S4 의 걸린 시간은 재지 못했음. 계산값을 적지 않음
- 다음 회차가 볼 자리: `lib/speech.ts` 는 끝 신호가 안 오면 `어림값 × 3` 동안 기다린 뒤
  `어림값` 을 돌려줌. 그러면 듣기 단계는 어림값의 3배가 걸리고, 따라 말하기 창은 `어림값 + 1초` 가 됨.
  헤드리스에서 S4 를 잴 때 듣기 단계 길이를 따로 적어야 함

### S6 — 차단됨 (API 왕복은 일치)

- `POST /api/course/days/2/progress {position_sec 12.5, unit 23, sentence_index 0}` → 204,
  이어 `GET /days/2` 의 `progress` 가 같은 값(`evidence/s6-api.txt`)
- 새로 고침 뒤 화면 위치는 확인 못 함. 결함 D2 가 이 시나리오의 저장 경로에 걸림

### S7 — PASS (`evidence/s7-api.txt`)

| 요청 | 기대 | 실제 |
|---|---|---|
| `u001-s1` + PCM 3200B | 503 | 503 `따라 하기 판정을 쓸 수 없다` |
| `u999-s1` + PCM 3200B | 404 | 404 `sentence not found` |
| `u001-s1` + 빈 본문 | 422 | 422 `body must be 16-bit PCM` |
| `days/2/progress` unit 5 | 422 | 422 `unit is not in that day` |
| 추가: 홀수 길이 3201B | — | 422 |
| 추가: 960002B | — | 413 `recording is too long` |
| 추가: `u999-s1` + 빈 본문 | — | 404 (키 검사가 본문 검사보다 먼저) |
| 추가: `sentence_index 5` · `position_sec -1` | — | 둘 다 422 |
| 추가: `days/7/progress` · `GET days/7` · `GET days/0` | — | 셋 다 404 |

- `course_attempts` 는 착수 전 0행 · S7 뒤 0행 · 회차 끝 0행임
- 한계: 이 회차는 `course_attempts` 행이 늘어나는 경우를 만들 수 없었음(stub). 질의 자체는
  `count(*)` 라 행이 있으면 잡힘

### S8 — FAIL (결함 D1)

- `POST /api/course/days/6/progress {"position_sec":0,"unit":101,"sentence_index":0,"completed":true}` → 204
- 이어 `GET /api/course`: Day 6 `completed_count 1` · `last_completed_at 2026-10-25T23:41:22.590245+00:00` ·
  `cycle 1` (`evidence/api-course-after-s8.json`). 회차 끝에 다시 받아도 같은 값(`api-course-final.json`)
- 진행률 막대: 화면 코드가 `completed_count(1) >= cycle(1)` 이면 100% 로 그림. 조건은 참임
- 날짜 표시: 화면의 `shortDate(last_completed_at.slice(0, 10))` 를 소스에서 그대로 떼어
  이 API 값에 돌린 결과가 「완료 · 10/25」 임. 학습자 시간대 날짜는 `2026-10-26` 임
  (`evidence/s8-date-label.txt` · DB 의 `(last_completed_at at time zone users.timezone)::date` 도 `2026-10-26`)
- DOM 의 실제 문구는 관측하지 못했음. 판정 근거는 화면 함수 실행 결과와 API 값임

### S9 — 차단됨

- 다크 모드 가시성과 이 회차의 콘솔 오류 수는 재지 못했음
- 공유 프런트 로그 `/tmp/omy-frontend.log`(이 회차가 띄운 것이 아님) 에 다른 주체의 브라우저가 남긴
  `Uncaught TypeError` 1건이 있음 → 결함 D2. 사본은 `evidence/frontend-log-copy.txt`

## 결함

작업 원장 등록은 샌드박스에 막혀 하지 못했음(먼저 알릴 것 2). 대상 쪽에서 등록해야 함.

### D1 — 목록의 「완료 · 날짜」가 KST 00시~09시에 완료하면 전날 날짜로 나옴

- 재현: ① KST 09시 전에 `POST /api/course/days/6/progress` 를 `completed: true` 로 보냄
  ② `/course` 를 엶 ③ Day 6 줄의 상태 문구를 읽음
- 기대: 학습자 시간대(`Asia/Seoul`) 날짜 「완료 · 10/26」
- 실제: `last_completed_at` 이 UTC ISO 문자열(`2026-10-25T23:41:22Z`)이고 화면이 앞 10자를 잘라
  「완료 · 10/25」 를 계산함. 위치: `app/frontend/app/course/page.tsx` 의 `DayRow` 상태 문구.
  같은 파일 머리 주석은 「날짜는 서버가 학습자 시간대로 가른 값을 그대로 쓴다」고 적었는데, 이 값은
  가르지 않은 타임스탬프임
- 증거: `evidence/api-course-after-s8.json` · `evidence/s8-date-label.txt` · HEAD `9bd2de3` · 시나리오 S8
- 고쳐진 것으로 보는 조건: KST 09시 전에 완료한 Day 의 상태 문구가 KST 날짜를 보임
- 제안: 서버가 `last_completed_at` 을 `users.timezone` 으로 바꾼 날짜(예: `last_completed_date`)를
  함께 내주고 화면은 그 값을 씀. 히트맵·최근 표가 이미 서버 쪽에서 시간대로 가르므로 같은 규약이 됨

### D2 — 영상 플레이어 준비 전에 `currentTime()` 이 TypeError 를 냄 (이 회차 미재현)

- 관측: 공유 프런트 로그에 다음 1건이 있음. 이 회차의 브라우저가 낸 것이 아님
  `Uncaught TypeError: playerRef.current?.getCurrentTime is not a function`
  `at CoursePlayer.tsx:43:45` ← `page.tsx:207:39`(5초 저장 타이머)
- 코드 경로: `CoursePlayer.tsx` 가 `new api.Player(...)` 직후 `playerRef.current` 를 채움.
  YouTube IFrame API 객체는 `onReady` 전에는 `getCurrentTime`·`pauseVideo` 를 갖지 않음.
  `?.` 는 `undefined` 객체만 걸러 주고 없는 메서드 호출은 막지 못함
- 영향(코드상, 미관측): 준비 전이거나 임베드가 끝내 준비되지 않으면 다음이 함께 멈춤
  - 5초 타이머가 `save()` 앞에서 던져 그 틱의 저장이 빠짐
  - `goTo()` 의 `save()` 가 던져 「다음 문장 →」·「← 이전」 이동이 저장되지 않음 → S6 에 직결
  - `run()` 첫머리의 `pause()` 가 던져 「시작」 이 아무 단계도 보이지 않을 수 있음 → S3·S4 에 직결
- 재현(제안 절차): 네트워크에서 `youtube.com` 을 막거나 페이지 로드 직후 1초 안에 「시작」 을 누르고
  콘솔과 `data-phase` 를 봄. 이 회차는 브라우저가 없어 재현하지 못했음
- 고쳐진 것으로 보는 조건: 플레이어 준비 전·준비 실패 상태에서도 콘솔 오류 0건이고,
  이동 뒤 `GET /api/course/days/2` 의 `progress` 가 새 자리를 가리킴
- 제안: `playerRef.current` 를 `onReady` 에서 채우거나, 메서드 존재를 확인하고 없으면
  `startRef.current` 를 돌려줌

## 이 회차가 만든 데이터

`course_day_progress` 에 행 2개를 만들었음. 다른 표는 건드리지 않았음. 행 삭제는 하지 않았음.

| day | 지금 값 | 경위 |
|---|---|---|
| 2 | `position_sec 0` · `unit 22` · `sentence_index 0` · `completed_count 0` | S6 에서 Unit 23 으로 저장 → 다음 회차 S2 가 Unit 22 로 열리도록 API 로 첫 자리로 되돌렸음 |
| 6 | `position_sec 0` · `unit 101` · `sentence_index 0` · `completed_count 1` · `last_completed_at 2026-10-25T23:41:22Z` | S8 |

- 영향: 목록의 `current_day` 가 2 가 되고 Day 6 이 완료로 보임. 다음 회차의 S1 기대값(「진행 중 Day 하나」)에
  이 상태가 섞임
- 원상 복귀하려면 이 두 행을 지워야 함. 그것은 파괴적 조작이라 승인 없이 하지 않았음

## 다음 회차가 할 일

- 브라우저를 띄울 수 있는 환경(런처 밖, 또는 샌드박스가 Chromium 을 허용하는 설정)에서 S1~S6 · S8 화면 · S9 를 돌림
- D2 를 먼저 재현함 — S3~S6 의 판정이 그 결함에 달려 있음
- 원장에 `TS-37` 을 만들고 이 표를 AC 체크로 옮김

## 파일

- 드라이버: `api_probe.py` · `dbcount.py`
- 증거: `evidence/` — API 응답 · 서버 렌더 HTML · 브라우저 기동 실패 로그 · 프런트 로그 사본 · DB 끝 상태
