// 보드 점검: 카드 수 · 깨진 이미지 · 가로 스크롤 줄 · 확대 보기 동작을 재고 화면 2장을 남김
import { open } from "./lib.mjs";
import { writeFileSync } from "node:fs";
const p = await open({ port: 9365, width: 1400, height: 900 });
const url = "file:///Users/redstar/MyProject/OhMyEnglish/tests/agent/runs/2026-11-01-b13/board/index.html";
await p.c.send("Page.navigate", { url }); await p.waitFor(`document.readyState === 'complete'`);
await p.ev(`Promise.all([...document.images].map(i => (i.loading = 'eager', i.complete ? 1 : new Promise(r => { i.onload = i.onerror = r; }))))`);
await new Promise((r) => setTimeout(r, 1500));
const stat = await p.ev(`({ cards: document.querySelectorAll('.card').length, arrows: document.querySelectorAll('.arrow').length, sections: document.querySelectorAll('section').length, lanes: document.querySelectorAll('.lane').length,
  broken: [...document.querySelectorAll('.card img')].filter(i => !i.naturalWidth).map(i => i.src), toc: document.querySelectorAll('nav.toc a').length,
  scrollRows: [...document.querySelectorAll('.row')].filter(r => r.scrollWidth > r.clientWidth).length, pageOverflow: document.documentElement.scrollWidth > innerWidth })`);
console.log(JSON.stringify(stat));
const shot = async (f) => { const r = await p.c.send("Page.captureScreenshot", { format: "jpeg", quality: 70 }); writeFileSync(f, Buffer.from(r.data, "base64")); };
await shot("/private/tmp/_b13-board-top.jpg");
await p.ev(`document.querySelector('#sc7 .card img').click()`); await new Promise((r) => setTimeout(r, 600));
console.log("lightbox", await p.ev(`document.getElementById('lb').classList.contains('on') && document.querySelector('#lb img').naturalWidth`));
await shot("/private/tmp/_b13-board-lb.jpg");
await p.ev(`document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))`);
console.log("closed", await p.ev(`!document.getElementById('lb').classList.contains('on')`));
await p.ev(`document.getElementById('sc10').scrollIntoView()`); await new Promise((r) => setTimeout(r, 400)); await shot("/private/tmp/_b13-board-sc10.jpg");
p.c.close();
