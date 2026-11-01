// 회차 b11 — 화면의 요소를 하나씩 실제 마우스로 누르고 결과를 기록함.
// 사용: node click.mjs <width> <path> [only-index,...]
// 요소마다 화면을 새로 열고(앞 클릭의 상태를 물려받지 않게) 가운데 좌표에 Input.dispatchMouseEvent 를 보냄.
import { open, APP, saver, sleep } from "./lib.mjs";
import { ENUM, SET } from "./enum.mjs";
const width = Number(process.argv[2]); const path = process.argv[3];
const only = process.argv[4] ? process.argv[4].split(",").map(Number) : null;
const slug = path.replace(/\//g, "_").replace(/^_$/, "_root").slice(0, 40);
const { note, save } = saver(`CLICK-${width}${slug}`);
const p = await open({ port: 9345, width, height: 1000 });
await p.c.send("Network.enable");
let reqs = [], sockets = [], dialogs = [];
p.c.on((d) => {
  if (d.method === "Network.requestWillBeSent" && /:8002|youtube|noembed/.test(d.params.request.url)) reqs.push(`${d.params.request.method} ${d.params.request.url.replace("http://localhost:8002", "")}`);
  if (d.method === "Network.webSocketCreated" && !/_next|webpack/.test(d.params.url)) sockets.push(d.params.url);
  if (d.method === "Page.javascriptDialogOpening") { dialogs.push(`${d.params.type}: ${d.params.message}`); p.c.send("Page.handleJavaScriptDialog", { accept: false }).catch(() => {}); }
});
const key = (e) => `${e.tid}|${e.href}|${e.tag}|${e.text.slice(0, 30)}`;
await p.nav(`${APP}${path}`); await sleep(3500);
const base = await p.ev(ENUM);
const results = [];
for (const [idx, e] of base.entries()) {
  if (only && !only.includes(idx)) continue;
  const r = { idx, tag: e.tag, tid: e.tid, text: e.text.slice(0, 50), href: e.href, disabled: e.disabled, ariaDisabled: e.ariaDisabled };
  if (["iframe", "video", "input", "textarea", "select"].includes(e.tag)) { r.skipped = "입력·삽입 요소 — 별도 시나리오"; results.push(r); continue; }
  try {
    await p.nav(`${APP}${path}`); await sleep(3000);
    const live = await p.ev(ENUM);
    const nth = base.slice(0, idx).filter((b) => key(b) === key(e)).length;
    const match = live.filter((l) => key(l) === key(e))[nth];
    if (!match) { r.result = "다시 연 화면에서 요소를 못 찾음"; results.push(r); continue; }
    // 화면 안으로 끌어온 뒤 가운데 좌표와 그 좌표의 맨 위 요소를 잼
    const pt = await p.ev(`(() => { const el = (${SET})[${match.i}]; el.scrollIntoView({ block: 'center', behavior: 'instant' });
      const b = el.getBoundingClientRect(); const x = Math.round(b.x + b.width / 2), y = Math.round(b.y + b.height / 2);
      const hit = document.elementFromPoint(x, y); return { x, y, hitOnTarget: el === hit || el.contains(hit), hitTag: hit?.tagName }; })()`);
    r.hitOnTarget = pt.hitOnTarget;
    reqs = []; sockets = []; dialogs = [];
    const before = await p.ev("location.pathname + location.search");
    for (const type of ["mousePressed", "mouseReleased"]) await p.c.send("Input.dispatchMouseEvent", { type, x: pt.x, y: pt.y, button: "left", clickCount: 1 });
    await sleep(2500);
    r.after = await p.ev(`({ path: location.pathname + location.search, hero: document.querySelector('[data-testid=home-hero]')?.dataset.mode ?? null,
      failed: document.querySelector('[data-testid=session-failed]')?.dataset.reason ?? null, locked: document.querySelector('nav[data-locked]')?.dataset.locked ?? null })`);
    r.moved = r.after.path !== before;
    if (sockets.length) {
      // 세션이 열렸음 — stub 은 세 턴을 재생하고 끝냄. 결과로 가거나 실패할 때까지 기다림
      try { await p.waitFor(`location.pathname.startsWith('/results/') || !!document.querySelector('[data-testid=session-failed]')`, 45000, 100); } catch (x) { r.sessionWait = String(x).slice(0, 120); }
      r.sessionEnd = await p.ev("location.pathname");
    }
    r.requests = [...new Set(reqs)].slice(0, 12); r.sockets = sockets; r.dialogs = dialogs;
  } catch (x) { r.error = String(x).slice(0, 300); }
  results.push(r); console.log(JSON.stringify(r));
}
note("path", path); note("results", results);
note("logs", p.logs.filter((l) => !/DevTools|HMR|Download the React/.test(l.text)));
save(); p.c.close();
