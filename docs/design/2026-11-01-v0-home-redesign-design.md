# v0 홈 대시보드 리디자인 — 설계서

- 작성 2026-11-01 · 태스크 `TASK-292`(결정) · 구현 태스크는 §7
- 디자인 원본: v0 채팅 `mWIhFuLAh5s` → `~/Downloads/oh-my-english-ui-redesign.zip`.
  컴포넌트 사본은 `docs/design/2026-11-01-v0-home-redesign/oh-my-english-dashboard.tsx.txt` 임.
- 설계 초안은 Plan 에이전트가 코드를 읽고 만들었고, 내가 결정·범위에 맞춰 옮겼음.

## 1. 사용자 결정 (2026-11-01)

1. 스타일은 Tailwind v4 + shadcn(+ lucide 아이콘)을 프런트에 도입함.
2. 화면 문구는 홈만이 아니라 모든 화면을 영어로 바꿈. 문구는 학습자의 현재 수준(단문·일상 어휘)에 맞춤(`h-doc`).
3. 데이터가 없는 칸은 가짜 수치를 두지 않고 있는 데이터로 채움. 백엔드는 바꾸지 않음.
4. 범위는 홈 + 공통 틀임. 사이드바와 밝은 테마를 모든 화면에 두고, 다른 화면의 내부 배치는 그대로 둠.
5. 위 넷 뒤에 사용자는 「추천대로 계속 진행」을 지시했음. 그래서 아래 권장안은 묻지 않고 확정으로 봄.

## 2. 먼저 처리할 함정 셋

1. `app/globals.css` 의 `* { padding: 0; margin: 0 }` 은 CSS 층 밖에 있어 Tailwind 간격 클래스를 이김. `@layer base` 로 옮김.
2. `--accent` 의 뜻이 충돌함. 이 앱에서는 브랜드 색(인라인 15곳)이고 shadcn 에서는 옅은 hover 배경임. shadcn 의 `--color-accent` 는 `--surface` 를 가리키게 하고, 이름 `--accent` 는 브랜드 색으로 남김.
3. 하네스(`tests/harness/`)와 회차 드라이버가 한국어 문구와 토큰 이름 둘(`--foreground` · `--foreground-muted`)을 읽음. 문구를 바꾸는 태스크에서 그 시험 코드도 함께 바꿈.

## 3. 구조 결정

| 주제 | 결정 | 근거 |
|---|---|---|
| 테마 | 밝은 테마만 둠. 어두운 테마 블록을 지움 | 결정 4 · 대비 검사를 한 벌만 함 |
| 기존 토큰 | 이름을 모두 남기고 값만 밝은 테마로 바꿈 | 각 화면의 인라인 스타일을 고치지 않아도 됨 |
| v0 색 | 되풀이되는 색을 토큰으로 둠(`--brand` · `--brand-soft` · `--hero` · `--page` · 카드 옅은 색 셋) | 인라인 `[#…]` 값 수십 개를 피함 |
| 옛 요소 모양 | Tailwind 기본 재설정이 버튼·제목·목록·입력 모양을 지우므로 `@layer base` 에 최소 모양을 되살림 | 옛 화면이 깨지지 않음 · 유틸리티가 이김 |
| shadcn | `button.tsx` · `lib/utils.ts` · `components.json` 만 손으로 옮김. CLI 패키지 `shadcn` · `tw-animate-css` · `@vercel/analytics` 는 넣지 않음 | 의존성을 줄임 |
| 공통 틀 | `components/app-shell.tsx`(클라이언트) — 넓은 화면은 사이드바, 좁은 화면은 위쪽 아이콘 막대. 데이터를 부르지 않음 | 이동마다 요청이 생기지 않음 |
| 학습 세션 | 세션이 도는 동안(`state !== "idle"`) 화면 전체를 덮는 층으로 그림 | 세션 중 사이드바를 누르면 화면이 내려가 연결이 끊김 |

사이드바 대응(가장 긴 경로가 이김): Home `/` · Practice `/course`(`/course*`·`/videos*` 에서 활성) · Review `/history`(`/results*` 포함) · Progress `/history/weekly`.

## 4. 파일 계획

- 새 파일: `postcss.config.mjs` · `components.json` · `lib/utils.ts` · `components/ui/button.tsx` · `components/app-shell.tsx` · `app/additionalLearning.ts`(추가 학습 목록과 `entryForTarget` 을 옮기고 고정 `key` 를 줌) · `components/home/HomeDashboard.tsx`.
- 바뀌는 파일: `package.json` · `app/globals.css` · `app/layout.tsx` · `app/page.tsx`(세션 논리는 그대로, 대기 상태만 대시보드로) · 각 화면의 문구.
- 문구에 기대지 않도록 `data-testid` 를 더함: `start-session` · `practice-<key>` · `session-failed` · `course-mode-manual` · `course-mode-auto` · `course-start` · `course-prev` · `course-next` · `course-retry` · `course-slow` · `course-listen` · `course-finish` · `course-back`.
- 기존 문법 코스 `data-testid` 13개와 `data-phase` · `data-attempts` · `data-verdict` 는 그대로 둠.

## 5. 대시보드 칸과 데이터

