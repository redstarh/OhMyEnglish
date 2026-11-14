// 390 영상 화면에서 오른쪽이 화면 밖으로 나가는 요소를 모두 잼 (2회 반복해 간헐 여부도 가름)
import { chromium } from "/Users/redstar/MyProject/OhMyEnglish/tests/agent/tools/node_modules/playwright/index.mjs";
import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
const HERE = dirname(fileURLToPath(import.meta.url));
const URL_ = "http://localhost:3000/videos/b502eaf3-0fdd-408c-b273-a0c58a6410d2";
const browser = await chromium.connectOverCDP("http://127.0.0.1:9401");
const out = [];
for (let i = 0; i < 2; i++) {
  const page = await browser.contexts()[0].newPage();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(URL_, { waitUntil: "domcontentloaded" });
  await new Promise((r) => setTimeout(r, 5000));
  out.push(
    await page.evaluate(() => {
      const items = [];
      for (const el of document.body.querySelectorAll("*")) {
        const r = el.getBoundingClientRect();
        if (r.width > 0 && r.right > window.innerWidth + 1)
          items.push({ tag: el.tagName, tid: el.getAttribute("data-testid"), w: Math.round(r.width), right: Math.round(r.right), style: (el.getAttribute("style") || "").slice(0, 120), cls: String(el.className).slice(0, 80), attrW: el.getAttribute("width") });
      }
      return { bodySW: document.body.scrollWidth, cw: document.documentElement.clientWidth, items: items.slice(0, 15) };
    }),
  );
  if (i === 0) await page.screenshot({ path: join(HERE, "evidence", "video-390-viewport.jpg"), type: "jpeg", quality: 70 });
  await page.close();
}
writeFileSync(join(HERE, "evidence", "probe-video-overflow.json"), JSON.stringify(out, null, 1));
console.log(JSON.stringify(out));
process.exit(0);
