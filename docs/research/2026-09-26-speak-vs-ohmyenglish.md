# 스픽(Speak) 대 OhMyEnglish 학습 콘텐츠 비교

작성일: 2026-09-26
근거: 스픽 쪽은 `docs/research/2026-09-26-speak-curriculum.md` · OhMyEnglish 쪽은 이 저장소의 코드와 문서
작성자: Claude 에이전트

## 0. 비교 방법과 경계

이 문서는 스픽 쪽에 새 웹 조사를 하지 않음. 스픽 쪽 사실은 위 조사문서를 그대로 인용함.
OhMyEnglish 쪽 사실은 이 저장소의 코드와 문서에서만 가져옴. 문장마다 파일 경로와 기호 또는
절 이름을 근거로 남김. 줄 번호는 쓰지 않음 — 코드가 바뀌면 줄 번호가 먼저 낡기 때문임.

OhMyEnglish 쪽 근거 상태를 세 가지로 나눔.

- 구현됨: `app/backend/app`·`app/frontend/app`의 코드에 실재함
- 설계서만: `docs/PRD.md`·`docs/design/**` 등 문서에는 있으나 코드에 없음
- 부재: 문서와 코드 모두에 없음

두 서비스는 규모가 다름. 스픽은 다수 사용자를 대상으로 한 상용 서비스임. OhMyEnglish는
단일 고정 사용자를 위한 로컬 도구이고 회원 시스템이 없음(`app/backend/app/models/user.py` —
`FIXED_USER_ID`). 콘텐츠 양을 견줄 때 이 전제를 먼저 읽어야 함.

## 1. 요약

스픽은 CEFR 5단계에 걸쳐 17개 코스·469개 day 페이지로 실측된 사전 제작 콘텐츠와, 오늘의 수업·
스피킹 연습·실전 대화의 3단계 반복 학습, 음소 단위 실시간 발음 코치, 간격 반복 스마트 리뷰,
사전 제작 롤플레이 90개 이상과 프리토킹 120개 이상을 갖춘 상용 서비스임
[출처: 스픽 조사문서 §1·§3·§5]. OhMyEnglish는 사전 제작 콘텐츠가 시드 시나리오 30건과 쉐도잉
클립 1건뿐인 단일 사용자 로컬 도구이고(`scripts/migrate.py` — `SEED_SCENARIOS`,
`SEED_SHADOWING_ITEMS`), 그 대신 학습자의 오류 이력을 근거로 세션마다 Claude가 다음 초점 패턴과
질문을 새로 만들고(`app/backend/app/services/plan.py` — `process_plan`), 대화 5회 뒤에는 학습자
대화 자체에서 맞춤 시나리오를 생성하며(`app/backend/app/services/scenario_generator.py`), 발음은
점수 대신 실시간 음성 모델의 시범·재발화 기록으로만 다룸(`docs/PRD.md` §10). 즉 스픽은 콘텐츠
라이브러리의 폭에서, OhMyEnglish는 개인 오류 이력 기반 생성·복습 루프의 깊이에서 각각 앞서 있음.

## 2. 축별 비교

### 2-1. 커리큘럼 구조·레벨

| | 스픽 | OhMyEnglish |
|---|---|---|
| 레벨 값역 | CEFR A1~C1 5단계 [스픽 조사문서 §2] | CEFR A1~C2 6단계 (`app/backend/app/models/plan.py` — `CefrLevel`) |
| 콘텐츠 단위 | 코스 17개·day 469개 (2024 시점 실측) [스픽 조사문서 §3] | 코스·day 개념 없음 |
| 레벨의 뜻 | 콘텐츠 묶음을 가리키는 값 | 사용자 1명의 진행 상태 컬럼(`users.current_level`) |
| 레벨 이동 규칙 | 미확인 | 한 번에 한 단계만 이동, 하향도 허용 (`app/backend/app/models/plan.py` — `_one_step_or_same`, `docs/PRD.md` R11-7) |

OhMyEnglish는 코스·day 같은 콘텐츠 목차 자체가 코드에 없음. `docs/first-4-weeks.md`가 1~4주차
목표·과제·완료 기준의 표를 두지만, 그 주차 구분을 코드로 강제하는 자리는 없음(설계서만).
레벨은 콘텐츠를 가리키는 값이 아니라 한 사용자의 진행 상태를 나타내는 컬럼 하나이고, 계획
생성이 그 값을 한 단계씩만 옮김(`app/backend/app/models/plan.py` — `PlanOutput._target_level_matches_level_and_instruction`,
`LevelDecision`).

