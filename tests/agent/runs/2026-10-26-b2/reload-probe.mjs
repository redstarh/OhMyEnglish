// 회차 b2 — 일회성 진단: 새로 고침 뒤 각 준비 단계까지의 시간.
import { connect, pageTarget, sleep } from "./cdp.mjs";
const c = await connect((await pageTarget()).webSocketDebuggerUrl);
await c.send("Page.enable");
const ev = async (e) => { const r = await c.send("Runtime.evaluate", { expression: e, returnByValue: true }); return r.result.value; };
await ev("window.__m = 1");
const t0 = Date.now();
c.send("Page.reload", {}).then(() => console.log("reload ack", Date.now() - t0));
const marks = {};
for (let i = 0; i < 1200 && Object.keys(marks).length < 4; i++) {
  let v; try { v = await ev(`({ fresh: !window.__m, ready: document.readyState, sentence: !!document.querySelector('[data-testid=course-sentence]'), hyd: (() => { const b=[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='시작'); return !!b && Object.keys(b).some(k=>k.startsWith('__reactProps')); })() })`); } catch { v = null; }
  if (v) for (const k of ["fresh", "sentence", "hyd"]) if (v[k] && !marks[k]) marks[k] = Date.now() - t0;
  if (v && v.fresh && v.ready === "complete" && !marks.complete) marks.complete = Date.now() - t0;
  await sleep(50);
}
console.log(JSON.stringify(marks));
c.close();
