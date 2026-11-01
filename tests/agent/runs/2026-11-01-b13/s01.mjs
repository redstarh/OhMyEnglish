// 시나리오 1 — 오늘의 문장 연습: 홈 → Start speaking → 카드 안 문장 연습 → Start → Listen → Next → Close
import { scenario, APP, sleep } from "./board.mjs";
const { p, step, note, done } = await scenario("s01");
const phase = `(document.querySelector('[data-testid=course-phase]')?.dataset.phase ?? 'idle')`;
try {
  await p.nav(`${APP}/`); await sleep(2500);
  await step("홈 대기 화면", "start-session", { desc: "오늘의 Day 카드에서 말하기를 시작함" });
  await p.waitFor(`document.querySelector('[data-testid=practice-day]')?.dataset.state === 'ready'`, 15000); await sleep(800);
  await step("카드 안 문장 연습이 열림", "course-mode-manual", { desc: "자동 이어 가기를 끄고 한 문장씩 진행함" });
  await step("수동 모드로 바꿈", "course-start", { desc: "듣기 → 따라 말하기 → 판정을 한 번 돎", after: 300 });
  await p.waitFor(`${phase} === 'done' && !!document.querySelector('[data-testid=course-notice]')`, 25000).catch((e) => note("notice wait: " + e.message)); await sleep(500);
  note("notice: " + (await p.ev(`document.querySelector('[data-testid=course-notice]')?.innerText ?? null`)));
  await step("따라 말하기 뒤 판정 안내(stub)", "course-listen", { desc: "stub 이라 판정 대신 안내 문구가 뜸 · 다시 들음(Listen 도 한 바퀴를 돎)", after: 300 });
  await p.waitFor(`${phase} === 'done'`, 25000).catch((e) => note("listen wait: " + e.message)); await sleep(500);
  await step("다시 듣기를 마침 · Start 자리가 Try again 으로 바뀜", "course-next", { desc: "다음 문장으로 감" });
  await step("다음 문장", "practice-close", { desc: "연습을 닫고 홈 대기로 돌아감" });
  await sleep(800);
  await step("홈 대기로 돌아옴", null, { scrollTop: true });
  done(true);
} catch (e) { note("ERROR " + e.message); done(false, e); }
