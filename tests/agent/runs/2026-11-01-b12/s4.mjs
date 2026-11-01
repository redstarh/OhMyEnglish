// 회차 b12 — 시나리오 4: 코스 Day 화면 회귀(영상 + 문장 연습). 사용: node s4.mjs <label> <day>
import { page, APP, sleep, dayProgress, yt, VID } from "./h.mjs";
import { saver } from "./lib.mjs";
const label = process.argv[2], day = Number(process.argv[3] ?? 3);
const { note, save } = saver(`S4-${label}`);
const p = await page({ width: 1400 });
// 영상 재생 — 사람처럼 iframe 가운데를 누름(이미 재생 중이면 누르지 않음)
const play = async () => { const v = await vid(); if (v?.mode === "playing" || (v && !v.paused && v.t > 0 && v.mode !== "unstarted")) return "already";
  const pt = await p.ev(`(() => { const f = document.querySelector('iframe'); f.scrollIntoView({ block: 'center' }); const r = f.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; })()`);
  for (const type of ["mousePressed", "mouseReleased"]) await p.c.send("Input.dispatchMouseEvent", { type, x: pt[0], y: pt[1], button: "left", clickCount: 1 }); return "clicked"; };
const vid = async () => { for (let i = 0; i < 20; i++) { const v = await yt(VID).catch((e) => ({ error: String(e) })); if (v && !v.error) return v; await sleep(500); } return null; };
try {
  const s0 = await dayProgress(day); note("saved0", s0);
  await p.nav(`${APP}/course/${day}`); await p.waitFor(p.hydrated("course-start"), 20000); await sleep(3000);
  const o = await p.sp(); note("open", { unit: o.unit, num: o.num, iframes: o.iframes, sp: o.sp, iframeSrc: (await p.ev(`document.querySelector('iframe')?.src ?? ''`)).split("&")[0] });
  note("videoAtOpen", await vid());
  await p.mouse("course-mode-manual"); await sleep(300);

  // 영상 재생 → 연습 시작 → 영상이 멈춰야 함
  note("play1", await play()); await sleep(4000);
  const v1 = await vid(); note("videoPlaying", v1);
  await p.mouse("course-start"); await sleep(1200);
  const v2 = await vid(); note("afterPracticeStart", { video: v2, phase: (await p.sp()).phase });
  // 연습이 도는 중에 영상 재생 → 연습이 멈춰야 함
  await p.mouse("course-retry"); await sleep(400);
  const ph0 = (await p.sp()).phase;
  const pl2 = await play(); await sleep(1500); note("play2", pl2);
  const s3 = await p.sp(); note("videoPlayDuringPractice", { phaseBefore: ph0, phaseAfter: s3.phase, start: s3.start, video: await vid() });

  // 영상이 지나는 단원 따라가기 — 연습을 다른 단원으로 옮김
  const u0 = s3.unit; let n = 0;
  while (n < 40 && (await p.sp()).unit === u0) { await p.mouse("course-next"); await sleep(120); n++; }
  await sleep(6500); // 5초 주기로 영상 단원을 읽음
  const s4 = await p.sp(); note("followShown", { practiceUnit: s4.unit, follow: s4.follow, video: await vid() });
  if (s4.follow) {
    const pt = await p.ev(`(() => { const b = [...document.querySelectorAll('button')].find(b => /where the video is/.test(b.textContent)); b.scrollIntoView({ block: 'center' }); const r = b.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; })()`);
    for (const type of ["mousePressed", "mouseReleased"]) await p.c.send("Input.dispatchMouseEvent", { type, x: pt[0], y: pt[1], button: "left", clickCount: 1 });
    await sleep(800); const s5 = await p.sp(); note("followClicked", { unit: s5.unit, num: s5.num, follow: s5.follow });
  }

  // 떠날 때 위치 저장(b5 D3 절차) — 12초 더 재생 → 앱 안 링크(← Back)
  await sleep(12000);
  const vLast = await vid(); p.reqs = [];
  await p.mouse("course-back"); await sleep(2500);
  const saved = await dayProgress(day);
  note("leaveSave", { videoJustBefore: vLast, path: await p.ev("location.pathname"), posts: p.post(/progress/).map((r) => r.body), saved, diff: vLast ? Math.round((vLast.t - Number(saved.position_sec)) * 100) / 100 : null });

  // 다시 열어 Finish Day
  await p.nav(`${APP}/course/${day}`); await p.waitFor(p.hydrated("course-start"), 20000); await sleep(2500);
  await p.mouse("course-mode-manual"); await sleep(200);
  n = 0; while (n < 150 && (await p.ev(`!document.querySelector('[data-testid=course-finish]')`))) { await p.mouse("course-next"); await sleep(100); n++; }
  const before = await dayProgress(day);
  await p.mouse("course-start"); const seen = await p.phases(15000, (s) => s[0] === "done");
  const fin0 = (await p.sp()).finish;
  await p.mouse("course-finish"); await sleep(2500);
  const f = await p.sp(); const after = await dayProgress(day);
  note("finish", { nexts: n, seen, finishBefore: fin0, notice: f.notice, unit: f.unit, num: f.num, before, after, delta: after.completed_count - before.completed_count, video: await vid() });
  await sleep(6000); note("afterFinish6s", { saved: await dayProgress(day), video: await vid() });
  await p.mouse("course-back"); await sleep(1500); note("afterBack", { path: await p.ev("location.pathname"), saved: await dayProgress(day) });
} catch (e) { note("ERROR", String(e?.stack ?? e).slice(0, 800)); }
finally { note("logs", p.logs.filter((l) => !/DevTools|HMR|Download the React|Fast Refresh/.test(l.text))); save(); p.c.close(); }
