# 회차 2026-11-01-b8 — 문법 코스 실제 Nova 전사 (`TASK-288`)

HEAD `e9130b5`, 작업 트리 깨끗함(이 폴더만 미추적). 회차 시작과 끝 모두 같음.
백엔드 pid 94314 는 03:14:40 KST 에 기동했음. 그 뒤 `app/backend/app` · `app/frontend/app` · `app/frontend/lib` 의 소스 변경은 없었음. 그래서 측정은 모두 `e9130b5` 판에 대한 것임.

## 먼저 알릴 것

1. 공유 판정: :3000(pid 98345) · :8002(pid 94314)는 남의 것이라 재기동·종료하지 않았음. 프로세스 환경은 `VOICE_ADAPTER=nova`, DSN DB 이름 `ohmyenglish_course_paid` 이고 SSO 임시 자격 증명이 있음(만료 04:25:09 UTC). 비밀값은 출력하지 않았음.
2. 이 회차도 전용 런처 없이 서브에이전트로 돌았음. 쓰기는 이 폴더와 `/private/tmp/_b8-*`(모두 삭제함)뿐임. 원장 갱신과 결함 등록은 하지 않았음.
3. 기록 공백: b6 기록에는 in-b · in-c 가 어떤 낱말을 바꾸고 뺐는지 적혀 있지 않음. b6 는 in-a·in-b 를 `u001-s4`(「The server is very slow today.」)에 썼으므로 세 파일 모두 그 문장에서 시도했음. 바뀐 낱말(slow → fast)과 빠진 낱말(very)은 이번 Nova 전사로 알게 된 것임.
4. 자동 모드 입력은 b6 의 `raw-s1.wav` · `raw-s2.wav` 로 새로 합성해 `/private/tmp/_b8-auto-s1s2.wav` 에 두었다가 지웠음. 배치는 `evidence/audio-compose-auto.txt` 에 있음(문장 1 은 2.7초, 문장 2 는 14.4초). raw-s1·s2 가 `u001-s1`·`u001-s2` 를 읽은 것이라는 점도 이번 전사로 확인했음.
5. 착수 기준선은 지시와 같았음. 격리 DB attempts 2 · progress 6 · llm_calls 0 이고 dev DB 는 attempts 0 · progress 0 · llm_calls 109 였음(`db-start.json` · `devdb-start.json`).

## 판정표

| # | 확인 | 판정 | 근거 |
|---|---|---|---|
| 1a | (a) 문장 그대로 | 통과 | 200 · `"the server is very slow today."` · 6낱말 모두 match · 화면 「내가 말한 문장」에 같은 전사 (`ATTEMPT-a.json/png`) |
| 1b | (b) 낱말 하나 바꿈 | 통과 | 200 · `"the server is very fast today."` · 원문 `slow` 만 `different` 이고 computed `underline` (`ATTEMPT-b.json/png`) |
| 1c | (c) 낱말 하나 뺌 | 통과 | 200 · `"the server is slow today"` · 원문 `very` 만 `missing` 이고 computed `line-through` (`ATTEMPT-c.json/png`) |
| 2 | 「따라 함 N회」 | 통과 (5/5) | `u001-s4` 2 → 3 → 4 → 5. 자동 모드에서 `u001-s1` 0 → 1, `u001-s2` 0 → 1. 매번 새로 고침 뒤 같고 API `attempts` 와 같음 (`ATTEMPT-*.json` · `AUTO-r1-reload.json`) |
| 3a | DB 새 행 | 통과 | `course_attempts` 2 → 7. 새 5행 모두 전사가 비어 있지 않음 (`db-end.json`) |
| 3b | `llm_calls` | 통과 | 0 → 5. 모두 `bedrock · amazon.nova-2-sonic-v1:0 · purpose nova` 이고 각 시도와 같은 초에 남음. input 592~607 · output 34~39 토큰 (`db-after-abc.json` · `db-end.json`) |
| 3c | 히트맵·이력 표 | 통과 | 셋 뒤: 오늘 칸 「2026-11-01 · 5회」 · 이력 `11/1 · 1 · 1 · 1문장 · 5회`. 끝: 「2026-11-01 · 7회」 · `11/1 · 1 · 1 · 3문장 · 7회`. 전날 칸 0 이고 DB KST 묶음 `2026-11-01 · 7행 · 3문장` 과 같음. 7 에는 b6 의 빈 전사 2행이 포함됨 (`OVERVIEW-after-abc.json` · `OVERVIEW-end.json`) |
| 4 | 자동 모드 2문장 | 통과 | 문장 1 `"i am a software tester."` → 1.5초 뒤 문장 2 → `"my team is in seoul."` → 1.5초 뒤 문장 3. 문장 2·3 의 listen 에서 전사·안내 모두 null 임. 단계와 말소리 구간: 문장 1 창 2665~5725ms 에 말소리 3334~4713ms, 문장 2 창 14033~16403ms 에 말소리 15033~16093ms (`AUTO-r1.json` · `AUTO-r1-s*-done.png`) |
| 5 | 콘솔 앱 예외 | 통과 (관측 구간 한정) | 4개 Chrome 모두 `exception` 0 · 오류 수준 로그 0. 경고 1건은 YouTube 임베드의 `postMessage` origin 경고임(b7 과 같은 종류) (`console-*.jsonl`) |
| AC4 | dev DB 쓰기 없음 | 통과 | `devdb-start.json` 과 `devdb-end.json` 이 바이트 단위로 같음 |

