// 관측 수단 양성 대조 — 넘침 검출 · 콘솔 오류 수집 · 리다이렉트 판정 · 실시간 표시 부재 대조.
// node runs/2026-11-14-b18/screens/probe-controls.mjs → evidence/probe-controls.json
import { chromium } from "/Users/redstar/MyProject/OhMyEnglish/tests/agent/tools/node_modules/playwright/index.mjs";
import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
const HERE = dirname(fileURLToPath(import.meta.url));
const APP = "http://localhost:3000";
const out = {};
const browser = await chromium.connectOverCDP("http://127.0.0.1:9461");
const ctx = browser.contexts()[0];
const page = await ctx.newPage();
await page.setViewportSize({ width: 390, height: 844 });
const errs = [];
page.on("console", (m) => m.type() === "error" && errs.push(m.text()));
page.on("pageerror", (e) => errs.push(String(e)));
try {
  await page.goto(APP + "/", { waitUntil: "domcontentloaded" });
  await page.waitForSelector('[data-testid="home-hero"]', { timeout: 20000 });
  // ① 넘침: 600 px 글자 상자를 주입
  out.overflowBefore = await page.evaluate(() => ({ body: document.body.scrollWidth, doc: document.documentElement.scrollWidth, w: innerWidth }));
  out.overflowAfter = await page.evaluate(() => {
    const d = document.createElement("div");
    d.textContent = "probe wide text";
    d.style.cssText = "width:600px;background:red";
    document.querySelector("main")?.appendChild(d) ?? document.body.appendChild(d);
    const r = d.getBoundingClientRect();
    const res = { body: document.body.scrollWidth, doc: document.documentElement.scrollWidth, w: innerWidth, boxRight: Math.round(r.right) };
    d.remove();
    return res;
  });
  // ② 콘솔 오류 수집
  await page.evaluate(() => console.error("probe-console-error"));
  await page.waitForTimeout(300);
  out.consoleCaught = errs.filter((e) => e.includes("probe-console-error")).length;
  // ③ 리다이렉트 판정 수단: 넘기지 않는 주소(/history)는 그대로 남는지
  await page.goto(APP + "/history", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(2500);
  out.historyStays = new URL(page.url()).pathname;
  // ④ 실시간 표시 부재 대조: 가짜 인식기 없이 Start → course-live-interim 이 생기지 않아야 함(진짜 인식기는 가짜 오디오를 전사하지 않음)
  await page.goto(APP + "/", { waitUntil: "domcontentloaded" });
  await page.evaluate(() => { localStorage.setItem("omy.course.translation", "off"); localStorage.removeItem("omy.course.mode"); });
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.waitForSelector('[data-testid="start-session"]', { timeout: 20000 });
  out.hasRealRecognizer = await page.evaluate(() => Boolean(window.SpeechRecognition || window.webkitSpeechRecognition));
  await page.locator('[data-testid="start-session"]').click();
  await page.waitForSelector('[data-testid="course-mode-manual"]', { timeout: 20000 });
  await page.locator('[data-testid="course-mode-manual"]').click();
  await page.locator('[data-testid="course-start"], [data-testid="course-retry"]').first().click();
  await page.waitForTimeout(5000);
  out.realInterim = await page.locator('[data-testid="course-live-interim"]').count();
  out.realNotice = await page.locator('[data-testid="course-notice"]').first().innerText().catch(() => null);
  await page.locator('[data-testid="practice-close"]').click();
  out.errorsOther = errs.filter((e) => !e.includes("probe-console-error")).slice(0, 10);
} catch (e) {
  out.error = String(e).slice(0, 400);
} finally {
  writeFileSync(join(HERE, "evidence", "probe-controls.json"), JSON.stringify(out, null, 1));
  console.log(JSON.stringify(out, null, 1));
  await page.close();
}
process.exit(0);
