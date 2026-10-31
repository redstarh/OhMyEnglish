// 회차 b5 — 지금 :3000 이 내려 주는 학습 화면 번들에 D3 수정이 실렸는지 읽기만 한다.
import { writeFileSync } from "node:fs";
import { connect, pageTarget, sleep, EV } from "./cdp.mjs";
const c = await connect((await pageTarget()).webSocketDebuggerUrl);
await c.send("Page.enable"); await c.send("Runtime.enable");
await c.send("Page.navigate", { url: "http://localhost:3000/course/3" });
await sleep(6000);
const r = await c.send("Runtime.evaluate", { awaitPromise: true, returnByValue: true, expression: `(async () => {
  const srcs = [...document.scripts].map(s => s.src).filter(s => s.startsWith('http://localhost:3000')); const hits = [];
  for (const s of srcs) { let t = ''; try { t = await (await fetch(s)).text(); } catch {} for (const k of ['lastTimeRef','completedRef','finishDay','Day 마치기']) if (t.includes(k)) hits.push([s.split('/').pop().slice(0,60), k]); }
  return { n: srcs.length, hits }; })()` });
console.log(JSON.stringify(r.result.value)); writeFileSync(`${EV}/codecheck.json`, JSON.stringify(r.result.value, null, 1)); c.close();
