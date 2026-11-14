# 회차 2026-11-14-b18 — 공통 지시 (화면 탭 · 버튼 탭)

호출자가 쓴 지시임. 두 탭이 이 파일과 자기 탭 지시(`BRIEF-screens.md` · `BRIEF-buttons.md`)를 함께 읽음.

## 대상과 스택 (호출자가 띄움 · 재기동·종료 금지)

- 앱: `http://localhost:3000` (이 리포의 `next dev`, HEAD `8cec9d2` 이후).
- 백엔드: `http://localhost:8002` = 시험용 서버 · 격리 DB `ohmyenglish_course_paid` · `VOICE_ADAPTER=nova`.
- 브라우저: 샌드박스 밖에서 호출자가 띄운 헤드리스 Chrome 임. 가짜 마이크·가짜 권한 UI 가 켜져 있음.
  - 화면 탭 = `http://127.0.0.1:9461` · 버튼 탭 = `http://127.0.0.1:9462`. 자기 포트만 씀.
- dev DB `ohmyenglish` 는 건드리지 않음. 시작 기준선은 `db-dev-start.json` 에 있음.

## 반드시 지킬 것 (회차 b16 실측)

1. ⛔ 브라우저를 직접 띄우지 않음 — 샌드박스 안의 `chromium.launch()` 는 SIGTRAP 으로 죽음. 늘 `chromium.connectOverCDP('http://127.0.0.1:<포트>')` 로 붙음. 새 페이지는 `browser.contexts()[0].newPage()` 로 열고, 끝나면 페이지만 닫음(브라우저는 닫지 않음).
2. ⛔ 셸 명령은 하나씩만 실행함 — `cd … &&` · `;` · `|` 를 붙인 복합 명령은 승인 요청으로 멈춤. 스크립트는 경로를 스스로 풀고(`import.meta.url`) 결과 파일도 스스로 씀. 실행은 `node runs/2026-11-14-b18/<탭>/<스크립트>.mjs` 처럼 단일 명령으로 함.
3. Playwright 는 `import { chromium } from "/Users/redstar/MyProject/OhMyEnglish/tests/agent/tools/node_modules/playwright/index.mjs";` 로 가져옴(스크립트 위치에서 `playwright` 를 찾지 못함). 판은 1.58.2 임.
4. 쓰기는 자기 탭 폴더 `runs/2026-11-14-b18/<screens|buttons>/` 아래뿐임. 앱 소스·`docs/`·리포 원장은 고치지 않음. 커밋하지 않음.
5. 요소는 `data-testid` 로 고름. 문구로 고르는 것은 testid 가 없을 때만이고 그때는 결과에 적음.
6. ⚠️ `/course/<day>` 와 홈 문장 연습은 열기만 해도 진도를 저장함 — 격리 DB 라 괜찮지만 결과에 적음.
7. 실제 코치 세션(Free talk 등 Nova 세션)은 탭마다 최대 2개. 가짜 마이크 소리는 말이 아니므로 전사·분석 결과는 판정하지 않음(버튼·화면 전환만 판정).

## 결과물

- `runs/2026-11-14-b18/<탭>/result.md` — 한국어 · 명사형 「~함」 종결. 판정 표(통과/실패/불확실 · 근거 경로), 결함은 재현 절차와 함께, 관측 수단이 동작했다는 양성 대조.
- 다 끝나면 마지막에 `runs/2026-11-14-b18/<탭>/DONE` 파일을 만듦(내용: 판정 요약 한 줄). 호출자는 이 파일로 끝남을 앎.
