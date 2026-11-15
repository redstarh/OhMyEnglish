// TASK-325 확인 — tailnet HTTPS 주소로 열면 화면이 뜨고 API 요청이 같은 출처로 가는가. 사용: node tailnet.mjs
// ⛔ 세션을 열지 않음 · 진도 저장 요청은 막음.
import { chromium } from "/Users/redstar/MyProject/OhMyEnglish/tests/agent/tools/node_modules/playwright/index.mjs";
const H = "https://redstarui-macbookair.tailf9cacf.ts.net";
// ⚠️ 이 맥 자신은 시스템 DNS 가 자기 tailnet 이름을 못 찾음(2026-11-15 실측) — 확인용으로 IP 를 고정함.
const b = await chromium.launch({ args: ["--host-resolver-rules=MAP redstarui-macbookair.tailf9cacf.ts.net 100.71.128.34"] });
const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
const p = await ctx.newPage();
const reqs = []; const errors = [];
p.on("request", (r) => { const u = r.url(); if (u.includes("/api/")) reqs.push(new URL(u).origin); });
p.on("console", (m) => { if (m.type() === "error") errors.push(m.text().slice(0, 160)); });
await p.route("**/api/course/days/*/progress", (r) => r.fulfill({ status: 204, body: "" }));
await p.goto(`${H}/`, { waitUntil: "load", timeout: 60000 }); await p.waitForSelector('[data-testid="start-session"]', { timeout: 60000 }); await p.waitForTimeout(1500);
const secure = await p.evaluate(() => window.isSecureContext);
const sr = await p.evaluate(() => typeof (window.SpeechRecognition || window.webkitSpeechRecognition));
await p.click('[data-testid="start-session"]'); await p.waitForSelector('[data-testid="course-card"]', { timeout: 30000 }); await p.waitForTimeout(800);
const translation = await p.locator('[data-testid="course-translation"]').count();
await p.screenshot({ path: new URL("evidence/tailnet-390.png", import.meta.url).pathname });
console.log(JSON.stringify({ secureContext: secure, speechRecognition: sr, apiOrigins: [...new Set(reqs)], koButton: translation, consoleErrors: errors.slice(0, 3) }));
await b.close();
