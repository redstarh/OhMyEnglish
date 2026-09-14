---
id: TASK-61
title: '신규 기능: 음성 명령으로 학습 제어 (PRD Voice Control) — 스키마는 이미 준비됨'
status: In Progress
assignee: []
created_date: '2026-09-09 13:11'
updated_date: '2026-09-14 17:28'
labels: []
dependencies: []
ordinal: 64000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
PRD §4-8 이 「UI와 음성 명령을 모두 통한 학습 제어」를 요구하고 Voice Control 절이 지원 명령을 열거한다: 학습 시작/계속/추가 학습 · 모드 변경 · 반복 · 천천히 말하기 · 힌트 요청 · 다음 문제 · 일시 정지 · 종료 · 복습·리포트 보기. 한국어와 간단한 영어를 모두 지원한다(예: 「추가 연습 시작」 · 「질문 다섯 개 더」 · 「Repeat that slowly.」).

⛔ 요구사항인데 원장에 태스크가 없었다(2026-09-09 사용자 질문에서 발견). 등록 누락이다.

이미 있는 것: ① 스키마가 최초 001 마이그레이션부터 받아들인다 — learning_sessions.started_via CHECK 에 voice_command · utterances.utterance_type CHECK 에 voice_command 와 command_confirmation ② Nova 의 tool 호출이 실물에서 작동한다(발음 tool 로 실증 · promptStart.toolConfiguration → toolUse → contentEnd(TOOL_USE)) ③ services/utterances.py 가 voice_command 를 「저장은 되지만 교정 대상이 아니다」로 이미 다룬다.
없는 것: 어댑터의 명령 실행 경로 하나다 — nova.py:112 가 「명령 실행 경로(voice_command 발화)는 이 어댑터에 없다」고 명시한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 명령 인식 수단을 정한다 — Nova tool 호출로 할지 전사문 패턴으로 할지 근거와 함께 고른다. ⛔ tool 은 이미 작동이 실증됐고 전사문 패턴은 오인식에 약하다
- [ ] #2 command_confirmation 을 쓴다 — 스키마가 그것을 두고 있는 이유가 오인식 방어다. 되돌릴 수 없는 명령(종료)은 확인을 거친다
- [ ] #3 지원 명령의 최소 집합을 정해 구현한다 — PRD 가 열거한 열 가지를 한 번에 다 하지 않고 시작·종료·반복부터 한다
- [ ] #4 한국어와 영어 명령을 모두 받는다 — PRD 가 그 예시를 든다
- [ ] #5 판별력을 게이트로 고정한다 — 명령이 아닌 학습 발화가 명령으로 오인되지 않는 음성 대조를 넣는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-09 조사 — 「음성 제어를 다른 프로젝트에서 참고할 수 있는가」(사용자 질문). 직접 grep 해 얻은 결론은 참고할 구현이 없음임. 대상 경로는 사용자가 지목한 ~/Downloads/realtime-meeting/ 임.

① realtime-meeting (TASK-58 의 참고 리포): 음성 명령 제어 0건임. `wake_word`·`voice_command`·hotword·keyword trigger 히트 0 이고 「명령」 히트 전부가 CLI 하위 명령(`migrate`·`start`·`stop`·`note`)임. 제어 표면이 CLI + 웹 UI 임(README.md). `src/realtime_meeting/**` 의 「발화」 히트 셋은 무음 판정·문장 분리·번역 문맥 복원이라 명령 인식과 무관함. 그 리포의 Fit/Gap 산출물(docs/design/2026-09-09-realtime-meeting-fit-gap.md)에도 「음성 명령」·「voice control」 언급이 0건임 — 조사 범위가 TTS·STT·LLM 이었기 때문임.
② ~/MyProject 전 리포 스캔: OhMyEnglish 자신(42파일 — 우리 PRD·스키마) 과 AllMyEnglish(9파일) 뿐임. WSEAgent·En-Coach·DevInfra·Research 는 0건임.
③ AllMyEnglish 의 9건은 전부 `docs/**` 의 `.md` 임 — 설계·스토리보드·UX 문서이고 구현 코드가 아님. 그 프로젝트는 폐기된 것이라 정본으로 쓰지 않음.

