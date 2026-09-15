---
id: TASK-61.13
title: '결함 후보: 코치가 「연습을 시작한다」고 말했는데 stage 가 requested 에 머물러 앱이 세션을 갈지 않는다'
status: To Do
assignee: []
created_date: '2026-09-15 18:46'
updated_date: '2026-09-15 22:57'
labels: []
dependencies: []
parent_task_id: TASK-61
ordinal: 188000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
회차 `runs/2026-09-16-task61-12-unspecified-mode` §3 이 1회 관측했다(`answer-ko` 팔). 코치가 「Okay, we will do pronunciation practice. … Repeat after me」라 말하고 발음 연습을 그 자리에서 시작했는데 제어 이벤트의 stage 가 `requested` 에 머물러 앱은 세션을 갈지 않았다. ⇒ 학습자에게는 「바뀐 것처럼」 들리고 기록은 `speaking` 세션에 남는다. ⚠️ 안전 쪽으로 틀린 것이다(엉뚱한 세션이 열리지는 않는다) — 그래서 결함 «후보» 다. ⛔ 규칙 13 은 확인이 필요한 명령에 두 번 부르기를 요구하므로 문면 미준수이지만, 표본 1건이라 크기를 모른다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 그 모양의 크기를 실물 회차로 센다 — 종류를 답한 뒤 confirmed 까지 가는 비율
- [x] #2 고치는 자리를 정한다: 문면을 더 세게 할지, 앱이 requested 를 받은 상태를 화면에 드러낼지
- [ ] #3 고치면 실물 회차로 관측한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 회차 1 — 크기 측정 (2026-09-16 KST · 세션 ohmyenglish-42)

정본 `tests/harness/runs/2026-09-16-task61-13-requested-stall/README.md`. 코드 변경 0건 · 검증 전용 스택(DB `ohmyenglish_t6113` · 백엔드 :8012 · 프론트 :3001 · Chrome :9333) · Nova 9세션 · Claude 0회.

AC#1 을 닫았음. **종류를 답한 뒤 `confirmed` 까지 가는 비율 = 4/8** (이 회차 3/6 + 앞 회차 answer-en·answer-ko 2건). 표본 8이므로 기전으로 단정하지 않음.

무엇이 갈랐는가: **코치가 종류를 되물었는가.** 되묻거나 질문으로 물은 4팔 전부 `confirmed`(4/4) · 스스로 `conversation` 을 골라 예고한 4팔 전부 `requested` 에서 정지(0/4). ⚠️ 언어와 엉켜 있으나 a6-ko-yes 가 한국어인데 되묻고 성립했으므로 언어 단독으로는 설명되지 않음.

새 findings 1건: **학습자의 명시적 「예」가 정지를 풀지 못함**(a5-ko-yes · 1/1). 코치가 그 「예」를 확인으로 받지 않고 다음 연습 문장으로 넘어갔음. 별도 태스크로 쪼개지 않고 AC#2 의 재료로 회차 기록에 둠.

해악의 모양: 발음 드릴이 `speaking`·`recommended` 세션 안에서 진행되고 결과 화면에 발음 신호로 남음. 화면에 모드가 바뀌지 않았다는 표시가 없음(스크린샷 둘을 직접 열어 확인했음).

AC#2·#3 은 열려 있음 — AC#2 는 설계 판단이라 통합 테스트 세션이 닫지 않음. ⚠️ 문면을 더 세게 하는 쪽이 이것을 닫는다는 근거는 없음: 앞 회차가 문면을 고쳐 되묻기를 0/4 → 3/5 로 옮겼고 그 뒤에도 이 모양이 4팔에서 났음.

## 개발 세션에 넘기는 요청 (2026-09-16 KST · 결정 112)

**결정 112**: 고치는 자리는 문면이 아니라 **앱**임. 수행 주체는 **개발 세션**임(통합 테스트 세션은 코드를 쓰지 않음). 정본은 `docs/ops/captain-instruction-register.md` 결정 112 임. ⛔ 표면의 모양(화면 표시 · 음성 재확인 · 둘 다)과 어느 층이 갖는가는 **정해지지 않았고 개발 세션의 설계 몫**임.

### 재현 절차 (실측 · 성공률 4팔 중 4팔에서 정지)

1. 검증 전용 스택을 세움 — DB `createdb -O ohmy` + `migrate.py`(`schema_migrations` 22) · 백엔드 `:8012` 래퍼(CORS `:3001` + `NovaEventTranslator.translate` 계측) · 프론트 사본 `:3001`(`node_modules` 하드링크) · 전용 Chrome `:9333`(fake media stream). 상세는 회차 README §0.
2. `tests/harness/p_app_path.py --port 9333 --url http://localhost:3001/ --wav vc15_learning_ko.wav,vc24_modeonly_ko.wav,vc26_kind_ko.wav --next-wait-ms 30000 --quiet-ms 1200 --settle-ms 25000 --settle-timeout-ms 240000 --walk-timeout-ms 60000`
3. 판정: 제어 이벤트가 `requested/conversation` → `requested/pronunciation` 으로 끝나고 `recv.session_started` 가 **1** 이면 재현임.

### 증거

- 회차 정본: `tests/harness/runs/2026-09-16-task61-13-requested-stall/README.md`
- 제어 이벤트 원자료: 같은 디렉터리 `control-events.log`(13건 · 줄마다 ISO 시각)
- 화면: `shot-a5-ko-yes-session.png`(발음 드릴이 speaking 세션 안에서 진행됨) · `shot-a5-ko-yes-results.png`(그 기록이 발음 신호로 남음)
- DB: `sessions.tsv` · `utterances.tsv` · `pronunciation-attempts.tsv`

### 게이트 실측 (기준선 커밋 b93d49f · 이 회차는 코드 변경 0건)

`pytest` 1239 passed(13.99s) · `ruff check` · `ruff format --check` 49 files · `ty check` · 프론트 `npx tsc --noEmit` · `npx eslint .` 여섯 다 초록임.

⛔ 「이렇게 고쳐라」는 이 요청에 없음 — 고침의 설계는 개발 세션 것임. AC#3(고친 뒤 실물 회차 관측)은 통합 테스트 세션이 받음.
<!-- SECTION:NOTES:END -->
