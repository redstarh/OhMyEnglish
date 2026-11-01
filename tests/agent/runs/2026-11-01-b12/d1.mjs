// 회차 b12 — 결함 후보 재현: 홈에서 Finish Day → Close 뒤 대기 카드·진도 카드가 갱신되는가, 다시 열면 어느 Day 인가(새로 고침 없이).
import { page, APP, sleep, api } from "./h.mjs";
import { saver } from "./lib.mjs";
const { note, save } = saver(`D1-${process.argv[2]}`);
const p = await page({ width: Number(process.argv[3] ?? 1400) });
const CARD = `(() => { const g = (t) => [...document.querySelectorAll('[data-testid="' + t + '"]')].find(e => e.getClientRects().length); return { title: g('home-hero-title')?.innerText ?? null, day: g('home-hero-day')?.innerText ?? null,
  progress: g('home-progress')?.innerText?.replace(/\\s+/g, ' ').slice(0, 60) ?? null, path: g('home-path')?.innerText?.replace(/\\s+/g, ' ').slice(40, 200) ?? null }; })()`;
try {
  const c0 = (await api("/api/course")).body; note("apiBefore", { current_day: c0.current_day, done: c0.days.filter((d) => (d.progress?.completed_count ?? 0) >= c0.cycle).length });
  await p.nav(`${APP}/`); await p.waitFor(p.hydrated("start-session"), 20000); await sleep(2000);
  note("cardBefore", await p.ev(CARD));
  await p.mouse("start-session"); await p.waitFor(`document.querySelector('[data-testid=practice-day]')?.dataset.state === 'ready'`, 10000); await sleep(500);
  await p.mouse("course-mode-manual"); await sleep(200);
  let n = 0; while (n < 150 && (await p.ev(`!document.querySelector('[data-testid=course-finish]')`))) { await p.mouse("course-next"); await sleep(100); n++; }
  await p.mouse("course-start"); await p.phases(15000, (s) => s[0] === "done");
  await p.mouse("course-finish"); await sleep(1500);
  note("finishedNotice", (await p.sp()).notice);
  await p.mouse("practice-close"); await sleep(1500);
  const c1 = (await api("/api/course")).body; note("apiAfter", { current_day: c1.current_day, done: c1.days.filter((d) => (d.progress?.completed_count ?? 0) >= c1.cycle).length, cycle: c1.cycle });
  note("cardAfterCloseNoReload", await p.ev(CARD));
  await p.shot(`D1-${process.argv[2]}-stale`);
  await p.mouse("start-session"); await p.waitFor(`document.querySelector('[data-testid=practice-day]')?.dataset.state === 'ready'`, 10000); await sleep(500);
  note("reopenNoReload", { practiceDay: (await p.sp()).practiceDay });
  await p.mouse("practice-close"); await sleep(800);
  note("cardAfterReopenClose", await p.ev(CARD));
} catch (e) { note("ERROR", String(e?.stack ?? e).slice(0, 800)); }
finally { note("logs", p.logs.filter((l) => !/DevTools|HMR|Download the React|Fast Refresh|503/.test(l.text))); save(); p.c.close(); }