### 2-2. 레슨 단위 형식

| | 스픽 | OhMyEnglish |
|---|---|---|
| 진행 단계 | 오늘의 수업 → 스피킹 연습 → 실전 대화 3단계, 약 20분·100문장 이상 [스픽 조사문서 §5-1] | 세션 모드 값역 5개, 진입점 있는 것은 4개 |
| 반복 방식 | 3단계를 순환·누적 [스픽 조사문서 §5-2] | 초점 패턴 1~2개 + 질문 3~5개를 세션마다 새로 산출 |
| 세션 종료 총평 | 미확인 | 세션 종료 후 별도 비동기 Claude 잡이 생성 |

OhMyEnglish의 세션 모드 값역은 `speaking`·`shadowing`·`review`·`pronunciation`·`scenario_intake`
다섯이고(`app/backend/app/models/session.py` — `SessionMode`), 그중 진입점이 있는 것은 `speaking`·
`shadowing`·`pronunciation`·`scenario_intake` 넷임 — `review`는 값역에는 있으나 소켓 쿼리스트링에
붙일 진입로가 없음(`app/backend/app/services/session_modes.py`). 한 세션의 드릴 질문은 3~5개
중 `drill_count`개만 실제로 대화에 실림(`app/backend/app/audio_gateway/nova.py` —
`build_system_prompt`의 `questions[:drill_count]`). `docs/first-4-weeks.md`의 「일일 세션
템플릿」(Warm-up·Scenario·Repair·Transfer·Close 5단계, 각 분 단위 배분)은 문서에만 있고 그
5단계를 강제하는 코드는 없음(설계서만). `docs/agent-system-prompt.md`의 "Session closing
format"은 실시간 음성 모델이 세션 안에서 그 자리에 총평을 말하는 것으로 적지만, 실제 구현은
세션이 끝난 뒤 별도 Claude 잡이 전사문을 읽어 총평을 만듦(`app/backend/app/services/session_summary.py` —
`build_summary_prompt`·`process_summary`) — 산출 주체가 문서와 다름.

### 2-3. 시나리오·롤플레이

| | 스픽 | OhMyEnglish |
|---|---|---|
| 사전 제작 규모 | 롤플레이 90개 이상, 프리토킹 120개 이상 [스픽 조사문서 §5-6] | 고정 시드 시나리오 30건 |
| 구체 목록 | 상황명·주제명 미확인 [스픽 조사문서 §8-5] | `daily_life` 9·`business` 9·`travel` 6·`shopping` 3·`health` 3 |
| 맞춤 생성 | 미확인(AI 프리톡이 상황·주제를 자유 설정) [스픽 조사문서 §5-5] | 대화 5회 뒤 Claude가 무대·상대·목표·초점·어조 5축으로 자동 생성 |
| 신규·반복 배치 | 미확인 | 창 10회당 신규 3회 고정 비율 |

OhMyEnglish의 시드 시나리오 30건은 `scripts/migrate.py`의 `SEED_SCENARIOS`에 고정 UUID로 박혀
있고, 세션 시작이 그중 하나를 고름(`app/backend/app/services/scenario_rotation.py`). 신규
상황과 반복 상황의 배치는 창 10회당 신규 3회로 고정됨(`app/backend/app/services/scenario_rotation.py` —
`WINDOW`·`NEW_PER_WINDOW`). 대화 5회가 쌓이면 Claude가 그 대화에서 무대·상대·목표·초점·어조
다섯 축을 뽑아 사용자 전용 시나리오를 만들고(`app/backend/app/services/scenario_generator.py` —
`build_scenario_prompt`, `_AXES`), 그렇게 만들어진 시나리오는 `is_generated` 플래그로 시드
시나리오와 구분됨(`app/backend/app/services/scenario_rotation.py` — `Candidate.is_generated`).
`docs/agent-system-prompt.md`의 "Business-report role play"(Status·Change·Risk·Decision·Next
steps 5단계 안내문)는 실제 런타임 시스템 프롬프트(`app/backend/app/audio_gateway/nova.py` —
`SYSTEM_PROMPT`)에는 실리지 않음 — 설계서에만 있음.

### 2-4. 발음 피드백

