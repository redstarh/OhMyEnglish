// 낱말 줄(공백 없는 span 들)의 최소 폭을 모든 코스 문장에 대해 잼 — 판정 상자 안 글꼴(0.85rem)·marginRight 4px 그대로
import { open, APP, API } from "./lib.mjs";
import { writeFileSync } from "node:fs";
const p = await open({ port: 9365, width: 390, height: 844 });
await p.nav(`${APP}/`); await new Promise((r) => setTimeout(r, 2500));
const all = [];
for (let d = 1; d <= 6; d++) { const j = await (await fetch(`${API}/api/course/days/${d}`)).json(); for (const u of j.units) u.sentences.forEach((s, i) => all.push({ day: d, unit: u.unit, i: i + 1, text: s.text })); }
const widths = await p.ev(`(() => { const host = document.createElement('div'); host.style.cssText = 'position:absolute;left:-9999px;top:0;font-size:0.85rem;white-space:normal;width:min-content'; document.body.appendChild(host);
  const res = ${JSON.stringify(all.map((a) => a.text))}.map(t => { host.innerHTML = ''; for (const w of t.split(/\\s+/).filter(Boolean)) { const s = document.createElement('span'); s.style.marginRight = '4px'; s.textContent = w; host.appendChild(s); } return Math.round(host.getBoundingClientRect().width); });
  host.remove(); return res; })()`);
all.forEach((a, k) => (a.w = widths[k]));
const over = all.filter((a) => a.w > 242);
console.log(JSON.stringify({ total: all.length, over242: over.length, max: Math.max(...widths), byDay: [1,2,3,4,5,6].map((d) => [d, all.filter((a) => a.day === d).length, over.filter((a) => a.day === d).length]), shortestOver: over.sort((a, b) => a.text.length - b.text.length)[0] }));
writeFileSync("evidence/r2-widthscan.json", JSON.stringify(all, null, 1)); p.c.close();