회귀(b7 대비): 고쳐짐에 해당하는 것은 b6·b7 의 차단 2건(실제 전사 · 자동 모드 실제 전사)임. 이번에 처음 통과했음. 새로 실패 0건임.

## Nova 호출 — 시도 POST 5회 (상한 10)

- `u001-s4` 수동 3회(a · b · c) · `u001-s1` 자동 1회 · `u001-s2` 자동 1회. 5건 모두 200 임.
- 계수 근거: `attempts.jsonl` 의 POST 5건 = 격리 DB 새 행 5건 = 새 `llm_calls` 5건.
- 탐침 3회(`ATTEMPT-a-probe` · `ATTEMPT-probe-s1` · `ATTEMPT-probe-s2`)는 녹음 창이 끝나기 0.5초 전에 떠나 POST 0 임. 자동 흐름은 문장 3 의 repeat 에 들어간 직후 떠나 그 문장의 POST 를 내지 않았음.
- 판정 대기(judge → done)는 5.30~5.50초였음.

## 새 결함

없음.

## 관찰 (결함으로 올리지 않음)

- 전사는 소문자로 시작하고 (c) 는 마침표도 없음. 낱말 판정은 대소문자·문장부호와 무관하게 match 를 냈음.
- b6·b7 관찰인 진행 저장 `net::ERR_ABORTED`(Fetch)가 이번에도 34건 났음. 진행 저장 POST 34건과 수가 같음. 저장은 도착했음(`progress.updated_at` 이 오름).
- b7 의 「앞 문장 안내가 다음 문장 동안 남음」은 이번에 안내가 생기지 않아(모두 실제 전사) 그 경로를 다시 재지 못했음. 전사 결과가 다음 문장의 listen 에서 지워지는 것만 확인했음.
- 한계: 헤드리스 Chrome 156 · 합성 음성 · 가짜 장치에서만 봤음. 물리 마이크 경로는 사람이 확인할 몫임.

## 만든 데이터 (격리 DB · 지우지 않음)

- `course_attempts` 5행 추가(`u001-s4` 3 · `u001-s1` 1 · `u001-s2` 1). `llm_calls` 5행 추가.
- `course_day_progress` 6행 그대로임. Day 1 의 위치가 Unit 1 문장 3 · 6.38초로 갱신됨.
- 앱이 보낸 PCM 사본은 `evidence/sent-*.wav` 5개임.
- Chrome·수집기는 `TaskStop` 으로 종료함. :9334 는 비어 있음. :3000·:8002 는 그대로 떠 있음.
