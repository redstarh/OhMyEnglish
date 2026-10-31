# 회차 2026-11-01-b9 — 리디자인 통합 회차 (TASK-298 · 리디자인 T6)

## 환경
- HEAD `f6fe294`(회차 시작과 끝이 같음 · `git diff HEAD` 는 비어 있음). 측정 대상 프런트는 `bb53dcd`·`b5952f3`·`f6fe294` 까지임.
- 프런트 :3000(next dev) · 백엔드 :8002(`VOICE_ADAPTER=stub` · 격리 DB `ohmyenglish_course_paid`) — 재기동·종료하지 않았음.
  백엔드가 격리 DB 를 쓰는지는 `/api/course` 의 진행 6행으로 대조함(dev DB 의 진행은 0행임).
- 헤드리스 Chrome 156 둘: :9335 는 가짜 장치·가짜 권한 UI 를 씀 · :9336 은 둘 다 빼고 띄움(마이크 거부용). 드라이버는 CDP 이고 요소는 `data-testid` 로 고름.
  영상 화면에는 testid 가 없어 버튼 문구로 골랐음.
- 공유 판정: 포트 :3000·:8002 는 호출자 소유의 스택이었음. 전역 상태는 바꾸지 않았음.
- 실행 형태: 전용 런처(`run.sh`)가 아니라 서브에이전트로 떴음. 그래서 OS 샌드박스 보장이 없었고 쓰기 경계는 규칙으로만 지켰음.
- 테스트 원장(`tests/agent/backlog/`)과 작업 원장은 갱신하지 않았음 — 호출자가 쓰기를 이 폴더로 한정했음. 결함 등록은 호출자 몫으로 남김.

## 판정표

| # | 시나리오 | 판정 | 근거 |
|---|---|---|---|
| 1 | 홈 1400 폭 · API 대조 | 통과 | 9칸이 API 계산값과 같음(`1 day in a row` · `Let's talk in English.` · `Speaking` · `1 / 6 days` · 막대 17% · `This week: 1 / 7 days` · `0 / 1 / 0` · focus empty). 가짜 수치(`68%`·`Alex`·`+8%`·`Good morning`) 0건. 하이드레이션 경고 0건 (`home-1400.json`) |
| 2 | 홈 390 폭 | 통과 | 칸 8개가 모두 x=20 · 폭 350 으로 세로로 쌓임. 위쪽 막대 4개가 보이고 사이드바 쪽은 숨음. scrollWidth 390 = clientWidth (`home-390.json`) |
| 3 | 사이드바 활성 항목 | 통과 | 7개 경로 × 2 폭 모두 `aria-current=page` 가 하나이고 설계서 §3 대응과 같음 (`NAV-1400.json` · `NAV-390.json`) |
| 4 | 추천 학습 | 통과 | 덮개 층은 fixed · z 50 이고, 사이드바 Home 자리의 `elementFromPoint` 는 덮개 안이었음. Coach 3줄 · You 3줄 → `/results/<id>` 로 이동함. 결과 화면 한국어 0건. 소켓 쿼리는 `source=recommended` (`SESSION-rec.json` · `SESSION-rec2.json`) |
| 5 | 쉐도잉 · More practice · 영상 | 통과 | `quick-shadowing` → `mode=shadowing` · 쉐도잉 패널이 뜨고 DB `shadowing_item_id` 가 채워짐. `practice-pronunciation` → `mode=pronunciation`. `practice-five_questions` → `mode=scenario_intake`. `quick-videos` · `practice-videos` → `/videos`. `practice-course` → `/course`. `practice-roleplay` 는 비활성 (`SESSION-shadow/pron/fiveq/weak.json` · `QUICK-LINKS.json`) |
| 6 | 마이크 거부 | 실패(부분) | 거부 → `session-failed` · `data-reason=microphone_permission_denied` · 「Please allow the microphone and try again.」 · Try again 은 같은 거부를 다시 받음 · `session-failed-home` → 홈 복귀(칸 정상) — 여기까지는 통과임 (`DENY.json`). **추가 학습 진입에서 실패한 뒤 Try again 은 고른 학습을 잃음** → 결함 D1 |
| 7 | 문법 코스 | 통과 · 관찰 1 | 목록: `Round 1` · `Continue ▶` · `Done · 11/1` · `Start` 영어. Day 6 수동: 시작 → repeat(2.1초) → 503 → 「I can't check your speaking now. You can keep going.」 · 다시 · 다음 · 63칸 넘겨 마지막 문장 · `course-finish` 는 done 전 비활성, 뒤 활성 · 마치기 → `completed_count 0→1` · 「You finished this Day!」 · 홈 `2 / 6 days`. 자동: 문장 1 listen → repeat → judge → done → 1.5초 뒤 문장 2 listen → repeat 로 이어짐 (`COURSE-day6.json`). 관찰 O1 |
| 8 | API 하나만 실패(CDP Fetch) | 통과 | 5개 API 를 하나씩 `ConnectionRefused` 로 끊었고 `/api/history` 는 500 으로도 돌렸음. 각각 그 API 에 기대는 칸만 오류 문구로 바뀜. Start speaking 은 늘 활성 · 하이드레이트됨 · 중심 hit 가 버튼임. 이력 실패 상태에서 실제로 눌러 결과 화면까지 감 (`FAIL-*.json`). 관찰 O2 |
| 9 | 영상 · 이력 · 주간 화면 | 통과 | 링크 붙여 넣기 → Check → Save → 영상 화면. 화면 문구는 모두 영어이고 남은 한국어는 YouTube 제목뿐임. 이력·주간의 한국어 0건 (`SCREENS.json`) |
| 10 | 콘솔 앱 예외 | 통과 | 증거 JSON 28개를 모았음. 예외 0 · 비네트워크 console.error 0. 네트워크 오류 28건은 503(stub 판정)과 일부러 끊은 요청뿐임 |

