// 회차 2026-11-01-b9 — CDP 드라이버 공용부. 요소는 data-testid 로 고르고 판정은 DOM 값·API 응답으로 함.
import { writeFileSync } from "node:fs";
export const R = "/Users/redstar/MyProject/OhMyEnglish/tests/agent/runs/2026-11-01-b9/r2";
export const EV = `${R}/evidence`;
export const APP = "http://localhost:3000", API = "http://localhost:8002";
export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function connect(wsUrl) {
  const ws = new WebSocket(wsUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  let id = 0; const pending = new Map(); const listeners = [];
  ws.onmessage = (msg) => {
    const d = JSON.parse(msg.data);
    if (d.id && pending.has(d.id)) { const { res, rej } = pending.get(d.id); pending.delete(d.id); d.error ? rej(new Error(JSON.stringify(d.error))) : res(d.result); }
    else if (d.method) for (const fn of listeners) fn(d);
  };
  const send = (method, params = {}) => new Promise((res, rej) => { const n = ++id; pending.set(n, { res, rej }); ws.send(JSON.stringify({ id: n, method, params })); });
  return { send, on: (fn) => listeners.push(fn), close: () => ws.close() };
}

// 보이는 요소 하나 (사이드바와 좁은 화면 막대에 같은 testid 가 두 번 있으므로 보이는 쪽을 고름)
export const VIS = (tid) => `[...document.querySelectorAll('[data-testid="${tid}"]')].find(e => e.getClientRects().length > 0 && getComputedStyle(e).visibility !== 'hidden')`;

export async function open({ port = 9335, width = 1400, height = 1000 } = {}) {
  const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  const page = list.find((t) => t.type === "page");
  const c = await connect(page.webSocketDebuggerUrl);
  const logs = [];
  c.on((d) => {
    if (d.method === "Runtime.consoleAPICalled") logs.push({ t: Date.now(), kind: "console." + d.params.type, url: null, text: d.params.args.map((a) => a.value ?? a.description ?? "").join(" ").slice(0, 600) });
    if (d.method === "Runtime.exceptionThrown") logs.push({ t: Date.now(), kind: "exception", text: (d.params.exceptionDetails.exception?.description ?? d.params.exceptionDetails.text).slice(0, 600) });
    if (d.method === "Log.entryAdded") logs.push({ t: Date.now(), kind: "log." + d.params.entry.level, url: d.params.entry.url ?? null, text: d.params.entry.text.slice(0, 600) });
  });
  await c.send("Page.enable"); await c.send("Runtime.enable"); await c.send("Log.enable");
  const viewport = (w, h) => c.send("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: 1, mobile: false });
  await viewport(width, height);
  const ev = async (expression) => {
    const r = await c.send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true, userGesture: true });
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description ?? r.exceptionDetails.text);
    return r.result.value;
  };
  const waitFor = async (e, t = 15000, s = 50) => { const st = Date.now(); let last; while (Date.now() - st < t) { try { if (await ev(e)) return Date.now() - st; } catch (x) { last = x; } await sleep(s); } throw new Error("timeout " + e + (last ? " / " + last.message : "")); };
  const nav = async (url, ready) => { await c.send("Page.navigate", { url }); await waitFor(`location.href === ${JSON.stringify(url)} && document.readyState === "complete"`); if (ready) await waitFor(ready); };
  // React 가 붙은 뒤에 누름 (하이드레이션 전 클릭은 무시됨)
  const hydrated = (tid) => `(() => { const b = ${VIS(tid)}; return !!b && Object.keys(b).some(k => k.startsWith('__reactProps')); })()`;
  const click = async (tid, t = 15000) => { await waitFor(hydrated(tid), t); return ev(`(() => { const b = ${VIS(tid)}; if (b.disabled) return 'disabled'; b.click(); return true; })()`); };
  const text = (tid) => ev(`(${VIS(tid)})?.innerText ?? null`);
  const shot = async (name) => { const r = await c.send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true }); writeFileSync(`${EV}/${name}.png`, Buffer.from(r.data, "base64")); };
  // 화면에 보이는 글자 중 한글이 든 줄
  const hangul = () => ev(`(() => { const out = []; const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT); let n;
    while ((n = w.nextNode())) { const s = n.textContent.trim(); if (!s || !/[ㄱ-ㆎ가-힣]/.test(s)) continue; const el = n.parentElement; if (!el || el.getClientRects().length === 0) continue;
      const tid = el.closest('[data-testid]')?.dataset.testid ?? null; out.push({ text: s.slice(0, 160), tid }); }
    for (const el of document.querySelectorAll('[aria-label],[title],[placeholder]')) for (const a of ['aria-label','title','placeholder']) { const v = el.getAttribute(a); if (v && /[ㄱ-ㆎ가-힣]/.test(v)) out.push({ attr: a, text: v.slice(0,160), tid: el.closest('[data-testid]')?.dataset.testid ?? null }); }
    return out; })()`);
  const overflowX = () => ev(`({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth, wide: [...document.querySelectorAll('body *')].filter(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.right > document.documentElement.clientWidth + 1; }).slice(0, 8).map(e => (e.dataset.testid || e.tagName) + ':' + Math.round(e.getBoundingClientRect().right)) })`);
  return { c, ev, waitFor, nav, click, text, shot, hangul, overflowX, viewport, logs, hydrated };
}

export const api = async (path) => { const r = await fetch(`${API}${path}`); return { status: r.status, body: await r.json().catch(() => null) }; };

export function saver(name) {
  const out = {};
  return { out, note: (k, v) => { out[k] = v; console.log(k, typeof v === "string" ? v : JSON.stringify(v)); }, save: () => writeFileSync(`${EV}/${name}.json`, JSON.stringify(out, null, 1)) };
}
