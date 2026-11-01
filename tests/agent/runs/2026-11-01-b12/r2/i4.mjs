// 회차 b12r 항목 4 — 문장 하나 넘김 → Close → D ms 안에 다시 열기. 다시 연 문장이 넘긴 문장이고, 뒤늦은 저장이 옛 자리를 쓰지 않아야 함.
// 사용: node i4.mjs <label> <delayMs>
import { page, APP, sleep, api } from "./h.mjs";
import { saver } from "./lib.mjs";
const [label, D, HOLD] = [process.argv[2], Number(process.argv[3] ?? 50), Number(process.argv[4] ?? 0)];
const { note, save } = saver(`I4-${label}`);
const p = await page({ width: 1400 });
const pos = (s) => s ? `${s.unit}|${s.num}` : null;
try {
  const c = (await api("/api/course")).body; const day = c.current_day; note("start", { day, saved: c.days.find((d) => d.day === day).progress });
  await p.nav(`${APP}/`); await p.waitFor(p.hydrated("start-session"), 20000); await sleep(2000);
  await p.mouse("start-session"); await p.waitFor(`document.querySelector('[data-testid=practice-day]')?.dataset.state === 'ready'`, 10000); await sleep(1500);
  await p.mouse("course-mode-manual"); await sleep(200);
  const s0 = await p.sp(); note("before", pos(s0));
  await p.mouse("course-next"); await sleep(400);
  const s1 = await p.sp(); note("advanced", pos(s1));
  // HOLD>0 이면 진도 POST 응답을 HOLD ms 붙잡음 — 닫기 저장이 다시 열기의 조회보다 늦게 닿는 경우를 만듦(판별력 확보)
  const held = [];
  if (HOLD > 0) {
    await p.c.send("Fetch.enable", { patterns: [{ urlPattern: "*/api/course/days/*/progress", requestStage: "Request" }] });
    p.c.on((d) => { if (d.method !== "Fetch.requestPaused") return; const id = d.params.requestId; const m = d.params.request.method;
      if (m !== "POST") { p.c.send("Fetch.continueRequest", { requestId: id }); return; }
      held.push({ t: Date.now(), body: d.params.request.postData }); setTimeout(() => p.c.send("Fetch.continueRequest", { requestId: id }).then(() => held.push({ released: Date.now() })), HOLD); });
  }
  p.reqs = [];
  // 닫기 → D ms 뒤 다시 열기 (페이지 안 타이머로 간격을 맞춤)
  const timing = await p.ev(`new Promise((res) => { const t0 = performance.now(); document.querySelector('[data-testid=practice-close]').click();
    setTimeout(() => { const b = document.querySelector('[data-testid=start-session]'); const t1 = performance.now(); if (!b) return res({ error: 'no start-session', t1: t1 - t0 }); b.click(); res({ reopenAt: Math.round((t1 - t0) * 10) / 10 }); }, ${D}); })`);
  const tr = Date.now(); note("timing", timing);
  await p.waitFor(`document.querySelector('[data-testid=practice-day]')?.dataset.state === 'ready'`, 10000, 5);
  await sleep(300);
  const s2 = await p.sp(); note("reopened", { pos: pos(s2), sameAsAdvanced: pos(s2) === pos(s1) });
  await sleep(8000); // 5초 주기 저장 한 번 이상
  const s3 = await p.sp(); note("after8s", pos(s3));
  const posts = p.post(/progress/).map((r) => ({ dt: r.t - tr, body: JSON.parse(r.body) }));
  const adv = s1; const advUnit = Number(adv.unit.match(/Unit (\d+)/)[1]); const advIdx = Number(adv.num.match(/Sentence (\d+)/)[1]) - 1;
  const older = posts.filter((x) => !(x.body.unit === advUnit && x.body.sentence_index === advIdx));
  note("posts", { all: posts.map((x) => [x.dt, x.body.unit, x.body.sentence_index, x.body.position_sec]), olderWrites: older.length, reqOrder: p.reqs.map((r) => [r.t - tr, r.m, r.u]) });
  note("held", held.map((h) => h.released ? ["released", h.released - tr] : ["held", h.t - tr, h.body]));
  await p.mouse("practice-close"); await sleep(1500 + HOLD);
  note("savedEnd", (await api("/api/course")).body.days.find((d) => d.day === day).progress);
} catch (e) { note("ERROR", String(e?.stack ?? e).slice(0, 800)); }
finally { note("logs", p.logs.filter((l) => !/DevTools|HMR|Download the React|Fast Refresh|503/.test(l.text))); save(); p.c.close(); }
