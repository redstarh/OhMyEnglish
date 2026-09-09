---
id: TASK-55
title: '결함(HIGH): 결과 화면이 사용자에게 HTTP 상태 코드를 그대로 보여준다'
status: Done
assignee: []
created_date: '2026-09-09 08:33'
updated_date: '2026-09-09 13:45'
labels: []
dependencies: []
ordinal: 58000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-09 사용자 여정 회차(TS-3)에서 관측. app/frontend/lib/api.ts:95 가 결과 API가 ${response.status}을 반환했습니다 를 던지고, app/frontend/app/results/[sessionId]/page.tsx:116 이 그것을 fetchError 로 세우며 :149-153 이 danger 색으로 그대로 그린다. 없는 세션 uuid 로 결과 화면을 열면 학습자가 결과 API가 404을 반환했습니다 를 본다. 메인이 그 네 줄을 직접 열어 확인했다. 결과 화면에는 홈으로 가는 인앱 링크가 없어(app/frontend/app/page.tsx:233 이 그 사실을 명시) 학습자가 브라우저 조작 없이 빠져나갈 수단이 없다. 곁가지로 그 문장의 조사가 틀린다 — 404(사백사)·422(사백이십이)는 를 이고 을 이 맞는 것은 500 류다. D1 을 고치면 그 문장이 사라지므로 함께 처리한다. 재현: 백엔드를 띄우고 /results/00000000-0000-4000-8000-000000000000 을 연다. API 자체는 404 로 옳게 응답하고 본문은 detail: session not found 다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 상태 코드를 화면 문구로 쓰지 않는다 — API·404 같은 기계 낱말이 학습자 화면에 노출되지 않는다
- [x] #2 404 는 그 학습 결과를 찾을 수 없습니다 류의 학습자 언어로 안내된다
- [x] #3 조사 오류가 사라진다 — 문장을 없애거나 상태 코드를 문구에서 뺀다
- [x] #4 고친 뒤 없는 uuid 로 결과 화면을 열어 문구를 직접 확인한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-09 완료. 상태 코드를 문구에서 빼고 분류용으로만 남겼음.

무엇을 고쳤는가:
① app/frontend/lib/api.ts — `결과 API가 ${status}을 반환했습니다` 를 던지던 자리를 `SessionResultsError(status)` 로 바꿈. `message` 는 영어(콘솔·로그용)임 — 한국어로 두면 다음 사람이 화면에 그려도 되는 문장으로 착각함.
② app/frontend/app/results/[sessionId]/page.tsx — `err.message` 를 그리던 자리를 `failureNotice(err)` 로 바꿈. 404 는 「그 학습 결과를 찾을 수 없습니다.」 · 그 외 4xx 는 「그 학습 결과를 열 수 없습니다.」 · 5xx·네트워크는 「결과를 불러오지 못했습니다. 다시 시도하고 있습니다...」 임. 상태 코드가 문구에서 사라졌으므로 조사 오류(AC3)도 함께 사라짐.
③ 인앱 출구 `← 학습 시작 화면으로` 를 상태와 무관하게 같은 자리에 넣음. ⚠️ 첫 관측에서 링크가 본문 글자와 구별되지 않는 것을 화면으로 직접 봤음 — `globals.css` 의 전역 `a` 가 `text-decoration: none` 이기 때문임. 색 토큰이 4개뿐이라 링크색이 없으므로 이 링크에만 밑줄을 줬고 전역 규칙은 건드리지 않았음.
④ app/frontend/app/page.tsx:233 의 주석이 「결과 화면에 인앱 링크가 없다」를 전제하고 있었음 — 같은 커밋에서 고침. 그 주석의 결론(폴링하지 않는다)은 그대로 두고 경로가 흔해진 사실만 적었음.
⑤ tests/harness/c3_results_screen.py — `MISSING_NOTICE` 상수 도입, `visit` 의 대기 문구와 상호 대조를 그것으로 바꿈. 「학습자 문구에 기계 낱말(API·404·422·HTTP)이 없다」를 단정으로 추가함. ⛔ 그 단정이 등호의 종속절이 아님을 `test_machine_word_check_has_independent_discrimination` 가 증명함 — 첫 줄은 기대 문구 그대로 두고 둘째 줄로만 상태 코드를 흘려 어긋남이 정확히 1건인 것을 요구함.
⑥ test_c3_gates.py 의 픽스처를 수정 후 회차로 갈았음(runs/2026-09-09-c3-dom-read-post-task55.json). 값을 손으로 고친 것이 아니라 브라우저 다리를 다시 돌렸음. 이전 회차는 그 시점의 기록이라 지우지 않았음.

AC4 증거 — 없는 uuid 로 결과 화면을 열어 직접 봤음: 첫 직계 <p> = `그 학습 결과를 찾을 수 없습니다.` · 상태 라벨 잔존 [] · C3 판정 PASS 58건 전건. 스크린샷 .harness/evidence/c3-missing.png 을 내가 열어서 확인했음(상태 코드 없음 · 밑줄 링크 보임).

게이트: pytest 871 passed · ruff check exit 0 · format unformatted 0 · ty check exit 0 · 게이트 밖 ruff 0건 · 프론트 tsc·eslint exit 0.
회차 기록은 tests/harness/runs/2026-09-09-task55-56-57-results-screen-fix.md 임.
<!-- SECTION:NOTES:END -->
