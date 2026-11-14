// 회차 b16 호출자 대조 — 화면 탭 D1(390 영상 iframe 넘침) · D2(홈과 /course 의 Day 상태). 사용: node verify/screens.mjs <포트>
import { chromium } from "/Users/redstar/MyProject/OhMyEnglish/tests/agent/tools/node_modules/playwright/index.mjs";
const b = await chromium.connectOverCDP(`http://127.0.0.1:${process.argv[2] ?? 9401}`);
const p = await b.contexts()[0].newPage();
await p.setViewportSize({ width: 390, height: 844 });
const vids = await (await fetch("http://localhost:8002/api/videos")).json();
await p.goto(`http://localhost:3000/videos/${vids.videos[0].id}`); await p.waitForTimeout(3000);
console.log("D1", JSON.stringify(await p.evaluate(() => { const f = document.querySelector("iframe"); return { bodySW: document.body.scrollWidth, iframeRight: f ? Math.round(f.getBoundingClientRect().right) : null, iframeW: f?.getAttribute("width") }; })));
await p.setViewportSize({ width: 1400, height: 1000 });
await p.goto("http://localhost:3000/"); await p.waitForSelector('[data-testid="home-path-all"]'); await p.click('[data-testid="home-path-all"]'); await p.waitForTimeout(500);
const home = await p.evaluate(() => [...document.querySelectorAll('[data-testid^="path-day-"]')].map((e) => e.dataset.testid.replace("path-day-", "D") + ":" + e.dataset.status));
await p.goto("http://localhost:3000/course"); await p.waitForTimeout(1500);
const course = await p.evaluate(() => [...document.querySelectorAll("main section, main li, main div")].map((e) => e.innerText).filter((t) => /^Day \d/.test(t)).map((t) => t.split("\n")[0] + " | " + (t.match(/Not started|In progress|Done|Unit \d+ · Sentence \d+[^\n]*/)?.[0] ?? "?")).filter((v, i, a) => a.indexOf(v) === i).slice(0, 6));
console.log("D2 home", home.join(" "));
console.log("D2 course", JSON.stringify(course));
await p.close(); process.exit(0);
