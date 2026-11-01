// 회차 b11 — 다른 화면에서 홈으로 갔다가 다시 떠날 때 세션 소켓이 열리는지 시각과 함께 잼.
// 사용: node probe.mjs <from-path> <testid-or-logo> [width]
import { open, APP, saver, sleep, VIS } from "./lib.mjs";
const [from, tid, W] = process.argv.slice(2);
const { note, save } = saver(`PROBE${from.replace(/\//g, "_")}-${tid}-${W ?? 1400}`);
const p = await open({ port: 9347, width: Number(W ?? 1400), height: 1000 });
await p.c.send("Network.enable");
const t0 = Date.now(); const ev = [];
p.c.on((d) => {
  if (d.method === "Network.webSocketCreated" && /8002/.test(d.params.url)) ev.push([Date.now() - t0, "ws", d.params.url]);
  if (d.method === "Page.frameNavigated" && !d.params.frame.parentId) ev.push([Date.now() - t0, "nav", d.params.frame.url]);
  if (d.method === "Page.navigatedWithinDocument") ev.push([Date.now() - t0, "spa", d.params.url]);
});
const mouse = async (t) => {
  const sel = t === "logo" ? `[...document.querySelectorAll('aside a[href="/"], header a[href="/"]')].find(e => e.getClientRects().length && !e.dataset.testid)` : VIS(t);
  const pt = await p.ev(`(() => { const e = ${sel}; const r = e.getBoundingClientRect(); return [Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2)]; })()`);
  for (const type of ["mousePressed", "mouseReleased"]) await p.c.send("Input.dispatchMouseEvent", { type, x: pt[0], y: pt[1], button: "left", clickCount: 1 });
};
await p.nav(`${APP}${from}`); await sleep(3000);
ev.push([Date.now() - t0, "mark", "click " + tid]); await mouse(tid);
await sleep(6000);
ev.push([Date.now() - t0, "mark", "state " + (await p.ev("location.pathname + ' hero=' + document.querySelector('[data-testid=home-hero]')?.dataset.mode"))]);
ev.push([Date.now() - t0, "mark", "navigate away"]); await p.nav(`${APP}${from}`); await sleep(5000);
ev.push([Date.now() - t0, "mark", "end"]);
note("events", ev); note("logs", p.logs.filter((l) => !/DevTools|HMR|Download the React|postMessage/.test(l.text)));
save(); p.c.close();
