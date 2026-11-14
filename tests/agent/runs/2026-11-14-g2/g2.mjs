// TASK-317 0단계 G2 — 시험용 Chrome 에서 Web Speech 인식기가 가짜 오디오를 전사하는가. 사용: node g2.mjs <포트>
import { writeFileSync } from "node:fs";
import { chromium } from "/Users/redstar/MyProject/OhMyEnglish/tests/agent/tools/node_modules/playwright/index.mjs";
const port = process.argv[2] ?? "9410";
const b = await chromium.connectOverCDP(`http://127.0.0.1:${port}`);
const ctx = b.contexts()[0];
await ctx.grantPermissions(["microphone"], { origin: "http://localhost:3000" });
const p = await ctx.newPage();
await p.goto("http://localhost:3000/");
const out = await p.evaluate(() => new Promise((resolve) => {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return resolve({ available: false });
  const r = new SR(); r.lang = "en-US"; r.continuous = true; r.interimResults = true;
  const events = []; const t0 = performance.now();
  const at = () => Math.round(performance.now() - t0);
  r.onaudiostart = () => events.push([at(), "audiostart"]);
  r.onspeechstart = () => events.push([at(), "speechstart"]);
  r.onresult = (e) => { for (let i = e.resultIndex; i < e.results.length; i++) events.push([at(), e.results[i].isFinal ? "final" : "interim", e.results[i][0].transcript]); };
  r.onerror = (e) => events.push([at(), "error", e.error]);
  r.onend = () => { events.push([at(), "end"]); resolve({ available: true, events }); };
  r.start();
  setTimeout(() => r.stop(), 12000);
}));
writeFileSync(new URL("g2-result.json", import.meta.url), JSON.stringify(out, null, 1));
console.log(JSON.stringify(out).slice(0, 1500));
await p.close();
process.exit(0);