## 결함

### D1 · 실패 화면의 「Try again」이 고른 학습을 버리고 추천 학습으로 다시 엶 — 중간(HIGH 미만 · MEDIUM)
- 재현: 1) 홈에서 `quick-shadowing`(또는 `practice-pronunciation`)을 누름 2) 마이크 요청이 거부됨 → 실패 상자가 뜸 3) 권한을 허용하고 「Try again」을 누름.
- 기대: 같은 진입(`mode=shadowing&source=additional`)으로 다시 엶.
- 실제: 소켓이 `ws://localhost:8002/ws/session`(쿼리 없음)으로 열림. DB 에 `mode=speaking` · `learning_source=recommended` 로 기록됨. 2/2 재현됨(쉐도잉 · 발음).
- 증거: `evidence/RETRY-quick-shadowing.json` · `RETRY-practice-pronunciation.json` · `RETRY-db-rows.json`(같은 진입의 정상 세션 `dd9d247c…` 는 `shadowing`·`additional` 임).
- 경계: 리디자인 전부터 있던 코드임(`0215c45~1` 의 `app/page.tsx` 에도 `onClick={() => void startSession()}`). 이번 회차가 처음 드러냈음.
- 측정 수단: 가짜 UI 플래그가 `Browser.setPermission denied` 를 덮었으므로, 첫 `getUserMedia` 한 번만 `NotAllowedError` 로 거절하는 주입을 썼음.
- 제안: 실패 직전의 `SessionEntry` 를 ref 에 두고 Try again 이 그것을 넘김.

## 관찰 (결함으로 올리지 않음)
- O1 · 수동 모드에서 「Next →」를 누르면 앞 문장의 안내(「I can't check your speaking now…」)가 다음 문장에 남음. 63칸을 넘긴 뒤에도 남아 있었음. b7 의 같은 관찰은 자동 모드였고 자동 쪽은 이번에 고쳐진 것으로 측정됨(문장 2 listen 에서 안내가 빔). 남은 것은 `goTo` 경로임.
- O2 · `/api/daily-summary` 만 실패하면 Focus 칸이 「No patterns yet. Start speaking to find them.」을 보임(`focusView` 는 두 요청이 다 실패해야 오류로 그림). 오늘 패턴이 있는 데이터에서는 거짓 문장이 되지만, 이번 데이터에는 오늘 패턴이 없어 반증하지 못했음.
- O3 · 「Weak spots」와 홈의 「Repair your mistakes」는 「Free talk」와 같은 진입(`source=additional`)을 냄. 리디자인 전 표에서 이어진 구조임.
- O4 · 결과 화면이 「Checking…」에 머묾. 격리 DB 의 분석 작업이 `pending`(attempts=1)으로 남아 있었음 — 스택 환경의 결과로 보이고 프런트 판정 대상이 아님.
- O5 · 「Weekly report · week of Oct 19」(홈)와 `10/19 ~ 10/25`(주간 화면)는 API 의 `week_start` 와 같음. 최신 보고서가 지난주 것이 아니라는 데이터 사실임.

## 남은 한국어
| 어디 | 문구 | 출처 |
|---|---|---|
| `/course/<day>` `course-unit` | `시간의 at · on · in` 등 단원 주제 | 백엔드 콘텐츠(`grammar_basic.json`) · 설계서 §6-4 |
| `/course/<day>` 플레이어 iframe `title` · `/videos` · `/videos/<id>` 제목 | `🕐 [1시간 Day 6] … 영어 듣기 + 따라 말하기 …` | YouTube 메타데이터(외부) |
| 코드에만 확인 · 화면 미관측 | `PAUSED_NOTICE` 「헤이, 학습 계속」 · 확인 대기 「네」 | 프런트 상수 · 설계서 §6-6 의도 |
| 백엔드 응답 본문 · 화면 미노출 | 503 `detail` 「따라 하기 판정을 쓸 수 없다」 | 백엔드 |

홈 · 사이드바 · 세션 · 실패 · 결과 · 이력 · 주간 · 영상 목록의 화면 문구에서는 한국어 0건임. `next-plan.reason` 이 `null` 이라 §6-1 의 홈 큰 문장은 이번 데이터로 관측하지 못했음.

## 차단
- 결과 화면의 교정·요약(§6-3 한국어)은 분석이 끝나지 않아 관측하지 못했음(O4).

## DB 대조
- dev DB `ohmyenglish`: 시작 18 · 144 · 0 · 0 → 끝 18 · 144 · 0 · 0 (`devdb-start.json` · `devdb-end.json`).
- 격리 DB: sessions 10 → 20(10건 모두 이 회차 것 — 시나리오 4·5 여섯 · 8 하나 · D1 측정 둘 · 거부가 먹히지 않았던 D1 1차 시도 하나 `bf0436f6`) · utterances 36 → 96 · progress 6 → 6(Day 6 `completed_count` 0 → 1) · attempts 7 → 7(503 은 기록하지 않음). 행은 남겨 두었음.
- 격리 DB 에 영상 1행(`b502eaf3…`)을 사용자 경로로 더했음.
