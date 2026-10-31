// 회차 b9 — 시나리오 3: 경로별 사이드바 활성 항목(설계서 §3). 사용: node nav.mjs <폭> <결과 세션 id>
import { open, APP, saver, sleep } from "./lib.mjs";
const width = Number(process.argv[2] ?? 1400), sid = process.argv[3];
const { note, save } = saver(`NAV-${width}`);
const p = await open({ width, height: 900 });
const EXPECT = { "/": "home", "/course": "practice", "/course/1": "practice", "/videos": "practice", "/history": "review", "/history/weekly": "progress", [`/results/${sid}`]: "review" };
const rows = [];
try {
  for (const [path, want] of Object.entries(EXPECT)) {
    await p.nav(`${APP}${path}`);
    await sleep(1200);
    const r = await p.ev(`(() => { const vis = [...document.querySelectorAll('[data-testid^=nav-]')].filter(e => e.getClientRects().length > 0);
      return { visibleCount: vis.length, active: vis.filter(e => e.getAttribute('aria-current') === 'page').map(e => e.dataset.testid.slice(4)),
        styles: vis.map(e => [e.dataset.testid, getComputedStyle(e).backgroundColor, getComputedStyle(e).color]) }; })()`);
    rows.push({ path, want, ...r, ok: r.active.length === 1 && r.active[0] === want });
  }
  note("rows", rows);
  note("allOk", rows.every((r) => r.ok));
} catch (e) { note("ERROR", String(e?.stack ?? e)); note("rows", rows); }
finally { note("logs", p.logs.filter((l) => !/DevTools|HMR/.test(l.text))); save(); p.c.close(); }