| | 스픽 | OhMyEnglish |
|---|---|---|
| 판정 단위 | 음소 단위 [스픽 조사문서 §5-4] | 목표 소리(`target_sound`) 단위 |
| 판정 주체 | AI 발음 코치(정확도 93% 이상 주장) [스픽 조사문서 §5-7] | 실시간 음성 모델(Nova) 하나 |
| 점수·등급 | 미확인(음소 단위 분석을 밝히나 점수 체계는 불명) | 명시적 비범위 |
| 결과 기록 | 미확인 | pending·correct·incorrect·unclear 4값 |

OhMyEnglish의 발음 판정은 실시간 음성 모델이 `report_pronunciation_coaching` tool을 불러 기록됨
(`app/backend/app/models/pronunciation.py` — `PRONUNCIATION_TOOL_NAME`). 결과값은
`pending`·`correct`·`incorrect`·`unclear` 네 값이고(같은 파일 — `PronunciationOutcome`), 전사문
기반 분석 경로는 원리적으로 발음을 판정하지 못한다고 명시함(`docs/PRD.md` R10-3). 음소 단위
점수·등급·원어민 유사도 지표는 명시적 비범위이고, 하는 일은 "시범과 재발화 기록"으로 한정됨
(`docs/PRD.md` §5·§10.3). 오디오 원본은 기본 저장하지 않음(`docs/PRD.md` R10-7). 한글 전사·
재요청 같은 보조 신호는 한때 값역에 있었으나 v1.5에서 요구가 철회되어 지금은 쓰는 코드가
0곳임(`docs/PRD.md` §16, `app/backend/app/models/pronunciation.py` 머리말 주석).

### 2-5. 복습·반복

| | 스픽 | OhMyEnglish |
|---|---|---|
| 이름 | 스마트 리뷰(간격 반복) [스픽 조사문서 §5-3] | 복습 사다리 |
| 간격 | 미확인(알고리즘 비공개) | 1일 → 3일 → 7일 고정 3단계 |
| 재발 시 처리 | 미확인 | 처음 단계(1일)로 되돌림 |
| 만성 판정 | 미확인 | 임계값 없이 사실만 제공, 판단은 Claude가 함 |

OhMyEnglish의 복습 간격은 1·3·7일 3단계로 고정되어 있고(`app/backend/app/services/review.py` —
`STAGE_DAYS`), 완주 여부는 정답 횟수를 누적하지 않고 예정일이 지난 뒤 다시 맞혔는지를 이력에서
매번 다시 계산함(같은 파일 — `fold_stages`, `recompute`). 다시 틀린 패턴은 주기를 처음으로
되돌림(`docs/PRD.md` R11-6). 만성 약점 여부는 제품이 임계값을 정하지 않고 재발 세션 수·최대
공백·지속 기간 같은 사실만 조회로 제공하며 판단은 Claude가 함(`app/backend/app/services/chronic.py` —
`load_chronic_metrics`, `deepest_recurrence`, `docs/PRD.md` R11-8). 오류는 시제·관사·전치사·
어순·동사형태·업무표현·발음억양 7종 고정 카테고리로 분류됨(`app/backend/app/models/analysis.py` —
`ErrorCategory`, `docs/agent-system-prompt.md` "Error-memory output").

### 2-6. 개인화·학습 계획

| | 스픽 | OhMyEnglish |
|---|---|---|
| 개인화 방식 | 미확인(코스·레벨 안에서의 진행으로 추정) | 세션 종료마다 오류 이력 기반 계획을 비동기 생성 |
| 계획 입력 | 미확인 | 복습 예정·최근 14일 발화·만성 지표·발음 시도 3계층 |
| 초기 레벨 진단 | 미확인 | 없음(시드 기본값 A2 고정) |
| 즉시 집중 연습 진입 | 미확인 | 결과 화면에서 오류 패턴 카드를 눌러 진입 |

OhMyEnglish는 한 세션이 끝날 때마다 다음 세션 계획을 비동기로 만들어 둠
(`app/backend/app/services/plan.py` — `process_plan`, `build_plan_prompt`). 계획 입력은 복습
예정 패턴·최근 14일 발화와 교정·만성 지표·발음 시도 집계 3계층을 모은 것이고
(`app/backend/app/services/plan_input.py` — `load_plan_input`, `RECENT_WINDOW_DAYS`), 출력은
초점 패턴 1~2개·질문 3~5개·레벨 결정·지시문으로 검증됨(`app/backend/app/models/plan.py` —
`PlanOutput`). 계획이 없거나 생성에 실패해도 학습은 시작됨(`docs/PRD.md` R11-5). 처음 사용자의
레벨을 재는 진단 절차는 코드에 없고, 시드 데이터가 `current_level`을 A2로 고정해 둠
(`scripts/migrate.py` — `seed`). 결과 화면에서 자주 틀리는 패턴 카드를 누르면 그 패턴을 초점으로
한 세션이 즉시 열림(`docs/PRD.md` §17, `app/frontend/app/results/[sessionId]/page.tsx` —
`DAILY_DRILL_LABEL`). 같은 요구의 음성 명령 경로("이 패턴으로 연습 만들어줘")는 v1.6에서
철회되어 화면 진입 하나로 한정됨(`docs/PRD.md` §17.1).

