// 회차 b12r4 — 진도 저장이 끝나지 않을 때 다시 열기의 조회가 상한(3000 ms) 뒤에 나가는가. 사용: node i5.mjs <label> <hold|nohold>
import { page, APP, sleep } from "./h.mjs";
import { saver } from "./lib.mjs";
const [label, mode] = process.argv.slice(2);
const { note, save } = saver(`I5-${label}`);
const p = await page({ width: 1400 });
const held = [];
try {
  if (mode === "hold") {
    // 진도 POST 는 영원히 붙잡음(풀지 않음). 그 밖의 요청(OPTIONS 포함)은 바로 보냄
    await p.c.send("Fetch.enable", { patterns: [{ urlPattern: "*/api/course/days/*/progress", requestStage: "Request" }] });
    p.c.on((d) => { if (d.method !== "Fetch.requestPaused") return; if (d.params.request.method === "POST") { held.push({ t: Date.now(), body: d.params.request.postData }); return; } p.c.send("Fetch.continueRequest", { requestId: d.params.requestId }); });
  }
  await p.nav(`${APP}/`); await p.waitFor(p.hydrated("start-session"), 20000); await sleep(2000);
  p.reqs = [];
  const t1 = Date.now(); await p.mouse("start-session");
  await p.waitFor(`document.querySelector('[data-testid=practice-day]')?.dataset.state === 'ready'`, 15000, 10); const open1 = Date.now() - t1;
  await sleep(800);
  await p.mouse("course-mode-manual"); await sleep(200);
  await p.mouse("course-next"); await sleep(500);
  const adv = await p.sp();
  await p.mouse("practice-close"); await sleep(300);
  const reqsBefore = p.reqs.length;
  const t2 = Date.now(); await p.mouse("start-session");
  await p.waitFor(`document.querySelector('[data-testid=practice-day]')?.dataset.state === 'ready'`, 15000, 10); const open2 = Date.now() - t2;
  await sleep(300); const re = await p.sp();
  const after = p.reqs.slice(reqsBefore).filter((r) => r.t >= t2 && r.m === "GET" && /\/api\/course(\/days\/\d+)?$/.test(r.u)).map((r) => [r.t - t2, r.u]);
  // 세 번째: 바로 닫고 다시 열기(저장은 여전히 붙잡힘)
  await p.mouse("practice-close"); await sleep(300);
  const n3 = p.reqs.length; const t3 = Date.now(); await p.mouse("start-session");
  await p.waitFor(`document.querySelector('[data-testid=practice-day]')?.dataset.state === 'ready'`, 15000, 10); const open3 = Date.now() - t3;
  const third = p.reqs.slice(n3).filter((r) => r.t >= t3 && r.m === "GET" && /\/api\/course(\/days\/\d+)?$/.test(r.u)).map((r) => [r.t - t3, r.u]);
  note("third", { reopenReadyMs: open3, gets: third, heldSoFar: held.length });
  note("result", { mode, firstOpenMs: open1, firstOpenGets: p.reqs.filter((r) => r.t >= t1 && r.t < t1 + 5000 && r.m === "GET").map((r) => [r.t - t1, r.u]).slice(0, 4),
    advanced: `${adv.unit}|${adv.num}`, reopenReadyMs: open2, reopenGets: after, reopened: { state: re.practiceDayState, day: re.practiceDay, pos: `${re.unit}|${re.num}` }, heldPosts: held.map((h) => [h.t - t1, h.body]) });
  await sleep(1000);
} catch (e) { note("ERROR", String(e?.stack ?? e).slice(0, 800)); }
finally { note("logs", p.logs.filter((l) => !/DevTools|HMR|Download the React|Fast Refresh/.test(l.text))); save(); p.c.close(); }
