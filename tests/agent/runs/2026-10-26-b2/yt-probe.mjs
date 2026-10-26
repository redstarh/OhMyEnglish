// 회차 b2 — 일회성 진단: /course/2 로드 뒤 YouTube 플레이어가 getCurrentTime 을 갖게 되는 시각.
import { writeFileSync } from "node:fs";
import { connect, pageTarget, sleep, EV } from "./cdp.mjs";
const c = await connect((await pageTarget()).webSocketDebuggerUrl);
await c.send("Page.enable");
const ev = async (e) => { try { return (await c.send("Runtime.evaluate", { expression: e, returnByValue: true })).result.value; } catch { return null; } };
const res = [];
for (let run = 0; run < 3; run++) {
  await c.send("Page.navigate", { url: "http://localhost:3000/course/2" });
  await sleep(30);
  const marks = {};
  for (let i = 0; i < 200; i++) {
    const v = await ev(`(() => { const f = document.querySelector('[data-testid=course-player] iframe'); let p = null;
      try { p = f && window.YT && YT.get ? YT.get(f.id) : null; } catch {}
      return { age: Math.round(performance.now()), iframe: !!f, api: !!(window.YT && YT.loaded), hasGet: !!(p && typeof p.getCurrentTime === 'function') }; })()`);
    if (v) for (const k of ["iframe", "api", "hasGet"]) if (v[k] && marks[k] === undefined) marks[k] = v.age;
    if (marks.hasGet !== undefined) break;
    await sleep(50);
  }
  res.push(marks);
  console.log(JSON.stringify(marks));
}
writeFileSync(`${EV}/yt-ready-probe.json`, JSON.stringify(res, null, 1));
c.close();
