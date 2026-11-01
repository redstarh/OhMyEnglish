// 시나리오 6 — 문법 코스: 사이드바 Practice → 코스 목록 → Day 열기 → 영상 + 문장 연습 → ← Back
import { scenario, APP, API, sleep } from "./board.mjs";
const { p, step, note, done } = await scenario("s06");
const phase = `(document.querySelector('[data-testid=course-phase]')?.dataset.phase ?? 'idle')`;
try {
  const day = (await (await fetch(`${API}/api/course`)).json()).current_day; note("current_day " + day);
  const open = { name: `[data-testid=course-day-${day}] 의 a/button`, js: `document.querySelector('[data-testid=course-day-${day}] a, [data-testid=course-day-${day}] button')` };
  await p.nav(`${APP}/`); await sleep(2500);
  await step("홈에서 사이드바 Practice", "nav-practice", { desc: "문법 코스로 감" });
  await p.waitFor(`location.pathname === '/course' && !!document.querySelector('[data-testid=course-day-${day}]')`, 15000); await sleep(1200);
  await step("코스 목록(Day 6개)", open, { desc: `진행 중인 Day ${day} 를 엶` });
  await p.waitFor(`!!document.querySelector('[data-testid=course-start]') && !!document.querySelector('iframe')`, 20000); await sleep(4000);
  await step("Day 화면 · 영상과 문장 연습", "course-start", { desc: "영상 아래 문장을 따라 말함", after: 300 });
  await p.waitFor(`${phase} === 'done'`, 25000).catch((e) => note("phase wait " + e.message)); await sleep(600);
  await step("따라 말하기 뒤 안내(stub)", "course-next", { desc: "다음 문장으로 감" });
  await step("다음 문장", "course-back", { desc: "위치를 저장하고 코스 목록으로 돌아감" });
  await p.waitFor(`location.pathname === '/course'`, 10000); await sleep(1200);
  await step("코스 목록으로 돌아옴", null, { scrollTop: true });
  done(true);
} catch (e) { note("ERROR " + e.message); done(false, e); }