### 2-7. 진행 리포트

| | 스픽 | OhMyEnglish |
|---|---|---|
| 화면 종류 | 조사 범위 밖(마케팅 페이지에 진행 리포트 화면 설명 없음) | 일일 오류 요약·완료 판정·연속 학습일·주간 리포트 |
| 점수·등급 | 미확인 | 명시적 비범위 |
| 월간 분석 | 조사 범위 밖 | 문서에만 있고 코드 없음 |

OhMyEnglish의 진행 리포트는 넷임. 그날 분석된 오류를 패턴별로 담는 일일 오류 요약
(`docs/PRD.md` §13, `app/backend/app/services/daily_summary.py`), 시나리오 1개 완주를 기준으로
한 일일 완료 판정(`docs/PRD.md` §14), 날짜가 하루도 비지 않고 이어진 연속 학습일과 최장 연속일
(`docs/PRD.md` §15, `app/backend/app/services/daily_summary.py` — `load_streak`,
`app/frontend/app/history/page.tsx`), 그리고 그 주의 사실(`WeekFacts`)과 Claude의 판단
(`improving`·`next_scenarios`)을 분리해 담는 주간 리포트(`app/backend/app/services/weekly_report.py`,
`app/backend/app/models/weekly_report.py`)임. 넷 모두 점수·등급·달성률을 담지 않는 것이
명시적 계약임(`docs/PRD.md` §13.2 R13-5, §15.3). `docs/requirements-summary.md`의 "월간 분석"
절은 `docs/PRD.md`에도 코드에도 대응하는 것이 없음 — 요구사항 요약 문서에만 있는 항목임.

### 2-8. 콘텐츠 양·소스

| | 스픽 | OhMyEnglish |
|---|---|---|
| 사전 제작 콘텐츠 | 코스 17개·day 469개(2024 시점 실측), 마케팅 페이지는 "500일·2,000개 이상" 주장 | 시나리오 30건·쉐도잉 클립 1건 |
| 콘텐츠 생성 방식 | 자체 제작·큐레이션으로 추정(미확인) | 세션마다 Claude가 질문·시나리오를 새로 생성 |
| 영상·오디오 소스 | 자체 제작으로 추정(미확인) | 사용자가 붙여넣은 YouTube 링크만 사용, 자동 수집·검색 없음 |
| 낱말 뜻 조회 | 미확인 | 저장하지 않고 매번 Claude 호출 |

OhMyEnglish가 미리 만들어 둔 콘텐츠는 시나리오 30건(`scripts/migrate.py` — `SEED_SCENARIOS`)과
쉐도잉 클립 1건(`scripts/migrate.py` — `SEED_SHADOWING_ITEMS`)뿐임. 그 이상의 콘텐츠는 세션마다
Claude가 그 사용자의 오류 이력에서 새로 만드는 질문·시나리오이거나(`app/backend/app/services/plan.py`,
`app/backend/app/services/scenario_generator.py`), 사용자가 직접 붙여넣는 자료임. 영상 학습은
YouTube 링크를 붙여넣는 것이 유일한 담기 경로이고 검색·자동 수집 기능은 의도적으로 두지 않음
(`app/frontend/app/videos/page.tsx` 머리말 주석). 낱말 뜻 조회도 표나 캐시를 두지 않고 문장을
Claude에 매번 넘겨 얻음(`app/backend/app/services/vocab.py`). 즉 스픽은 대규모 사전 제작 콘텐츠
라이브러리이고, OhMyEnglish는 소량 고정 콘텐츠에 실행 시점 생성·사용자 제공 콘텐츠를 얹은
구조임.

## 3. 격차

### 3-1. 스픽에 있는데 OhMyEnglish에 없는 것

- 코스·day 단위의 대규모 사전 제작 커리큘럼(17개 코스·469개 day) — OhMyEnglish는 코스·day
  개념 자체가 코드에 없음
