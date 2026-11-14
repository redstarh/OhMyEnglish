// 가로 넘침 검출의 양성 대조: 390 홈에 600px 요소를 넣고
// ⑴ 문서 scrollWidth ⑵ 글자 상자 오른쪽 끝(offRight 검출기) ⑶ 가로를 자르는 조상을 잼
import { chromium } from "/Users/redstar/MyProject/OhMyEnglish/tests/agent/tools/node_modules/playwright/index.mjs";
import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
const OUT = join(dirname(fileURLToPath(import.meta.url)), "evidence", "probe-overflow.json");
const browser = await chromium.connectOverCDP("http://127.0.0.1:9401");
const page = await browser.contexts()[0].newPage();
await page.setViewportSize({ width: 390, height: 844 });
await page.goto("http://localhost:3000/", { waitUntil: "domcontentloaded" });
await page.waitForSelector('[data-testid="home-hero"]', { timeout: 20000 });
const out = await page.evaluate(() => {
  const de = document.documentElement;
  const before = { sw: de.scrollWidth, cw: de.clientWidth };
  const d = document.createElement("div");
  d.style.width = "600px";
  d.textContent = "probe-wide-text";
  document.querySelector('[data-testid="home-path"]').appendChild(d);
  const r = d.getBoundingClientRect();
  const clippers = [];
  for (let el = d.parentElement; el; el = el.parentElement) {
    const s = getComputedStyle(el);
    if (["hidden", "clip", "auto", "scroll"].includes(s.overflowX))
      clippers.push({ tag: el.tagName, tid: el.getAttribute("data-testid"), cls: String(el.className).slice(0, 80), overflowX: s.overflowX, sw: el.scrollWidth, cw: el.clientWidth });
  }
  return { before, injected: { sw: de.scrollWidth, cw: de.clientWidth }, textRight: Math.round(r.right), innerWidth: window.innerWidth, offRightDetects: r.right > window.innerWidth + 1, clippers };
});
writeFileSync(OUT, JSON.stringify(out, null, 1));
console.log(JSON.stringify(out));
await page.close();
process.exit(0);
