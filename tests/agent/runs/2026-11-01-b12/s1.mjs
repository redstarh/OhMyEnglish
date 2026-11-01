// 회차 b12 — 시나리오 1(홈 대기) · 2 앞부분(열기·대조) · 3(영상 위치 보존). 사용: node s1.mjs <label> [width]
import { page, APP, sleep, api, dayProgress } from "./h.mjs";
import { saver } from "./lib.mjs";
const label = process.argv[2], width = Number(process.argv[3] ?? 1400);
const { note, save } = saver(`S1-${label}`);
const p = await page({ width });
try {
  const course0 = (await api("/api/course")).body;
  const cd = course0.current_day; const cur = course0.days.find((d) => d.day === cd);
  note("course0", { cycle: course0.cycle, current_day: cd, cur });
  const detail = (await api(`/api/course/days/${cd}`)).body;
  const pu = detail.progress; const ui = Math.max(0, detail.units.findIndex((u) => u.unit === pu?.unit)); const si = pu?.sentence_index ?? 0;
  const expect = (u, s) => ({ unit: `Unit ${detail.units[u].unit} · ${detail.units[u].topic}`, num: `Sentence ${s + 1} / ${detail.units[u].sentences.length}`, sentence: detail.units[u].sentences[s].text });
  note("expectAtSaved", expect(ui, si));

  await p.nav(`${APP}/`); await p.waitFor(p.hydrated("start-session"), 20000); await sleep(2500);
  const idle = await p.sp(); note("idle", idle);
  note("idleHeroText", await p.ev(`document.querySelector('[data-testid=home-hero]').innerText`));
  note("idleChecks", {
    titleOk: idle.heroTitle === `Day ${cd}: listen and say it.`, dayOk: idle.heroDay === `Day ${cd} · Units ${cur.first_unit}–${cur.last_unit}`,
    coachWords: await p.ev(`[...document.querySelectorAll('[data-testid=home-hero] *')].filter(e => /coach|recommend/i.test(e.textContent) && !e.children.length).map(e => e.textContent)`),
    recommendedTestids: await p.ev(`[...document.querySelectorAll('[data-testid]')].map(e => e.dataset.testid).filter(t => /recommend|home-hero-reason|home-level/.test(t))`),
    nextPlanReq: p.reqs.filter((r) => /next-plan/.test(r.u)).length, homeReqs: [...new Set(p.reqs.map((r) => r.m + " " + r.u))],
  });
  const idleBoxes = await p.boxes(); note("idleBoxes", idleBoxes);
  await p.shot(`S1-${label}-idle`);

  // 열기
  p.reqs = []; p.sockets = [];
  await p.mouse("start-session");
  await p.waitFor(`document.querySelector('[data-testid=practice-day]')?.dataset.state === 'ready'`, 10000);
  await sleep(1200);
  const opened = await p.sp(); note("opened", opened);
  note("openedChecks", { dayLine: opened.practiceDay === `Day ${cd} · Units ${cur.first_unit}–${cur.last_unit}`, ...Object.fromEntries(Object.entries(expect(ui, si)).map(([k, v]) => [k, opened[k] === v])),
    iframesInPage: opened.iframes, sockets: p.sockets, reqs: p.reqs.map((r) => r.m + " " + r.u) });
  note("practiceBoxes", await p.boxes()); note("overflowPractice", await p.overflowX()); note("heroTopAfterOpen", await p.ev(`Math.round(document.querySelector('[data-testid=home-hero]').getBoundingClientRect().top)`));
  await p.shot(`S1-${label}-practice`);

  // 시나리오 3: 다음 문장 2번 → 이전 1번 → 닫기. 영상 위치는 그대로, 문장 번호만 바뀌어야 함
  p.reqs = [];
  await p.mouse("course-mode-manual"); await sleep(300);
  await p.mouse("course-next"); await sleep(600); note("next1", (await p.sp()).num);
  await p.mouse("course-next"); await sleep(600); note("next2", (await p.sp()).num);
  await p.mouse("course-prev"); await sleep(600); const moved = await p.sp(); note("prev1", { num: moved.num, unit: moved.unit });
  await p.mouse("practice-close"); await sleep(1500);
  note("afterClose", await p.sp());
  note("progressPosts", p.post(/progress/));
  const after = await dayProgress(cd); note("progressAfterClose", after);
  note("s3Checks", { positionKept: after.position_sec === cur.progress?.position_sec, before: cur.progress, after });
  note("closedBoxes", await p.boxes());

  // 코스 Day 화면이 홈에서 옮긴 자리에서 시작하는가
  p.reqs = [];
  await p.nav(`${APP}/course/${cd}`); await p.waitFor(p.hydrated("course-start"), 20000); await sleep(1500);
  const dayPage = await p.sp();
  note("dayPage", { unit: dayPage.unit, num: dayPage.num, sentence: dayPage.sentence, iframes: dayPage.iframes, iframeSrc: await p.ev(`document.querySelector('iframe')?.src ?? null`) });
  note("dayPageMatchesHome", { unit: dayPage.unit === moved.unit, num: dayPage.num === moved.num });
} catch (e) { note("ERROR", String(e?.stack ?? e).slice(0, 800)); }
finally { note("logs", p.logs.filter((l) => !/DevTools|HMR|Download the React|Fast Refresh/.test(l.text))); save(); p.c.close(); }
