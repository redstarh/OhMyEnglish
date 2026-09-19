---
id: TASK-249
title: '검증 회차: 즉시 드릴 경로의 화면 관측과 회귀 기준선 잔여'
status: Done
assignee: []
created_date: '2026-09-19 11:41'
updated_date: '2026-09-19 12:42'
labels: []
dependencies: []
ordinal: 313000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
통합테스트 회차(TASK-229)가 다음 회차 몫으로 남긴 둘을 닫음. ⛔ 첫째가 이 태스크의 핵심임 — TASK-241 이 만든 즉시 드릴 경로를 «내가 쓴 코드가 아닌 맥락»에서 관측함(작성자와 검증자를 가르는 규칙). 백엔드 쪽은 검사로 덮었으나 화면 네 자리(SessionEntry.patternKey · entryQuery·entryFromQuery · dashboardEntryHref · 결과 화면 링크)는 tsc·eslint·build 와 코드 검토로만 확인했음. 대상: 테스트 원장의 TS-36 AC#3 과 TS-4 의 남은 AC 둘.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 TS-36 AC#3 이 화면에서 관측돼 그 시나리오가 Done 으로 닫힘
- [x] #2 TS-4 의 남은 AC 둘(규칙 4 의 성공분 교정 포함 · 규칙 1 대 3 우선순위)이 앱 경로로 관측됨
- [x] #3 관측 결과가 회차 문서로 남고 실패가 있으면 결함으로 등록됨
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
완료 (2026-09-19). 회차 둘로 닫았음 — B8(관측) · B9(고침 뒤 재관측).

AC#1 TS-36 AC#3 — 통과. 회차 B9 가 팔 셋으로 갈랐고 그 증거를 호출 세션이 직접 열어 확인했음:
- 팔 A (?source=additional&pattern=verb_tense_past_simple_for_past_events): session_started 에 focus_pattern = 그 키. 세션 a331a4e5.
- 팔 B (패턴 없음): focus_pattern 키 «부재» (session_started_keys = ['session_id','type']).
- 팔 C (없는 키 「존재하지않는키_b9」): focus_pattern 키 «부재» 이면서 세션은 정상으로 열리고 끝남(프레임에 session_ended 까지). ⇒ 「기록은 남기지만 일어나지 않은 대체는 보고하지 않는다」가 성립함.
팔 C 가 이 회차의 핵심임 — 팔 A 만 재면 모든 세션에 싣는 구현도 통과하고 그것은 반대 방향 결함임.
유료 호출 0건(회차 창 llm_calls 0행) · 회차 자료 전부 걷힘(focus_pattern_key is not null 잔여 0건 · 직접 셌음).

AC#2 TS-4 의 남은 둘 — 통과. 회차 B8 이 격리 사용자로 세션 셋을 심어 앱 경로로 관측했음. 규칙 4 는 job 구성 2|0|1 로 partial_failure + corrections 1건을 «긍정으로» 보였고, 우선순위는 세션 failed + non-terminal 1건이 connection_failed 를 낸 것으로 봤음. ⛔ 판별력은 대조 팔이 만들었음 — 세션 status 한 값만 다르고 job 구성이 같은 팔이 analyzing 을 냈음. 그것이 없으면 「우선순위가 지켜졌다」와 「내 시드가 non-terminal job 을 못 만들었다」를 가를 수 없었음.

AC#3 결함 등록 — TASK-250(초점 대체를 볼 표면 0곳 · 고침) · TASK-251(음성 경로 소유자 부재 · TASK-252 로 결정 대기).

⚠️ 이 태스크가 실제로 잡은 것: 내가 TASK-241 노트에 「기록만 남고 지시문이 안 바뀌면 코치는 다른 것을 연습시키는데 「경로가 있다」로 보인다」를 위험으로 적어 두고도 그것을 밖에서 판정할 수단을 만들지 않았음. 작성자와 검증자를 가른 것이 그 빠뜨림을 드러냈음.

⚠️ 내 착수 지시의 전제 하나가 반증됐음 — 「주소를 직접 치면 마이크 대체본이 죽어 「마이크 권한을 요청하는 중입니다...」에서 멈춤」. 회차 B8 이 대체본 없이 주소를 직접 열었을 때 getUserMedia 가 원본인 채로 resolve 하고 세션이 정상으로 끝났음. 기전 차이(같은 문서 이동이면 대체본이 살아남음)는 실재하므로 마이크 «내용」을 재는 회차에는 여전히 갈림.

함정 둘을 영구 지식으로 옮겼음 — H-CI(orca tab create --url 이 주소를 두 번 로드해 개수 판정이 2배가 됨 · 앱 결함으로 올라갈 뻔했음) · H-CJ(정상일 때 아무것도 안 쓰는 로그의 낡은 mtime 과 앞 회차가 남긴 줄).
<!-- SECTION:NOTES:END -->
