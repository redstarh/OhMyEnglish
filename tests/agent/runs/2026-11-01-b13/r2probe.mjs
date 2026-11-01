// r2 탐침 ① 390 폭 Free talk 누른 직후 카드가 화면 안에 있는지 ② r1 원본 PNG 의 이어 가기 줄·빠른 카드 높이(픽셀 판독)
import { page, APP, sleep } from "./h.mjs";
import { slowSocket } from "./slow.mjs";
import { readFileSync, writeFileSync } from "node:fs";
const R = "/Users/redstar/MyProject/OhMyEnglish/tests/agent/runs/2026-11-01-b13";
const out = {};
const p = await page({ width: 390, height: 844 });
await p.c.send("Page.addScriptToEvaluateOnNewDocument", { source: slowSocket(900) });
await p.nav(`${APP}/`); await sleep(2500);
await p.mouse("practice-free_talk"); await p.waitFor(`document.querySelector('[data-testid=home-hero]')?.dataset.mode === 'session'`, 10000, 20); await sleep(1500);
out.sessionView = await p.ev(`(() => { const h = document.querySelector('[data-testid=home-hero]').getBoundingClientRect(); return { scrollY: Math.round(scrollY), heroTop: Math.round(h.top), heroBottom: Math.round(h.bottom), innerHeight, heroVisiblePx: Math.max(0, Math.min(h.bottom, innerHeight) - Math.max(h.top, 0)) }; })()`);
let r = await p.c.send("Page.captureScreenshot", { format: "png" }); writeFileSync(`${R}/evidence/r2-390-freetalk-view.png`, Buffer.from(r.data, "base64"));
await p.waitFor(`location.pathname.startsWith('/results/')`, 40000, 50);
// ② 픽셀 판독: 세로 한 줄(x)에서 바탕색과 다른 구간의 길이
await p.viewport(1400, 900);
for (const [f, x, y0, y1] of [["raw-r1/s01-01.png", 310, 400, 600], ["raw-r1/s01-01.png", 310, 690, 900], ["raw/../evidence/r2-w1400-idle.png", 310, 380, 900]]) {
  const b64 = readFileSync(`${R}/${f}`).toString("base64");
  out[`${f}@x${x}:${y0}-${y1}`] = await p.ev(`new Promise((res) => { const im = new Image(); im.onload = () => { const c = document.createElement('canvas'); c.width = im.width; c.height = im.height; const g = c.getContext('2d'); g.drawImage(im, 0, 0);
    const px = (x, y) => [...g.getImageData(x, y, 1, 1).data.slice(0, 3)]; const bg = px(280, ${y0}); const diff = (a) => Math.max(...a.map((v, i) => Math.abs(v - bg[i]))) > 4;
    const runs = []; let st = null; for (let y = ${y0}; y < Math.min(${y1}, im.height); y++) { const d = diff(px(${x}, y)); if (d && st === null) st = y; if (!d && st !== null) { runs.push([st, y - st]); st = null; } } if (st !== null) runs.push([st, ${y1} - st]);
    res({ bg, runs: runs.filter(r => r[1] > 20) }); }; im.src = 'data:image/png;base64,${b64}'; })`);
}
console.log(JSON.stringify(out, null, 1)); writeFileSync(`${R}/evidence/r2-probe-misc.json`, JSON.stringify(out, null, 1)); p.c.close();