결정 46 (2026-09-09) — AC1 의 수단은 Nova tool 호출로 확정됨. 인식률이 낮은 것을 관측한 뒤에만 AllMyEnglish/docs/** 의 명령 목록·확인 UX 서술을 참고로 엶. 정본으로 쓰지 않고 PRD Voice Control 절과 대조하는 용도임. 근거는 docs/ops/captain-instruction-register.md 결정 46 이 소유함.

착수 전 조사 2026-09-14 (세션 ohmyenglish-f4) — ⛔ 착수하지 않았음. 다음 세션이 다시 조사하지 않게 확인한 사실만 남김.

⚠️ **태스크 제목의 「스키마는 이미 준비됨」을 정확히 갈랐음** — 값역은 있고 «경로»는 0곳임.
값역(있음): 001 이 learning_sessions.started_via 에 voice_command 를, utterances.utterance_type 에 voice_command·command_confirmation 을 최초부터 담았음(011 이 그 CHECK 를 drop·재생성하며 shadowing_recording 을 더했고 두 값은 그대로임).
경로(0곳): 그 두 리터럴을 쓰는 «생산» 코드가 0건임(테스트·하네스에만 있음). sessions.py 가 「started_via 는 인자로 받지 않는다 — 음성 명령 진입이 생기는 턴에 그때 더한다」로, nova.py 가 「명령 실행 경로는 이 어댑터에 없다」로 각각 그 부재를 적어 뒀음.
⇒ 이미 있는 것은 **다루는 로직 하나**임 — utterances.py 가 그 두 종류를 분석 대상에서 빼는 규칙을 이미 가짐(즉 값이 들어오면 오류 분석을 오염시키지 않음).

PRD Voice Control(§7 · R 번호 없이 불릿 다섯): UI 버튼과 «동일한 행동»을 음성으로 · 지원 명령 열거(학습 시작/계속/추가 학습 · 모드 변경 · 반복 · 천천히 말하기 · 힌트 요청 · 다음 문제 · 일시 정지 · 종료 · 복습·리포트 보기) · 한국어와 간단한 영어 · ⛔ 「Oh My English, …」 같은 표지나 명령 버튼으로 학습 답변과 명령을 가름 + 시각적 마이크 상태 · ⛔ 결과가 큰 명령(종료·녹음 삭제)은 음성으로 한 번 더 확인. §4-8 이 MVP 범위로 둠.

Nova tool 배선: 지금 선언된 tool 이 **하나**임(report_pronunciation_coaching). 선언은 nova.py 의 _pronunciation_tool_configuration 이 promptStart.toolConfiguration 에 싣고, 수신은 NovaEventTranslator._on_tool_use 가 이름이 다르면 «버림». ⇒ 명령 tool 을 더하려면 그 두 자리를 함께 고쳐야 하고 이름 분기가 지금 배타적임.

세션 제어의 현재 표면: 클라이언트→서버 메시지가 **4종뿐**임(audio · end_session · shadowing_turn_start · shadowing_turn_end). 종료는 프런트 버튼 하나이고 ⛔ 세션 «중간» 모드 변경 경로는 없음(모드는 접속 쿼리로만 정해지므로 다시 시작해야 함). ⇒ PRD 의 「모드 변경」 명령은 지금 UI 에도 없는 행동이라 「UI 와 동일한 행동」의 대응이 없음 — 그 항목은 범위 판단이 필요함.

경계: 결정 46 이 순서를 고정했음 — Nova tool 로 먼저 만들고, 인식률이 낮은 것을 «관측한 뒤에만» AllMyEnglish 문서를 열며 ⛔ 그것을 정본으로 쓰지 않음. 결정 44 는 realtime-meeting 적용을 TASK-60 하나로 줄였고 그 리포에 wake_word·voice_command 히트가 0건임.

⇒ 범위가 「tool 선언 + 수신 분기 + 명령 실행 경로 + 표지(발화·버튼) + 확인 절차 + 시각적 마이크 상태」이고 그 안에 제품 판단이 둘 있음: ① 지원 명령 열 가지 가운데 무엇을 첫 슬라이스에 넣는가(모드 변경은 UI 에도 없음) ② 표지를 발화(「Oh My English」)로 할지 버튼으로 할지. ⛔ brainstorming → writing-plans 를 태우는 것이 맞음.

착수 2026-09-14 (세션 `ohmyenglish-93`) — 첫 조각을 「안내문만 고침」으로 좁혔음.

## 사용자 판단 셋

1. 필요한 상황: 화면과 버튼은 쓸 수 있고 문제는 대화 흐름이 끊기는 것임. ⇒ 버튼 표지는 목적을 스스로 깎으므로 후보에서 내려갔음.
2. 첫 조각: 「다시 말해 줘 · 천천히 · 힌트」임.
3. 안내문 원칙: 길지 않고 핵심만 간결하게 함. ⇒ 규칙 번호를 새로 만들지 않고 기존 5번에 붙였음.

## ⛔ 조사가 드러낸 갈림 — 열 가지 명령이 성질이 다른 둘임

- **코치가 말로 답하면 끝나는 것**: 다시 말해 줘 · 천천히 · 힌트. 앱 상태를 바꾸지 않으므로 tool·표지·확인 절차가 전부 불필요함.
- **앱 상태를 바꾸는 것**: 종료 · 일시 정지 · 모드 변경 · 다음 문제 · 복습 보기. 이쪽만 tool 이 필요함.

⇒ 첫 조각은 첫째 부류이고, 그래서 AC#1·#2·#5 를 건드리지 않음. ⚠️ 이 갈림을 앞 조사가 잡지 못했음 — 열 가지를 한 목록으로 다뤘기 때문임.

⛔ **「학습 시작」은 이번 범위에서 뺐음.** `api/ws.py:338` 이 연결을 받고 `:378` 에서 곧 세션을 만듦. 즉 연결이 곧 세션 시작이라, 음성으로 시작을 받으려면 세션 전에 마이크를 열어 계속 들어야 함. 그것은 별개 기능이고 이 태스크 범위 밖임.

⚠️ **`hint_timing` 은 이미 있음** — 그날 계획이 「언제 힌트를 줄지」를 지시문에 실음(`nova.py:625`). 없던 것은 「학습자가 먼저 청하는 경우」뿐임. 즉 힌트 기능을 새로 만든 것이 아니고 진입 조건을 하나 넓힌 것임.

## 고친 것

`audio_gateway/nova.py` 의 대화 규칙 5번 한 줄임. 「학습자가 막히면」을 「막히거나 부탁하면」으로 넓히고 「부탁하면 다시 말하거나 천천히 말한다」를 붙였음. 새 규칙 번호를 만들지 않았음.

테스트 하나를 먼저 써서 실패를 직접 본 뒤 고쳤음 — `test_the_coach_answers_a_learners_request_to_repeat_slow_down_or_hint`(`tests/unit/test_nova.py`). 공백을 눕혀 비교함(그 줄이 길이 제한으로 두 줄로 접혀 있음).

## ⚠️ AC 를 하나도 닫지 않았음

AC#3 이 「시작·종료·반복부터」를 제안했으나 이 조각은 그 셋이 아님. AC#1·#2·#5 는 tool 부류에 걸림. ⇒ 진행만 기록함.

## ⛔ 미결 — 문면은 확인했고 거동은 확인하지 못했음

코치가 실제로 부탁을 들어주는지는 실물 통화로만 확인되고 그 회차를 돌리지 않았음. 사용자가 지금 확인 조작을 할 수 없는 상황이라고 알려 왔음. ⚠️ 즉 이 조각은 「안내문에 그 문장이 있음」까지만 참임.

## 게이트 — 그 턴에 직접 돌린 출력

`pytest` **1191 passed**(19.28s · exit 0) · `ruff check` 안·밖 exit 0 · `ruff format --check` 안·밖 exit 0 · `ty` All checks passed.

2026-09-15 (세션 ohmyenglish-65) 착수하지 않음 — 판단과 근거를 남김.

사용자가 자러 가며 남은 작업을 위임했으나, 이 태스크는 «신규 기능»이고 AC#1(명령 인식 수단) · AC#2(command_confirmation 로 오인식 방어) · AC#3(최소 명령 집합)이 제품 계약을 새로 만드는 판단임. ⛔ 내 권고는 사용자가 깨어 있을 때 brainstorming → writing-plans 절차로 시작하는 것임 — 위임이 「제품을 새로 설계해도 된다」로 넓어지지 않는다고 읽었음.

⚠️ 그리고 이 세션이 발음 축의 오염 방어를 방금 넣었고(결정 82·95·98·99·100 이행) 그 방어가 실사용에서 도는 것을 아직 관측하지 않았음 — 새 기능을 얹기 전에 그 관측이 앞서는 것이 순서상 낫다고 판단했음(TASK-78.1 AC#2 가 같은 관측을 요구함).

착수 전 조사는 이미 원장에 있음(AC#1 의 ⛔ 문장이 tool 이 실증됐다는 사실을 적었음).
<!-- SECTION:NOTES:END -->
