// 모바일 홈이 아이폰 Safari 가시 영역(12 Pro Max 428×745 · iPhone 16 393×659)에서 스크롤 없이 들어가는지 잼(`TASK-344`).
// 실행: 프런트 :3000 이 떠 있을 때 `node tests/agent/tools/mobile-fit.mjs` (이 폴더의 Playwright 를 씀).
// ⛔ 쓰기 요청은 모두 막음(dev DB 를 바꾸지 않음). 판정 요청은 가짜 응답, 문장·번역은 가장 긴 경우로 바꿔 씀.
// 판정: 화면 넷 + 최악 상태(KO 켬 · 두 줄 문장 · 불일치 결과)에서 문서 세로 넘침 0 · 결과 칸 안 넘침 0 ·
//       카드 밖으로 잘린 요소 0 · 44 px 미만 터치 대상 0 · 버튼 줄 위치가 KO·판정 전후로 같음. 하나라도 어기면 종료 코드 1.
import { chromium } from "playwright";
import { readFileSync } from "node:fs";
const src = readFileSync(new URL("../runs/2026-11-14-b17/live.mjs", import.meta.url), "utf8");
const start = src.indexOf("function installFakes()"); const end = src.indexOf("\n}\n", start) + 2;
const installFakes = src.slice(start, end);
const LONG = "We used to deploy every single release by hand on Friday nights.";
const SAID = "We use to deploy every release by hand on the Friday night.";
const failures = [];
const check = (ok, msg) => { console.log(`${ok ? "ok  " : "FAIL"} ${msg}`); if (!ok) failures.push(msg); };
const under44 = () => [...document.querySelectorAll("button, a")].filter((e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && r.height < 44 && !e.closest("nextjs-portal"); }).map((e) => e.dataset.testid || e.textContent.trim().slice(0, 14));
const b = await chromium.launch({ args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"] });
for (const [w, h] of [[428, 745], [393, 659]]) {
  const ctx = await b.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  await ctx.grantPermissions(["microphone"], { origin: "http://localhost:3000" });
  const page = await ctx.newPage();
  await page.addInitScript(`${installFakes}; installFakes(); window.__srScript = [{type:"interim",at:200,text:"We use to"},{type:"final",at:600,text:${JSON.stringify(SAID)}},{type:"end",at:900}];`);
  await page.route("**/api/**", async (r) => {
    const req = r.request(); const url = req.url();
    if (url.includes("/attempts/text")) {
      const said = SAID.toLowerCase().replace(/[.]/g, "").split(" ");
      const words = LONG.replace(/[.]/g, "").split(" ").map((word) => ({ word, verdict: said.includes(word.toLowerCase()) ? "match" : (word.length > 5 ? "missing" : "different") }));
      return r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ transcript: SAID, words, attempts: 1 }) });
    }
    if (req.method() !== "GET") return r.fulfill({ status: 204, body: "" });
    if (/\/api\/course\/days\/\d+$/.test(url.split("?")[0])) {
      const res = await r.fetch(); const data = await res.json();
      const walk = (o) => { if (Array.isArray(o)) o.forEach(walk); else if (o && typeof o === "object") { if (typeof o.text === "string" && "translation" in o) { o.text = LONG; o.translation = "우리는 예전에 금요일 밤마다 모든 배포를 하나하나 손으로 직접 했다."; } Object.values(o).forEach(walk); } };
      walk(data); return r.fulfill({ response: res, json: data });
    }
    return r.continue();
  });
  for (const path of ["/", "/progress"]) {
    await page.goto(`http://localhost:3000${path}`, { waitUntil: "networkidle" });
    const v = await page.evaluate((fn) => ({ over: document.documentElement.scrollHeight - innerHeight, small: eval(fn)() }), under44.toString());
    check(v.over <= 0, `${w}x${h} ${path} 세로 넘침 ${v.over}`);
    check(v.small.length === 0, `${w}x${h} ${path} 44 px 미만 ${JSON.stringify(v.small)}`);
  }
  await page.goto("http://localhost:3000/", { waitUntil: "networkidle" });
  // ⚠️ 연습은 열리자마자 시작함(`TASK-348`) — Manual 로 두어 한 번 판정 뒤 멈추게 하고, 그 뒤 KO 를 켜고 다시 시도함.
  await page.evaluate(() => localStorage.setItem("omy.course.mode", "manual"));
  await page.getByRole("button", { name: /Start speaking/ }).click();
  await page.waitForSelector('[data-testid="course-card"]', { timeout: 15000 });
  const navOff = await page.evaluate(() => Math.round(document.querySelector('[data-testid="course-prev"]').getBoundingClientRect().top));
  await page.waitForSelector('[data-testid="course-retry"]', { timeout: 20000 });
  await page.waitForFunction(() => document.querySelector('[data-testid="course-phase"]')?.dataset.phase === "done", null, { timeout: 20000 });
  await page.getByTestId("course-translation").click(); await page.waitForTimeout(400);
  const navY0 = await page.evaluate(() => Math.round(document.querySelector('[data-testid="course-prev"]').getBoundingClientRect().top));
  await page.getByTestId("course-retry").click();
  await page.waitForSelector('[data-testid="course-spoken"]', { timeout: 20000 }).catch(() => console.log("no result"));
  await page.waitForTimeout(800);
  const v = await page.evaluate(() => {
    const card = document.querySelector('[data-testid="course-card"]').getBoundingClientRect();
    const clipped = [...document.querySelectorAll('[data-testid="course-card"] *')].filter(e => { const r = e.getBoundingClientRect(); return r.height > 0 && (r.bottom > card.bottom + 0.5 || r.right > card.right + 0.5); }).map(e => e.dataset.testid || e.tagName).slice(0, 6);
    const slot = document.querySelector('[data-testid="course-result-slot"]');
    const nav = document.querySelector('[data-testid="course-prev"]').getBoundingClientRect();
    return { sh: document.documentElement.scrollHeight, clipped, slotOverflow: slot.scrollHeight - slot.clientHeight, sentence: document.querySelector('[data-testid="course-sentence"]').textContent.slice(0, 30), navTop: Math.round(nav.top) };
  });
  check(v.sh - h <= 0, `${w}x${h} 최악 상태 세로 넘침 ${v.sh - h}`);
  check(v.slotOverflow <= 0, `${w}x${h} 결과 칸 안 넘침 ${v.slotOverflow}`);
  check(v.clipped.length === 0, `${w}x${h} 카드 밖 요소 ${JSON.stringify(v.clipped)}`);
  check(navOff === navY0 && navY0 === v.navTop, `${w}x${h} 버튼 줄 위치 KO 끔 ${navOff} · 켬 ${navY0} · 판정 뒤 ${v.navTop}`);
  await page.screenshot({ path: `/tmp/mobile-fit-${w}-worst.png` });
  await ctx.close();
}
await b.close();
console.log(failures.length ? `FAILED ${failures.length}` : "ALL PASS");
process.exit(failures.length ? 1 : 0);
