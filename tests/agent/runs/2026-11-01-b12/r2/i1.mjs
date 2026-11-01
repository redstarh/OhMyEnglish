// 회차 b12r 항목 1 — 홈 Finish Day → Close 직후 카드 3곳이 /api/course 와 맞는가 · 다시 열면 카드가 말한 Day 인가.
import { page, APP, sleep, api } from "./h.mjs";
import { saver } from "./lib.mjs";
const { note, save } = saver(`I1-${process.argv[2]}`);
const p = await page({ width: Number(process.argv[3] ?? 1400) });
const CARD = `(() => { const g = (t) => [...document.querySelectorAll('[data-testid="' + t + '"]')].find(e => e.getClientRects().length); const prog = g('home-progress')?.innerText ?? '';
  return { title: g('home-hero-title')?.innerText ?? null, day: g('home-hero-day')?.innerText ?? null, days: (prog.match(/(\\d+) \\/ 6 days/) || [])[1] ?? null,
    pathDays: [...(g('home-path')?.querySelectorAll('a[data-testid^=path-day-]') ?? [])].map(a => a.dataset.testid + ':' + a.innerText.replace(/\\s+/g, ' ').slice(0, 60)) }; })()`;
// API 로 기대값 계산 — 완료 Day 수는 이번 회차(cycle)에서 끝낸 Day 수
const expected = async () => { const c = (await api("/api/course")).body; const cur = c.days.find((d) => d.day === c.current_day);
  return { current_day: c.current_day, cycle: c.cycle, day: `Day ${cur.day} · Units ${cur.first_unit}–${cur.last_unit}`, title: `Day ${cur.day}: listen and say it.`,
    doneThisCycle: c.days.filter((d) => (d.progress?.completed_count ?? 0) >= c.cycle).length }; };
const matches = (card, exp) => ({ title: card.title === exp.title, day: card.day === exp.day, pathHasCurrent: card.pathDays.some((s) => s.startsWith(`path-day-${exp.current_day}:`)) });
try {
  const e0 = await expected(); note("expBefore", e0);
  await p.nav(`${APP}/`); await p.waitFor(p.hydrated("start-session"), 20000); await sleep(2000);
  note("cardBefore", await p.ev(CARD));
  await p.mouse("start-session"); await p.waitFor(`document.querySelector('[data-testid=practice-day]')?.dataset.state === 'ready'`, 10000); await sleep(500);
  note("openedDay", (await p.sp()).practiceDay);
  await p.mouse("course-mode-manual"); await sleep(200);
  let n = 0; while (n < 150 && (await p.ev(`!document.querySelector('[data-testid=course-finish]')`))) { await p.mouse("course-next"); await sleep(100); n++; }
  await p.mouse("course-start"); await p.phases(15000, (s) => s[0] === "done");
  await p.mouse("course-finish"); await sleep(1500);
  note("finishedNotice", (await p.sp()).notice);
  p.reqs = [];
  await p.mouse("practice-close"); const tc = Date.now();
  const e1 = await expected(); note("expAfter", e1);
  // 닫은 뒤 카드가 API 와 맞기까지 걸린 시간
  let card, ms = null; const st = Date.now();
  while (Date.now() - st < 5000) { card = await p.ev(CARD); const m = matches(card, e1); if (m.title && m.day && m.pathHasCurrent) { ms = Date.now() - tc; break; } await sleep(50); }
  await sleep(500); card = await p.ev(CARD);
  note("cardAfterClose", { card, matchMs: ms, match: matches(card, e1), reqsAfterClose: p.reqs.map((r) => [r.t - tc, r.m, r.u]) });
  await p.shot(`I1-${process.argv[2]}-after-close`);
  await p.mouse("start-session"); await p.waitFor(`document.querySelector('[data-testid=practice-day]')?.dataset.state === 'ready'`, 10000); await sleep(500);
  const reopened = (await p.sp()).practiceDay; note("reopen", { practiceDay: reopened, cardDay: card.day, same: reopened === card.day });
  await p.mouse("practice-close"); await sleep(1000);
  // 새로 고침한 카드와도 같아야 함(진도 카드 숫자의 기준)
  await p.nav(`${APP}/`); await p.waitFor(p.hydrated("start-session"), 20000); await sleep(2500);
  const fresh = await p.ev(CARD); note("cardFreshReload", { fresh, sameAsAfterClose: JSON.stringify(fresh) === JSON.stringify(card) });
} catch (e) { note("ERROR", String(e?.stack ?? e).slice(0, 800)); }
finally { note("logs", p.logs.filter((l) => !/DevTools|HMR|Download the React|Fast Refresh|503/.test(l.text))); save(); p.c.close(); }
