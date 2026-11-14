// TestAgent 스모크 — 샌드박스 안에서 Playwright 브라우저가 뜨는가. 사용: node smoke.mjs
import { chromium } from "playwright";
const variants = {
  default: {},
  nosandbox: { args: ["--no-sandbox", "--disable-gpu"] },
  chrome: { channel: "chrome", args: ["--no-sandbox"] },
};
for (const [name, opts] of Object.entries(variants)) {
  try {
    const b = await chromium.launch(opts);
    const p = await b.newPage();
    await p.goto("http://localhost:3000/");
    console.log(name, "OK", await p.title());
    await b.close();
  } catch (e) {
    console.log(name, "ERR", e.message.split("\n").filter((l) => !l.includes("<launching>")).slice(-8).join(" | ").slice(-700));
  }
}
