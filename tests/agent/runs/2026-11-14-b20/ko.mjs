// TASK-328 — KO 번역 줄: 565개가 두 줄에 드는가 · 켬/끔에 따른 카드 높이. 사용: node ko.mjs <포트>
// ⛔ dev DB — 진도 저장 요청은 막음. Start 는 누르지 않음.
import { readFileSync } from "node:fs";
import { chromium } from "/Users/redstar/MyProject/OhMyEnglish/tests/agent/tools/node_modules/playwright/index.mjs";
const ko = Object.values(JSON.parse(readFileSync("/Users/redstar/MyProject/OhMyEnglish/app/backend/app/content/grammar_basic_ko.json", "utf8")));
const OUT = new URL("./evidence/", import.meta.url).pathname;
const b = await chromium.connectOverCDP(`http://127.0.0.1:${process.argv[2] ?? 9450}`);
const ctx = b.contexts()[0];
const results = [];
for (const on of [false, true]) {
  for (const [w, h] of [[1400, 1000], [390, 844], [320, 800]]) {
    const p = await ctx.newPage();
    await p.addInitScript((v) => window.localStorage.setItem("omy.course.translation", v), on ? "on" : "off");
    await p.route("**/api/course/days/*/progress", (r) => r.fulfill({ status: 204, body: "" }));
    await p.setViewportSize({ width: w, height: h });
    await p.goto("http://localhost:3000/"); await p.waitForSelector('[data-testid="start-session"]'); await p.waitForTimeout(700);
    const idle = await p.evaluate(() => Math.round(document.querySelector('[data-testid="home-hero"]').getBoundingClientRect().height * 10) / 10);
    await p.click('[data-testid="start-session"]'); await p.waitForSelector('[data-testid="course-translation"]'); await p.waitForTimeout(700);
    const r = await p.evaluate((ko) => {
      const hero = document.querySelector('[data-testid="home-hero"]').getBoundingClientRect().height;
      const card = document.querySelector('[data-testid="course-card"]').getBoundingClientRect().height;
      const t = document.querySelector('[data-testid="course-translation-text"]');
      const toggle = document.querySelector('[data-testid="course-translation"]');
      let overflow = [];
      if (t) { const orig = t.textContent; for (const s of ko) { t.textContent = s; if (t.scrollHeight > t.clientHeight + 1) overflow.push(s); } t.textContent = orig; }
      return { hero: Math.round(hero * 10) / 10, card: Math.round(card * 10) / 10, text: t?.textContent ?? null, pressed: toggle.getAttribute("aria-pressed"), toggleH: Math.round(toggle.getBoundingClientRect().height), overflow: overflow.length, sample: overflow.slice(0, 2) };
    }, ko);
    results.push({ on, w, idle, ...r });
    console.log(on ? "KO on " : "KO off", w, JSON.stringify({ idle, ...r }));
    await p.screenshot({ path: `${OUT}ko-${on ? "on" : "off"}-${w}.png` });
    await p.close();
  }
}
process.exit(0);
