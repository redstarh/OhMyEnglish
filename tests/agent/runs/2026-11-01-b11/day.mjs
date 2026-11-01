// 회차 b11 — Day 화면 하나를 깊게 누름. 사용: node day.mjs <day> <width>
import { open, APP, saver, sleep, VIS } from "./lib.mjs";
const day = process.argv[2], width = Number(process.argv[3] ?? 1400);
const { note, save } = saver(`DAY${day}-${width}`);
const p = await open({ port: 9347, width, height: 1000 });
await p.c.send("Network.enable");
let reqs = [];
p.c.on((d) => { if (d.method === "Network.requestWillBeSent" && /:8002/.test(d.params.request.url)) reqs.push(`${d.params.request.method} ${d.params.request.url.replace("http://localhost:8002", "")}`); });
const S = `(() => { const g = (t) => document.querySelector('[data-testid=' + t + ']'); return { phase: g('course-phase')?.dataset.phase ?? null, num: g('course-sentence-number')?.innerText ?? null,
  unit: g('course-unit')?.innerText ?? null, sentence: g('course-sentence')?.innerText?.slice(0, 80) ?? null, attempts: g('course-attempts')?.innerText ?? null, notice: g('course-notice')?.innerText ?? null,
  prevDisabled: g('course-prev')?.disabled ?? null, finish: g('course-finish') ? g('course-finish').disabled : 'absent', retry: !!g('course-retry'), start: !!g('course-start'),
  auto: g('course-mode-auto')?.getAttribute('aria-pressed'), manual: g('course-mode-manual')?.getAttribute('aria-pressed'), follow: [...document.querySelectorAll('button')].find(b => /where the video is/.test(b.textContent))?.textContent ?? null, path: location.pathname }; })()`;
const mouse = async (t) => {
  const pt = await p.ev(`(() => { const e = ${VIS(t)}; if (!e) return null; e.scrollIntoView({ block: 'center', behavior: 'instant' }); const r = e.getBoundingClientRect(); return [Math.round(r.x + r.width / 2), Math.round(r.y + r.height / 2)]; })()`);
  if (!pt) return null;
  for (const type of ["mousePressed", "mouseReleased"]) await p.c.send("Input.dispatchMouseEvent", { type, x: pt[0], y: pt[1], button: "left", clickCount: 1 });
  return pt;
};
const step = async (name, t, wait = 1500) => { reqs = []; const pt = t ? await mouse(t) : null; await sleep(wait); const s = await p.ev(S); note(name, { clicked: t, pt, ...s, reqs: [...new Set(reqs)] }); return s; };
const phases = async (ms) => { const seen = []; const st = Date.now(); while (Date.now() - st < ms) { const ph = await p.ev(`document.querySelector('[data-testid=course-phase]')?.dataset.phase`); if (seen.at(-1) !== ph) seen.push(ph); await sleep(100); } return seen; };
try {
  await p.nav(`${APP}/course/${day}`); await p.waitFor(p.hydrated("course-start"), 20000); await sleep(2500);
  await step("open", null, 0);
  await step("manual", "course-mode-manual", 600);
  reqs = []; await mouse("course-start"); note("startPhases", await phases(12000)); note("afterStart", { ...(await p.ev(S)), reqs: [...new Set(reqs)] });
  reqs = []; await mouse("course-retry"); note("retryPhases", await phases(12000)); note("afterRetry", { ...(await p.ev(S)), reqs: [...new Set(reqs)] });
  reqs = []; await mouse("course-slow"); note("slowPhases", await phases(12000)); note("afterSlow", await p.ev(S));
  reqs = []; await mouse("course-listen"); note("listenPhases", await phases(12000)); note("afterListen", await p.ev(S));
  await step("next", "course-next", 1200);
  await step("prev", "course-prev", 1200);
  await step("auto", "course-mode-auto", 600);
  reqs = []; await mouse("course-start"); note("autoPhases", await phases(20000)); note("afterAuto", { ...(await p.ev(S)), reqs: [...new Set(reqs)] });
  await step("manualAgain", "course-mode-manual", 3000);
  // 마지막 문장까지 넘김 → 마치기 버튼
  let n = 0; while (n < 120 && (await p.ev(`!document.querySelector('[data-testid=course-finish]')`))) { await mouse("course-next"); await sleep(150); n++; }
  note("nextCountToLast", n); await step("last", null, 300);
  reqs = []; await mouse("course-start"); note("lastPhases", await phases(12000)); note("afterLast", { ...(await p.ev(S)), reqs: [...new Set(reqs)] });
  await step("finish", "course-finish", 2500);
  note("finishText", (await p.ev(`document.querySelector('main')?.innerText ?? document.body.innerText`)).slice(0, 800));
  await p.shot(`DAY${day}-${width}-finish`);
  await step("back", "course-back", 2000);
} catch (e) { note("ERROR", String(e?.stack ?? e).slice(0, 600)); }
finally { note("logs", p.logs.filter((l) => !/DevTools|HMR|Download the React/.test(l.text))); save(); p.c.close(); }
