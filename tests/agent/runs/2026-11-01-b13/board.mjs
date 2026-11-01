// 회차 b13 — 시나리오 화면 보드용 화면 찍기 공용부.
// step(): 누를 요소에 빨간 테두리를 얹고 그 요소가 보이게 스크롤한 뒤 뷰포트를 찍음 → 테두리를 걷고 진짜 마우스로 누름.
// 찍은 원본은 raw/<시나리오>-<번호>.png 로, 단계 정보는 raw/<시나리오>.json 으로 남김.
import { writeFileSync } from "node:fs";
import { page, APP, API, sleep, VIS } from "./h.mjs";
export { APP, API, sleep, VIS };
export const R = "/Users/redstar/MyProject/OhMyEnglish/tests/agent/runs/2026-11-01-b13";

// 요소 지목: 문자열이면 data-testid, { js, name } 이면 그 식이 돌려주는 요소(testid 가 없는 화면용)
export const EL = (t) => (typeof t === "string" ? VIS(t) : t.js);
export const byText = (sel, re, name) => ({ name, js: `[...document.querySelectorAll(${JSON.stringify(sel)})].find(e => e.getClientRects().length && ${re}.test(e.textContent.trim()))` });
const HYD = (t) => `(() => { const b = ${EL(t)}; return !!b && (b.tagName === 'IFRAME' || Object.keys(b).some(k => k.startsWith('__react'))); })()`;
const MARK = (tid) => `(() => { document.getElementById('__b13mark')?.remove(); const e = ${EL(tid)}; if (!e) return null;
  e.scrollIntoView({ block: 'center', behavior: 'instant' }); const r = e.getBoundingClientRect();
  const m = document.createElement('div'); m.id = '__b13mark';
  Object.assign(m.style, { position: 'fixed', left: (r.x - 5) + 'px', top: (r.y - 5) + 'px', width: (r.width + 10) + 'px', height: (r.height + 10) + 'px',
    border: '4px solid #ff2d55', borderRadius: '10px', boxShadow: '0 0 0 4px rgba(255,45,85,.25)', zIndex: 2147483647, pointerEvents: 'none' });
  document.body.appendChild(m); return { text: (e.innerText || e.getAttribute('aria-label') || e.value || '').trim().slice(0, 80), disabled: !!e.disabled }; })()`;
const UNMARK = `document.getElementById('__b13mark')?.remove()`;

export async function scenario(key, { width = 1400, height = 900, port = 9365, init } = {}) {
  const p = await page({ width, height, port });
  if (init) await p.c.send("Page.addScriptToEvaluateOnNewDocument", { source: init });
  const steps = []; const meta = { key, width, height, startedAt: new Date().toISOString(), steps, notes: [] };
  const save = () => writeFileSync(`${R}/raw/${key}.json`, JSON.stringify(meta, null, 1));
  let n = 0;
  const capture = async () => { const r = await p.c.send("Page.captureScreenshot", { format: "png" }); n++; const file = `${key}-${String(n).padStart(2, "0")}.png`; writeFileSync(`${R}/raw/${file}`, Buffer.from(r.data, "base64")); return file; };
  const mouse = async (t) => { const pt = await p.ev(`(() => { const e = ${EL(t)}; if (!e) return null; e.scrollIntoView({ block: 'center', behavior: 'instant' }); const r = e.getBoundingClientRect(); return [Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2)]; })()`);
    if (!pt) throw new Error("no element " + JSON.stringify(t)); for (const type of ["mousePressed", "mouseReleased"]) await p.c.send("Input.dispatchMouseEvent", { type, x: pt[0], y: pt[1], button: "left", clickCount: 1 }); return pt; };
  p.mouseAny = mouse;
  // 단계: 화면을 찍고(누를 요소 표시) 누름. tid 가 없으면 화면만 찍음(마지막 단계).
  const step = async (title, tid, { desc = "", click = true, after = 900, scrollTop = false } = {}) => {
    let el = null;
    if (tid) { await p.waitFor(HYD(tid), 20000); el = await p.ev(MARK(tid)); await sleep(250); }
    else if (scrollTop) { await p.ev("window.scrollTo(0,0)"); await sleep(200); }
    const file = await capture();
    if (tid) await p.ev(UNMARK);
    const rec = { n, title, desc, tid: typeof tid === 'string' ? tid : null, selector: tid && typeof tid !== 'string' ? tid.name : null, label: el?.text ?? null, disabled: el?.disabled ?? null, file, path: await p.ev("location.pathname + location.search"), at: new Date().toISOString() };
    steps.push(rec); console.log(key, n, title, rec.tid ?? rec.selector ?? "-", JSON.stringify(rec.label), rec.path); save();
    if (tid && click) { await mouse(tid); await sleep(after); }
    return rec;
  };
  const note = (s) => { meta.notes.push(s); console.log("NOTE", key, s); save(); };
  const done = (ok = true, err) => { meta.ok = ok; if (err) meta.error = String(err?.stack ?? err).slice(0, 800);
    meta.logs = p.logs.filter((l) => !/DevTools|HMR|Download the React|Fast Refresh/.test(l.text)).slice(0, 60); meta.endedAt = new Date().toISOString(); save(); p.c.close(); };
  return { p, step, note, done, meta };
}
