// TestAgent 스모크 — 샌드박스 밖에서 띄운 Chrome 에 CDP 로 붙는가. 사용: node tools/cdp-smoke.mjs <포트>
// ⛔ 단일 명령으로 돌게 함 — 헤드리스 TestAgent 는 `cd … && …` 같은 복합 명령에 승인을 요구함(회차 b16 실측).
import { writeFileSync } from "node:fs";
import { chromium } from "playwright";
const out = new URL("../runs/2026-11-14-b16/", import.meta.url).pathname;
const port = process.argv[2] ?? "9400";
let line;
try {
  const b = await chromium.connectOverCDP(`http://127.0.0.1:${port}`);
  const ctx = b.contexts()[0] ?? (await b.newContext());
  const p = await ctx.newPage();
  await p.goto("http://localhost:3000/");
  line = `CDP OK ${await p.title()} nav=${await p.locator('[data-testid^="nav-"]').count()}`;
  await p.screenshot({ path: `${out}cdp-smoke.png` });
  await p.close();
} catch (e) {
  line = `CDP ERR ${e.message.split("\n").slice(0, 6).join(" | ").slice(0, 600)}`;
}
writeFileSync(`${out}cdp-smoke.txt`, line + "\n");
console.log(line);
