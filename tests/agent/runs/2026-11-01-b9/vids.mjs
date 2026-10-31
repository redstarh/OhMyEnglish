// 회차 b9 — 시나리오 5: quick-videos · practice-videos · practice-course 링크 이동
import { open, APP, saver, sleep } from "./lib.mjs";
const { note, save } = saver("QUICK-LINKS");
const p = await open();
try {
  for (const tid of ["quick-videos", "practice-videos", "practice-course", "home-path-all", "path-day-1"]) {
    await p.nav(`${APP}/`);
    await p.click(tid, 20000);
    await p.waitFor(`location.pathname !== '/'`, 10000);
    await sleep(800);
    note(tid, { path: await p.ev("location.pathname"), h1: await p.ev("document.querySelector('h1')?.innerText ?? null") });
  }
  note("roleplayDisabled", await p.ev(`(() => { await0 = 0; const b = document.querySelector('[data-testid=practice-roleplay]'); return null; })()`).catch(() => null));
  await p.nav(`${APP}/`); await sleep(1500);
  note("roleplay", await p.ev(`(() => { const b = document.querySelector('[data-testid=practice-roleplay]'); return b ? { disabled: b.disabled, text: b.innerText } : null; })()`));
} catch (e) { note("ERROR", String(e?.stack ?? e)); }
finally { note("logs", p.logs.filter((l) => !/DevTools|HMR/.test(l.text))); save(); p.c.close(); }
