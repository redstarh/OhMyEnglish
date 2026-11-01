// 시나리오 2 — Day 마치기: 홈 문장 연습 → 마지막 문장 → Finish Day → 진도 카드 갱신
import { scenario, APP, API, sleep } from "./board.mjs";
const { p, step, note, done } = await scenario("s02");
const phase = `(document.querySelector('[data-testid=course-phase]')?.dataset.phase ?? 'idle')`;
const course = async () => { const b = await (await fetch(`${API}/api/course`)).json(); return { current_day: b.current_day, days: b.days?.map((d) => [d.day, d.progress?.completed_count ?? null, d.status ?? null]) }; };
try {
  note("course before: " + JSON.stringify(await course()));
  await p.nav(`${APP}/`); await sleep(2500);
  note("progress card before: " + (await p.text("home-progress"))?.replace(/\n/g, " | "));
  await step("홈 대기 · 진도 카드를 봄", "start-session", { desc: "오늘의 Day 연습을 엶" });
  await p.waitFor(`document.querySelector('[data-testid=practice-day]')?.dataset.state === 'ready'`, 15000); await sleep(800);
  await p.mouse("course-mode-manual"); await sleep(300);
  await step("카드 안 문장 연습(수동)", "course-next", { desc: "Next → 를 마지막 문장까지 여러 번 누름(중간 화면은 생략)" });
  let k = 0; while (k < 400 && (await p.ev(`!!document.querySelector('[data-testid=course-next]')`))) { await p.mouse("course-next"); k++; await sleep(60); }
  note(`Next pressed ${k + 1} times`); await sleep(500);
  await step("마지막 문장 · Finish Day 는 아직 비활성", "course-start", { desc: "마지막 문장을 한 번 따라 말함", after: 300 });
  await p.waitFor(`${phase} === 'done'`, 25000); await sleep(600);
  await step("판정이 끝나 Finish Day 가 켜짐", "course-finish", { desc: "이 Day 를 마침" });
  await sleep(1500);
  note("after finish: " + JSON.stringify(await p.sp()));
  note("course after: " + JSON.stringify(await course()));
  await step("You finished this Day! 안내", "practice-close", { desc: "연습을 닫음" });
  await sleep(2500);
  note("progress card after close: " + (await p.text("home-progress"))?.replace(/\n/g, " | ") + " / hero: " + (await p.text("home-hero-title")) + " / " + (await p.text("home-hero-day")));
  await step("홈 대기 · 진도 카드와 Day 카드가 갱신됨", null, { scrollTop: true });
  done(true);
} catch (e) { note("ERROR " + e.message); done(false, e); }
