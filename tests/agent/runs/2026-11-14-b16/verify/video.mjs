// TASK-321 확인 — 영상 화면의 iframe 이 창 너비 안에 드는가. 사용: node verify/video.mjs <포트>
import { chromium } from "/Users/redstar/MyProject/OhMyEnglish/tests/agent/tools/node_modules/playwright/index.mjs";
const b = await chromium.connectOverCDP(`http://127.0.0.1:${process.argv[2] ?? 9420}`);
const p = await b.contexts()[0].newPage();
const vids = await (await fetch("http://localhost:8002/api/videos")).json();
for (const [w, h] of [[390, 844], [1400, 1000]]) {
  await p.setViewportSize({ width: w, height: h });
  await p.goto(`http://localhost:3000/videos/${vids.videos[0].id}`); await p.waitForTimeout(3500);
  console.log(w, JSON.stringify(await p.evaluate(() => { const f = document.querySelector("iframe"); const r = f?.getBoundingClientRect(); return { bodySW: document.body.scrollWidth, iframeRight: r && Math.round(r.right), iframeW: r && Math.round(r.width), iframeH: r && Math.round(r.height) }; })));
  await p.screenshot({ path: new URL(`video-${w}.png`, import.meta.url).pathname });
}
await p.close(); process.exit(0);
