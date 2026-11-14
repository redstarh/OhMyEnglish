// 세션을 열지 않고, CDP 마이크 거부가 페이지에 닿는지만 잼: node runs/2026-11-14-b16/screens/probe-mic.mjs
import { chromium } from "/Users/redstar/MyProject/OhMyEnglish/tests/agent/tools/node_modules/playwright/index.mjs";
import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
const OUT = join(dirname(fileURLToPath(import.meta.url)), "evidence", "probe-mic.json");
const APP = "http://localhost:3000";
const browser = await chromium.connectOverCDP("http://127.0.0.1:9401");
const page = await browser.contexts()[0].newPage();
const cdp = await browser.newBrowserCDPSession();
const probe = () =>
  page.evaluate(async () => {
    const st = await navigator.permissions.query({ name: "microphone" }).then((p) => p.state, (e) => "query-err:" + e.name);
    const gum = await navigator.mediaDevices.getUserMedia({ audio: true }).then(
      (s) => {
        s.getTracks().forEach((t) => t.stop());
        return "granted-stream";
      },
      (e) => "rejected:" + e.name,
    );
    return { st, gum };
  });
const out = {};
await page.goto(APP + "/about:blank".slice(0, 1), { waitUntil: "domcontentloaded" });
out.before = await probe();
const r1 = await cdp.send("Browser.setPermission", { permission: { name: "microphone" }, setting: "denied", origin: APP }).then(() => "ok", (e) => String(e));
out.setDenied = r1;
out.afterDenied = await probe();
await page.reload({ waitUntil: "domcontentloaded" });
out.afterDeniedReload = await probe();
out.restore = await cdp.send("Browser.setPermission", { permission: { name: "microphone" }, setting: "granted", origin: APP }).then(() => "ok", (e) => String(e));
out.afterRestore = await probe();
writeFileSync(OUT, JSON.stringify(out, null, 1));
console.log(JSON.stringify(out));
await cdp.detach();
await page.close();
process.exit(0);
