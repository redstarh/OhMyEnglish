// 회차 b11 — Day 화면의 「Go to Unit N (where the video is)」 버튼. 사용: node follow.mjs <day>
import { open, APP, saver, sleep, VIS } from "./lib.mjs";
const day = process.argv[2];
const { note, save } = saver(`FOLLOW-day${day}`);
const p = await open({ port: 9345, width: 1400, height: 1000 });
const S = `({ unit: document.querySelector('[data-testid=course-unit]')?.innerText, num: document.querySelector('[data-testid=course-sentence-number]')?.innerText,
  follow: [...document.querySelectorAll('button')].find(b => /where the video is/.test(b.textContent))?.textContent ?? null })`;
const mouse = async (expr) => { const pt = await p.ev(`(() => { const e = ${expr}; if (!e) return null; e.scrollIntoView({ block: 'center', behavior: 'instant' }); const r = e.getBoundingClientRect(); return [Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2)]; })()`);
  if (!pt) return null; for (const type of ["mousePressed", "mouseReleased"]) await p.c.send("Input.dispatchMouseEvent", { type, x: pt[0], y: pt[1], button: "left", clickCount: 1 }); return pt; };
try {
  await p.nav(`${APP}/course/${day}`); await p.waitFor(p.hydrated("course-start"), 20000); await sleep(2500);
  note("open", await p.ev(S));
  await mouse(`document.querySelector('[data-testid=course-mode-manual]')`);
  // 영상과 다른 단원까지 넘김
  for (let i = 0; i < 12; i++) { await mouse(VIS("course-next")); await sleep(150); }
  note("afterNext", await p.ev(S));
  // 영상을 재생해 위치가 생기게 함
  await mouse(`document.querySelector('iframe')`); await sleep(5000);
  note("afterPlay", await p.ev(S));
  const f = await p.ev(S);
  if (f.follow) { await mouse(`[...document.querySelectorAll('button')].find(b => /where the video is/.test(b.textContent))`); await sleep(1500); note("afterFollow", await p.ev(S)); }
} catch (e) { note("ERROR", String(e?.stack ?? e).slice(0, 500)); }
finally { note("logs", p.logs.filter((l) => !/DevTools|HMR|Download the React|postMessage/.test(l.text)).slice(0, 5)); save(); p.c.close(); }
