// 회차 b9 — 시나리오 8: 브라우저 수준에서 API 하나만 실패시키고 칸별 안내와 Start speaking 을 봄 (CDP Fetch).
// 사용: node fail.mjs <api 경로 조각> <net|500> [click]
import { open, APP, saver, sleep, VIS } from "./lib.mjs";
const frag = process.argv[2], how = process.argv[3] ?? "net", doClick = process.argv[4] === "click";
const name = `FAIL-${frag.replace(/\//g, "_")}-${how}`;
const { note, save } = saver(name);
const p = await open();
let hits = 0;
p.c.on(async (d) => {
  if (d.method !== "Fetch.requestPaused") return;
  hits++;
  if (how === "net") await p.c.send("Fetch.failRequest", { requestId: d.params.requestId, errorReason: "ConnectionRefused" });
  else await p.c.send("Fetch.fulfillRequest", { requestId: d.params.requestId, responseCode: 500,
    responseHeaders: [{ name: "Content-Type", value: "application/json" }, { name: "Access-Control-Allow-Origin", value: APP }], body: Buffer.from('{"detail":"boom"}').toString("base64") });
});
try {
  await p.c.send("Fetch.enable", { patterns: [{ urlPattern: `http://localhost:8002/api/${frag}*`, requestStage: "Request" }] });
  await p.nav(`${APP}/`);
  await p.waitFor(`['home-streak','home-hero','home-course-progress','home-week-days','home-weekly-stats','home-path','home-focus'].every(t => document.querySelector('[data-testid='+t+']')?.dataset.state !== 'loading')`, 20000);
  await sleep(800);
  note("interceptHits", hits);
  note("cells", await p.ev(`Object.fromEntries(['home-streak','home-hero','home-level','home-course-progress','home-week-days','stat-sessions','stat-best-streak','stat-patterns','home-weekly-stats','home-path','home-focus'].map(t => { const e = document.querySelector('[data-testid='+t+']'); return [t, e ? [e.dataset.state ?? null, e.innerText.replace(/\\s+/g,' ').slice(0, 160)] : null]; }))`));
  const btn = await p.ev(`(() => { const b = ${VIS("start-session")}; const r = b.getBoundingClientRect(); const hit = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);
    return { disabled: b.disabled, hydrated: Object.keys(b).some(k => k.startsWith('__reactProps')), hitIsButton: b.contains(hit) }; })()`);
  note("startSession", btn);
  if (doClick) {
    await p.click("start-session");
    await p.waitFor(`!!document.querySelector('[data-testid=session-overlay]') || location.pathname.startsWith('/results/')`, 10000, 10);
    await p.waitFor(`location.pathname.startsWith('/results/') || !!document.querySelector('[data-testid=session-failed]')`, 60000);
    note("afterClickPath", await p.ev("location.pathname"));
  }
  await p.shot(name);
} catch (e) { note("ERROR", String(e?.stack ?? e)); }
finally { note("logs", p.logs.filter((l) => !/DevTools|HMR/.test(l.text)).map((l) => [l.kind, l.text.slice(0, 200)])); await p.c.send("Fetch.disable").catch(() => {}); save(); p.c.close(); }