각 칸은 따로 불러 따로 실패함. 한 요청이 실패해도 그 카드만 비고 「Start speaking」은 늘 눌림. 첫 렌더는 모두 「불러오는 중」이라 하이드레이션 어긋남이 없음.

| v0 칸 | 데이터 | 표시 | 없을 때 |
|---|---|---|---|
| 날짜 | 브라우저 날짜(마운트 뒤) | `Sun, Nov 1` | 빈 줄 |
| 인사 「Good morning, Alex」 | 이름 데이터 없음 | `Welcome back.` | — |
| 연속 학습일 | `/api/history` `streak.current` | `3 days in a row` | `Start a streak today` |
| 오늘의 연습 | `next-plan.reason` | 그 문장 | `Let's talk in English.` |
| 레벨 | `next-plan.target_level` | `Speaking · Level A2` | `Speaking` |
| 진도 68% | 문법 코스 완료 Day 수 / 6 | `Course 2 / 6 days` + 막대 | `0 / 6 days` |
| 세션 · 분 · 패턴 | 주간 `session_count` · `streak.longest` · `pattern_count` | `4 Sessions` · `7 Best streak` · `5 Patterns` | `–` · `No weekly report yet.` |
| 주간 목표 4/5 | 최근 7일 중 학습한 날 | `This week: 4 / 7 days` | `0 / 7 days` |
| Continue your path | `/api/course` 의 진행 중 Day 와 다음 Day | `Day 3 · Units 42–62 · 69 min` → `/course/3` | `Can't load the course.` |
| Focus patterns | 오늘 패턴(분석됨) 아니면 주간 상위 패턴 셋 | `target_form` · `3 times today` | `No patterns yet. Start speaking to find them.` |
| 패턴 % 막대 · 「+8% this month」 · 아바타 | 데이터 없음 | 뺌 | — |
| 빠른 카드 셋 | 쉐도잉 · `/videos` · 약점 패턴 집중 | 그 학습을 시작 | — |
| More practice(새로 둠) | 추가 학습 목록 전부 | 버튼 줄 | PRD §7 은 추가 학습을 늘 보이게 함 |

## 6. 백엔드에서 오는 한국어 — 이번 범위 밖(미결)

백엔드를 바꾸지 않는다는 결정 3 에 따라 다음은 한국어로 남음. 영어로 바꾸려면 프롬프트·콘텐츠 변경이 필요하므로 따로 태스크로 둠(`TASK-299`).

1. `next-plan.reason`(홈의 큰 문장) — `services/plan.py` 프롬프트가 한국어 한 문장을 요구함
2. 오류 패턴 `target_form` 의 한국어 자리 표시(`go to the + 장소 명사`)
3. 교정 이유·설명 · 세션 요약 · 주간 인사이트(각 프롬프트가 한국어를 요구함)
4. 문법 코스 단원 `topic`(`content/grammar_basic.json`)
5. 낱말 뜻·번역(설계상 한국어 — 그대로 두는 것이 맞을 것으로 봄)
6. 음성 명령 안내(「헤이, 학습 종료」) — 영어 명령이 실제로 통하는지 실물 음성으로 확인되지 않았음. 확인 전에는 화면 안내를 영어 명령으로 단정하지 않음

## 7. 구현 태스크

| 태스크 | 내용 | 선행 |
|---|---|---|
| `TASK-293` | 도구·토큰: 의존성 · PostCSS · shadcn 버튼 · `globals.css` 밝은 테마 · `layout.tsx` | — |
| `TASK-294` | 공통 틀: 사이드바·좁은 화면 막대 | 293 |
| `TASK-295` | 홈 분리: 추가 학습 목록 분리 · 세션 덮개 층 | 293 |
| `TASK-296` | 대시보드: §5 대응대로 | 294 · 295 |
| `TASK-297` | 모든 화면 영어 문구 · 시험용 `data-testid` | 295 |
| `TASK-298` | 하네스 갱신 · 통합 회차 · codex 리뷰 | 296 · 297 |

## 8. 위험과 확인 방법

- 층 밖 CSS 가 유틸리티를 이김 → `globals.css` 에 층 밖 `*`·`a`·`body`·`html` 규칙이 없는지 grep 함. 8개 경로를 찍어 버튼 테두리·제목 크기를 봄
- Tailwind 가 안 돎 → `npm run build` 통과 · 브라우저에서 shadcn 버튼 높이가 32px 인지 봄
- 대비 → `measure_contrast.py --schemes light` 에서 본문·흐린 글자 둘 다 4.5:1 이상
- 하이드레이션 경고 → 날짜는 effect 에서만 정함 · 개발 서버 콘솔을 봄
- 실시간 세션 깨짐 → 세션 논리는 문구 외 손대지 않음 · 하네스 C1·C5·앱 경로와 회차 하나로 확인
- 번들 크기 → 아이콘은 이름으로만 가져옴 · `/` 의 First Load JS 를 전후 비교함
- 회차 드라이버의 한국어 선택자 → 옛 회차는 증거로 두고 새 회차는 `data-testid` 로 고름
- 회차는 dev DB 가 아니라 격리 DB(`ohmyenglish_course_paid`)와 `VOICE_ADAPTER=stub` 으로 돌림 — 스텁 세션이 학습 데이터를 오염시키지 않게 함
