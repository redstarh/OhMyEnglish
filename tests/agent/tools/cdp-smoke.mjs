// TestAgent 스모크 — 샌드박스 밖에서 띄운 Chrome 에 CDP 로 붙는가. 사용: node cdp-smoke.mjs <포트>
import { chromium } from "playwright";
const port = process.argv[2] ?? "9400";
try {
  const b = await chromium.connectOverCDP(`http://127.0.0.1:${port}`);
  const ctx = b.contexts()[0] ?? (await b.newContext());
  const p = await ctx.newPage();
  await p.goto("http://localhost:3000/");
  console.log("CDP OK", await p.title(), await p.locator('[data-testid^="nav-"]').count());
  await p.screenshot({ path: "../runs/2026-11-14-b16/cdp-smoke.png" });
  await p.close();
  await b.close();
} catch (e) {
  console.log("CDP ERR", e.message.split("\n").slice(0, 6).join(" | ").slice(0, 600));
}