- 사전 제작 롤플레이 90개 이상·프리토킹 주제 120개 이상 규모의 상황 뱅크 — OhMyEnglish의 고정
  시드는 30건뿐임(생성형으로 보완하지만 사전 제작 뱅크의 규모 자체는 훨씬 작음)
- 음소 단위 발음 정확도 지표(93% 이상 주장)와 그에 준하는 채점 — OhMyEnglish는 점수·등급을
  명시적으로 비범위로 둠(`docs/PRD.md` §5)
- 여러 day를 묶어 복습하는 "리뷰 데이(Review Day)" 같은 코스 내 복습 단위 — OhMyEnglish의
  복습은 코스 단위가 아니라 오류 패턴 단위임

### 3-2. OhMyEnglish에 있는데 스픽 쪽 조사에서 확인되지 않은 것

- 학습자 개인의 오류 이력을 원문·교정·이유·발생 시각까지 저장하고 그 사실을 세션 계획 입력으로
  직접 재사용하는 경로(`app/backend/app/services/plan_input.py`,
  `app/backend/app/services/plan.py`)
- 오류 재발 시 복습 주기를 처음 단계로 되돌리는 규칙(`docs/PRD.md` R11-6) — 스픽의 간격 반복
  알고리즘이 재발을 어떻게 다루는지는 조사문서에 없음
- 결과 화면에서 특정 오류 패턴을 골라 그 패턴에 집중한 세션을 즉시 여는 진입
  (`app/frontend/app/results/[sessionId]/page.tsx`)
- 사용자가 고른 YouTube 영상의 특정 구간에서 문장을 직접 캡처해 쉐도잉·발음·복습 경로에
  그대로 태우는 개인화 콘텐츠 파이프라인(`app/backend/app/services/videos.py`,
  `app/frontend/app/videos/page.tsx`)
- 대화 5회를 근거로 그 학습자만의 시나리오를 자동 생성하는 경로
  (`app/backend/app/services/scenario_generator.py`)
- 오류 이력에 대한 임계값 없는 사실 조회와 판단의 분리(`app/backend/app/services/chronic.py`,
  `docs/PRD.md` R11-8) — 스픽의 판정 기준은 조사문서에서 확인되지 않음

OhMyEnglish 쪽은 저장소 코드가 근거이므로 이 문서에 OhMyEnglish 쪽 "미확인" 항목을 따로 만들지
않음. 아래 4장은 스픽 조사문서의 미확인 사항을 그대로 옮긴 것임.

## 4. 미확인 사항 — 스픽 조사문서에서 옮김

다음은 스픽 쪽 조사가 끝내 확인하지 못한 항목임(`docs/research/2026-09-26-speak-curriculum.md`
§8). 이 문서는 그 미확인을 그대로 유지하고 추측으로 채우지 않음.

1. 32개 마케팅 코스명과 17개 실측 코스 코드의 정확한 대응 관계
2. `basics-2`·`basics-2-2`·`basics-2-3` 세 코스의 실제 이름
3. `be-1`·`be-2`·`bi-1` 코스의 정확한 이름과 `be`·`bi`가 가리키는 말
4. `me`·`pv`·`te` 코드가 정말 엄마·아빠, phrasal verb, travel의 머리글자인지
5. AI 튜터 롤플레이 90개·프리토킹 120개의 구체적인 상황명·주제명 목록
6. 유닛(unit)이라는 용어를 스픽이 실제로 쓰는지
7. 로그인 후 실제 앱 화면에서 3단계 학습법이 화면 단위로 어떻게 구현되는지
8. "500일"과 실측 469일의 차이가 반올림인지 시점 차이인지
9. 영어판 커리큘럼 페이지(`https://www.speak.com/en/content`)가 HTTP 404인 이유

## 5. 참고 문서

- `docs/research/2026-09-26-speak-curriculum.md` — 스픽 쪽 근거 정본
- `docs/PRD.md` v1.6 — OhMyEnglish 요구사항 정본
- `docs/requirements-summary.md` v1.1 — 학습자 관점 요약
- `docs/first-4-weeks.md` — 첫 4주 학습 플로우 설계
- `docs/agent-system-prompt.md` — 대화 규칙 설계 정본(런타임 프롬프트와의 차이는 2-2·2-3절 참조)
- `app/backend/app/models/`·`app/backend/app/services/`·`app/backend/app/audio_gateway/` —
  OhMyEnglish 백엔드 구현
- `app/frontend/app/` — OhMyEnglish 프런트엔드 구현
- `scripts/migrate.py` — 시드 데이터 정본
