// 회차 b6 — 드라이버 공용부. 판정은 DOM 값·API 응답·DB 로 한다.
import { writeFileSync } from "node:fs";
import { connect, pageTarget, sleep, EV, PORT } from "./cdp.mjs";
export { sleep, EV, PORT };
export const APP = "http://localhost:3000", API = "http://localhost:8002";
export async function open() {
  const c = await connect((await pageTarget()).webSocketDebuggerUrl);
  await c.send("Page.enable"); await c.send("Runtime.enable");
  const ev = async (expression) => {
    const r = await c.send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true, userGesture: true });
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description ?? r.exceptionDetails.text);
    return r.result.value;
  };
  const waitFor = async (e, t = 15000, s = 30) => { const st = Date.now(); while (Date.now() - st < t) { try { if (await ev(e)) return Date.now() - st; } catch {} await sleep(s); } throw new Error("timeout " + e); };
  const btn = (text) => `[...document.querySelectorAll('button')].find(b => b.textContent.trim() === ${JSON.stringify(text)})`;
  const click = async (text) => {
    await waitFor(`(() => { const b = ${btn(text)}; return !!b && Object.keys(b).some(k => k.startsWith('__reactProps')); })()`, 15000, 10);
    return ev(`(() => { const b = ${btn(text)}; b.click(); return true; })()`);
  };
  const nav = async (url, ready) => { await c.send("Page.navigate", { url }); await waitFor(`location.href === ${JSON.stringify(url)} && document.readyState !== "loading"`); if (ready) await waitFor(ready); };
  const reload = async (ready) => { await ev("window.__rm = 1"); await c.send("Page.reload", {}); await waitFor(`!window.__rm && document.readyState !== "loading"`); if (ready) await waitFor(ready); };
  const state = () => ev(`({
    unit: document.querySelector('[data-testid=course-unit]')?.textContent,
    num: document.querySelector('[data-testid=course-sentence-number]')?.textContent,
    sentence: document.querySelector('[data-testid=course-sentence]')?.textContent,
    attempts: document.querySelector('[data-testid=course-attempts]')?.textContent,
    phase: document.querySelector('[data-testid=course-phase]')?.dataset.phase ?? null,
    notice: document.querySelector('[data-testid=course-notice]')?.textContent ?? null,
    transcript: document.querySelector('[data-testid=course-transcript]')?.textContent ?? null,
    words: [...document.querySelectorAll('[data-testid=course-spoken] [data-verdict]')].map(s => ({ w: s.textContent, v: s.dataset.verdict, deco: getComputedStyle(s).textDecorationLine })),
    mode: localStorage.getItem('omy.course.mode'),
  })`);
  const shot = async (name) => { const r = await c.send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true }); writeFileSync(`${EV}/${name}.png`, Buffer.from(r.data, "base64")); };
  const READY = `!!document.querySelector('[data-testid=course-sentence]') && !!(${btn("시작")} || ${btn("다시")})`;
  return { c, ev, waitFor, click, nav, reload, state, shot, btn, READY };
}
export const api = async (path) => (await fetch(`${API}${path}`)).json();
export function saver(name) {
  const out = {};
  return { out, note: (k, v) => { out[k] = v; console.log(k, typeof v === "string" ? v : JSON.stringify(v)); }, save: () => writeFileSync(`${EV}/${name}.json`, JSON.stringify(out, null, 1)) };
}
